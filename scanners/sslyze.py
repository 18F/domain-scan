###
# Inspect a site's TLS configuration using sslyze.
#
# If data exists for a domain from `pshtt`, will check results
# and only process domains with valid HTTPS, or broken chains.
#
# Supported options:
#
# --sslyze-serial - If set, will use a synchronous (single-threaded
#   in-process) scanner. Defaults to true when local, false in cloud.
# --sslyze-certs - If set, will use the CertificateInfoScanner and
#   return certificate info. Defaults to true.
###

from scanners import utils
import logging

import sslyze
from sslyze.synchronous_scanner import SynchronousScanner
from sslyze.concurrent_scanner import ConcurrentScanner, PluginRaisedExceptionScanResult
from sslyze.plugins.openssl_cipher_suites_plugin import Tlsv10ScanCommand, Tlsv11ScanCommand, Tlsv12ScanCommand, Sslv20ScanCommand, Sslv30ScanCommand
from sslyze.plugins.certificate_info_plugin import CertificateInfoScanCommand

import idna
import cryptography
import cryptography.hazmat.backends.openssl
from cryptography.hazmat.primitives.serialization import Encoding
from cryptography.hazmat.primitives.asymmetric import ec, dsa, rsa

# Number of seconds to wait during sslyze connection check.
# Not much patience here, and very willing to move on.
network_timeout = 5


# If we have pshtt data, use it to skip some domains, and to adjust
# scan hostnames to canonical URLs where we can.
def init_domain(domain, environment, options):
    # If we have pshtt data, skip domains which pshtt saw as not
    # supporting HTTPS at all.
    if utils.domain_doesnt_support_https(domain):
        logging.warn("\tSkipping, HTTPS not supported.")
        return False

    # If we have pshtt data and it says canonical endpoint uses www
    # and the given domain is bare, add www.
    if utils.domain_uses_www(domain):
        hostname = "www.%s" % domain
    else:
        hostname = domain

    return {
        'hostname': hostname
    }


