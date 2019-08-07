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


# to count elements
def num_elements(x):
    if isinstance(x, dict):
        return sum([num_elements(_x) for _x in x.values()])
    elif isinstance(x, list):
        return sum([num_elements(_x) for _x in x])
    else:
        return 1


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

        # try the query and store the responsecode
        try:
            response = requests.get("https://" + domain + page, allow_redirects=True, timeout=30)
            results[page]['responsecode'] = response.status_code
        except:
            logging.debug("could not get data from %s%s", domain, page)
            results[page]['responsecode'] = '-1'

        # if it's supposed to be json, try parsing it so we can mine it later
        try:
            jsondata = {}
            if re.search(r'\.json$', page):
                # This might be heavyweight if there is json and it is big
                jsondata = response.json()
        except:
            jsondata = {}

        # see if there is a 'conformsTo' field, which indicates that it might
        # be open-data compliant.
        try:
            results[page]['opendata_conforms_to'] = str(jsondata['conformsTo'])
        except:
            results[page]['opendata_conforms_to'] = ''

        # see if there is a 'measurementType' field, which indicates that it might
        # be code.gov compliant.
        try:
            results[page]['codegov_measurementtype'] = str(jsondata['measurementType'])
        except:
            results[page]['codegov_measurementtype'] = ''

        # As a catchall, indicate how many items are in the json doc
        results[page]['json_items'] = str(num_elements(jsondata))

        # Get the content-type
        try:
            results[page]['content_type'] = str(response.headers['Content-Type'])
        except:
            results[page]['content_type'] = ''

        # get the content-length
        try:
            results[page]['content_length'] = str(response.headers['Content-Length'])
        except:
            results[page]['content_length'] = ''

        # This is the final url that we ended up at, in case of redirects.
        try:
            results[page]['final_url'] = response.url
        except:
            results[page]['final_url'] = ''

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
