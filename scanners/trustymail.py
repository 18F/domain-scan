import logging
from scanners import utils
import os
import json

###
# == trustymail ==
#
# Inspect a site's DNS Mail configuration using DHS NCATS' trustymail tool.
#
###

command = os.environ.get("TRUSTYMAIL_PATH", "trustymail")

# default to a long timeout
timeout = 30

# default to a custom user agent, can be overridden
user_agent = os.environ.get("TRUSTYMAIL_USER_AGENT", "github.com/18f/domain-scan, trustymail.py")


def scan(domain, options):
    logging.debug("[%s][trustymail]" % domain)

    # cache output from pshtt
    cache_trustymail = utils.cache_path(domain, "trustymail", ext="json")

    if (os.path.exists(cache_trustymail)):
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

        # # TODO: Fix this upstream
        # if (field != "HSTS Header") and (field != "HSTS Max Age") and (field != "Redirect To"):
        #     if value is None:
        #         value = False

        row.append(value)

    yield row


headers = [
    "Domain", "Base Domain", "Live",
    "Sends Mail", "Mail Servers",
    "SPF Record", "Valid SPF", "SPF Results",
    "DMARC Record", "Valid DMARC", "DMARC Results",
    "DMARC Record on Base Domain", "Valid DMARC Record on Base Domain", "DMARC Results on Base Domain",
    "Syntax Errors"
]