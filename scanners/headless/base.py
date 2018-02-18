import logging
import json

from utils import utils

###
# Local Python bridge to the JS bridge to the JS scanner.
# Shells out to run Node on base.js, which runs headless Chrome
# and then pulls in the scanner-specific JS scanning function.
# Resulting data is serialized and returned via STDOUT.
###

def headless_scan(scanner_name, domain, environment, options):
    raw = utils.scan(
        [
            "./scanners/headless/base.js",
            scanner_name,
            utils.json_for({
                'domain': domain,
                'environment': environment,
                'options': options
            })
        ]
    )

    if not raw:
        logging.warn("\tError calling out to %s.js, skipping." % scanner_name)
        return None

    try:
        data = utils.from_json(raw)
    except json.decoder.JSONDecodeError:
        logging.warn("\tError inside %s.js, skipping. Error below:\n\n%s" % (scanner_name, raw))
        return None

    return data
