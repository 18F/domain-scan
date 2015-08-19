import logging
from scanners import utils
import json
import os
import sys
import urllib.request
import urllib.parse
import base64
import re

##
# == subdomains ==
#
# Say whether a subdomain redirects within the domain but to another subdomain.
# Say whether a subdomain has all numbers in its leftmost subdomain.
# Say whether a subdomain has any numbers in its leftmost subdomain.
##

def scan(domain, options):
    logging.debug("[%s][subdomains]" % domain)

    # This only looks at subdomains, remove second-level root's and www's.
    if re.sub("^www.", "", domain) == base_domain_for(domain):
        logging.debug("\tSkipping, second-level domain.")
        return None

    # If inspection data exists, check to see if we can skip.
    inspection = utils.data_for(domain, "inspect")
    if not inspection:
        logging.debug("\tSkipping, wasn't inspected.")
        return None

    if not inspection.get("up"):
        logging.debug("\tSkipping, subdomain wasn't up during inspection.")
        return None

    # If the subdomain redirects anywhere, see if it redirects within the domain
    endpoint = inspection["endpoints"][inspection.get("canonical_protocol")]["root"]
    if endpoint.get("redirect_to"):

        sub_original = domain
        base_original = base_domain_for(domain)

        sub_redirect = urllib.parse.urlparse(endpoint["redirect_to"]).hostname
        sub_redirect = re.sub("^www.", "", sub_redirect) # discount www redirects
        base_redirect = base_domain_for(sub_redirect)
        
        redirected_external = base_original != base_redirect
        redirected_subdomain = (
            (base_original == base_redirect) and 
            (sub_original != sub_redirect)
        )
    else:
        redirected_external = False
        redirected_subdomain = False

    status_code = endpoint.get("status", None)
    wildcard = check_wildcard(domain, options)
    
    if (wildcard['wild']) and (wildcard['wild'] == wildcard['itself']):
        matched_wild = True
    else:
        matched_wild = False
    
    yield [
        base_original,
        inspection["up"],
        redirected_external,
        redirected_subdomain,
        any_numbers(subdomains_for(domain)),
        status_code,
        matched_wild
    ]


headers = [
    "Base Domain",
    "Live",
    "Redirects Externally",
    "Redirects To Subdomain",
    "Any Numbers",
    "HTTP Status Code",
    "Matched Wildcard DNS"
]

# does a number appear anywhere in this thing
def any_numbers(string):
    return (re.search(r'\d', string) is not None)

# return base domain for a subdomain
def base_domain_for(subdomain):
    return str.join(".", subdomain.split(".")[-2:])

# return everything to the left of the base domain
def subdomains_for(subdomain):
    return str.join(".", subdomain.split(".")[:-2])

# return wildcard domain for a given subdomain
# e.g. abc.mountains.gov -> *.mountains.gov
def wildcard_for(subdomain):
    return "*." + str.join(".", subdomain.split(".")[1:])

def check_wildcard(subdomain, options):

    wildcard = wildcard_for(subdomain)

    cache = utils.cache_path(subdomain, "subdomains")
    if (options.get("force", False) is False) and (os.path.exists(cache)):
        logging.debug("\tCached.")
        raw = open(cache).read()
        data = json.loads(raw)

    else:
        logging.debug("\t dig +short '%s'" % wildcard)
        raw_wild = utils.unsafe_execute("dig +short '%s'" % wildcard)

        if raw_wild == "":
            raw_wild = None
            raw_self = None
        else:
            logging.debug("\t dig +short '%s'" % subdomain)
            raw_self = utils.unsafe_execute("dig +short '%s'" % subdomain)

        if raw_wild:
            parsed_wild = raw_wild.split("\n")
            parsed_wild.sort()
        else:
            parsed_wild = None

        if raw_self:
            parsed_self = raw_self.split("\n")
            parsed_self.sort()
        else:
            parsed_self = None

        data = {'response': {'wild': parsed_wild, 'itself': parsed_self}}
        utils.write(
            utils.json_for(data),
            cache
        )

    return data['response']
