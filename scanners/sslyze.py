###
# Inspect a site's TLS configuration using sslyze.
#
# If data exists for a domain from `pshtt`, will check results
# and only process domains with valid HTTPS, or broken chains.
#
# Supported options:
#
# --sslyze-serial - If set, will use a synchronous (single-threaded
#   in-process) scanner. Defaults to true.
# --sslyze-certs - If set, will use the CertificateInfoScanner and
#   return certificate info. Defaults to true.
###

import logging
from typing import Any

from sslyze.server_connectivity_tester import ServerConnectivityTester, ServerConnectivityError
from sslyze.synchronous_scanner import SynchronousScanner
from sslyze.concurrent_scanner import ConcurrentScanner, PluginRaisedExceptionScanResult
from sslyze.plugins.openssl_cipher_suites_plugin import Tlsv10ScanCommand, Tlsv11ScanCommand, Tlsv12ScanCommand, Tlsv13ScanCommand, Sslv20ScanCommand, Sslv30ScanCommand
from sslyze.plugins.certificate_info_plugin import CertificateInfoScanCommand
from sslyze.ssl_settings import TlsWrappedProtocolEnum

import idna
import cryptography
import cryptography.hazmat.backends.openssl
from cryptography.hazmat.primitives.serialization import Encoding
from cryptography.hazmat.primitives.asymmetric import ec, dsa, rsa

from utils import FAST_CACHE_KEY, utils

# Number of seconds to wait during sslyze connection check.
# Not much patience here, and very willing to move on.
network_timeout = 5

# Advertise Lambda support
lambda_support = True


# If we have pshtt data, use it to skip some domains, and to adjust
# scan hostnames to canonical URLs where we can.
#
# If we have trustymail data, use it to identify any mail servers that
# support STARTTLS so we can scan them.
#
# Check the fastcache to determine if we have already tested any of
# the mail servers when scanning other domains.
def init_domain(domain, environment, options):
    hosts_to_scan = []
    cached_data = []
    cache_dir = options.get('_', {}).get('cache_dir', './cache')

    # If we have pshtt data, skip domains which pshtt saw as not
    # supporting HTTPS at all.
    if utils.domain_doesnt_support_https(domain, cache_dir=cache_dir):
        logging.warning('\tHTTPS not supported for {}'.format(domain))
    else:
        # If we have pshtt data and it says canonical endpoint uses
        # www and the given domain is bare, add www.
        if utils.domain_uses_www(domain, cache_dir=cache_dir):
            hostname = 'www.%s' % domain
        else:
            hostname = domain

        hosts_to_scan.append({
            'hostname': hostname,
            'port': 443,
            'starttls_smtp': False
        })

    # If we have trustymail data, see if there are any mail servers
    # that support STARTTLS that we should scan
    mail_servers_to_test = utils.domain_mail_servers_that_support_starttls(domain, cache_dir=cache_dir)
    for mail_server in mail_servers_to_test:
        # Check if we already have results for this mail server,
        # possibly from a different domain.
        #
        # I have found that SMTP servers (as compared to HTTP/HTTPS
        # servers) are MUCH more sensitive to having multiple
        # connections made to them.  In testing the various cyphers we
        # make a lot of connections, and multiple government domains
        # often use the same SMTP servers, so it makes sense to check
        # if we have already hit this mail server when testing a
        # different domain.
        cached_value = None
        if FAST_CACHE_KEY in environment:
            cached_value = environment[FAST_CACHE_KEY].get(mail_server, None)

        if cached_value is None:
            logging.debug('Adding {} to list to be scanned'.format(mail_server))
            hostname_and_port = mail_server.split(':')
            hosts_to_scan.append({
                'hostname': hostname_and_port[0],
                'port': int(hostname_and_port[1]),
                'starttls_smtp': True
            })
        else:
            logging.debug('Using cached data for {}'.format(mail_server))
            cached_data.append(cached_value)

    if not hosts_to_scan:
        logging.warning('\tNo hosts to scan for {}'.format(domain))

    return {
        'hosts_to_scan': hosts_to_scan,
        'cached_data': cached_data
    }


