import logging

from utils import utils

# Evaluate third party service usage using Chrome headless.

# Can also be run in Lambda.
lambda_support = True

# Signal that this is a JS-based scan using headless Chrome.
# The scan method will be defined in third_parties.js instead.
scan_headless = True


# Use pshtt data if we have it, to either skip redirect/inactive
# domains, or to start with the canonical URL right away.
def init_domain(domain, environment, options):
    cache_dir = options.get("_", {}).get("cache_dir", "./cache")
    # If we have data from pshtt, skip if it's not a live domain.
    if utils.domain_not_live(domain):
        logging.debug("\tSkipping, domain not reachable during inspection.")
        return False

    # If we have data from pshtt, skip if it's just a redirector.
    if utils.domain_is_redirect(domain, cache_dir=cache_dir):
        logging.debug("\tSkipping, domain seen as just an external redirector during inspection.")
        return False

    # To scan, we need a URL, not just a domain.
    url = None
    if not (domain.startswith('http://') or domain.startswith('https://')):

        # If we have data from pshtt, use the canonical endpoint.
        if utils.domain_canonical(domain, cache_dir=cache_dir):
            url = utils.domain_canonical(domain, cache_dir=cache_dir)

        # Otherwise, well, whatever.
        else:
            url = 'http://' + domain
    else:
        url = domain

    # Standardize by ending with a /.
    url = url + "/"

    return {'url': url}


# Gets the return value of scan(), convert to a CSV row.
def to_rows(data):

    return [[
        data['url'],
        data.get('present'),
        data.get('banner_bad_text'),
    ]]


headers = [
    'Scanned URL',
    'USWDS Present',
    'USWDS Bad Banner Text'
]