# Run sslyze on the given domain.
def scan(domain, environment, options):
    # Allow hostname to be adjusted by init_domain.
    hostname = environment.get("hostname", domain)

    data = {
        'hostname': hostname,
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
        logging.warn(error)
        data['errors'].append(error)

    # Join all errors into a string before returning.
    data['errors'] = ' '.join(data['errors'])

    return data


# Given a response dict, turn it into CSV rows.
def to_rows(data):
    row = [
        data['hostname'],

        data['protocols'].get('sslv2'), data['protocols'].get('sslv3'),
        data['protocols'].get('tlsv1.0'), data['protocols'].get('tlsv1.1'),
        data['protocols'].get('tlsv1.2'),

        data['config'].get('any_dhe'), data['config'].get('all_dhe'),
        data['config'].get('weakest_dh'),
        data['config'].get('any_rc4'), data['config'].get('all_rc4'),
        data['config'].get('any_3des'),

        data['certs'].get('key_type'), data['certs'].get('key_length'),
        data['certs'].get('leaf_signature'),
        data['certs'].get('any_sha1_served'),
        data['certs'].get('any_sha1_constructed'),
        data['certs'].get('not_before'), data['certs'].get('not_after'),
        data['certs'].get('served_issuer'), data['certs'].get('constructed_issuer'),

        data.get('errors')
    ]

    return [row]


headers = [
    "Scanned Hostname",
    "SSLv2", "SSLv3", "TLSv1.0", "TLSv1.1", "TLSv1.2",

    "Any Forward Secrecy", "All Forward Secrecy",
    "Weakest DH Group Size",
    "Any RC4", "All RC4",
    "Any 3DES",

    "Key Type", "Key Length",
    "Signature Algorithm",
    "SHA-1 in Served Chain",
    "SHA-1 in Constructed Chain",
    "Not Before", "Not After",
    "Highest Served Issuer", "Highest Constructed Issuer",

    "Errors"
]


# Get the relevant fields out of sslyze's JSON format.
#
# Certificate PEM data must be separately parsed using
# the Python cryptography module.

def run_sslyze(data, environment, options):
    hostname = data['hostname']

    # SynchronousScanner has a memory leak over time, so local
    # scanning defaults to using ConcurrentScanner.
    #
    # But Lambda can't use multiprocessing.Queue, so cloud scanning
    # defaults to using SynchronousScanner.
    scan_method = environment.get("scan_method", "local")
    default_sync = {"local": False, "lambda": True}[scan_method]

    # Each sslyze worker can use a sync or parallel mode.
    sync = options.get("sslyze-serial", default_sync)

    # Initialize either a synchronous or concurrent scanner.
    server_info, scanner = init_sslyze(hostname, options, sync=sync)

    if server_info is None:
        data['errors'].append("Connectivity not established.")
        return data

    # Whether sync or concurrent, get responses for all scans.
    if sync:
        sslv2, sslv3, tlsv1, tlsv1_1, tlsv1_2, certs = scan_serial(scanner, server_info, data, options)
    else:
        sslv2, sslv3, tlsv1, tlsv1_1, tlsv1_2, certs = scan_parallel(scanner, server_info, data, options)

    # Only analyze protocols if all the scanners functioned.
    # Very difficult to draw conclusions if some worked and some did not.
    if sslv2 and sslv3 and tlsv1 and tlsv1_1 and tlsv1_2:
        analyze_protocols_and_ciphers(data, sslv2, sslv3, tlsv1, tlsv1_1, tlsv1_2)

    if certs:
        data['certs'] = analyze_certs(certs)

    return data


def analyze_protocols_and_ciphers(data, sslv2, sslv3, tlsv1, tlsv1_1, tlsv1_2):
    data['protocols'] = {
        'sslv2': supported_protocol(sslv2),
        'sslv3': supported_protocol(sslv3),
        'tlsv1.0': supported_protocol(tlsv1),
        'tlsv1.1': supported_protocol(tlsv1_1),
        'tlsv1.2': supported_protocol(tlsv1_2)
    }

    accepted_ciphers = (
        (sslv2.accepted_cipher_list or []) +
        (sslv3.accepted_cipher_list or []) +
        (tlsv1.accepted_cipher_list or []) +
        (tlsv1_1.accepted_cipher_list or []) +
        (tlsv1_2.accepted_cipher_list or [])
    )

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

        # Find the weakest available DH group size, if any are available.
        weakest_dh = 1234567890  # nonsense maximum
        for cipher in accepted_ciphers:
            if cipher.dh_info is not None:
                size = int(cipher.dh_info['GroupSize'])
                if size < weakest_dh:
                    weakest_dh = size

        if weakest_dh == 1234567890:
            weakest_dh = None

        data['config']['weakest_dh'] = weakest_dh


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
def init_sslyze(hostname, options, sync=False):
    global network_timeout

    network_timeout = int(options.get("network_timeout", network_timeout))

    try:
        server_info = sslyze.server_connectivity.ServerConnectivityInfo(hostname=hostname, port=443)
    except sslyze.server_connectivity.ServerConnectivityError as error:
        logging.warn("\tServer connectivity not established during initialization.")
        return None, None
    except Exception as err:
        utils.notify(err)
        logging.warn("\tUnknown exception when initializing server connectivity info.")
        return None, None

    try:
        # logging.debug("\tTesting connectivity with timeout of %is." % network_timeout)
        server_info.test_connectivity_to_server(network_timeout=network_timeout)
    except sslyze.server_connectivity.ServerConnectivityError as err:
        logging.warn("\tServer connectivity not established during test.")
        return None, None
    except Exception as err:
        utils.notify(err)
        logging.warn("\tUnknown exception when performing server connectivity info.")
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

    certs = None
    if options.get("sslyze-certs", True) is True:

        try:
            logging.debug("\t\tCertificate information scan.")
            certs = scanner.run_scan_command(server_info, CertificateInfoScanCommand())
        # Let generic exceptions bubble up.
        except idna.core.InvalidCodepoint:
            logging.warn(utils.format_last_exception())
            data['errors'].append("Invalid certificate/OCSP for this domain.")
            certs = None
    else:
        certs = None

    logging.debug("\tDone scanning.")

    return sslv2, sslv3, tlsv1, tlsv1_1, tlsv1_2, certs


# Run each scan in parallel, using multi-processing.
# Faster, but can generate many processes.
def scan_parallel(scanner, server_info, data, options):
    logging.debug("\tRunning scans in parallel.")

    def queue(command):
        try:
            return scanner.queue_scan_command(server_info, command)
        except OSError as err:
            text = ("OSError - likely too many processes and open files.")
            data['errors'].append(text)
            logging.warn("%s\n%s" % (text, utils.format_last_exception()))
            return None, None, None, None, None, None
        except Exception as err:
            text = ("Unknown exception queueing sslyze command.\n%s" % utils.format_last_exception())
            data['errors'].append(text)
            logging.warn(text)
            return None, None, None, None, None, None

    # Initialize commands and result containers
    sslv2, sslv3, tlsv1, tlsv1_1, tlsv1_2, certs = None, None, None, None, None, None

    # Queue them all up
    queue(Sslv20ScanCommand())
    queue(Sslv30ScanCommand())
    queue(Tlsv10ScanCommand())
    queue(Tlsv11ScanCommand())
    queue(Tlsv12ScanCommand())

    if options.get("sslyze-certs", True) is True:
        queue(CertificateInfoScanCommand())

    # Reassign them back to predictable places after they're all done
    was_error = False
    for result in scanner.get_results():
        try:
            if isinstance(result, PluginRaisedExceptionScanResult):
                error = ("Scan command failed: %s" % result.as_text())
                logging.warn(error)
                data['errors'].append(error)
                return None, None, None, None, None, None

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
            elif type(result.scan_command) == CertificateInfoScanCommand:
                certs = result
            else:
                error = "Couldn't match scan result with command! %s" % result
                logging.warn("\t%s" % error)
                data['errors'].append(error)
                was_error = True

        except Exception as err:
            was_error = True
            text = ("Exception inside async scanner result processing.\n%s" % utils.format_last_exception())
            data['errors'].append(text)
            logging.warn("\t%s" % text)

    # There was an error during async processing.
    if was_error:
        return None, None, None, None, None, None

    logging.debug("\tDone scanning.")

    return sslv2, sslv3, tlsv1, tlsv1_1, tlsv1_2, certs
