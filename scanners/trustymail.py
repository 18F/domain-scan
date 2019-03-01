import logging
from typing import Any, List

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
        dns_hostnames = list_from_dict_key(options, 'dns')
        resolver = dns.resolver.Resolver(configure=not dns_hostnames)
        if dns_hostnames:
            resolver.nameservers = dns_hostnames
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
        # Use TCP, since we care about the content and correctness of
        # the records more than whether their records fit in a single
        # UDP packet.
        try:
            mx_records = resolver.query(domain, 'MX', tcp=True)
        except (dns.resolver.NoNameservers, dns.resolver.NXDOMAIN) as error:
            # The NoNameServers exception means that we got a SERVFAIL
            # response.  These responses are almost always permanent,
            # not temporary, so let's treat the domain as not live.
            logging.info('No MX records for domain {}: {}'.format(domain, error))
            mx_records = []
        except (dns.resolver.NoAnswer, dns.exception.Timeout) as error:
            logging.warning('Encountered an error retrieving MX records for domain {}: {}.'.format(domain, error))
            mx_records = []

        # The rstrip is because dnspython's string representation of
        # the record will contain a trailing period if it is a FQDN.
        mail_servers_to_test = {
            '{}:{}'.format(record.exchange.to_text().rstrip('.').lower(), port)
            for record in mx_records
            for port in smtp_ports
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
    dns_hostnames = list_from_dict_key(options, 'dns')

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
    # If the user listed no specific scans then perform all scans.  It
    # is necessary to do this here in case use_cached_data is True and
    # we set scan_types['mx'] to True below.
    if all([not scan_types[key] for key in scan_types]):
        for key in scan_types:
            scan_types[key] = True

    # Do we need to perform the MX and STARTTLS scans or do we have
    # already-cached data for that?
    #
    # Since we only provide cached data if we have data for _every_
    # mail server associated with the domain, it suffices to check if
    # cached_data is empty here,
    cached_data = environment.get('cached_data', {})
    use_cached_data = len(cached_data) > 0
    if use_cached_data:
        # This is true because we want the actual MX records, even
        # though we already did the DNS query in init_domain()
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

    data = tmail.scan(domain, timeout, smtp_timeout, smtp_localhost,
                      smtp_ports, smtp_cache, scan_types,
                      dns_hostnames)

    if not data:
        logging.warning("\ttrustymail scan failed, skipping.")

    # Crowbar in the cached data, if necessary
    if use_cached_data:
        ports = set()
        servers = set()
        for mail_server in cached_data:
            # Grab the server and port
            server_and_port = mail_server.split(':')
            server = server_and_port[0]
            port = server_and_port[1]
            servers.add(server)
            ports.add(port)

            cached_result = cached_data[mail_server]
            data.starttls_results[mail_server] = {
                'supports_smtp': cached_result['supports_smtp'],
                'starttls': cached_result['starttls']
            }

        for server in servers:
            data.mail_servers.append(server)
        for port in ports:
            data.ports_tested.add(port)

    # Reset the logging level
    logging.getLogger().setLevel(old_log_level)

    return data.generate_results()


def list_from_dict_key(d: dict, k: str, delim: str=',') -> List[str]:
    """Extract a list from a delimited string in a dictionary.

    Parameters
    ----------
    d : dict
        The dictionary containing the delimited string.

    k : str
        The key under which the delimited value is stored in the
        dictionary.

    delim : str
        The delimiter for the delimited string.

    Returns
    -------
    List[str]: The list extracted from the delimited string, or an
    empty list if the dictionary key is None or does not exist.
    """
    ans = []
    s = d.get(k, None)
    if s is not None:
        ans = s.split(',')

    return ans


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

        servers = list_from_dict_key(data, 'Mail Servers')
        ports = [
            int(port) for port in list_from_dict_key(data,
                                                     'Mail Server Ports Tested')
        ]
        smtp_results = list_from_dict_key(data,
                                          'Domain Supports SMTP Results')
        starttls_results = list_from_dict_key(data,
                                              'Domain Supports STARTTLS Results')

        fast_cache = environment[FAST_CACHE_KEY]
        for server in servers:
            for port in ports:
                mail_server = '{}:{}'.format(server, port)
                # Avoid overwriting the cached data if someone
                # else wrote it while we were running
                if mail_server not in fast_cache:
                    fast_cache[mail_server] = {
                        'supports_smtp': mail_server in smtp_results,
                        'starttls': mail_server in starttls_results
                    }


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
