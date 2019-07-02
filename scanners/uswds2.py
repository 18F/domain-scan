import logging
import requests
import re
from lxml import html

###
# Scanner to search for uswds compliance.  It is just scraping the front page
# and searching for particular content.


# Set a default number of workers for a particular scan type.
# Overridden by a --workers flag. XXX not actually overridden?
workers = 50


# Required scan function. This is the meat of the scanner, where things
# that use the network or are otherwise expensive would go.
#
# Runs locally or in the cloud (Lambda).
def scan(domain: str, environment: dict, options: dict) -> dict:
    results = {}
    for i in headers:
        results[i] = 0

    # Get the url
    try:
        response = requests.get("http://" + domain, timeout=5)
    except:
        logging.debug("got error while querying %s", domain)
        results["domain"] = domain
        results["status_code"] = "error"
        return results

    body = response.text

    # check for class.*usa- in body
    res = re.findall(r'class.*"usa-', body)
    if res:
        results["usa_classes_detected"] = len(res)

    # check for "Federal government websites always use a .gov or .mil domain"
    res = re.findall(r'Official website of the U.S. Government', body)
    if res:
        results["official_website_detected"] = len(res)

    # check for uswds in text anywhere
    res = re.findall(r'uswds', body)
    if res:
        results["uswds_detected"] = len(res)

    # check for usa- in text anywhere
    res = re.findall(r'usa-', body)
    if res:
        results["usa_detected"] = len(res)

    # check for favicon-57.png (flag) in text anywhere
    res = re.findall(r'favicon-57.png', body)
    if res:
        results["flag_detected"] = len(res)

    # check for things in CSS files
    tree = html.fromstring(response.content)
    csspages = tree.xpath('/html/head/link[@rel="stylesheet"]/@href')
    for csspage in csspages:
        url = "https://" + domain + csspage
        try:
            cssresponse = requests.get(url, timeout=5)
        except:
            logging.debug("got error while querying for css page %s", url)
            continue
        cssbody = cssresponse.text

        # check for Source Sans font in CSS files
        res = re.findall(r'[sS]ource ?[Ss]ans', cssbody)
        if res:
            results["sourcesans_detected"] = len(res)

        # check for uswds string in CSS files
        res = re.findall(r'uswds', cssbody)
        if res:
            results["uswdsincss_detected"] = len(res)

    # generate a final score
    # The quick-n-dirty score is to add up all the number of things we found.
    score = 0
    for i in results.keys():
        score += results[i]
    results["total_score"] = score

    # add the status code and domain
    results["status_code"] = response.status_code
    results["domain"] = domain

    logging.warning("uswds2 %s Complete!", domain)

    return results


# Required CSV row conversion function. Usually one row, can be more.
#
# Run locally.
def to_rows(data):
    row = []
    for i in headers:
        row.extend([data[i]])
    return [row]


# CSV headers for each row of data. Referenced locally.
headers = [
    "domain",
    "status_code",
    "usa_classes_detected",
    "official_website_detected",
    "uswds_detected",
    "usa_detected",
    "flag_detected",
    "sourcesans_detected",
    "uswdsincss_detected",
    "total_score"
]
