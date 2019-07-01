import logging
import requests

###
# Very simple scanner that follows redirects for a number of pages
# per domain to see if there is a 200 at the end or not.


# Set a default number of workers for a particular scan type.
# Overridden by a --workers flag. XXX not actually overridden?
workers = 50


# This is the list of pages that we will be checking.
pages = [
    "/",
    "/code.json",
    "/data.json",
    "/data",
    "/developer",
    "/digitalstrategy/",
    "/open",
    "/privacy",
    "/robots.txt",
    "/sitemap.xml"
]


# Optional one-time initialization for all scans.
# If defined, any data returned will be passed to every scan instance and used
# to update the environment dict for that instance
# Will halt scan execution if it returns False or raises an exception.
#
# Run locally.
def init(environment: dict, options: dict) -> dict:
    logging.debug("Init function.")
    return {'pages': pages}


# Required scan function. This is the meat of the scanner, where things
# that use the network or are otherwise expensive would go.
#
# Runs locally or in the cloud (Lambda).
def scan(domain: str, environment: dict, options: dict) -> dict:
    logging.debug("Scan function called with options: %s" % options)

    results = {}

    # Perform the "task".
    for page in environment['pages']:
        try:
            response = requests.head("http://" + domain + page, allow_redirects=True, timeout=4)
            results[page] = str(response.status_code)
        except:
            logging.debug("could not get data from %s%s", domain, page)
            results[page] = "query failed"

    logging.warning("%s Complete!", domain)

    return results


# Required CSV row conversion function. Usually one row, can be more.
#
# Run locally.
def to_rows(data):
    row = []
    # XXX This is commented out because somehow the CSV writer throws an exception,
    # XXX and this scanner is only going to be used to generate json.
    # for page in headers:
    #     row.append(data[page])
    return row


# CSV headers for each row of data. Referenced locally.
headers = pages
