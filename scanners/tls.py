import logging
from scanners import utils
import json
import os


###
# == tls ==
#
# Inspect a site's valid TLS configuration using ssllabs-scan.
#
# If data exists for a domain from `pshtt`, will check results
# and only process domains with valid HTTPS, or broken chains.
###

command = os.environ.get("SSLLABS_PATH", "ssllabs-scan")
workers = 1


def scan(domain, options):
    logging.debug("[%s][tls]" % domain)

    # If inspection data exists, check to see if we can skip.
    if utils.domain_doesnt_support_https(domain):
        logging.debug("\tSkipping, HTTPS not supported in inspection.")
        return None

    # cache reformatted JSON from ssllabs
    cache = utils.cache_path(domain, "tls")

    # Optional: if pshtt data says canonical endpoint uses www and this domain
    # doesn't have it, add it.
    if utils.domain_uses_www(domain):
        scan_domain = "www.%s" % domain
    else:
        scan_domain = domain

    force = options.get("force", False)

    if (force is False) and (os.path.exists(cache)):
        logging.debug("\tCached.")
        raw = open(cache).read()
        data = json.loads(raw)

        if data.get('invalid'):
            return None
    else:
        logging.debug("\t %s %s" % (command, scan_domain))

        usecache = str(not force).lower()

        if options.get("debug"):
            cmd = [command, "--usecache=%s" % usecache,
                   "--verbosity=debug", scan_domain]
        else:
            cmd = [command, "--usecache=%s" % usecache,
                   "--quiet", scan_domain]

        raw = utils.scan(cmd)
        if raw:
            data = json.loads(raw)

            # if SSL Labs gave us back an error response, cache this
            # as an invalid entry.
            if len(data) < 1:
                utils.write(utils.invalid({'response': data}), cache)
                return None

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
            h2 = ("h2" in npn)

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
            h2
        ]


headers = [
    "Grade",  # unique to SSL Labs
    "Signature Algorithm", "Key Type", "Key Size",  # strength
    "Forward Secrecy", "OCSP Stapling",  # privacy
    "Fallback SCSV",  # good things
    "RC4", "SSLv3",  # old things
    "TLSv1.2", "SPDY", "Requires SNI",  # forward
    "HTTP/2"  # ever forward
]
