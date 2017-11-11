from scanners import utils
import logging

import re
from pshtt import pshtt

###
# Measure a site's HTTP behavior using DHS NCATS' pshtt tool.

# Network timeout for each internal pshtt HTTP request.
pshtt_timeout = 20

# default to a custom user agent, can be overridden
user_agent = "github.com/18f/domain-scan, pshtt.py"


# Download third party data once, at the top of the scan.
def init(environment, options):
    logging.warn("[pshtt] Downloading third party data...")
    return {
        'preload_list': pshtt.load_preload_list(),
        'preload_pending': pshtt.load_preload_pending(),
        'suffix_list': pshtt.load_suffix_list()
    }


# Run locally or in the cloud.
# Gets third-party data passed into the environment.
def scan(domain, environment, options):

    domain = format_domain(domain)

    # If these aren't loaded (e.g. a Lambda test function),
    # then this will pull the third parties from the network.
    pshtt.initialize_external_data(
        environment.get('preload_list'),
        environment.get('preload_pending'),
        environment.get('suffix_list')
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



# cache_pshtt = utils.cache_path(domain, "pshtt", ext="json")
    # if (force is False) and (os.path.exists(cache_pshtt)):
    #     logging.debug("\tCached.")
    #     raw = utils.read(cache_pshtt)
    #     data = json.loads(raw)
    #     if (data.__class__ is dict) and data.get('invalid'):
    #         return None


    # if not results:
    #     utils.write(utils.invalid({}), cache_pshtt)
    #     logging.warn("\tBad news scanning, sorry!")
    #     return None

    # data = json.loads(raw)
    # utils.write(utils.json_for(data), utils.cache_path(domain, "pshtt"))


#     if os.path.exists(third_parties_cache):
#         logging.warn("Clearing cached third party pshtt data before scanning.")
#         for path in glob.glob(os.path.join(third_parties_cache, "*")):
#             os.remove(path)
#         os.rmdir(third_parties_cache)


# To save on bandwidth to Lambda, slice the preload and pending
# lists down to an array of just the value, if it exists.
# Override the list in place, which should only modify it per-scan.
# def init_domain(domain, environment, options):
#     environment['preload_list'] = [value for value in ]
