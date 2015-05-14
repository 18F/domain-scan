import logging
from scanners import utils
import json
import os


###
# == tls ==
#
# Inspect a site's valid TLS configuration using ssllabs-scan.
#
# If data exists for a domain from `inspect`, will check results
# and only process domains with valid HTTPS, or broken chains.
###


command = os.environ.get("SSLLABS_PATH", "ssllabs-scan")
init = None


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

            def ccs_map(n):
                return {
                    -1: "N/A (Error)",
                    0: "N/A (Unknown)",
                    1: "No (not vulnerable)",
                    2: "No (not exploitable)",
                    3: "Yes"
                }[n]

            def fs_map(n):
                return {
                    0: "0 - No",
                    1: "1 - Some",
                    2: "2 - Modern",
                    4: "3 - Robust"
                }[n]

            yield [
                endpoint['grade'],
                endpoint['details']['cert']['sigAlg'],
                endpoint['details']['key']['alg'],
                endpoint['details']['key']['size'],
                fs_map(endpoint['details']['forwardSecrecy']),
                endpoint['details']['ocspStapling'],
                endpoint['details'].get('fallbackScsv', "N/A"),
                endpoint['details'].get('freak'),
                ccs_map(endpoint['details']['openSslCcs']),
                sslv3,
                tlsv12,
                spdy,
                endpoint['details']['sniRequired'],
                h2
            ]

headers = [
    "Grade",  # unique to SSL Labs
    "Signature Algorithm", "Key Type", "Key Size",  # strength
    "Forward Secrecy", "OCSP Stapling",  # privacy
    "Fallback SCSV",  # good things
    "FREAK",
    "CVE-2014-0224", "SSLv3",  # bad things
    "TLSv1.2", "SPDY", "Requires SNI",  # forward
    "HTTP/2",  # ever forward
]
