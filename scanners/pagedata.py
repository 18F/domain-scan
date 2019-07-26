import logging
import requests
import re

###
# Very simple scanner that gets some basic info from a list of pages on a domain.


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
        results[page] = {}

        try:
            response = requests.get("https://" + domain + page, allow_redirects=True, timeout=60)
            try:
                if re.search(r'\.json$', page):
                    # This might be heavyweight if there is json and it is big
                    results[page]['opendata_conforms_to'] = str(response.json()['conformsTo'])
                else:
                    results[page]['opendata_conforms_to'] = ''
            except:
                results[page]['opendata_conforms_to'] = ''

            try:
                results[page]['content_type'] = str(response.headers['Content-Type'])
            except:
                results[page]['content_type'] = ''

            try:
                results[page]['content_length'] = str(response.headers['Content-Length'])
            except:
                results[page]['content_length'] = ''

            results[page]['final_url'] = response.url
            results[page]['responsecode'] = response.status_code            
        except:
            logging.debug("could not get data from %s%s", domain, page)
            results[page] = {
                'responsecode': str(-1),
                'opendata_conforms_to': '',
                'content_type': '',
                'content_length': '',
                'final_url': '',
            }

    logging.warning("pagedata %s Complete!", domain)

    return results


# Required CSV row conversion function. Usually one row, can be more.
#
# Run locally.
def to_rows(data):
    row = []
    for page in headers:
        row.extend([data[page]])
    return [row]


# CSV headers for each row of data. Referenced locally.
headers = pages
