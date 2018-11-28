import logging
from typing import Any

import dns.resolver

from utils import FAST_CACHE_KEY

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


# Check the fastcache to determine if we have already tested any of
# the mail servers when scanning other domains.
def init_domain(domain, environment, options):
    cached_data = {}

    if not options['no_fast_cache']:
        #
        # Grab the MX records so we can check if the corresponding
        # mail servers have already been scanned.
        #

        timeout = int(options.get('timeout', default_timeout))
        smtp_ports = {
            int(port)
            for port in options.get('smtp_ports', default_smtp_ports).split(',')
        }
        dns_hostnames = options.get('dns', default_dns).split(',')
        # Note that we _do not_ use the system configuration in
        # /etc/resolv.conf.
        resolver = dns.resolver.Resolver(configure=False)
        # This is a setting that controls whether we retry DNS servers
        # if we receive a SERVFAIL response from them.  We set this to
        # False because, unless the reason for the SERVFAIL is truly
        # temporary and resolves before trustymail finishes scanning
        # the domain, this can obscure the potentially informative
        # SERVFAIL error as a DNS timeout because of the way
        # dns.resolver.query() is written.  See
        # http://www.dnspython.org/docs/1.14.0/dns.resolver-pysrc.html#Resolver.query.
        resolver.retry_servfail = False
        # Set some timeouts.  The timeout should be less than or equal
        # to the lifetime, but longer than the time a DNS server takes
        # to return a SERVFAIL (since otherwise it's possible to get a
        # DNS timeout when you should be getting a SERVFAIL.)  See
        # http://www.dnspython.org/docs/1.14.0/dns.resolver-pysrc.html#Resolver.query
        # and
        # http://www.dnspython.org/docs/1.14.0/dns.resolver-pysrc.html#Resolver._compute_timeout.
        resolver.timeout = float(timeout)
        resolver.lifetime = float(timeout)
        resolver.nameservers = dns_hostnames.split(',')
        # Use TCP, since we care about the content and correctness of
        # the records more than whether their records fit in a single
        # UDP packet.
        mx_records = resolver.query(domain.domain_name, 'MX', tcp=True)

        # The rstrip is because dnspython's string representation of
        # the record will contain a trailing period if it is a FQDN.
        mail_servers_to_test = {
            '{}:{}'.format(record.exchange.to_text().rstrip('.').lower(), port)
            for record in mx_records
            for port in smtp_ports.split(',')
        }
        # Check if we already have results for all mail servers to be
        # tested, possibly from a different domain.
        #
        # I have found that SMTP servers (as compared to HTTP/HTTPS
        # servers) are MUCH more sensitive to having multiple
        # connections made to them.  In testing the various cyphers we
        # make a lot of connections, and multiple government domains
        # often use the same SMTP servers, so it makes sense to check
        # if we have already hit this mail server when testing a
        # different domain.
        #
        # Note that we only use the cached data if we have data for
        # _every_ mail server associated with this domain.
        cached = FAST_CACHE_KEY in environment and all([
            mail_server in environment[FAST_CACHE_KEY]
            for mail_server in mail_servers_to_test
        ])
        if cached:
            logging.debug('Using cached data for {} mail servers'.format(domain))
            cached_data = {
                mail_server: environment[FAST_CACHE_KEY][mail_server]
                for mail_server in mail_servers_to_test
            }

    return {
        'cached_data': cached_data
    }


def scan(domain, environment, options):
    # Save the old logging level
    old_log_level = logging.getLogger().getEffectiveLevel()
    log_level = logging.WARN
    if options.get('debug', False):
        log_level = logging.DEBUG
    logging.basicConfig(format='%(asctime)-15s %(message)s', level=log_level)

    timeout = int(options.get('timeout', default_timeout))
    smtp_timeout = int(options.get('smtp_timeout', default_smtp_timeout))
    smtp_localhost = options.get('smtp_localhost', None)
    smtp_ports = {
        int(port)
        for port in options.get('smtp_ports', default_smtp_ports).split(',')
    }
    dns_hostnames = options.get('dns', default_dns).split(',')

    # --starttls implies --mx
    if options.get('starttls', False):
        options.set('mx', True)

    # Whether or not to use an in-memory SMTP cache.  For runs against
    # a single domain this will not make any difference, unless an MX
    # record is duplicated.
    smtp_cache = not options.get('no_smtp_cache', False)

    # User might not want every scan performed.
    scan_types = {
        'mx': options.get('mx', False),
        'starttls': options.get('starttls', False),
        'spf': options.get('spf', False),
        'dmarc': options.get('dmarc', False)
    }

    # Do we need to perform the MX and STARTTLS scans or do we have
    # already-cached data for that?
    #
    # Since we only provide cached data if we have data for _every_
    # mail server associated with the domain, it suffices to check if
    # cached_data is empty here,
    cached_data = environment.get('cached_data', {})
    use_cached_data = len(cached_data) >= 0
    if use_cached_data:
        # This is true because we want the actual MX records
        scan_types['mx'] = True
        scan_types['starttls'] = False

    import trustymail
    # Monkey patching trustymail to make it cache the PSL where we
    # want
    trustymail.PublicSuffixListFilename = 'cache/public-suffix-list.txt'
    if environment['scan_method'] == 'lambda':
        # Monkey patching trustymail to make the PSL cache read-only
        trustymail.PublicSuffixListReadOnly = True
    import trustymail.trustymail as tmail

    data = tmail.scan(domain, timeout, smtp_timeout, smtp_localhost, smtp_ports, smtp_cache, scan_types, dns_hostnames).generate_results()

    if not data:
        logging.warning("\ttrustymail scan failed, skipping.")

    # TODO: Cram the cached data into data

    # Reset the logging level
    logging.getLogger().setLevel(old_log_level)

    return data


def post_scan(domain: str, data: Any, environment: dict, options: dict):
    """Post-scan hook for trustymail

    Add mail server results to the fast cache, keyed by the
    concatenation of the mail server and port.  Do not update if an
    appropriate cache entry appeared while we were running, since the
    earlier entry is more likely to be correct because it is less
    likely to have triggered any defenses that are in place.

    Parameters
    ----------
    domain : str
        The domain being scanned.

    data : Any
        The result returned by the scan function for the domain
        currently being scanned.

    environment: dict
        The environment data structure associated with the scan that
        produced the results in data.

    options: dict
        The CLI options.

    """
    # Make sure fast caching hasn't been disabled
    if not options['no_fast_cache'] and data is not None:
        if FAST_CACHE_KEY not in environment:
            environment[FAST_CACHE_KEY] = {}

        mail_servers = data['Mail Servers']
        ports = data['Mail Server Ports Tested']
        smtp_results = data['Domain Supports SMTP Results']
        starttls_results = data['Domain Supports STARTTLS Results']
        

        fast_cache = environment[FAST_CACHE_KEY]
        # Add the SMTP host results to the fast cache
        for record in data:
            if record['starttls_smtp']:
                key = '{}:{}'.format(record['hostname'],
                                     record['port'])
                # Avoid overwriting the cached data if someone
                # else wrote it while we were running
                if key not in fast_cache:
                    fast_cache[key] = record


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
