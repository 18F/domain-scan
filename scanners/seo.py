import logging
import requests

from http import HTTPStatus

from bs4 import BeautifulSoup
from builtwith import builtwith

from .sitemap import scan as sitemap_scan

"""
Fairly simple scanner that makes a few checks for SEO and
search indexing readiness.
It first runs the sitemap scanner to capture the presence of
(and key contents of) sitemap.xml and robots.txt files.
then runs additional SEO checks to determine:

* What platform does the site run on
# Does a sitemap.xml exist?
# How many of the total URLs are in the sitemap
# How many PDFs are in the sitemap?
# How many URLs are there total
# Does a Robots.txt exist
# Crawl delay? (number)
# Est hours to index (crawl delay x #number of URLs)
# Does a Main element exist
# Does OG Date metadata exist
# Are Title tags unique
# Are meta descriptions unique

Further, by comparing the site root with a second page (/privacy) it
will compare the two pages to determine if the title and descriptions
appear to be unique.

Possible future scope:
* expanded checking (grab some set of URLs from Nav and look at them, too)

"""

# Set a default number of workers for a particular scan type.
workers = 50

# This is the initial list of pages that we will be checking.
pages = [
    "/",
    "/privacy",
]

# CSV headers for each row of data. Referenced locally.
headers = [
    'Platforms',
    'Sitemap.xml',
    'Sitemap Final URL',
    'Sitemap items',
    'PDFs in sitemap',
    'Sitemaps from index',
    'Robots.txt',
    'Crawl delay',
    'Sitemaps from robots',
    'Total URLs',
    'Est time to index',
    'Main tags found',
    'Warnings'] + pages


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
# Runs locally or in the cloud (Lambda).
def scan(domain: str, environment: dict, options: dict) -> dict:
    logging.debug("Scan function called with options: %s" % options)

    # Run sitemap_scan to capture that data
    sitemap_results = sitemap_scan(domain, environment, options)
    fqd = "https://%s" % domain  # note lack of trailing slash

    if sitemap_results['status_code'] == HTTPStatus.OK:
        sitemap_status = "OK"
    else:
        sitemap_status = sitemap_results['status_code']

    results = {
        'Platforms': 'Unknown',
        'Sitemap.xml': sitemap_status,
        'Sitemap Final URL': sitemap_results['final_url'],
        'Sitemap items': sitemap_results['url_tag_count'],
        'PDFs in sitemap': sitemap_results['pdfs_in_urls'],
        'Sitemaps from index': sitemap_results['sitemap_locations_from_index'],
        'Robots.txt': sitemap_results['robots'],
        'Crawl delay': sitemap_results['crawl_delay'],
        'Sitemaps from robots': sitemap_results['sitemap_locations_from_robotstxt'],
        'Total URLs': sitemap_results['url_tag_count'] if sitemap_results['url_tag_count'] else 0,
        'Est time to index': 'Unknown',
        'Main tags found': False,
        'Warnings': {},
    }

    # See if we can determine platforms used for the site
    build_info = builtwith(fqd)
    if 'web-frameworks' in build_info:
        results['Platforms'] = build_info['web-frameworks']

    # If we found additional sitemaps in a sitemap index or in robots.txt, we
    # need to go look at them and update our url total.
    additional_urls = 0
    for loc in sitemap_results['sitemap_locations_from_index']:
        if loc != sitemap_results['final_url']:
            sitemap = requests.get(loc)
            if sitemap.status_code == HTTPStatus.OK:
                soup = BeautifulSoup(sitemap.text, 'xml')
                additional_urls += len(soup.find_all('url'))

    for loc in sitemap_results['sitemap_locations_from_robotstxt']:
        if loc != sitemap_results['final_url']:
            sitemap = requests.get(loc)
            if sitemap.status_code == HTTPStatus.OK:
                soup = BeautifulSoup(sitemap.text, 'xml')
                additional_urls += len(soup.find_all('url'))
    results['Total URLs'] = results['Total URLs'] + additional_urls

    # Can we compute how long it will take to index all URLs (in hours)?
    if results['Crawl delay']:
        results['Est time to index'] = (int(results['Total URLs']) * int(results['Crawl delay'])) / 3600

    # We'll write to these empty lists for simple dupe checking later
    titles = []
    descriptions = []
    for page in environment['pages']:
        try:
            r = requests.get("https://" + domain + page, timeout=4)
            # if we didn't find the page, write minimal info and skip to next page
            if r.status_code != HTTPStatus.OK:
                results[page] = '404'
                continue
            htmlsoup = BeautifulSoup(r.text, 'lxml')
            # get title and put in dupe-checking list
            title = htmlsoup.find('title').get_text()
            titles.append(title)
            # and description
            description = htmlsoup.select_one("meta[name='description']")
            if description:
                descriptions.append(description['content'])
            # and can we find dc:date?
            dc_date = htmlsoup.select_one("meta[name='article:published_time']")
            if not dc_date:
                dc_date = htmlsoup.select_one("meta[name='article:modified_time']")
                if not dc_date:
                    dc_date = htmlsoup.select_one("meta[name='DC.Date']")
            # if we found one, grab the content
            if dc_date:
                dc_date = dc_date['content']

            # Find the main tag (or alternate), if we haven't found one already.
            # Potential TO-DO: check that there is only one. Necessary? ¯\_(ツ)_/¯
            if not results['Main tags found']:
                maintag = True if htmlsoup.find('main') else False
                # if we couldn't find `main` look for the corresponding role
                if not maintag:
                    maintag = True if htmlsoup.select('[role=main]') else False
                results['Main tags found'] = maintag
            if r.status_code == HTTPStatus.OK:
                results[page] = {
                    'title': title,
                    'description': description,
                    'date': dc_date
                }
        except Exception as error:
            results[page] = "Could not get data from %s%s: %s" % (domain, page, error)

    # now check for dupes
    if len(titles) != len(set(titles)):
        results['warnings']['Duplicate titles found'] = True
    if len(descriptions) != len(set(descriptions)):
        results['warnings']['Duplicate descriptions found'] = True

    logging.warning("SEO scan for %s Complete!", domain)

    return results


# Required CSV row conversion function. Usually one row, can be more.
#
# Run locally.
def to_rows(data):
    row = []
    # logging.warning("DEBUG: data we're writing to rows: %s", data)
    for header in headers:
        row.extend([data[header]])
    return [row]
