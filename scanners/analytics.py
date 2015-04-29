
from scanners import utils
import logging
import os

###
# == analytics ==
#
# Check whether a domain is present in a CSV, set in --analytics.
###

command = None
analytics_domains = None

def init(options):
    global analytics_domains

    analytics_file = options.get("analytics")
    if (not analytics_file) or (not analytics_file.endswith(".csv")) or (not os.path.exists(analytics_file)):
        logging.error("--analytics should point to a CSV of participating domains.")
        return False

    analytics_domains = utils.load_domains(analytics_file)

    return True

def scan(domain, options):
    logging.debug("[%s][analytics]" % domain)
    logging.debug("\tChecking file.")

    data = {
        'participating': (domain in analytics_domains)
    }

    cache = utils.cache_path(domain, "analytics")
    utils.write(utils.json_for(data), cache)

    yield [data['participating']]

headers = ["Participates in Analytics"]
