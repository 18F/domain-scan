import logging
import requests
from domain_scan.scanners import utils

###
# CSP Scanner - check the presence of CSP headers
#


# Set a default number of workers for a particular scan type.
# Overridden by a --workers flag.
workers = 2


# default to a custom user agent, can be overridden
user_agent = "github.com/18f/domain-scan, csp.py"


def init_domain(domain, environment, options):
    cache_dir = options.get("_", {}).get("cache_dir", "./cache")
    # If we have data from pshtt, skip if it's not a live domain.
    if utils.domain_not_live(domain, cache_dir=cache_dir):
        logging.debug("\tSkipping, domain not reachable during inspection.")
        return False

    # If we have data from pshtt, skip if it's just a redirector.
    if utils.domain_is_redirect(domain, cache_dir=cache_dir):
        logging.debug("\tSkipping, domain seen as just an external redirector during inspection.")
        return False

    # requests needs a URL, not just a domain.
    url = None
    if not (domain.startswith('http://') or domain.startswith('https://')):

        # If we have data from pshtt, use the canonical endpoint.
        if utils.domain_canonical(domain, cache_dir=cache_dir):
            url = utils.domain_canonical(domain, cache_dir=cache_dir)

        # Otherwise, well, ssl should work.
        else:
            url = 'https://' + domain
    else:
        url = domain

    return {'url': url}


def scan(domain, environment, options):
    logging.debug("CSP Check called with options: %s" % options)
    url = environment.get("url", domain)
    logging.debug("URL: %s", url)
    response = requests.get(url)
    csp_set = False
    if "content-security-policy" in response.headers:
        csp_set = True
    logging.warn("Complete!")
    return {
        'csp_set': csp_set
    }


# Required CSV row conversion function. Usually one row, can be more.
#
# Run locally.
def to_rows(data):
    return [
        [data['csp_set']]
    ]


# CSV headers for each row of data. Referenced locally.
headers = ["CSP Set for domain"]