# Run sslyze on the given domain.
def scan(domain, environment, options):
    # Allow hostnames to be adjusted by init_domain
    default_host = {
        'hostname': domain,
        'port': 443,
        'starttls_smtp': False
    }

    retVal = []
    for host_to_scan in environment.get('hosts_to_scan', [default_host]):

        data = {
            'hostname': host_to_scan.get('hostname'),
            'port': host_to_scan.get('port'),
            'starttls_smtp': host_to_scan.get('starttls_smtp'),
            'protocols': {},
            'config': {},
            'certs': {},
            'errors': []
        }

        # Run the SSLyze scan on the given hostname.
        response = run_sslyze(data, environment, options)

        # Error condition.
        if response is None:
            error = "No valid target for scanning, couldn't connect."
            logging.warning(error)
            data['errors'].append(error)

        # Join all errors into a string before returning.
        data['errors'] = ' '.join(data['errors'])

        retVal.append(data)

    # Return the scan results together with the already-cached results
    # (if there were any)
    retVal.extend(environment['cached_data'])
    return retVal


def post_scan(domain: str, data: Any, environment: dict, options: dict):
    """Post-scan hook for sslyze

    Add SMTP results to the fast cache, keyed by the concatenation of
    the mail server and port.  Do not update if an appropriate cache
    entry appeared while we were running, since the earlier entry is
    more likely to be correct because it is less likely to have
    triggered any defenses that are in place.

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


# Given a response dict, turn it into CSV rows.
def to_rows(data):
    retVal = []
    for row in data:

        ev = row.get('certs', {}).get('ev', {})

        retVal.append([
            row['hostname'],
            row['port'],
            row['starttls_smtp'],

            row['protocols'].get('sslv2'), row['protocols'].get('sslv3'),
            row['protocols'].get('tlsv1.0'), row['protocols'].get('tlsv1.1'),
            row['protocols'].get('tlsv1.2'), row['protocols'].get('tlsv1.3'),

            row['config'].get('any_dhe'), row['config'].get('all_dhe'),
            row['config'].get('any_rc4'), row['config'].get('all_rc4'),
            row['config'].get('any_3des'),

            row['certs'].get('key_type'), row['certs'].get('key_length'),
            row['certs'].get('leaf_signature'),
            row['certs'].get('any_sha1_served'),
            row['certs'].get('any_sha1_constructed'),
            row['certs'].get('not_before'), row['certs'].get('not_after'),
            row['certs'].get('served_issuer'), row['certs'].get('constructed_issuer'),

            ev.get('asserted'), ev.get('trusted'),
            str.join(", ", ev.get('trusted_oids', [])),
            str.join(", ", ev.get('trusted_browsers', [])),

            row['certs'].get('is_symantec_cert'),
            row['certs'].get('symantec_distrust_date'),
            str.join(', ', row.get('ciphers', [])),

            row.get('errors')
        ])

    return retVal


headers = [
    "Scanned Hostname",
    "Scanned Port",
    "STARTTLS SMTP",
    "SSLv2", "SSLv3", "TLSv1.0", "TLSv1.1", "TLSv1.2", "TLSv1.3",

    "Any Forward Secrecy", "All Forward Secrecy",
    "Any RC4", "All RC4",
    "Any 3DES",

    "Key Type", "Key Length",
    "Signature Algorithm",
    "SHA-1 in Served Chain",
    "SHA-1 in Constructed Chain",
    "Not Before", "Not After",
    "Highest Served Issuer", "Highest Constructed Issuer",

    "Asserts EV", "Trusted for EV",
    "EV Trusted OIDs", "EV Trusted Browsers",

    "Is Symantec Cert", "Symantec Distrust Date",
    "Accepted Ciphers",

    "Errors"
]


# Get the relevant fields out of sslyze's JSON format.
#
# Certificate PEM data must be separately parsed using
# the Python cryptography module.

def run_sslyze(data, environment, options):
    # Each sslyze worker can use a sync or parallel mode.
    #
    # SynchronousScanner can show memory leaks when parsing certs,
    # so local scanning defaults to using ConcurrentScanner.
    #
    # And Lambda can't use multiprocessing.Queue, so in the cloud,
    # this default cannot be overridden.
    scan_method = environment.get("scan_method", "local")

    if scan_method == "lambda":
        sync = True
    else:
        sync = options.get("sslyze_serial", True)

    # Initialize either a synchronous or concurrent scanner.
    server_info, scanner = init_sslyze(data['hostname'], data['port'], data['starttls_smtp'], options, sync=sync)

    if server_info is None:
        data['errors'].append("Connectivity not established.")
        return data

    # Whether sync or concurrent, get responses for all scans.
    if sync:
        sslv2, sslv3, tlsv1, tlsv1_1, tlsv1_2, tlsv1_3, certs = scan_serial(scanner, server_info, data, options)
    else:
        sslv2, sslv3, tlsv1, tlsv1_1, tlsv1_2, tlsv1_3, certs = scan_parallel(scanner, server_info, data, options)

    # Only analyze protocols if all the scanners functioned.
    # Very difficult to draw conclusions if some worked and some did not.
    if sslv2 and sslv3 and tlsv1 and tlsv1_1 and tlsv1_2 and tlsv1_3:
        analyze_protocols_and_ciphers(data, sslv2, sslv3, tlsv1, tlsv1_1, tlsv1_2, tlsv1_3)

    if certs:
        data['certs'] = analyze_certs(certs)

    return data


def analyze_protocols_and_ciphers(data, sslv2, sslv3, tlsv1, tlsv1_1, tlsv1_2, tlsv1_3):
    data['protocols'] = {
        'sslv2': supported_protocol(sslv2),
        'sslv3': supported_protocol(sslv3),
        'tlsv1.0': supported_protocol(tlsv1),
        'tlsv1.1': supported_protocol(tlsv1_1),
        'tlsv1.2': supported_protocol(tlsv1_2),
        'tlsv1.3': supported_protocol(tlsv1_3)
    }

    accepted_ciphers = (
        (sslv2.accepted_cipher_list or []) +
        (sslv3.accepted_cipher_list or []) +
        (tlsv1.accepted_cipher_list or []) +
        (tlsv1_1.accepted_cipher_list or []) +
        (tlsv1_2.accepted_cipher_list or []) +
        (tlsv1_3.accepted_cipher_list or [])
    )
    data['ciphers'] = [cipher.name for cipher in accepted_ciphers]

    if len(accepted_ciphers) > 0:
        # Look at accepted cipher suites for RC4 or DHE.
        # This is imperfect, as the advertising of RC4 could discriminate based on client.
        # DHE and ECDHE may not remain the only forward secret options for TLS.
        any_rc4 = False
        any_dhe = False
        all_rc4 = True
        all_dhe = True
        any_3des = False

        for cipher in accepted_ciphers:
            name = cipher.openssl_name
            if "RC4" in name:
                any_rc4 = True
            else:
                all_rc4 = False

            if ("3DES" in name) or ("DES-CBC3" in name):
                any_3des = True

            if name.startswith("DHE-") or name.startswith("ECDHE-"):
                any_dhe = True
            else:
                all_dhe = False

        data['config']['any_rc4'] = any_rc4
        data['config']['all_rc4'] = all_rc4
        data['config']['any_dhe'] = any_dhe
        data['config']['all_dhe'] = all_dhe
        data['config']['any_3des'] = any_3des


def analyze_certs(certs):
    data = {'certs': {}}

    # Served chain.
    served_chain = certs.certificate_chain

    # Constructed chain may not be there if it didn't validate.
    constructed_chain = certs.verified_certificate_chain

    highest_served = parse_cert(served_chain[-1])
    issuer = cert_issuer_name(highest_served)

    if issuer:
        data['certs']['served_issuer'] = issuer
    else:
        data['certs']['served_issuer'] = "(None found)"

    if (constructed_chain and (len(constructed_chain) > 0)):
        highest_constructed = parse_cert(constructed_chain[-1])
        issuer = cert_issuer_name(highest_constructed)
        if issuer:
            data['certs']['constructed_issuer'] = issuer
        else:
            data['certs']['constructed_issuer'] = "(None constructed)"

    leaf = parse_cert(served_chain[0])
    leaf_key = leaf.public_key()

    if hasattr(leaf_key, "key_size"):
        data['certs']['key_length'] = leaf_key.key_size
    elif hasattr(leaf_key, "curve"):
        data['certs']['key_length'] = leaf_key.curve.key_size
    else:
        data['certs']['key_length'] = None

    if isinstance(leaf_key, rsa.RSAPublicKey):
        leaf_key_type = "RSA"
    elif isinstance(leaf_key, dsa.DSAPublicKey):
        leaf_key_type = "DSA"
    elif isinstance(leaf_key, ec.EllipticCurvePublicKey):
        leaf_key_type = "ECDSA"
    else:
        leaf_key_type == str(leaf_key.__class__)

    data['certs']['key_type'] = leaf_key_type

    # Signature of the leaf certificate only.
    data['certs']['leaf_signature'] = leaf.signature_hash_algorithm.name

    # Beginning and expiration dates of the leaf certificate
    data['certs']['not_before'] = leaf.not_valid_before
    data['certs']['not_after'] = leaf.not_valid_after

    any_sha1_served = False
    for cert in served_chain:
        if parse_cert(cert).signature_hash_algorithm.name == "sha1":
            any_sha1_served = True

    data['certs']['any_sha1_served'] = any_sha1_served

    if data['certs'].get('constructed_issuer'):
        data['certs']['any_sha1_constructed'] = certs.has_sha1_in_certificate_chain

    extensions = leaf.extensions
    oids = []
    try:
        ext = extensions.get_extension_for_class(cryptography.x509.extensions.CertificatePolicies)
        policies = ext.value
        for policy in policies:
            oids.append(policy.policy_identifier.dotted_string)
    except cryptography.x509.ExtensionNotFound:
        # If not found, just move on.
        pass

    data['certs']['ev'] = {
        'asserted': False,
        'trusted': False,
        'trusted_oids': [],
        'trusted_browsers': []
    }

    for oid in oids:

        # If it matches the generic EV OID, the certifciate is
        # asserting that it was issued following the EV guidelines.
        data['certs']['ev']['asserted'] = (oid == evg_oid)

        # Check which browsers for which the cert is marked as EV.
        browsers = []
        if oid in mozilla_ev:
            browsers.append("Mozilla")
        if oid in google_ev:
            browsers.append("Google")
        if oid in microsoft_ev:
            browsers.append("Microsoft")
        if oid in apple_ev:
            browsers.append("Apple")

        if len(browsers) > 0:
            data['certs']['ev']['trusted'] = True

            # Log each new OID we observe as marked for EV.
            if oid not in data['certs']['ev']['trusted_oids']:
                data['certs']['ev']['trusted_oids'].append(oid)

            # For all matching browsers, log each new one.
            for browser in browsers:
                if browser not in data['certs']['ev']['trusted_browsers']:
                    data['certs']['ev']['trusted_browsers'].append(browser)

    # Is this cert issued by Symantec?
    distrust_timeline = certs.symantec_distrust_timeline
    is_symantec_cert = (distrust_timeline is not None)
    data['certs']['is_symantec_cert'] = is_symantec_cert
    if is_symantec_cert:
        data['certs']['symantec_distrust_date'] = distrust_timeline.name
    else:
        data['certs']['symantec_distrust_date'] = None

    return data['certs']


# Given the cert sub-obj from the sslyze JSON, use
# the cryptography module to parse its PEM contents.
def parse_cert(cert):
    backend = cryptography.hazmat.backends.openssl.backend
    pem_bytes = cert.public_bytes(Encoding.PEM).decode('ascii').encode('utf-8')
    return cryptography.x509.load_pem_x509_certificate(pem_bytes, backend)


# Given a parsed cert from the cryptography module,
# get the issuer name as best as possible
def cert_issuer_name(parsed):
    attrs = parsed.issuer.get_attributes_for_oid(cryptography.x509.oid.NameOID.COMMON_NAME)
    if len(attrs) == 0:
        attrs = parsed.issuer.get_attributes_for_oid(cryptography.x509.oid.NameOID.ORGANIZATIONAL_UNIT_NAME)
    if len(attrs) == 0:
        return None
    return attrs[0].value


# Given CipherSuiteScanResult, whether the protocol is supported
def supported_protocol(result):
    return (len(result.accepted_cipher_list) > 0)


# SSlyze initialization boilerplate
def init_sslyze(hostname, port, starttls_smtp, options, sync=False):
    global network_timeout

    network_timeout = int(options.get("network_timeout", network_timeout))

    tls_wrapped_protocol = TlsWrappedProtocolEnum.PLAIN_TLS
    if starttls_smtp:
        tls_wrapped_protocol = TlsWrappedProtocolEnum.STARTTLS_SMTP

    try:
        # logging.debug("\tTesting connectivity with timeout of %is." % network_timeout)
        server_tester = ServerConnectivityTester(hostname=hostname, port=port, tls_wrapped_protocol=tls_wrapped_protocol)
        server_info = server_tester.perform(network_timeout=network_timeout)
    except ServerConnectivityError:
        logging.warning("\tServer connectivity not established during test.")
        return None, None
    except Exception as err:
        utils.notify(err)
        logging.warning("\tUnknown exception when performing server connectivity info.")
        return None, None

    if sync:
        scanner = SynchronousScanner(network_timeout=network_timeout)
    else:
        scanner = ConcurrentScanner(network_timeout=network_timeout)

    return server_info, scanner


# Run each scan in-process, one at a time.
# Takes longer, but no multi-process funny business.
def scan_serial(scanner, server_info, data, options):

    logging.debug("\tRunning scans in serial.")
    logging.debug("\t\tSSLv2 scan.")
    sslv2 = scanner.run_scan_command(server_info, Sslv20ScanCommand())
    logging.debug("\t\tSSLv3 scan.")
    sslv3 = scanner.run_scan_command(server_info, Sslv30ScanCommand())
    logging.debug("\t\tTLSv1.0 scan.")
    tlsv1 = scanner.run_scan_command(server_info, Tlsv10ScanCommand())
    logging.debug("\t\tTLSv1.1 scan.")
    tlsv1_1 = scanner.run_scan_command(server_info, Tlsv11ScanCommand())
    logging.debug("\t\tTLSv1.2 scan.")
    tlsv1_2 = scanner.run_scan_command(server_info, Tlsv12ScanCommand())
    logging.debug("\t\tTLSv1.3 scan.")
    tlsv1_3 = scanner.run_scan_command(server_info, Tlsv13ScanCommand())

    certs = None
    if options.get("sslyze_certs", True) is True:

        try:
            logging.debug("\t\tCertificate information scan.")
            certs = scanner.run_scan_command(server_info, CertificateInfoScanCommand())
        # Let generic exceptions bubble up.
        except idna.core.InvalidCodepoint:
            logging.warning(utils.format_last_exception())
            data['errors'].append("Invalid certificate/OCSP for this domain.")
            certs = None
    else:
        certs = None

    logging.debug("\tDone scanning.")

    return sslv2, sslv3, tlsv1, tlsv1_1, tlsv1_2, tlsv1_3, certs


# Run each scan in parallel, using multi-processing.
# Faster, but can generate many processes.
def scan_parallel(scanner, server_info, data, options):
    logging.debug("\tRunning scans in parallel.")

    def queue(command):
        try:
            return scanner.queue_scan_command(server_info, command)
        except OSError:
            text = ("OSError - likely too many processes and open files.")
            data['errors'].append(text)
            logging.warning("%s\n%s" % (text, utils.format_last_exception()))
            return None, None, None, None, None, None, None
        except Exception:
            text = ("Unknown exception queueing sslyze command.\n%s" % utils.format_last_exception())
            data['errors'].append(text)
            logging.warning(text)
            return None, None, None, None, None, None, None

    # Initialize commands and result containers
    sslv2, sslv3, tlsv1, tlsv1_1, tlsv1_2, tlsv1_3, certs = None, None, None, None, None, None

    # Queue them all up
    queue(Sslv20ScanCommand())
    queue(Sslv30ScanCommand())
    queue(Tlsv10ScanCommand())
    queue(Tlsv11ScanCommand())
    queue(Tlsv12ScanCommand())
    queue(Tlsv13ScanCommand())

    if options.get("sslyze-certs", True) is True:
        queue(CertificateInfoScanCommand())

    # Reassign them back to predictable places after they're all done
    was_error = False
    for result in scanner.get_results():
        try:
            if isinstance(result, PluginRaisedExceptionScanResult):
                error = ("Scan command failed: %s" % result.as_text())
                logging.warning(error)
                data['errors'].append(error)
                return None, None, None, None, None, None, None

            if type(result.scan_command) == Sslv20ScanCommand:
                sslv2 = result
            elif type(result.scan_command) == Sslv30ScanCommand:
                sslv3 = result
            elif type(result.scan_command) == Tlsv10ScanCommand:
                tlsv1 = result
            elif type(result.scan_command) == Tlsv11ScanCommand:
                tlsv1_1 = result
            elif type(result.scan_command) == Tlsv12ScanCommand:
                tlsv1_2 = result
            elif type(result.scan_command) == Tlsv13ScanCommand:
                tlsv1_3 = result
            elif type(result.scan_command) == CertificateInfoScanCommand:
                certs = result
            else:
                error = "Couldn't match scan result with command! %s" % result
                logging.warning("\t%s" % error)
                data['errors'].append(error)
                was_error = True

        except Exception:
            was_error = True
            text = ("Exception inside async scanner result processing.\n%s" % utils.format_last_exception())
            data['errors'].append(text)
            logging.warning("\t%s" % text)

    # There was an error during async processing.
    if was_error:
        return None, None, None, None, None, None, None

    logging.debug("\tDone scanning.")

    return sslv2, sslv3, tlsv1, tlsv1_1, tlsv1_2, tlsv1_3, certs


# EV Guidelines OID
evg_oid = "2.23.140.1.1"

# Google source:
# https://cs.chromium.org/chromium/src/net/cert/ev_root_ca_metadata.cc?sq=package:chromium&dr=C

google_ev = [
    "1.2.392.200091.100.721.1",
    "1.2.616.1.113527.2.5.1.1",
    "1.3.159.1.17.1",
    "1.3.171.1.1.10.5.2",
    "1.3.6.1.4.1.13177.10.1.3.10",
    "1.3.6.1.4.1.14370.1.6",
    "1.3.6.1.4.1.14777.6.1.1",
    "1.3.6.1.4.1.14777.6.1.2",
    "1.3.6.1.4.1.17326.10.14.2.1.2",
    "1.3.6.1.4.1.17326.10.14.2.2.2",
    "1.3.6.1.4.1.17326.10.8.12.1.2",
    "1.3.6.1.4.1.17326.10.8.12.2.2",
    "1.3.6.1.4.1.22234.2.5.2.3.1",
    "1.3.6.1.4.1.23223.1.1.1",
    "1.3.6.1.4.1.29836.1.10",
    "1.3.6.1.4.1.34697.2.1",
    "1.3.6.1.4.1.34697.2.2",
    "1.3.6.1.4.1.34697.2.3",
    "1.3.6.1.4.1.34697.2.4",
    "1.3.6.1.4.1.40869.1.1.22.3",
    "1.3.6.1.4.1.4146.1.1",
    "1.3.6.1.4.1.4788.2.202.1",
    "1.3.6.1.4.1.6334.1.100.1",
    "1.3.6.1.4.1.6449.1.2.1.5.1",
    "1.3.6.1.4.1.782.1.2.1.8.1",
    "1.3.6.1.4.1.7879.13.24.1",
    "1.3.6.1.4.1.8024.0.2.100.1.2",
    "2.16.156.112554.3",
    "2.16.528.1.1003.1.2.7",
    "2.16.578.1.26.1.3.3",
    "2.16.756.1.83.21.0",
    "2.16.756.1.89.1.2.1.1",
    "2.16.756.5.14.7.4.8",
    "2.16.792.3.0.4.1.1.4",
    "2.16.840.1.113733.1.7.23.6",
    "2.16.840.1.113733.1.7.48.1",
    "2.16.840.1.114028.10.1.2",
    "2.16.840.1.114171.500.9",
    "2.16.840.1.114404.1.1.2.4.1",
    "2.16.840.1.114412.2.1",
    "2.16.840.1.114413.1.7.23.3",
    "2.16.840.1.114414.1.7.23.3",
    "2.16.840.1.114414.1.7.24.3"
]

# Mozilla source:
# https://dxr.mozilla.org/mozilla-central/source/security/certverifier/ExtendedValidation.cpp

mozilla_ev = [
    "1.2.156.112559.1.1.6.1",
    "1.2.392.200091.100.721.1",
    "1.2.616.1.113527.2.5.1.1",
    "1.3.159.1.17.1",
    "1.3.171.1.1.10.5.2",
    "1.3.6.1.4.1.13177.10.1.3.10",
    "1.3.6.1.4.1.14370.1.6",
    "1.3.6.1.4.1.14777.6.1.1",
    "1.3.6.1.4.1.14777.6.1.2",
    "1.3.6.1.4.1.17326.10.14.2.1.2",
    "1.3.6.1.4.1.17326.10.8.12.1.2",
    "1.3.6.1.4.1.22234.2.14.3.11",
    "1.3.6.1.4.1.22234.2.5.2.3.1",
    "1.3.6.1.4.1.22234.3.5.3.1",
    "1.3.6.1.4.1.22234.3.5.3.2",
    "1.3.6.1.4.1.34697.2.1",
    "1.3.6.1.4.1.34697.2.2",
    "1.3.6.1.4.1.34697.2.3",
    "1.3.6.1.4.1.34697.2.4",
    "1.3.6.1.4.1.40869.1.1.22.3",
    "1.3.6.1.4.1.4146.1.1",
    "1.3.6.1.4.1.4788.2.202.1",
    "1.3.6.1.4.1.6334.1.100.1",
    "1.3.6.1.4.1.6449.1.2.1.5.1",
    "1.3.6.1.4.1.782.1.2.1.8.1",
    "1.3.6.1.4.1.7879.13.24.1",
    "1.3.6.1.4.1.8024.0.2.100.1.2",
    "2.16.156.112554.3",
    "2.16.528.1.1003.1.2.7",
    "2.16.578.1.26.1.3.3",
    "2.16.756.1.89.1.2.1.1",
    "2.16.756.5.14.7.4.8",
    "2.16.792.3.0.4.1.1.4",
    "2.16.840.1.113733.1.7.23.6",
    "2.16.840.1.113733.1.7.48.1",
    "2.16.840.1.114028.10.1.2",
    "2.16.840.1.114404.1.1.2.4.1",
    "2.16.840.1.114412.2.1",
    "2.16.840.1.114413.1.7.23.3",
    "2.16.840.1.114414.1.7.23.3"
]


# Microsoft source:
# https://github.com/PeculiarVentures/tl-create
# Filtered to --microsoft with --for of SERVER_AUTH.

microsoft_ev = [
    "0.4.0.2042.1.4",
    "0.4.0.2042.1.5",
    "1.2.156.112559.1.1.6.1",
    "1.2.156.112559.1.1.7.1",
    "1.2.156.112570.1.1.3",
    "1.2.392.200091.100.721.1",
    "1.2.40.0.17.1.22",
    "1.2.616.1.113527.2.5.1.1",
    "1.2.616.1.113527.2.5.1.7",
    "1.3.159.1.17.1",
    "1.3.171.1.1.1.10.5",
    "1.3.171.1.1.10.5.2",
    "1.3.6.1.4.1.13177.10.1.3.10",
    "1.3.6.1.4.1.14370.1.6",
    "1.3.6.1.4.1.14777.6.1.1",
    "1.3.6.1.4.1.14777.6.1.2",
    "1.3.6.1.4.1.15096.1.3.1.51.2",
    "1.3.6.1.4.1.15096.1.3.1.51.4",
    "1.3.6.1.4.1.17326.10.14.2.1.2",
    "1.3.6.1.4.1.17326.10.16.3.6.1.3.2.1",
    "1.3.6.1.4.1.17326.10.16.3.6.1.3.2.2",
    "1.3.6.1.4.1.17326.10.8.12.1.1",
    "1.3.6.1.4.1.17326.10.8.12.1.2",
    "1.3.6.1.4.1.18332.55.1.1.2.12",
    "1.3.6.1.4.1.18332.55.1.1.2.22",
    "1.3.6.1.4.1.22234.2.14.3.11",
    "1.3.6.1.4.1.22234.2.5.2.3.1",
    "1.3.6.1.4.1.22234.3.5.3.1",
    "1.3.6.1.4.1.22234.3.5.3.2",
    "1.3.6.1.4.1.23223.1.1.1",
    "1.3.6.1.4.1.29836.1.10",
    "1.3.6.1.4.1.311.94.1.1",
    "1.3.6.1.4.1.34697.2.1",
    "1.3.6.1.4.1.34697.2.2",
    "1.3.6.1.4.1.34697.2.3",
    "1.3.6.1.4.1.34697.2.4",
    "1.3.6.1.4.1.36305.2",
    "1.3.6.1.4.1.38064.1.1.1.0",
    "1.3.6.1.4.1.40869.1.1.22.3",
    "1.3.6.1.4.1.4146.1.1",
    "1.3.6.1.4.1.4146.1.2",
    "1.3.6.1.4.1.4788.2.202.1",
    "1.3.6.1.4.1.6334.1.100.1",
    "1.3.6.1.4.1.6449.1.2.1.5.1",
    "1.3.6.1.4.1.782.1.2.1.8.1",
    "1.3.6.1.4.1.7879.13.24.1",
    "1.3.6.1.4.1.8024.0.2.100.1.2",
    "2.16.156.112554.3",
    "2.16.528.1.1003.1.2.7",
    "2.16.578.1.26.1.3.3",
    "2.16.756.1.17.3.22.32",
    "2.16.756.1.17.3.22.34",
    "2.16.756.1.83.21.0",
    "2.16.756.1.89.1.2.1.1",
    "2.16.792.3.0.4.1.1.4",
    "2.16.840.1.113733.1.7.23.6",
    "2.16.840.1.113733.1.7.48.1",
    "2.16.840.1.113839.0.6.9",
    "2.16.840.1.114028.10.1.2",
    "2.16.840.1.114404.1.1.2.4.1",
    "2.16.840.1.114412.2.1",
    "2.16.840.1.114413.1.7.23.3",
    "2.16.840.1.114414.1.7.23.3",
    "2.16.840.1.114414.1.7.24.2",
    "2.16.840.1.114414.1.7.24.3"
]

# Apple source:
# https://github.com/PeculiarVentures/tl-create
# Filtered to --apple with a --for of SERVER_AUTH.

apple_ev = [
    "1.2.250.1.177.1.18.2.2",
    "1.2.392.200091.100.721.1",
    "1.2.616.1.113527.2.5.1.1",
    "1.3.159.1.17.1",
    "1.3.6.1.4.1.13177.10.1.3.10",
    "1.3.6.1.4.1.14370.1.6",
    "1.3.6.1.4.1.14777.6.1.1",
    "1.3.6.1.4.1.14777.6.1.2",
    "1.3.6.1.4.1.17326.10.14.2.1.2",
    "1.3.6.1.4.1.17326.10.8.12.1.2",
    "1.3.6.1.4.1.18332.55.1.1.2.22",
    "1.3.6.1.4.1.22234.2.14.3.11",
    "1.3.6.1.4.1.22234.2.5.2.3.1",
    "1.3.6.1.4.1.22234.3.5.3.1",
    "1.3.6.1.4.1.23223.1.1.1",
    "1.3.6.1.4.1.23223.2",
    "1.3.6.1.4.1.34697.2.1",
    "1.3.6.1.4.1.34697.2.2",
    "1.3.6.1.4.1.34697.2.3",
    "1.3.6.1.4.1.34697.2.4",
    "1.3.6.1.4.1.40869.1.1.22.3",
    "1.3.6.1.4.1.4146.1.1",
    "1.3.6.1.4.1.4788.2.202.1",
    "1.3.6.1.4.1.6334.1.100.1",
    "1.3.6.1.4.1.6449.1.2.1.5.1",
    "1.3.6.1.4.1.782.1.2.1.8.1",
    "1.3.6.1.4.1.7879.13.24.1",
    "1.3.6.1.4.1.8024.0.2.100.1.2",
    "2.16.156.112554.3",
    "2.16.528.1.1003.1.2.7",
    "2.16.578.1.26.1.3.3",
    "2.16.756.1.83.21.0",
    "2.16.756.1.89.1.2.1.1",
    "2.16.756.5.14.7.4.8",
    "2.16.792.3.0.4.1.1.4",
    "2.16.840.1.113733.1.7.23.6",
    "2.16.840.1.113733.1.7.48.1",
    "2.16.840.1.114028.10.1.2",
    "2.16.840.1.114404.1.1.2.4.1",
    "2.16.840.1.114412.1.3.0.2",
    "2.16.840.1.114412.2.1",
    "2.16.840.1.114413.1.7.23.3",
    "2.16.840.1.114414.1.7.23.3",
    "2.16.840.1.114414.1.7.24.3"
]
