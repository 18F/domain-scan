import logging
import urllib.request
import re
import requests
import socket
from urllib.error import URLError

###
# Scan focused on learning about the /privacy page, as per
# https://github.com/18F/site-scanning/issues/89.


# Set a default number of workers for a particular scan type.
# Overridden by a --workers flag. XXX not actually overridden?
workers = 50


def mergelists(a, b):
    return list(set().union(a, b))


# Required scan function. This is the meat of the scanner, where things
# that use the network or are otherwise expensive would go.
#
# Runs locally or in the cloud (Lambda).
def scan(domain: str, environment: dict, options: dict) -> dict:
    logging.debug("Scan function called with options: %s" % options)

    results = {}
    url = 'https://' + domain + '/privacy'

    # get statuscode for /privacy
    try:
        response = requests.head(url, allow_redirects=True, timeout=4)
        results['statuscode'] = str(response.status_code)
        results['final_url'] = response.url
    except:
        logging.debug("could not get data from %s", url)
        results['statuscode'] = str(-1)
        results['final_url'] = ''

    # search /privacy for email addresses
    results['emails'] = []
    try:
        with urllib.request.urlopen(url, timeout=5) as privacypage:
            for count, line in enumerate(privacypage):
                line = line.decode().rstrip()
                emails = re.findall('<a href="mailto:(.*?)"', line)
                if emails:
                    results['emails'] = mergelists(emails, results['emails'])
    except:
        logging.debug('error while trying to retrieve emails from %s', url)

    # search /privacy for H[123] tags
    results['h1'] = []
    results['h2'] = []
    results['h3'] = []
    try:
        with urllib.request.urlopen(url, timeout=5) as privacypage:
            for count, line in enumerate(privacypage):
                line = line.decode().rstrip()
                h1s = re.findall('<h1>(.*)</h1>', line)
                h2s = re.findall('<h2>(.*)</h2>', line)
                h3s = re.findall('<h3>(.*)</h3>', line)
                if h1s or h2s or h3s:
                    results['h1'] = mergelists(h1s, results['h1'])
                    results['h2'] = mergelists(h2s, results['h2'])
                    results['h3'] = mergelists(h3s, results['h3'])
    except (TimeoutError, URLError, ConnectionRefusedError):
        logging.debug('error while trying to retrieve emails from %s', url)

    logging.warning("sitemap %s Complete!", domain)

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
headers = [
    'statuscode',
    'final_url',
    'emails',
    'h1',
    'h2',
    'h3',
]
