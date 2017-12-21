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
default_timeout = 30

# This is the same default timeout used in trustymail/cli.py
default_smtp_timeout = 5

# These are the same default ports used in trustymail.cli.py
default_smtp_ports = '25,465,587'

# We want to enforce the use of Google DNS by default.  This gives
# more consistent results.
default_dns = '8.8.8.8,8.8.4.4'

# Advertise lambda support
lambda_support = True


def scan(domain, environment, options):
    # Save the old logging level
    old_log_level = logging.getLogger().getEffectiveLevel()
    log_level = logging.WARN
    if options.get('debug', False):
        log_level = logging.DEBUG
    logging.basicConfig(format='%(asctime)-15s %(message)s', level=log_level)

    timeout = int(options.get('timeout', default_timeout))

    smtp_timeout = int(options.get('smtp-timeout', default_smtp_timeout))

    smtp_localhost = options.get('smtp-localhost', None)

    smtp_ports = {int(port) for port in options.get('smtp-ports', default_smtp_ports).split(',')}

    dns_hostnames = options.get('dns', default_dns).split(',')

    # --starttls implies --mx
    if options.get('starttls', False):
        options.set('mx', True)

    # Whether or not to use an in-memory SMTP cache.  For runs against
    # a single domain this will not make any difference, unless an MX
    # record is duplicated.
    smtp_cache = not options.get('no-smtp-cache', False)

    # User might not want every scan performed.
    scan_types = {
        'mx': options.get('mx', False),
        'starttls': options.get('starttls', False),
        'spf': options.get('spf', False),
        'dmarc': options.get('dmarc', False)
    }

    data = trustymail.scan(domain, timeout, smtp_timeout, smtp_localhost, smtp_ports, smtp_cache, scan_types, dns_hostnames).generate_results()
    
    if not data:
        logging.warn("\ttrustymail command failed, skipping.")

    # Reset the logging level
    logging.getLogger().setLevel(old_log_level)

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
