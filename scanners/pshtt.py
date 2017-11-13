import logging

import re
from pshtt import pshtt

###
# Measure a site's HTTP behavior using DHS NCATS' pshtt tool.

# Network timeout for each internal pshtt HTTP request.
pshtt_timeout = 20

# default to a custom user agent, can be overridden
user_agent = "github.com/18f/domain-scan, pshtt.py"

# Keep here to get some best-effort container reuse in Lambda.
suffix_list = None


# Download third party data once, at the top of the scan.
def init(environment, options):
    logging.warn("[pshtt] Downloading third party data...")
    return {
        'preload_list': pshtt.load_preload_list(),
        'preload_pending': pshtt.load_preload_pending()
    }


# To save on bandwidth to Lambda, slice the preload and pending
# lists down to an array of just the value, if it exists.
# Override the list in place, which should only modify it per-scan.
def init_domain(domain, environment, options):
    if domain in environment.get("preload_list", []):
        environment["preload_list"] = [domain]
    else:
        environment["preload_list"] = []

    if domain in environment.get("preload_pending", []):
        environment["preload_pending"] = [domain]
    else:
        environment["preload_pending"] = []

    return environment


# Run locally or in the cloud.
# Gets third-party data passed into the environment.
def scan(domain, environment, options):
    global suffix_list

    domain = format_domain(domain)

    # Always pull suffix list from network, but try to benefit
    # from container re-use.
    if suffix_list is None:
        logging.warn("\tDownloading public suffix list.")
        suffix_list, content = pshtt.load_suffix_list()

    # If these aren't loaded (e.g. a Lambda test function),
    # then this will pull the third parties from the network.
    pshtt.initialize_external_data(
        init_preload_list=environment.get('preload_list'),
        init_preload_pending=environment.get('preload_pending'),
        init_suffix_list=suffix_list
    )

    results = pshtt.inspect_domains(
        [domain],
        {
            'timeout': pshtt_timeout,
            'user_agent': user_agent
        }
    )

    # Actually triggers the work.
    results = list(results)

    # pshtt returns array of results, but we always send in 1.
    return results[0]


# Given a response from pshtt, convert it to a CSV row.
def to_rows(data):
    row = []
    for field in headers:
        value = data[field]

        # TODO: Fix this upstream
        if (field != "HSTS Header") and (field != "HSTS Max Age") and (field != "Redirect To"):
            if value is None:
                value = False

        row.append(value)

    return [row]


headers = [
    "Canonical URL", "Live", "Redirect", "Redirect To",
    "Valid HTTPS", "Defaults to HTTPS", "Downgrades HTTPS",
    "Strictly Forces HTTPS", "HTTPS Bad Chain", "HTTPS Bad Hostname",
    "HTTPS Expired Cert", "HTTPS Self Signed Cert",
    "HSTS", "HSTS Header", "HSTS Max Age", "HSTS Entire Domain",
    "HSTS Preload Ready", "HSTS Preload Pending", "HSTS Preloaded",
    "Base Domain HSTS Preloaded", "Domain Supports HTTPS",
    "Domain Enforces HTTPS", "Domain Uses Strong HSTS", "Unknown Error",
]


def format_domain(domain):
    return re.sub("^(https?://)?(www\.)?", "", domain)
