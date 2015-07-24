
from scanners import utils
import logging
import os
import requests

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
    if (not analytics_file) or (not analytics_file.endswith(".csv")):
        no_csv = "--analytics should point to the file path or URL to a CSV of participating domains."
        logging.error(no_csv)
        return False

    # It's a URL, download it first.
    if analytics_file.startswith("http:") or analytics_file.startswith("https:"):

        analytics_path = os.path.join(utils.cache_dir(), "analytics.csv")

        try:
            response = requests.get(analytics_file)
            utils.write(response.text, analytics_path)
        except:
            no_csv = "--analytics URL not downloaded successfully."
            logging.error(no_csv)
            return False

    # Otherwise, read it off the disk
    else:
        analytics_path = analytics_file

        if (not os.path.exists(analytics_path)):
            no_csv = "--analytics file not found."
            logging.error(no_csv)
            return False

    analytics_domains = utils.load_domains(analytics_path)

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
