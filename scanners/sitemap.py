import logging
import urllib.request
from lxml import etree
import re
import requests

###
# Scan focused on learning about the sitemap.xml file, as per
# https://github.com/18F/site-scanning/issues/87.


# Set a default number of workers for a particular scan type.
# Overridden by a --workers flag. XXX not actually overridden?
workers = 50


# Required scan function. This is the meat of the scanner, where things
# that use the network or are otherwise expensive would go.
#
# Runs locally or in the cloud (Lambda).
def scan(domain: str, environment: dict, options: dict) -> dict:
    logging.debug("Scan function called with options: %s" % options)

    results = {}

    # get statuscode and final_url for sitemap.xml
    try:
        response = requests.head("https://" + domain + '/sitemap.xml', allow_redirects=True, timeout=4)
        results['statuscode'] = str(response.status_code)
        results['final_url'] = response.url
    except:
        logging.debug("could not get data from %s/sitemap.xml", domain)
        results['statuscode'] = str(-1)
        results['final_url'] = ''

    # search sitemap and count the <url> tags
    url = 'https://' + domain + '/sitemap.xml'
    i = 0
    try:
        with urllib.request.urlopen(url) as sitemap:
            for event, element in etree.iterparse(sitemap):
                tag = etree.QName(element.tag).localname
                if tag == 'url':
                    i = i + 1
                element.clear()
    except:
        logging.debug('error while trying to retrieve sitemap.xml')
    results['url_tag_count'] = i

    # search robots.txt for sitemap locations
    url = 'https://' + domain + '/robots.txt'
    results['sitemap_locations_from_robotstxt'] = []
    try:
        with urllib.request.urlopen(url, timeout=5) as robots:
            for count, line in enumerate(robots):
                line = line.decode().rstrip()
                sitemaps = re.findall('[sS]itemap: (.*)', line)
                if sitemaps:
                    results['sitemap_locations_from_robotstxt'] = list(set().union(sitemaps, results['sitemap_locations_from_robotstxt']))
    except:
        logging.debug('error while trying to retrieve robots.txt for %s', url)

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
    'url_tag_count',
    'sitemap_locations_from_robotstxt',
]
