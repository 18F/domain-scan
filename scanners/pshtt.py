import logging
from scanners import utils
import os
import json

###
# == pshtt ==
#
# Inspect a site's TLS configuration using DHS NCATS' pshtt tool.
#
###

command = os.environ.get("PSHTT_PATH", "pshtt")

# default to a long timeout
timeout = 30

# default to a custom user agent, can be overridden
user_agent = os.environ.get("PSHTT_USER_AGENT", "github.com/18f/domain-scan, pshtt.py")

# save (and look for) preload file in cache/preload-list.json
# same format as inspect.py uses
preload_cache = utils.cache_single("preload-list.json")


# The preload list cache is only important across individual
# executions of pshtt. Not intended to be cached across
# individual executions of domain-scan itself.
def init(options):
    if os.path.exists(preload_cache):
        logging.warn("Clearing cached preload-list.json file before scanning.")
        os.remove(preload_cache)
    return True


def scan(domain, options):
    logging.debug("[%s][pshtt]" % domain)

    # cache output from pshtt
    cache_pshtt = utils.cache_path(domain, "pshtt", ext="json")

    force = options.get("force", False)
    data = None

    if (force is False) and (os.path.exists(cache_pshtt)):
        logging.debug("\tCached.")
        raw = open(cache_pshtt).read()
        data = json.loads(raw)
        if (data.__class__ is dict) and data.get('invalid'):
            return None

    else:
        logging.debug("\t %s %s" % (command, domain))

        raw = utils.scan([
            command,
            domain,
            '--json',
            '--user-agent', '\"%s\"' % user_agent,
            '--timeout', str(timeout),
            '--preload-cache', preload_cache
        ])

        if not raw:
            utils.write(utils.invalid({}), cache_pshtt)
            logging.warn("\tBad news scanning, sorry!")
            return None

        data = json.loads(raw)
        utils.write(utils.json_for(data), utils.cache_path(domain, "pshtt"))

    # pshtt scanner uses JSON arrays, even for single items
    data = data[0]

    row = []
    for field in headers:
        value = data[field]

        # TODO: Fix this upstream
        if (field != "HSTS Header") and (field != "HSTS Max Age") and (field != "Redirect To"):
            if value is None:
                value = False

        row.append(value)

    yield row


headers = [
    "Canonical URL", "Live", "Redirect", "Redirect To",
    "Valid HTTPS", "Defaults to HTTPS", "Downgrades HTTPS",
    "Strictly Forces HTTPS", "HTTPS Bad Chain", "HTTPS Bad Hostname",
    "HTTPS Expired Cert", "HTTPS Self Signed Cert",
    "HSTS", "HSTS Header", "HSTS Max Age", "HSTS Entire Domain",
    "HSTS Preload Ready", "HSTS Preload Pending", "HSTS Preloaded",
    "Base Domain HSTS Preloaded", "Domain Supports HTTPS",
    "Domain Enforces HTTPS", "Domain Uses Strong HSTS", "Unknown Error"
]
