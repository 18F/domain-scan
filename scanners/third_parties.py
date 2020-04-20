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
            url = 'https://' + domain
    else:
        url = domain

    # Standardize by ending with a /.
    url = url + "/"

    return {'url': url}


# Gets the return value of scan(), convert to a CSV row.
def to_rows(data):

    return [[
        data['url'],
        len(data['external_domains']),
        str.join(" | ", data['external_domains']),
        str.join(" | ", data['external_urls']),
        str.join(" | ", data['nearby_domains']),
        str.join(" | ", data['nearby_urls']),
        str.join(" | ", data['known_services']),
        str.join(" | ", data['unknown_services']),
        str.join(" | ", data['page_urls']),
        str.join(" | ", data['page_domains'])
    ]]


headers = [
    'Scanned URL',
    'Number of External Domains',
    'External Domains',
    'External URLs',
    'Nearby Domains',
    'Nearby URLs',
    'Known Services',
    'Unknown Services',
    'URLs on the page',
    'Domains in the URLs on the page'
]
