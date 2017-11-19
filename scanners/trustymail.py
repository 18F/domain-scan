import logging
from scanners import utils
import os
import json

###
# Inspect a site's DNS Mail configuration using DHS NCATS' trustymail tool.

# TODO: move to trustymail's Python API
command = os.environ.get("TRUSTYMAIL_PATH", "trustymail")

# default to a long timeout
timeout = 30


def scan(domain, environment, options):

    full_command = [
        command,
        domain,
        '--json',
        '--timeout', str(timeout),
        # Use Google DNS
        '--dns-hostnames', '8.8.8.8,8.8.4.4'
    ]

    if options.get("debug", False):
        full_command.append("--debug")

    raw = utils.scan(full_command)

    if not raw:
        logging.warn("\ttrustymail command failed, skipping.")
        return None

    data = json.loads(raw)

    # trustymail uses JSON arrays, even for single items.
    data = data[0]

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
    "Syntax Errors", "Errors"
]
