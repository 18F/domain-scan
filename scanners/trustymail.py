import logging
from scanners import utils
import os
import json

from trustymail import trustymail

###
# Inspect a site's DNS Mail configuration using DHS NCATS' trustymail tool.

# TODO: move to trustymail's Python API
command = os.environ.get("TRUSTYMAIL_PATH", "trustymail")

# default to a long timeout
timeout = 30

# Advertise lambda support
lambda_support = True


def scan(domain, environment, options):
    # if options.get("debug", False):
    #     full_command.append("--debug")

    data = trustymail.scan(domain, timeout, 5, None, {25, 465, 587}, True, {'mx': True, 'starttls': True, 'spf': True, 'dmarc': True}, ['8.8.8.8', '8.8.4.4']).generate_results()
    
    if not data:
        logging.warn("\ttrustymail command failed, skipping.")

    return data


def to_rows(data):
    row = []
    for field in headers:
        value = data[field]
        row.append(value)

    return [row]


headers = [
    "Live",
    "MX Record", "Mail Servers", "Mail Server Ports Tested",
    "Domain Supports SMTP", "Domain Supports SMTP Results",
    "Domain Supports STARTTLS", "Domain Supports STARTTLS Results",
    "SPF Record", "Valid SPF", "SPF Results",
    "DMARC Record", "Valid DMARC", "DMARC Results",
    "DMARC Record on Base Domain", "Valid DMARC Record on Base Domain",
    "DMARC Results on Base Domain", "DMARC Policy",
    "Syntax Errors", "Debug Info"
]
