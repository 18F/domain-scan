import logging
from scanners import utils
import json
import os
import base64
import urllib.request
import re


###
# == tls ==
#
# Inspect a site's valid TLS configuration using ssllabs-scan.
#
# If data exists for a domain from `inspect`, will check results
# and only process domains with valid HTTPS, or broken chains.
###

command = os.environ.get("SSLLABS_PATH", "ssllabs-scan")
workers = 5

chrome_preload_list = None


def get_chrome_preload_list():
    logging.debug("Fetching chrome preload list...")

    preload_list_url = ('https://chromium.googlesource.com/chromium/src/net/+'
                        '/master/http/transport_security_state_static.json')
    with urllib.request.urlopen(preload_list_url + '?format=text') as response:
        raw = response.read()

    # To avoid parsing the contents of the file out of the source tree viewer's
    # HTML, we download it as a raw file. googlesource.com Base64-encodes the
    # file to avoid potential content injection issues, so we need to decode it
    # before using it. https://code.google.com/p/gitiles/issues/detail?id=7
    raw = base64.b64decode(raw).decode('utf-8')

    # The .json file contains '//' comments, which are not actually valid JSON,
    # and confuse Python's JSON decoder. Begone, foul comments!
    raw = ''.join([ re.sub(r'//.*$', '', line)
                    for line in raw.splitlines() ])

    preload_list_json = json.loads(raw)
    return { entry['name'] for entry in preload_list_json['entries'] }


def init(options):
    """
    Download the Chrome preload list at the beginning of the scan, and
    re-use it for each scan. It is unnecessary to re-download the list for each
    scan because it changes infrequently.
    """
    global chrome_preload_list
    chrome_preload_list = get_chrome_preload_list()
    return True


def scan(domain, options):
    logging.debug("[%s][tls]" % domain)

    # If inspection data exists, check to see if we can skip.
    inspection = utils.data_for(domain, "inspect")
    if inspection and (not inspection.get("support_https")):
        logging.debug("\tSkipping, HTTPS not supported in inspection.")
        yield None

    else:
        # cache reformatted JSON from ssllabs
        cache = utils.cache_path(domain, "tls")

        force = options.get("force", False)

        if (force is False) and (os.path.exists(cache)):
            logging.debug("\tCached.")
            raw = open(cache).read()
            data = json.loads(raw)

            if data.get('invalid'):
                return None
        else:
            logging.debug("\t %s %s" % (command, domain))

            usecache = str(not force).lower()

            if options.get("debug"):
                cmd = [command, "--usecache=%s" % usecache,
                       "--verbosity=debug", domain]
            else:
                cmd = [command, "--usecache=%s" % usecache,
                       "--quiet", domain]
            raw = utils.scan(cmd)
            if raw:
                data = json.loads(raw)

                # we only give ssllabs-scan one at a time,
                # so we can de-pluralize this
                data = data[0]

                # if SSL Labs had an error hitting the site, cache this
                # as an invalid entry.
                if data["status"] == "ERROR":
                    utils.write(utils.invalid(data), cache)
                    return None

                utils.write(utils.json_for(data), cache)
            else:
                return None
                # raise Exception("Invalid data from ssllabs-scan: %s" % raw)

        # can return multiple rows, one for each 'endpoint'
        for endpoint in data['endpoints']:

            # this meant it couldn't connect to the endpoint
            if not endpoint.get("grade"):
                continue

            sslv3 = False
            tlsv12 = False
            for protocol in endpoint['details']['protocols']:
                if ((protocol['name'] == "SSL") and
                        (protocol['version'] == '3.0')):
                    sslv3 = True
                if ((protocol['name'] == "TLS") and
                        (protocol['version'] == '1.2')):
                    tlsv12 = True

            spdy = False
            h2 = False
            npn = endpoint['details'].get('npnProtocols', None)
            if npn:
                spdy = ("spdy" in npn)
                h2 = ("h2-" in npn)

            yield [
                endpoint['grade'],
                endpoint['details']['cert']['sigAlg'],
                endpoint['details']['key']['alg'],
                endpoint['details']['key']['size'],
                endpoint['details']['forwardSecrecy'],
                endpoint['details']['ocspStapling'],
                endpoint['details'].get('fallbackScsv', "N/A"),
                endpoint['details']['supportsRc4'],
                sslv3,
                tlsv12,
                spdy,
                endpoint['details']['sniRequired'],
                h2,
                domain in chrome_preload_list,
            ]

headers = [
    "Grade",  # unique to SSL Labs
    "Signature Algorithm", "Key Type", "Key Size",  # strength
    "Forward Secrecy", "OCSP Stapling",  # privacy
    "Fallback SCSV",  # good things
    "RC4", "SSLv3",  # old things
    "TLSv1.2", "SPDY", "Requires SNI",  # forward
    "HTTP/2",  # ever forward
    "In Chrome Preload List"
]
