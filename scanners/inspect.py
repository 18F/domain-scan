import logging
from scanners import utils
import json
import os
import urllib.request
import base64
import re

##
# == inspect ==
#
# Evaluate HTTP/HTTPS/HSTS configuration using site-inspector.
##


command = os.environ.get("SITE_INSPECTOR_PATH", "site-inspector")

chrome_preload_list = None


def get_chrome_preload_list(options):

    preload_cache = utils.cache_single("preload-list.json")
    preload_json = None

    if (not options.get("force", False)) and os.path.exists(preload_cache):
        logging.debug("Using cached Chrome preload list.")
        preload_json = json.loads(open(preload_cache).read())
    else:
        logging.debug("Fetching Chrome preload list from source...")

        preload_list_url = 'https://chromium.googlesource.com/chromium/src/net/+/master/http/transport_security_state_static.json'
        preload_list_url_as_text = preload_list_url + '?format=text'
        with urllib.request.urlopen(preload_list_url_as_text) as response:
            raw = response.read()

        # To avoid parsing the contents of the file out of the source tree viewer's
        # HTML, we download it as a raw file. googlesource.com Base64-encodes the
        # file to avoid potential content injection issues, so we need to decode it
        # before using it. https://code.google.com/p/gitiles/issues/detail?id=7
        raw = base64.b64decode(raw).decode('utf-8')

        # The .json file contains '//' comments, which are not actually valid JSON,
        # and confuse Python's JSON decoder. Begone, foul comments!
        raw = ''.join([re.sub(r'^\s*//.*$', '', line)
                       for line in raw.splitlines()])

        preload_json = json.loads(raw)
        utils.write(utils.json_for(preload_json), preload_cache)

    return {entry['name'] for entry in preload_json['entries']}


def init(options):
    """
    Download the Chrome preload list at the beginning of the scan, and
    re-use it for each scan. It is unnecessary to re-download the list for each
    scan because it changes infrequently.
    """
    global chrome_preload_list
    chrome_preload_list = get_chrome_preload_list(options)
    return True


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
    # TODO: site-inspector should float this up
    hsts_details = canonical_https.get('hsts_details', {})
    max_age = hsts_details.get('max_age', None)

    yield [
        data['canonical'], data['up'],
        data['redirect'], data['redirect_to'],
        https_valid, data['default_https'], data['downgrade_https'],
        data['enforce_https'],
        https_bad_chain, https_bad_name,
        data['hsts'], data['hsts_header'],
        max_age,
        data['hsts_entire_domain'],
        data['hsts_entire_domain_preload'],
        domain in chrome_preload_list,
        data['broken_root'], data['broken_www']
    ]

headers = [
    "Canonical", "Live",
    "Redirect", "Redirect To",
    "Valid HTTPS", "Defaults to HTTPS",
    "Downgrades HTTPS", "Strictly Forces HTTPS",
    "HTTPS Bad Chain", "HTTPS Bad Hostname",
    "HSTS", "HSTS Header", "HSTS Max Age",
    "HSTS All Subdomains",
    "HSTS Preload Ready", "HSTS Preloaded",
    "Broken Root", "Broken WWW"
]
