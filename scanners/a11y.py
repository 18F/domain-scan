import logging
from scanners import utils
import json
import os
import boto3

workers = 25
PA11Y_STANDARD = 'WCAG2AA'
pa11y = os.environ.get("PA11Y_PATH", "pa11y")
headers = [
    "redirectedTo",
    "typeCode",
    "code",
    "message",
    "context",
    "selector"
]

def get_from_inspect_cache(domain):
    inspect_cache = utils.cache_path(domain, "inspect")
    inspect_raw = open(inspect_cache).read()
    inspect_data = json.loads(inspect_raw)
    return inspect_data

def get_domain_to_scan(inspect_data, domain):
    domain_to_scan = None
    redirect = inspect_data.get('redirect', None)
    if redirect:
        domain_to_scan = inspect_data.get('redirect_to')
    else:
        domain_to_scan = domain
    return domain_to_scan

def get_a11y_cache(domain):
    return utils.cache_path(domain, "a11y")

def domain_is_cached(cache):
    return os.path.exists(cache)

def cache_is_not_forced(options):
    return options.get("force", False) is False

def get_errors_from_pa11y_lambda_scan(domain, cache):
    client = boto3.client(
        'lambda',
        aws_access_key_id=os.environ['AWS_ACCESS_KEY_ID'],
        aws_secret_access_key=os.environ['AWS_SECRET_ACCESS_KEY'],
        region_name=os.environ['AWS_REGION_NAME']
    )

    lambda_options = {
        'url': domain,
        'pa11yOptions': {
            'standard': 'WCAG2AA',
            'wait': 500,
            'ignore': [
                'notice',
                'warning',
                'WCAG2AA.Principle1.Guideline1_4.1_4_3.G18.BgImage',
                'WCAG2AA.Principle1.Guideline1_4.1_4_3.G18.Abs',
                'WCAG2AA.Principle1.Guideline1_4.1_4_3.G145.Abs',
                'WCAG2AA.Principle3.Guideline3_1.3_1_1.H57.2',
                'WCAG2AA.Principle3.Guideline3_1.3_1_1.H57.3',
                'WCAG2AA.Principle3.Guideline3_1.3_1_2.H58.1',
                'WCAG2AA.Principle4.Guideline4_1.4_1_1.F77',
                'WCAG2AA.Principle4.Guideline4_1.4_1_2.H91'
            ]
        }
    }

    payload = json.dumps(lambda_options).encode()

    response = client.invoke(
        FunctionName=os.environ['AWS_LAMBDA_PA11Y_FUNCTION_NAME'],
        Payload=payload,
    )

    response_payload_bytes = response['Payload'].read()
    response_payload_string = response_payload_bytes.decode('UTF-8')
    response_payload_json = json.loads(response_payload_string)

    logging.debug("Invoking a11y_lambda function: %s" % lambda_options)

    results = response_payload_json
    errors = get_errors_from_results(results)
    cachable = json.dumps({'results' : errors})
    logging.debug("Writing to cache: %s" % domain)
    content = cachable
    destination = cache
    utils.write(content, destination)
    return errors

def get_errors_from_results(results):
    errors = []
    for result in results:
        if result['type'] == 'error':
            errors.append(result)
    return errors

def get_errors_from_scan_or_cache(domain, options):
    a11y_cache = get_a11y_cache(domain)
    the_domain_is_cached = domain_is_cached(a11y_cache)
    the_cache_is_not_forced = cache_is_not_forced(options)
    logging.debug("the_domain_is_cached: %s" % the_domain_is_cached)
    logging.debug("the_cache_is_not_forced: %s" % the_cache_is_not_forced)

    # the_domain_is_cached: True
    # the_cache_is_not_forced: False
    if the_domain_is_cached and the_cache_is_not_forced:
        logging.debug("\tCached.")
        raw = open(a11y_cache).read()
        data = json.loads(raw)
        if data.get('invalid'):
            return []
        else:
            logging.debug("Getting from cache: %s" % domain)
            results = data.get('results')
            errors = get_errors_from_results(results)
            return errors
    else:
        logging.debug("\tNot cached.")
        errors = get_errors_from_pa11y_lambda_scan(domain, a11y_cache)
        return errors


def scan(domain, options):
    logging.debug("[%s]=[a11y]" % domain)

    inspect_data = get_from_inspect_cache(domain)
    domain_to_scan = get_domain_to_scan(inspect_data, domain)
    errors = get_errors_from_scan_or_cache(domain_to_scan, options)

    for data in errors:
        logging.debug("Writing data for %s" % domain)
        yield [
            domain_to_scan,
            data['typeCode'],
            data['code'],
            data['message'],
            data['context'],
            data['selector']
        ]
