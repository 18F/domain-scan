import logging
from scanners import utils
import json
import os


###
# == tls ==
#
# Inspect a site's valid TLS configuration using ssllabs-scan.
#
# If data exists for a domain from `inspect`, will check results
# and only process domains with valid HTTPS, or broken chains.
###

command = os.environ.get("PA11Y_PATH", "pa11y")
workers = 1

def scan(domain, options):
    cmd = [command, "18f.gsa.gov"]
    result = utils.scan(cmd)
    print (domain)
    print(result)
    yield [
        "foo",
        "bar",
        "baz"
    ]

headers = [
    "Errors",
    "Warnings",
    "Notices"
]