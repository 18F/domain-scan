import logging
import re
import requests

from bs4 import BeautifulSoup
from http import HTTPStatus
from urllib import request, robotparser

"""
This scan looks for any sitemap.xml files, including those found in robots.txt,
as outlined in https://github.com/18F/site-scanning/issues/87.
It will also surface the crawl delay outlined in robots.txt.
Results returned include:
    * Status code of the sitemap file (200, 404, etc)
    * Final url of the sitemap (to account for redirects and such)
    * URL tag count (the number of URLs found in the sitemap)
    * The number of PDF files found in those URLs
    * Sitemap locations from index (as a list, for cases where sitemap.xml is an index)
    * Crawl delay (from robots.txt)
    * Sitemap locations from robots.txt (as a list)

Note that if you are calling seo.py then you should not run this scan,
as it is already called by seo.py and there's no reason to run it twice.
"""

# Set a default number of workers for a particular scan type.
# Overridden by a --workers flag. XXX not actually overridden?
workers = 50


# Required scan function. This is the meat of the scanner, where things
# that use the network or are otherwise expensive would go.
# Runs locally or in the cloud (Lambda).
def scan(domain: str, environment: dict, options: dict) -> dict:
    logging.debug("Scan function called with options: %s" % options)

    sitemap = None
    fqd = "https://%s" % domain # note lack of trailing slash
    results = {
        'status_code': None,
        'final_url': None,
        'url_tag_count': None,
        'pdfs_in_urls': None,
        'sitemap_locations_from_index': [],
        'crawl_delay': None,
        'sitemap_locations_from_robotstxt': []
    }

    # get status_code and final_url for sitemap.xml
    try:
        sitemap = requests.get(fqd + '/sitemap.xml')
        results['status_code'] = sitemap.status_code
        results['final_url'] = sitemap.url
    except Exception as error:
        results['status_code'] = "Could not get data from %s/sitemap.xml: %s" % (domain, error)

    # Check once more that we have a usable sitemap before parsing it
    if sitemap and sitemap.status_code == HTTPStatus.OK:
        soup = BeautifulSoup(sitemap.text, 'xml')
        urls = soup.find_all('url')
        results['url_tag_count'] = len(urls)
        # and how many of those URLs appear to be PDFs
        if urls:
            results['pdfs_in_urls'] = len([u for u in urls if '.pdf' in u.get_text()])
        # And check if it's a sitemap index
        if soup.find('sitemapindex'):
            results['sitemap_locations_from_index'] = [loc.text for loc in soup.select("sitemap > loc")]

    # Now search robots.txt for crawl delay and sitemap locations
    # when we have Python 3.8 RobotFileParser may be a better option than regex for this.
    # But it can be kinda funky, too.
    try:
        robots = request.urlopen(fqd + '/robots.txt', timeout=5).read().decode()
        # Note we have seen cases where a site is defining crawl delay more than once or
        # are declaring different crawl delays per user agent. We are only grabbing 
        # the first instance. Subsequent declarations are ignored.
        # This could lead to incorrect results and should be double-checked if 
        # the crawl delay is particularly critical to you. For our purposes,
        # simply grabbing the first is Good Enough.
        cd = re.search('[cC]rawl-[dD]elay: (.*)', robots)
        if cd:
            results['crawl_delay'] = cd.group()
        results['sitemap_locations_from_robotstxt'] = re.findall('[sS]itemap: (.*)', robots)
    except Exception as error:
        logging.warning("Error trying to retrieve robots.txt for %s: %s" % (fqd, error))

    logging.warning("sitemap %s Complete!", domain)
    return results

# Required CSV row conversion function. Usually one row, can be more.
# Run locally.
def to_rows(data):
    row = []
    for page in headers:
        row.extend([data[page]])
    return [row]


# CSV headers for each row of data. Referenced locally.
headers = [
    'status_code',
    'final_url',
    'url_tag_count',
    'pdfs_in_urls',
    'sitemap_locations_from_index',
    'crawl_delay',
    'sitemap_locations_from_robotstxt',
]