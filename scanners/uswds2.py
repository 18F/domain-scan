import logging
import requests
import re
from lxml import html
import math

###
# Scanner to search for uswds compliance.  It is just scraping the front page
# and CSS files and searching for particular content.


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
    except Exception:
        logging.debug("got error while querying %s", domain)
        results["domain"] = domain
        results["status_code"] = -1
        return results

    # check for class.*usa- in body
    res = re.findall(r'class.*"usa-', response.text)
    if res:
        results["usa_classes_detected"] = round(math.sqrt(len(res))) * 5

    # # check for official text
    # # (testing revealed that this generated FPs)
    # # XXX Try this in the header only?
    # res = re.findall(r'fficial website of the', response.text)
    # if res:
    #     results["official_website_detected"] = len(res)

    # check for uswds in text anywhere
    res = re.findall(r'uswds', response.text)
    if res:
        results["uswds_detected"] = len(res)

    # check for .usa- in text anywhere
    res = re.findall(r'\.usa-', response.text)
    if res:
        results["usa_detected"] = len(res)

    # check for favicon-57.png (flag) in text anywhere
    res = re.findall(r'favicon-57.png', response.text)
    if res:
        results["flag_detected"] = 20

    # count how many tables are in the, to deduct from the score
    res = re.findall(r'<table ', response.text)
    if res:
        results["tables"] = len(res) * -10

    # check for things in CSS files
    try:
        tree = html.fromstring(response.content)
        csspages = tree.xpath('/html/head/link[@rel="stylesheet"]/@href')
    except Exception:
        csspages = []

    for csspage in csspages:
        res = re.findall(r'^http.?://', csspage, re.IGNORECASE)
        if res:
            url = csspage
        else:
            url = "https://" + domain + csspage

        try:
            cssresponse = requests.get(url, timeout=5, stream=True)
        except Exception:
            logging.debug("got error while querying for css page %s", url)
            continue

        # This is to try to not run out of memory.  This provides a sliding window
        # so that if one of the patterns spans a chunk boundary, we will not miss it.
        lastbody = ''
        for nextbody in cssresponse.iter_content(chunk_size=20480):
            nextbody = str(nextbody)
            cssbody = lastbody + nextbody
            lastbody = nextbody

            # check for Source Sans font in CSS files
            # This is a widely-used font that USWDS uses.
            res = re.findall(r'[sS]ource ?[Ss]ans', cssbody)
            if res:
                results["sourcesansfont_detected"] = 5

            # check for Merriweather font in CSS files
            # This is a widely-used font that USWDS uses.
            res = re.findall(r'[Mm]erriweather', cssbody)
            if res:
                results["merriweatherfont_detected"] = 5

            # Check for Public Sans font in CSS files
            # This is an uncommon font, created by GSA.
            res = re.findall(r'[Pp]ublic ?[Ss]ans', cssbody)
            if res:
                results["publicsansfont_detected"] = 20

            # check for uswds string in CSS files
            res = re.findall(r'uswds', cssbody)
            if res:
                results["uswdsincss_detected"] = 20

            # check for uswds version in CSS files
            # This means that a USWDS style sheet is included, though perhaps not used.
            res = re.findall(r'uswds v[0-9.]* ', cssbody)
            if res:
                vstuff = res[0].split(' ')
                results["uswdsversion"] = vstuff[1]
                results["total_score"] = results["total_score"] + 20

            # check for favicon-57.png (flag) in css
            res = re.findall(r'favicon-57.png', cssbody)
            if res:
                results["flagincss_detected"] = 20

            # # check for standard USWDS 1.x colors in css
            # # (testing showed that this did not detect more, and it also caused FPs)
            # res = re.findall(r'#0071bc|#205493|#112e51|#212121|#323a45|#aeb0b5', cssbody)
            # if res:
            #     results["stdcolors_detected"] += len(res)

    # generate a final score
    # The quick-n-dirty score is to add up all the number of things we found.
    for i in results.keys():
        if isinstance(results[i], int) and i != 'total_score':
            results["total_score"] += results[i]
    if results["total_score"] < 0:
        results["total_score"] = 0

    # add the status code and domain
    results["status_code"] = response.status_code
    results["domain"] = domain
    if results["uswdsversion"] == 0:
        results["uswdsversion"] = ""

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
    # "official_website_detected",
    "uswds_detected",
    "usa_detected",
    "flag_detected",
    "flagincss_detected",
    "sourcesansfont_detected",
    "uswdsincss_detected",
    "merriweatherfont_detected",
    "publicsansfont_detected",
    "uswdsversion",
    "tables",
    "total_score"
]
