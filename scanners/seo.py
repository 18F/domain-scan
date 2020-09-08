import logging
import requests

from bs4 import BeautifulSoup

"""
Fairly simple scanner that makes a few checks for SEO and 
search indexing readiness. It will attempt to determine:
* Does a robots.txt file exist at the expected location (/robots.txt)
* If a sitemap.xml file exists
  * If so, how many URLs are in it?
  * How many of those URLs are PDF files?
* Does a `main` element exist on pages
* Does OG data exist (particularly date)

Further, by comparing the site root with a second page (/privacy in most cases)
it will compare the two pages to determine if the title and descriptions 
appear to be unique.

Possible future scope:
* crawl delay (how do we determine)
* total urls (set of nav + sitemap maybe?)
* builtwith (requires paid API access)

"""

# Set a default number of workers for a particular scan type.
# Overridden by a --workers flag. XXX not actually overridden?
workers = 50


# This is the list of pages that we will be checking.
pages = [
    "/",
    "/privacy",
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
# Runs locally or in the cloud (Lambda).
def scan(domain: str, environment: dict, options: dict) -> dict:
    logging.debug("Scan function called with options: %s" % options)

    # Initialize results with a quick check for the presence of robots.txt. 
    # Because we're not reading robots.txt, we only need the status code.
    # We could put these in `pages` but since we have specialized needs for each 
    # and no need to iterate through them, I don't want to.
    results = {
        'robots': requests.get("https://" + domain + '/robots.txt').status_code,
    }
    # Now let's take a look at sitemap
    sitemap = requests.get("https://" + domain + '/sitemap.xml')
    sitemap_status = sitemap.status_code

    results['sitemap'] = {
        'status': sitemap_status
    }
    # If we have found a sitemap, see how many URLs are in there.
    # TO DO: If sitemap.xml redirects to a sitemap index, 
    # we're not handling that correctly yet. We need to detect that
    # redirect, then ... what? Follow from there?
    if sitemap_status is 200:
        soup = BeautifulSoup(sitemap.text, 'xml')
        urls  = soup.find_all('url')
        results['sitemap']['urls found'] = len(urls)
        # and how many of those URLs appear to be PDFs
        if len(urls) > 0:
            pdfs = 0
            for u in urls:
                if '.pdf' in u.get_text():
                    pdfs += 1
            results['sitemap']['pdfs found in sitemap'] = pdfs

    # We'll write to this empty list for simple dupe checking later
    titles = []
    # Perform the "task".
    for page in environment['pages']:
        try:
            r = requests.get("https://" + domain + page, allow_redirects=True, timeout=4)
            htmlsoup = BeautifulSoup(r.text, 'lxml')
            maintag = True if htmlsoup.find('main') else False
            title = htmlsoup.find('title').get_text()
            # for dupe checking
            titles.append(title)
            
            results[page] = {
                'page': page,
                'status': str(r.status_code),
                'title': title,
                'main tag': maintag
            }
        except Exception as error:
            results[page] = "Could not get data from %s%s: %s" % (domain, page, error)

    # now check for dupe titles
    if len(titles) != len(set(titles)):
        results['duplicate titles'] = True
    logging.warning('DEBUG: results' + str(results))

    logging.warning("SEO scan for %s Complete!", domain)

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
