import json
import logging
import os
import requests
import yaml

from scanners import utils


workers = 3
pa11y = os.environ.get("PA11Y_PATH", "pa11y")

redirects = {}
config = ""


def init(environment, options):
    global redirects
    global config

    redirects_file = options.get("a11y_redirects")
    config_file = options.get("a11y_config")

    # Parse redirects
    if redirects_file:
        if not redirects_file.endswith(".yml"):
            logging.error("--a11y_redirects should be a YML file")
            return False

        # if remote, try to download
        if redirects_file.startswith("http:") or redirects_file.startswith("https:"):
            redirects_path = os.path.join(utils.cache_dir(), "a11y_redirects.yml")

            try:
                response = requests.get(redirects_file)
                utils.write(response.text, redirects_path)
            except:
                logging.error("--a11y_redirects URL not downloaded successfully.")
                return False

        # Otherwise, read it off the disk
        else:
            redirects_path = redirects_file

            if (not os.path.exists(redirects_path)):
                logging.error("--a11y_redirects file not found.")
                return False

        with open(redirects_path, 'r') as f:
            redirects = yaml.load(f)

    # Get config
    if config_file:
        if not config_file.endswith(".json"):
            logging.error("--a11y_config should be a json file")
            return False

        # if remote, try to download
        if config_file.startswith("http:") or config_file.startswith("https:"):
            config_path = os.path.join(utils.cache_dir(), "a11y_config.json")

            try:
                response = requests.get(config_file)
                utils.write(response.text, config_path)
            except:
                logging.error("--a11y_config URL not downloaded successfully.")
                return False

        config = config_path
    return True


# If we have pshtt data, use it to skip some domains. If redirect
# data says so, adjust scan URL for some domains.
def init_domain(domain, environment, options):
    # If we've got pshtt data, use it to cut down work.
    if (
        utils.domain_is_redirect(domain) or
        utils.domain_not_live(domain)
    ):
        logging.debug("\tSkipping a11y scan based on pshtt data.")
        return False

    # Use redirect/blacklist data to adjust (or stop) scan URL.
    url = get_url_to_scan(domain)

    if not url:
        logging.debug("\tSkipping a11y scan based on redirect/blacklist data.")
        return False

    # Send adjusted URL to scan function.
    return {'url': url}


# Shell out to a11y and run the scan.
def scan(domain, environment, options):
    url = environment.get("url", domain)

    errors = run_a11y_scan(url)

    return {
        'url': url,
        'errors': errors
    }


def to_rows(data):
    rows = []

    for error in data['errors']:
        rows.append([
            data['url'],
            error['typeCode'],
            error['code'],
            error['message'],
            error['context'],
            error['selector']
        ])

    return rows


headers = [
    "redirectedTo",
    "typeCode",
    "code",
    "message",
    "context",
    "selector"
]


def run_a11y_scan(domain):
    command = [pa11y, domain, "--reporter", "json", "--level", "none", "--timeout", "300000"]

    if config:
        command += ["--config", config]

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

    return results


def get_url_to_scan(domain):
    global redirects

    url_to_scan = None

    # Redirects can be blacklists or redirects.
    if domain in redirects:
        # blacklist will force a domain to be skipped
        if redirects[domain]['blacklist']:
            url_to_scan = None
        # otherwise, scan will be redirected to new location
        else:
            url_to_scan = redirects[domain]['redirect']

    # Otherwise, leave domain alone.
    else:
        url_to_scan = domain

    return url_to_scan
