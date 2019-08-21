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
    for page in pages:
        results[page] = {}
        results[page]['content_type'] = ''
        results[page]['content_length'] = 0
        results[page]['final_url'] = ''
        results[page]['opendata_conforms_to'] = ''
        results[page]['codegov_measurementtype'] = ''
        results[page]['json_items'] = 0

        # try the query and store the responsecode
        try:
            response = requests.get("https://" + domain + page, allow_redirects=True, stream=True, timeout=10)
            results[page]['responsecode'] = response.status_code
        except:
            logging.debug("could not get data from %s%s", domain, page)
            results[page]['responsecode'] = '-1'
            continue

        # Get the content-type
        try:
            results[page]['content_type'] = str(response.headers['Content-Type'])
        except:
            results[page]['content_type'] = ''

        # get the content-length
        try:
            results[page]['content_length'] = str(response.headers['Content-Length'])
        except:
            results[page]['content_length'] = 0

        # This is the final url that we ended up at, in case of redirects.
        try:
            results[page]['final_url'] = response.url
        except:
            results[page]['final_url'] = ''

        # This is to try to not run out of memory.  This provides a sliding window
        # so that if one of the patterns spans a chunk boundary, we will not miss it.
        lastbody = ''
        try:
            for nextbody in response.iter_content(chunk_size=20480):
                nextbody = str(nextbody)
                body = lastbody + nextbody
                lastbody = nextbody

                # see if there is a 'conformsTo' field, which indicates that it might
                # be open-data compliant.
                conformstolist = re.findall(r'"conformsTo": "(.*?)"', body)
                results[page]['opendata_conforms_to'] = ' '.join(conformstolist)

                # see if there is a 'measurementType' field, which indicates that it might
                # be code.gov compliant.
                measurementtypelist = re.findall(r'"measurementType": "(.*?)"', body)
                results[page]['codegov_measurementtype'] = ' '.join(measurementtypelist)

                # As a catchall, indicate how many items are in the json doc.
                # This is really kinda ugly, because it relies on json being properly formatted
                # and also will not count the last block of data.  But parsing json
                # will run us out of memory.
                results[page]['json_items'] = results[page]['json_items'] + len(re.findall(r'": "', lastbody))
        except Exception as err:
            logging.debug("problem iterating over response from %s: %s", domain + page, err)

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
