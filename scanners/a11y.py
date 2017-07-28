import json
import logging
import os

import yaml

from scanners import utils


workers = 3
pa11y = os.environ.get("PA11Y_PATH", "pa11y")
headers = [
    "redirectedTo",
    "typeCode",
    "code",
    "message",
    "context",
    "selector"
]


def get_from_pshtt_cache(domain):
    pshtt_cache = utils.cache_path(domain, "pshtt")
    pshtt_raw = open(pshtt_cache).read()
    pshtt_data = json.loads(pshtt_raw)
    if type(pshtt_data) == list:
        pshtt_data = pshtt_data[0]
    return pshtt_data


def get_domain_to_scan(domain):
    domain_to_scan = None
    with open('config/a11y-redirects.yml', 'r') as f:
        redirects = yaml.load(f)
    if domain in redirects:
        if not redirects[domain]['blacklist']:
            domain_to_scan = redirects[domain]['redirect']
    else:
        domain_to_scan = domain

    return domain_to_scan


def get_a11y_cache(domain):
    return utils.cache_path(domain, "a11y")


def domain_is_cached(cache):
    return os.path.exists(cache)


def cache_is_not_forced(options):
    return options.get("force", False) is False


def cache_errors(errors, domain, cache):
    cachable = json.dumps({'results': errors})
    logging.debug("Writing to cache: %s" % domain)
    content = cachable
    destination = cache
    utils.write(content, destination)


def run_a11y_scan(domain, cache):
    logging.debug("[%s][a11y]" % domain)
    pa11y = os.environ.get("PA11Y_PATH", "pa11y")
    domain_to_scan = get_domain_to_scan(domain)
    command = [pa11y, domain_to_scan, "--reporter", "json", "--config", "config/pa11y_config.json", "--level", "none", "--timeout", "300000"]
    raw = utils.scan(command)
    if not raw or raw == '[]\n':
        results = [{
            'typeCode': '',
            'code': '',
            'message': '',
            'context': '',
            'selector': '',
            'type': ''
        }]
    else:
        results = json.loads(raw)

    cache_errors(results, domain, cache)

    return results


def get_errors_from_scan_or_cache(domain, options):
    a11y_cache = get_a11y_cache(domain)
    the_domain_is_cached = domain_is_cached(a11y_cache)
    the_cache_is_not_forced = cache_is_not_forced(options)
    logging.debug("the_domain_is_cached: %s" % the_domain_is_cached)
    logging.debug("the_cache_is_not_forced: %s" % the_cache_is_not_forced)

    # the_domain_is_cached: True
    # the_cache_is_not_forced: False
    results = []
    if the_domain_is_cached and the_cache_is_not_forced:
        logging.debug("\tCached.")
        raw = open(a11y_cache).read()
        data = json.loads(raw)
        if not data.get('invalid'):
            logging.debug("Getting from cache: %s" % domain)
            results = data.get('results')
    else:
        logging.debug("\tNot cached.")
        results = run_a11y_scan(domain, a11y_cache)
    return results


def scan(domain, options):
    logging.debug("[%s][a11y]" % domain)

    domain_to_scan = get_domain_to_scan(domain)
    if (utils.domain_is_redirect(domain) or
            utils.domain_not_live(domain) or
            not domain_to_scan):
        logging.debug("Skipping a11y scan for %s" % domain)
        return None
    logging.debug("Running scan for %s" % domain)
    errors = get_errors_from_scan_or_cache(domain, options)

    for data in errors:
        logging.debug("Writing data for %s" % domain)
        yield [
            domain,
            data['typeCode'],
            data['code'],
            data['message'],
            data['context'],
            data['selector']
        ]
