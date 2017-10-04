import logging
from scanners import utils
import os

import json
import cryptography
import cryptography.hazmat.backends.openssl
from cryptography.hazmat.primitives.asymmetric import ec, dsa, rsa

###
# == sslyze ==
#
# Inspect a site's TLS configuration using sslyze.
#
# If data exists for a domain from `pshtt`, will check results
# and only process domains with valid HTTPS, or broken chains.
###

command = os.environ.get("SSLYZE_PATH", "sslyze")


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

        # This is --regular minus --heartbleed
        # See: https://github.com/nabla-c0d3/sslyze/issues/217
        raw_response = utils.scan([
            command,
            "--sslv2", "--sslv3", "--tlsv1", "--tlsv1_1", "--tlsv1_2",
            "--reneg", "--resum", "--certinfo",
            "--http_get", "--hide_rejected_ciphers",
            "--compression", "--openssl_ccs",
            "--fallback", "--http_headers", "--quiet",
            scan_domain, "--json_out=%s" % cache_json
        ])

        if raw_response is None:
            # TODO: save standard invalid JSON data...?
            utils.write(utils.invalid({}), cache_json)
            logging.warn("\tBad news scanning, sorry!")
            return None

        raw_json = utils.scan(["cat", cache_json])
        if not raw_json:
            logging.warn("\tBad news reading JSON, sorry!")
            return None

        utils.write(raw_json, cache_json)

    data = parse_sslyze(raw_json)

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

        data['certs'].get('key_type'), data['certs'].get('key_length'),
        data['certs'].get('leaf_signature'),
        data['certs'].get('any_sha1_served'),
        data['certs'].get('any_sha1_constructed'),
        data['certs'].get('not_before'), data['certs'].get('not_after'),
        data['certs'].get('served_issuer'), data['certs'].get('constructed_issuer'),

        data['config']['hsts_enabled'], data['config']['hsts_sub'],
>       data['config']['hsts_age'], data['config']['hsts_pre'],
        data.get('errors')
    ]


headers = [
    "Scanned Hostname",
    "SSLv2", "SSLv3", "TLSv1.0", "TLSv1.1", "TLSv1.2",

    "Any Forward Secrecy", "All Forward Secrecy",
    "Weakest DH Group Size",
    "Any RC4", "All RC4",

    "Key Type", "Key Length",
    "Signature Algorithm",
    "SHA-1 in Served Chain",
    "SHA-1 in Constructed Chain",
    "Not Before", "Not After",
    "Highest Served Issuer", "Highest Constructed Issuer",
    
    "HSTS Enabled","HSTS Subdomains","HSTS Age","HSTS Preload",

    "Errors"
]

# Get the relevant fields out of sslyze's JSON format.
#
# Certificate PEM data must be separately parsed using
# the Python cryptography module.
#
# If we were using the sslyze Python API, this would be
# done for us automatically, but serializing the results
# to disk for caching would be prohibitively complex.


def parse_sslyze(raw_json):

    data = json.loads(raw_json)

    # 1. Isolate first successful scanned IP.
    if len(data['accepted_targets']) == 0:
        return None
    target = data['accepted_targets'][0]['commands_results']

    # Protocol version support.
    data = {
        'protocols': {
            'sslv2': supported_protocol(target, 'sslv2'),
            'sslv3': supported_protocol(target, 'sslv3'),
            'tlsv1.0': supported_protocol(target, 'tlsv1'),
            'tlsv1.1': supported_protocol(target, 'tlsv1_1'),
            'tlsv1.2': supported_protocol(target, 'tlsv1_2')
        },

        'config': {},

        'certs': {},

        'errors': None
    }

    # TODO: Whether OCSP stapling is enabled.
    # Relevant fields: https://nabla-c0d3.github.io/sslyze/documentation/available-scan-commands.html#sslyze.plugins.certificate_info_plugin.CertificateInfoScanResult.ocsp_response

    # ocsp = target.select_one('ocspStapling')
    # if ocsp:
    #     data['config']['ocsp_stapling'] = (ocsp["isSupported"] == 'True')

    data['config']['hsts_enabled'] = False
    data['config']['hsts_sub'] = False
    data['config']['hsts_age'] = 0
    data['config']['hsts_pre'] = False

    if target['http_headers']['hsts_header'] != None:
        data['config']['hsts_enabled'] = True
        data['config']['hsts_sub'] = target['http_headers']['hsts_header']['include_subdomains']
        data['config']['hsts_age'] = target['http_headers']['hsts_header']['max_age']
        data['config']['hsts_pre'] = target['http_headers']['hsts_header']['preload']
    
    accepted_ciphers = (
        target['sslv2'].get("accepted_cipher_list", []) +
        target['sslv3'].get("accepted_cipher_list", []) +
        target['tlsv1'].get("accepted_cipher_list", []) +
        target['tlsv1_1'].get("accepted_cipher_list", []) +
        target['tlsv1_2'].get("accepted_cipher_list", [])
    )

    if len(accepted_ciphers) > 0:
        # Look at accepted cipher suites for RC4 or DHE.
        # This is imperfect, as the advertising of RC4 could discriminate based on client.
        # DHE and ECDHE may not remain the only forward secret options for TLS.
        any_rc4 = False
        any_dhe = False
        all_rc4 = True
        all_dhe = True
        for cipher in accepted_ciphers:
            name = cipher["openssl_name"]
            if "RC4" in name:
                any_rc4 = True
            else:
                all_rc4 = False

            if name.startswith("DHE-") or name.startswith("ECDHE-"):
                any_dhe = True
            else:
                all_dhe = False

        data['config']['any_rc4'] = any_rc4
        data['config']['all_rc4'] = all_rc4
        data['config']['any_dhe'] = any_dhe
        data['config']['all_dhe'] = all_dhe

        # Find the weakest available DH group size, if any are available.
        weakest_dh = 1234567890  # nonsense maximum
        for cipher in accepted_ciphers:
            if cipher.get('dh_info', None) is not None:
                size = int(cipher['dh_info']['GroupSize'])
                if size < weakest_dh:
                    weakest_dh = size

        if weakest_dh == 1234567890:
            weakest_dh = None

        data['config']['weakest_dh'] = weakest_dh

    # If there was an exception parsing the certificate, catch it before fetching cert info.
    if False:
        data['errors'] = "TODO"

    else:

        # Served chain.
        served_chain = target['certinfo']['certificate_chain']

        # Constructed chain may not be there if it didn't validate.
        constructed_chain = target['certinfo']['verified_certificate_chain']

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
            data['certs']['any_sha1_constructed'] = target['certinfo']['has_sha1_in_certificate_chain']

    return data


# Given the cert sub-obj from the sslyze JSON, use
# the cryptography module to parse its PEM contents.
def parse_cert(cert):
    backend = cryptography.hazmat.backends.openssl.backend
    pem_bytes = cert['as_pem'].encode('utf-8')
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


# examines whether the protocol version turned out ot be supported
def supported_protocol(target, protocol):
    if target[protocol].get("error_message", None) is not None:
        logging.debug("Error connecting to %s: %s" % (protocol, target[protocol]["error_message"]))
        return False
    elif target[protocol].get("accepted_cipher_list", None) is None:
        return False
    else:
        return (len(target[protocol]["accepted_cipher_list"]) > 0)
