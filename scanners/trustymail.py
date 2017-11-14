import logging
from scanners import utils
import os
import json

###
# Inspect a site's DNS Mail configuration using DHS NCATS' trustymail tool.

command = os.environ.get("TRUSTYMAIL_PATH", "trustymail")

# default to a long timeout
timeout = 30


def scan(domain, options):
    logging.debug("[%s][trustymail]" % domain)

    # cache output from pshtt
    cache_trustymail = utils.cache_path(domain, "trustymail", ext="json")

    force = options.get("force", False)

    if (force is False) and (os.path.exists(cache_trustymail)):
        logging.debug("\tCached.")
        raw = open(cache_trustymail).read()
        data = json.loads(raw)
        if (data.__class__ is dict) and data.get('invalid'):
            return None

    else:
        logging.debug("\t %s %s" % (command, domain))

        raw = utils.scan([
            command,
            domain,
            '--json',
            '--timeout', str(timeout),
        ])

        if not raw:
            utils.write(utils.invalid({}), cache_trustymail)
            logging.warn("\tBad news scanning, sorry!")
            return None

        data = json.loads(raw)
        utils.write(utils.json_for(data), utils.cache_path(domain, "trustymail"))

    # trustymail scanner follows pshtt in  using JSON arrays, even for single items
    data = data[0]

    row = []
    for field in headers:
        value = data[field]

        row.append(value)

    yield row


headers = [
    "Live", "MX Record", "Mail Servers",
    "SPF Record", "Valid SPF", "SPF Results",
    "DMARC Record", "Valid DMARC", "DMARC Results",
    "DMARC Record on Base Domain", "Valid DMARC Record on Base Domain", "DMARC Results on Base Domain", "DMARC Policy",
    "Syntax Errors"
]
