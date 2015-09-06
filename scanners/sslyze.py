import logging
from scanners import utils
import json
import os

from bs4 import BeautifulSoup

###
# == sslyze ==
#
# Inspect a site's TLS configuration using sslyze.
#
# If data exists for a domain from `inspect`, will check results
# and only process domains with valid HTTPS, or broken chains.
###

command = os.environ.get("SSLYZE_PATH", "sslyze.py")

# Kind of a hack for now, other methods of running sslyze with Python 2 welcome
command_env = {'PYENV_VERSION': os.environ.get("SSLYZE_PYENV", "2.7.9")}

def scan(domain, options):
	logging.debug("[%s][sslyze]" % domain)

	# Optional: skip domains which don't support HTTPS in prior inspection
	inspection = utils.data_for(domain, "inspect")
	if inspection and (not inspection.get("support_https")):
		logging.debug("\tSkipping, HTTPS not supported in inspection.")
		return None

	# Optional: if inspect data says canonical endpoint uses www and this domain
	# doesn't have it, add it.
	if inspection and (inspection.get("canonical_endpoint") == "www") and (not domain.startswith("www.")):
		scan_domain = "www.%s" % domain
	else:
		scan_domain = domain

	# cache XML from sslyze
	cache_xml = utils.cache_path(domain, "sslyze", ext="xml")
	# because sslyze manages its own output (can't yet print to stdout),
	# we have to mkdir_p the path ourselves
	utils.mkdir_p(os.path.dirname(cache_xml))

	force = options.get("force", False)

	if (force is False) and (os.path.exists(cache_xml)):
		logging.debug("\tCached.")
		xml = open(cache_xml).read()

	else:
		logging.debug("\t %s %s" % (command, domain))
		# use scan_domain (possibly www-prefixed) to do actual scan
		raw = utils.scan([command, "--regular", "--quiet", scan_domain, "--xml_out=%s" % cache_xml], env=command_env)
		
		if raw is None:
			# TODO: save standard invalid XML data...?
			logging.warn("\tBad news scanning, sorry!")
			return None

		xml = utils.scan(["cat", cache_xml])
		if not xml:
			logging.warn("\tBad news reading XML, sorry!")
			return None

		utils.write(xml, cache_xml)

	data = parse_sslyze(xml)

	if data is None:
		logging.warn("\tNo valid target for scanning, couldn't connect.")
		return None

	utils.write(utils.json_for(data), utils.cache_path(domain, "sslyze"))

	yield [
		base_domain_for(domain),
		data['sslv2'], data['sslv3'], data['tlsv1.0'], data['tlsv1.1'], data['tlsv1.2'], 

		data['key_type'], data['key_length'],
		data['leaf_signature'], data['any_sha1'],

		data['any_dhe'],

		data['any_rc4'],
		data['served_issuer'], data['ocsp_stapling']
	]

headers = [
	"Base Domain",
	"SSLv2", "SSLv3", "TLSv1.0", "TLSv1.1", "TLSv1.2",
	
	"Key Type", "Key Length",
	"Signature Algorithm", "SHA-1 in Chain", 

	"Any Forward Secrecy",

	"Any RC4",
	"Highest Served Issuer", "OCSP Stapling"
]

# Get the relevant fields out of sslyze's XML format. I couldn't find this documented
# anywhere, so I'm just winging it by looking at example XML.
def parse_sslyze(xml):
	
	doc = BeautifulSoup(xml, "xml")

	# We'll just go after the first found valid target IP.
	target = doc.select_one("target")

	if target is None:
		return None

	# Protocol version support.
	data = {
		'sslv2': (target.find('sslv2')["isProtocolSupported"] == 'True'),
		'sslv3': (target.find('sslv3')["isProtocolSupported"] == 'True'),
		'tlsv1.0': (target.find('tlsv1')["isProtocolSupported"] == 'True'),
		'tlsv1.1': (target.find('tlsv1_1')["isProtocolSupported"] == 'True'),
		'tlsv1.2': (target.find('tlsv1_2')["isProtocolSupported"] == 'True')
	}

	# Whether OCSP stapling is enabled.
	data['ocsp_stapling'] = (target.select_one('ocspStapling')["isSupported"] == 'True')

	# Find the issuer of the last served cert.
	# This is an attempt at finding the CA name, but won't work if the served
	# chain is incomplete. I'll take what I can get without doing path chasing.
	certificates = target.select("certificateChain certificate")
	issuer = certificates[-1].select_one("issuer commonName")
	if not issuer:
		issuer = certificates[-1].select_one("issuer organizationalUnitName")

	if issuer and issuer.text:
		data['served_issuer'] = issuer.text
	else:
		data['served_issuer'] = "(None found)"

	# Key algorithm and length for leaf certificate only.
	data['key_type'] = target.select_one("certificateChain certificate[position=leaf] subjectPublicKeyInfo publicKeyAlgorithm").text
	data['key_length'] = int(target.select_one("certificateChain certificate[position=leaf] subjectPublicKeyInfo publicKeySize").text)

	# Signature of the leaf certificate only.
	data['leaf_signature'] = target.select_one("certificateChain certificate[position=leaf] signatureAlgorithm").text

	# Look at only served leaf and intermediate certificates
	signatures = target.select("certificateChain certificate[position=leaf],certificate[position=intermediate] signatureAlgorithm")
	any_sha1 = False
	for signature in signatures:
		if "sha1With" in signature.text:
			any_sha1 = True
	data['any_sha1'] = any_sha1

	
	accepted_ciphers = target.select("acceptedCipherSuites cipherSuite")
	
	# Look at accepted cipher suites for RC4 or DHE.
	# This is imperfect, as the advertising of RC4 could discriminate based on client.
	# DHE and ECDHE may not remain the only forward secret options for TLS.
	any_rc4 = False
	any_dhe = False
	for cipher in accepted_ciphers:
		name = cipher["name"]

		if "RC4" in name:
			any_rc4 = True
		if name.startswith("DHE-") or name.startswith("ECDHE-"):
			any_dhe = True
	data['any_rc4'] = any_rc4
	data['any_dhe'] = any_dhe


	return data


# return base domain for a subdomain
def base_domain_for(subdomain):
    return str.join(".", subdomain.split(".")[-2:])
