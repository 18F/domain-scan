import logging
from scanners import utils
import json
import os


##
# == inspect ==
#
# Evaluate HTTP/HTTPS/HSTS configuration using site-inspector.
##


command = os.environ.get("SITE_INSPECTOR_PATH", "site-inspector")
init = None


def scan(domain, options):
    logging.debug("[%s][inspect]" % domain)

    # cache JSON as it comes back from site-inspector
    cache = utils.cache_path(domain, "inspect")
    if (options.get("force", False) is False) and (os.path.exists(cache)):
        logging.debug("\tCached.")
        raw = open(cache).read()
        data = json.loads(raw)
        if data.get('invalid'):
            return None

    else:
        logging.debug("\t %s %s --http" % (command, domain))
        raw = utils.scan([command, domain, "--http"])
        if not raw:
            utils.write(utils.invalid({}), cache)
            return None
        utils.write(raw, cache)
        data = json.loads(raw)

    # TODO: get this from a site-inspector field directly
    canonical_https = data['endpoints']['https'][data['canonical_endpoint']]
    # TODO: guarantee these as present in site-inspector
    https_valid = canonical_https.get('https_valid', False)
    https_bad_chain = canonical_https.get('https_bad_chain', False)
    https_bad_name = canonical_https.get('https_bad_name', False)

    yield [
        data['canonical'], data['up'],
        data['redirect'], data['redirect_to'],
        https_valid, data['default_https'], data['downgrade_https'],
        data['enforce_https'],
        https_bad_chain, https_bad_name,
        data['hsts'], data['hsts_header'], data['hsts_entire_domain'],
        data['hsts_entire_domain_preload'],
        data['broken_root'], data['broken_www']
    ]

headers = [
    "Canonical", "Live",
    "Redirect", "Redirect To",
    "Valid HTTPS", "Defaults to HTTPS",
    "Downgrades HTTPS", "Strictly Forces HTTPS",
    "HTTPS Bad Chain", "HTTPS Bad Hostname",
    "HSTS", "HSTS Header", "HSTS All Subdomains", "HSTS Preload Ready",
    "Broken Root", "Broken WWW"
]
