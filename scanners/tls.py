import logging
from scanners import utils
import json
import os

ssllabs_cmd = os.environ.get("SSLLABS_PATH", "ssllabs-scan")

###
# Inspect a site's valid TLS configuration using ssllabs-scan.
#
# If site inspection data exists for a domain, will check results
# and only process domains with valid HTTPS, or broken chains.
###
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
            logging.debug("\t %s %s" % (ssllabs_cmd, domain))

            usecache = str(not force).lower()

            if options.get("debug"):
                cmd = [ssllabs_cmd, "--usecache=%s" % usecache,
                       "--verbosity=debug", domain]
            else:
                cmd = [ssllabs_cmd, "--usecache=%s" % usecache,
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
                  utils.write(invalid(data), cache)
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
                endpoint['details']['heartbleed'],
                sslv3,
                endpoint['details']['key'].get('debianFlaw', False),
                tlsv12,
                spdy,
                endpoint['details']['sniRequired'],
                h2
            ]

headers = [
    "Grade",  # unique to SSL Labs
    "Signature Algorithm", "Key Type", "Key Size",  # strength
    "Forward Secrecy", "OCSP Stapling",  # privacy
    "Heartbleed", "SSLv3", "Debian Flaw",  # bad things
    "TLSv1.2", "SPDY", "Requires SNI",  # forward
    "HTTP/2",  # ever forward
]

