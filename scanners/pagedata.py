import logging
import os
import re
import resource
import time
import urllib.request
from urllib.parse import urlparse

import ijson
import requests

###
# Very simple scanner that gets some basic info from a list of pages on a domain.


# Set a default number of workers for a particular scan type.
# Overridden by a --workers flag. XXX not actually overridden?
workers = 30


user_agent = os.environ.get("PAGEDATA_USER_AGENT", "18F/domain-scan/pagedata.py")


# This is the list of pages that we will be checking.
pages = [
    "/",
    "/code.json",
    "/coronavirus",
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
    "/redirecttest-foo-bar-baz",
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

        headers = {
            'User-Agent': user_agent,
        }

        # try the query and store the responsecode
        try:
            response = requests.head(url, allow_redirects=True, timeout=4, headers=headers)
            results[page]['responsecode'] = str(response.status_code)
        except Exception:
            logging.debug("could not get data from %s%s", domain, page)
            results[page]['responsecode'] = '-1'

        # if it's supposed to be json, try parsing it as a stream
        if page.endswith('.json'):
            counter = 0
            try:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=5) as jsondata:
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
                            # be code.gov compliant.  Taken from https://code.gov/about/compliance/inventory-code
                            if prefix.endswith('.measurementType') or prefix.endswith('.measurementtype'):
                                results[page]['codegov_measurementtype'] = ' '.join([value, results[page]['codegov_measurementtype']])
                            if prefix.endswith('measurementType.method') or prefix.endswith('measurementtype.method'):
                                results[page]['codegov_measurementtype'] = ' '.join([value, results[page]['codegov_measurementtype']])
                            if prefix.endswith('measurementType.ifOther') or prefix.endswith('measurementtype.ifOther'):
                                results[page]['codegov_measurementtype'] = ' '.join([value, results[page]['codegov_measurementtype']])

                        results[page]['json_items'] = str(counter)
                        logging.debug('memory usage after parsing json for %s: %d', url, resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
                    except Exception:
                        logging.debug('error parsing json for %s', url)
            except Exception:
                logging.debug('could not open %s', url)

        # Get the content-type
        try:
            results[page]['content_type'] = str(response.headers['Content-Type'])
        except Exception:
            results[page]['content_type'] = ''

        # get the content-length
        try:
            results[page]['content_length'] = str(response.headers['Content-Length'])
        except Exception:
            # sometimes cloudfront seems to have errors or cache misses, so let's try again
            try:
                # sleep a bit to let it have time to cache the page
                time.sleep(0.01)
                newresponse = requests.head(url, allow_redirects=True, timeout=4)
                results[page]['content_length'] = str(newresponse.headers['Content-Length'])
            except Exception:
                results[page]['content_length'] = ''

        # This is the final url that we ended up at, in case of redirects.
        try:
            results[page]['final_url_in_same_domain'] = False
            results[page]['final_url'] = response.url
            if urlparse(response.url).hostname.endswith(domain):
                results[page]['final_url_in_same_domain'] = True
        except Exception:
            results[page]['final_url'] = ''

        # get the page if it's the /data page so that we can scrape it
        if page == '/data':
            try:
                response = requests.get(url, allow_redirects=True, timeout=5, headers=headers)

                # check for "chief data officer"
                try:
                    res = re.findall(r'chief data officer', response.text, flags=re.IGNORECASE)
                    if res:
                        results[page]['contains_chiefdataofficer'] = True
                    else:
                        results[page]['contains_chiefdataofficer'] = False
                except Exception:
                    results[page]['contains_chiefdataofficer'] = False

                # check for "Charter"
                try:
                    res = re.findall(r'Charter', response.text, flags=re.IGNORECASE)
                    if res:
                        results[page]['contains_charter'] = True
                    else:
                        results[page]['contains_charter'] = False
                except Exception:
                    results[page]['contains_charter'] = False
            except Exception:
                logging.debug("got error while scraping %s", domain)

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
