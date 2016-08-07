import logging
from scanners import utils
import os
import json

###
# == ncats ==
#
# Inspect a site's TLS configuration using NCATS' Python site inspector.
#
# Currently depends on pyenv to manage calling out to Python2 from Python3.
###

command = os.environ.get("NCATS_PATH", "site_inspector_cli")

# Kind of a hack for now, other methods of running sslyze with Python 2 welcome
pyenv_version = os.environ.get("NCATS_PYENV", "2.7.11")

# default to a long timeout
timeout = 30

# default to a custom user agent, can be overridden
user_agent = os.environ.get("NCATS_USER_AGENT", "github.com/18f/domain-scan, ncats.py")

# save (and look for) preload file in cache/preload-list.json
# same format as inspect.py uses
preload_cache = utils.cache_single("preload-list.json")

def scan(domain, options):
    logging.debug("[%s][ncats]" % domain)

    # cache output from ncats
    cache_ncats = utils.cache_path(domain, "ncats", ext="json")

    force = options.get("force", False)
    data = None

    if (force is False) and (os.path.exists(cache_ncats)):
        logging.debug("\tCached.")
        raw = open(cache_ncats).read()
        data = json.loads(raw)

    else:
        logging.debug("\t %s %s" % (command, domain))

        # Give the Python shell environment a pyenv environment.
        pyenv_init = "eval \"$(pyenv init -)\" && pyenv shell %s" % pyenv_version
        # Really un-ideal, but calling out to Python2 from Python 3 is a nightmare.
        # I don't think this tool's threat model includes untrusted CSV, either.
        raw = utils.unsafe_execute("%s && %s %s --json --user-agent %s --timeout %i --preload-cache %s" % (pyenv_init, command, domain, user_agent, timeout, preload_cache))

        if raw is None:
            # TODO: save invalid data...?
            logging.warn("\tBad news scanning, sorry!")
            return None

        data = json.loads(raw)
        utils.write(utils.json_for(data), utils.cache_path(domain, "ncats"))

    row = []
    for field in headers:
        row.append(data[field])

    yield row

headers = [
    "Domain", "Live", "Redirect",
    "Valid HTTPS", "Defaults HTTPS", "Downgrades HTTPS",
    "Strictly Forces HTTPS", "HTTPS Bad Chain", "HTTPS Bad Host Name",
    "Expired Cert", "Weak Signature Chain", "HSTS", "HSTS Header",
    "HSTS Max Age", "HSTS All Subdomains", "HSTS Preload",
    "HSTS Preload Ready", "HSTS Preloaded",
    "Broken Root", "Broken WWW"
]
