import logging

###
# Inspect a site's DNS Mail configuration using DHS NCATS' trustymail tool.
###

# default to a long timeout
default_timeout = 30

# This is the same default timeout used in trustymail/scripts/trustymail
default_smtp_timeout = 5

# These are the same default ports used in trustymail/scripts/trustymail
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

    import trustymail.trustymail as tmail
    import trustymail
    if environment['scan_method'] == 'local':
        # Local scanning
        #
        # Monkey patching trustymail to make it cache the PSL where we want
        trustymail.PublicSuffixListFilename = 'cache/public-suffix-list.txt'
    else:
        # Lambda scanning
        #
        # Monkey patching trustymail to make it cache the PSL where we want
        trustymail.PublicSuffixListFilename = './public-suffix-list.txt'
        # Monkey patching trustymail to make the PSL cache read-only
        trustymail.PublicSuffixListReadOnly = True

    data = tmail.scan(domain, timeout, smtp_timeout, smtp_localhost, smtp_ports, smtp_cache, scan_types, dns_hostnames).generate_results()

    if not data:
        logging.warn("\ttrustymail scan failed, skipping.")

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
    "DMARC Results on Base Domain", "DMARC Policy", "DMARC Policy Percentage",
    "DMARC Aggregate Report URIs", "DMARC Forensic Report URIs",
    "DMARC Has Aggregate Report URI", "DMARC Has Forensic Report URI",
    "Syntax Errors", "Debug Info"
]
