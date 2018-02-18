import logging
import json
import os
import re

from utils import utils
from utils.known_services import known_services

# Evaluate third party service usage using Chrome headless.
#
# If data exists for a domain from `pshtt`, it:
# * will not run if the domain is used only to redirect externally
# * otherwise, will run using the "canonical" URL.
#
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

# Advertise Lambda support
lambda_support = True

# Advertise use of headless Chrome
headless = True


def init_domain(domain, environment, options):
    # If we have data from pshtt, skip if it's not a live domain.
    if utils.domain_not_live(domain):
        logging.debug("\tSkipping, domain not reachable during inspection.")
        return False

    # If we have data from pshtt, skip if it's just a redirector.
    if utils.domain_is_redirect(domain):
        logging.debug("\tSkipping, domain seen as just an external redirector during inspection.")
        return False

    # To scan, we need a URL, not just a domain.
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


# Pass-through to the local JS handler.
def scan(domain, environment, options):

    # TODO: move this into the central scan orchestrator
    # for scanners where its `headless` attribute is True?
    raw = utils.scan(
        [
            "./scanners/headless/third_parties.js",
            utils.json_for({
                'domain': domain,
                'environment': environment,
                'options': options
            })
        ]
    )

    logging.warn(raw)
    return None

    if not raw:
        logging.warn("\tError calling out to third_parties.js, skipping.")
        return None

    return utils.from_json(raw)


# Gets the return value of scan(), convert to a CSV row.
def to_rows(data):

    # services_for(url, data, domain, options)

    return [[
        services['url'], len(services['external'])
    ]]


# Given a response from the script we gave to Chrome headless,
def services_for(url, data, domain, options):
    services = {
        'url': url,
        'external': list(known_services.keys())
    }
    return services

# known service names from a standard mapping
service_names = list(known_services.keys())
service_names.sort()

headers = [
    'Scanned URL',
    'Number of External Domains',
    'Number of External URLs',
    'External Domains',
    'External URLs'
] + service_names
