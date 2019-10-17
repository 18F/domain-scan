import logging
import requests
import ijson
import resource
import urllib.request
from urllib.parse import urlparse

###
# Very simple scanner that gets some basic info from a list of pages on a domain.


# Set a default number of workers for a particular scan type.
# Overridden by a --workers flag. XXX not actually overridden?
workers = 30


# This is the list of pages that we will be checking.
pages = [
    "/",
    "/code.json",
    "/data.json",
    "/data",
    "/developer",
    "/digitalstrategy",
    "/open",
    "/privacy",
    "/robots.txt",
    "/sitemap.xml",
    "/cj",
    "/digitalstrategy/datacenteroptimizationstrategicplan.json",
    "/digitalstrategy/FITARAmilestones.json",
    "/digitalstrategy/governanceboards.json",
    "/digitalstrategy/costsavings.json",
    "/digitalstrategy/bureaudirectory.json",
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
        url = "https://" + domain + page
        results[page] = {}
        results[page]['opendata_conforms_to'] = ''
        results[page]['codegov_measurementtype'] = ''
        results[page]['json_items'] = str(0)

        # try the query and store the responsecode
        try:
            response = requests.head(url, allow_redirects=True, timeout=4)
            results[page]['responsecode'] = str(response.status_code)
        except:
            logging.debug("could not get data from %s%s", domain, page)
            results[page]['responsecode'] = '-1'

        # if it's supposed to be json, try parsing it as a stream
        if page.endswith('.json'):
            counter = 0
            try:
                with urllib.request.urlopen(url, timeout=5) as jsondata:
                    try:
                        parser = ijson.parse(jsondata)
                        for prefix, event, value in parser:
                            # As a catchall, indicate how many items are in the json doc
                            if event == 'string':
                                counter = counter + 1

                            # see if there is a 'conformsTo' field, which indicates that it might
                            # be open-data compliant.
                            if prefix.endswith('.conformsTo') or prefix.endswith('.conformsto'):
                                results[page]['opendata_conforms_to'] = ' '.join([value, results[page]['opendata_conforms_to']])

                            # see if there is a 'measurementType' field, which indicates that it might
                            # be code.gov compliant.
                            if prefix.endswith('.measurementType') or prefix.endswith('.measurementtype'):
                                results[page]['codegov_measurementtype'] = ' '.join([value, results[page]['codegov_measurementtype']])
                            if prefix.endswith('measurementType.method') or prefix.endswith('measurementtype.method'):
                                results[page]['codegov_measurementtype'] = ' '.join([value, results[page]['codegov_measurementtype']])
                            if prefix.endswith('measurementType.ifOther') or prefix.endswith('measurementtype.ifOther'):
                                results[page]['codegov_measurementtype'] = ' '.join([value, results[page]['codegov_measurementtype']])

                        results[page]['json_items'] = str(counter)
                        logging.debug('memory usage after parsing json for %s: %d', url, resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
                    except:
                        logging.debug('error parsing json for %s', url)
            except:
                logging.debug('could not open %s', url)

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
            results[page]['final_url_in_same_domain'] = False
            results[page]['final_url'] = response.url
            if urlparse(response.url).hostname.endswith(domain):
                results[page]['final_url_in_same_domain'] = True
        except:
            results[page]['final_url'] = ''

        logging.debug('memory usage after page %s: %d', url, resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)

    logging.debug('memory usage for pagedata %s: %d', "https://" + domain, resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
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
