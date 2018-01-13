import logging
import json
import os
import re

from utils import utils
from utils.known_services import known_services

# Evaluate third party service usage using Chrome headless.
#
# If data exists for a domain from `pshtt`, will:
# * not run if the domain just redirects externally
# * start with any detected (internal) redirect URL
#
# Options:
#
# * --timeout: Override default timeout of 60s.
# * --affiliated: A suffix (e.g. ".gov", "twimg.com") known to
#       be affiliated with the scanned domains.
#
# Looks for known, affiliated, and unknown services.

# Categories/Fields:
#
# * All external domains: All unique external domains that get pinged.
# * All subdomains: All unique subdomains that get pinged.
#
# * Affiliated domains: Service domains known to be affiliated.
# * Unknown domains: Any other external service domains.
#
# * [Known Service]: True / False


command = os.environ.get("CHROME_PATH", "echo")

default_timeout = 60


# Advertise Lambda support
lambda_support = True


def init_domain(domain, environment, options):
    # If we have data from pshtt, skip if it's not a live domain.
    if utils.domain_not_live(domain):
        logging.debug("\tSkipping, domain not reachable during inspection.")
        return False

    # If we have data from pshtt, skip if it's just a redirector.
    if utils.domain_is_redirect(domain):
        logging.debug("\tSkipping, domain seen as just an external redirector during inspection.")
        return False

    # phantomas needs a URL, not just a domain.
    url = None
    if not (domain.startswith('http://') or domain.startswith('https://')):

        # If we have data from pshtt, use the canonical endpoint.
        if utils.domain_canonical(domain):
            url = utils.domain_canonical(domain)

        # Otherwise, well, whatever.
        else:
            url = 'http://' + domain
    else:
        url = domain

    return {'url': url}


def scan(domain, environment, options):
    timeout = int(options.get("timeout", default_timeout))

    url = environment["url"]

    raw = utils.scan(
        [
            command,
            url
        ],
        allowed_return_codes=[252]
    )

    if not raw:
        logging.warn("\tError with the phantomas command, skipping.")
        return None

    # TODO: this is just 'echo' for now
    data = raw

    return services_for(url, data, domain, options)


# Gets the return value of scan(), convert to a CSV row.
def to_rows(services):
    return [[
        services['url'], len(services['external'])
    ]]


headers = [
    'Scanned URL',
    'Number of External Domains'
]


# Given a response from the script we gave to Chrome headless,
def services_for(url, data, domain, options):
    services = {
        'url': url,
        'external': []
    }
    return services

