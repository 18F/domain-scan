import logging
from scanners import utils
import os

import timeout_decorator

import sslyze
from sslyze.synchronous_scanner import SynchronousScanner
from sslyze.concurrent_scanner import ConcurrentScanner, PluginRaisedExceptionScanResult
from sslyze.plugins.openssl_cipher_suites_plugin import Tlsv10ScanCommand, Tlsv11ScanCommand, Tlsv12ScanCommand, Sslv20ScanCommand, Sslv30ScanCommand
from sslyze.plugins.certificate_info_plugin import CertificateInfoScanCommand

import json
import cryptography
import cryptography.hazmat.backends.openssl
from cryptography.hazmat.primitives.serialization import Encoding
from cryptography.hazmat.primitives.asymmetric import ec, dsa, rsa

###
# == sslyze ==
#
# Inspect a site's TLS configuration using sslyze.
#
# If data exists for a domain from `pshtt`, will check results
# and only process domains with valid HTTPS, or broken chains.
#
# Supported options:
#
# --sslyze-serial - If set, will use a synchronous (single-threaded
#   in-process) scanner. Defaults to false.
###

command = os.environ.get("SSLYZE_PATH", "sslyze")

# This timeout is enforced in this file, in Python, not in sslyze.
timeout = 20


def scan(domain, options):
    logging.debug("[%s][sslyze]" % domain)

    # Optional: skip domains which don't support HTTPS in pshtt scan.
    if utils.domain_doesnt_support_https(domain):
        logging.debug("\tSkipping, HTTPS not supported.")
        return None

    # Optional: if pshtt data says canonical endpoint uses www and this domain
    # doesn't have it, add it.
    if utils.domain_uses_www(domain):
        scan_domain = "www.%s" % domain
    else:
        scan_domain = domain

    # cache JSON from sslyze
    cache_json = utils.cache_path(domain, "sslyze")
    # because sslyze manages its own output (can't yet print to stdout),
    # we have to mkdir_p the path ourselves
    utils.mkdir_p(os.path.dirname(cache_json))

    force = options.get("force", False)

    if (force is False) and (os.path.exists(cache_json)):
        logging.debug("\tCached.")
        raw_json = open(cache_json).read()
        try:
            data = json.loads(raw_json)
            if (data.__class__ is dict) and data.get('invalid'):
                return None
        except json.decoder.JSONDecodeError as err:
            logging.warn("Error decoding JSON.  Cache probably corrupted.")
            return None

    else:
        # use scan_domain (possibly www-prefixed) to do actual scan
        logging.debug("\t %s %s" % (command, scan_domain))

        try:
            # TODO: timeout not actually enforced, due to issues
            # with multiprocessing.
            # If we have to, we can try single-threading to enforce a timeout.
            data = run_sslyze(scan_domain, options)
        except timeout_decorator.timeout_decorator.TimeoutError:
            # logging.warn(utils.format_last_exception())
            logging.warn("\tTimeout error (%is) running sslyze." % timeout)

        if data is None:
            # TODO: save standard invalid JSON data...?
            utils.write(utils.invalid({}), cache_json)
            logging.warn("\tBad news scanning, sorry!")
            return None

        # not so raw...
        raw_json = utils.json_for(data)
        utils.write(raw_json, cache_json)

    if data is None:
        logging.warn("\tNo valid target for scanning, couldn't connect.")
        return None

    yield [
        scan_domain,
        data['protocols']['sslv2'], data['protocols']['sslv3'],
        data['protocols']['tlsv1.0'], data['protocols']['tlsv1.1'],
        data['protocols']['tlsv1.2'],

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

def run_sslyze(hostname, options):
    sync = options.get("sslyze-serial", False)

    # Initialize either a synchronous or concurrent scanner.
    server_info, scanner = init_sslyze(hostname, sync)

    # Whether sync or concurrent, get responses for all scans.
    if sync:
        sslv2, sslv3, tlsv1, tlsv1_1, tlsv1_2, certs = scan_serial(scanner, server_info)
    else:
        sslv2, sslv3, tlsv1, tlsv1_1, tlsv1_2, certs = scan_parallel(scanner, server_info)

    # Parse the results into a dict, which will also be cached as JSON.
    data = {
        'protocols': {
            'sslv2': supported_protocol(sslv2),
            'sslv3': supported_protocol(sslv3),
            'tlsv1.0': supported_protocol(tlsv1),
            'tlsv1.1': supported_protocol(tlsv1_1),
            'tlsv1.2': supported_protocol(tlsv1_2)
        },

        'config': {},

        'certs': {},

        'errors': None
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

    return data


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
def init_sslyze(hostname, sync=False):
    try:
        server_info = sslyze.server_connectivity.ServerConnectivityInfo(hostname=hostname, port=443)
    except sslyze.server_connectivity.ServerConnectivityError as error:
        logging.warn("\tServer connectivity not established during initialization.")
        return None
    except Exception as err:
        utils.notify(err)
        logging.warn("\tUnknown exception when initializing server connectivity info.")
        return None

    try:
        server_info.test_connectivity_to_server()
    except sslyze.server_connectivity.ServerConnectivityError as err:
        logging.warn("\tServer connectivity not established during test.")
        return None
    except Exception as err:
        utils.notify(err)
        logging.warn("\tUnknown exception when performing server connectivity info.")
        return None

    if sync:
        scanner = SynchronousScanner()
    else:
        scanner = ConcurrentScanner()

    return server_info, scanner

# Run each scan in-process, one at a time.
# Takes longer, but no multi-process funny business.
def scan_serial(scanner, server_info):
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
    logging.debug("\t\tCertificate information scan.")
    certs = scanner.run_scan_command(server_info, CertificateInfoScanCommand())
    logging.debug("\tDone scanning.")

    return sslv2, sslv3, tlsv1, tlsv1_1, tlsv1_2, certs

# Run each scan in parallel, using multi-processing.
# Faster, but can generate many processes.
def scan_parallel(scanner, server_info):
    logging.debug("\tRunning scans in parallel.")

    def queue(command):
        try:
            return scanner.queue_scan_command(server_info, command)
        except Exception as err:
            utils.notify(err)
            logging.warn("Unknown exception queueing sslyze command.")
            return None


    # Initialize commands and result containers
    sslv2, sslv3, tlsv1, tlsv1_1, tlsv1_2, certs = None, None, None, None, None, None

    # Queue them all up
    queue(Sslv20ScanCommand())
    queue(Sslv30ScanCommand())
    queue(Tlsv10ScanCommand())
    queue(Tlsv11ScanCommand())
    queue(Tlsv12ScanCommand())
    queue(CertificateInfoScanCommand())

    # Reassign them back to predictable places after they're all done
    was_error = False
    for result in scanner.get_results():
        try:
            if isinstance(result, PluginRaisedExceptionScanResult):
                logging.warn(u'Scan command failed: {}'.format(result.as_text()))
                return None

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
                logging.warn("\tCouldn't match scan result with command! %s" % result)
                was_error = True

        except Exception as err:
            logging.warn("\t Exception inside async scanner result processing.")
            was_error = True
            utils.notify(err)

    # There was an error during async processing.
    if was_error:
        return None

    logging.debug("\tDone scanning.")

    return sslv2, sslv3, tlsv1, tlsv1_1, tlsv1_2, certs


