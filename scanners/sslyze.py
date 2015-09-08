import logging
from scanners import utils
import json
import os

from bs4 import BeautifulSoup
import dateutil.parser

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
		data['protocols']['sslv2'], data['protocols']['sslv3'], 
		data['protocols']['tlsv1.0'], data['protocols']['tlsv1.1'], 
		data['protocols']['tlsv1.2'], 

		data['config'].get('any_dhe'), data['config'].get('all_dhe'),
		data['config'].get('weakest_dh'),
		data['config'].get('any_rc4'), data['config'].get('all_rc4'),

		data['config'].get('ocsp_stapling'),
		
		data['certs'].get('key_type'), data['certs'].get('key_length'),
		data['certs'].get('leaf_signature'), data['certs'].get('any_sha1'),
		data['certs'].get('not_before'), data['certs'].get('not_after'),
		data['certs'].get('served_issuer'), 

		data.get('errors')
	]

headers = [
	"SSLv2", "SSLv3", "TLSv1.0", "TLSv1.1", "TLSv1.2",

	"Any Forward Secrecy", "All Forward Secrecy", 
	"Weakest DH Group Size",
	"Any RC4", "All RC4",

	"OCSP Stapling",

	"Key Type", "Key Length",
	"Signature Algorithm", "SHA-1 in Served Chain", 
	"Not Before", "Not After",
	"Highest Served Issuer", 

	"Errors"
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
		'protocols': {
			'sslv2': (target.find('sslv2')["isProtocolSupported"] == 'True'),
			'sslv3': (target.find('sslv3')["isProtocolSupported"] == 'True'),
			'tlsv1.0': (target.find('tlsv1')["isProtocolSupported"] == 'True'),
			'tlsv1.1': (target.find('tlsv1_1')["isProtocolSupported"] == 'True'),
			'tlsv1.2': (target.find('tlsv1_2')["isProtocolSupported"] == 'True')
		},

		'config': {},

		'certs': {},

		'errors': None
	}

	# Whether OCSP stapling is enabled.
	ocsp = target.select_one('ocspStapling')
	if ocsp:
		data['config']['ocsp_stapling'] = (ocsp["isSupported"] == 'True')

	
	accepted_ciphers = target.select("acceptedCipherSuites cipherSuite")
	
	if len(accepted_ciphers) > 0:
		# Look at accepted cipher suites for RC4 or DHE.
		# This is imperfect, as the advertising of RC4 could discriminate based on client.
		# DHE and ECDHE may not remain the only forward secret options for TLS.
		any_rc4 = False
		any_dhe = False
		all_rc4 = True
		all_dhe = True
		for cipher in accepted_ciphers:
			name = cipher["name"]
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
		weakest_dh = 1234567890 # nonsense maximum
		groups = target.select("acceptedCipherSuites cipherSuite keyExchange[Type=DH]")
		for group in groups:
			size = int(group["GroupSize"])
			if size < weakest_dh:
				weakest_dh = size

		if weakest_dh == 1234567890:
			weakest_dh = None

		data['config']['weakest_dh'] = weakest_dh


	# If there was an exception parsing the certificate, catch it before fetching cert info.
	if target.select_one("certinfo[exception]") is not None:
		data['errors'] = target.select_one("certinfo[exception]")["exception"]

	else:

		# Find the issuer of the last served cert.
		# This is an attempt at finding the CA name, but won't work if the served
		# chain is incomplete. I'll take what I can get without doing path chasing.
		certificates = target.select("certificateChain certificate")
		issuer = certificates[-1].select_one("issuer commonName")
		if not issuer:
			issuer = certificates[-1].select_one("issuer organizationalUnitName")

		if issuer and issuer.text:
			data['certs']['served_issuer'] = issuer.text
		else:
			data['certs']['served_issuer'] = "(None found)"

		leaf = target.select_one("certificateChain certificate[position=leaf]")

		# Key algorithm and length for leaf certificate only.
		data['certs']['key_type'] = leaf.select_one("subjectPublicKeyInfo publicKeyAlgorithm").text
		data['certs']['key_length'] = int(leaf.select_one("subjectPublicKeyInfo publicKeySize").text)

		# Signature of the leaf certificate only.
		data['certs']['leaf_signature'] = leaf.select_one("signatureAlgorithm").text

		# Beginning and expiration dates of the leaf certificate
		before_date = leaf.select_one("validity notBefore").text
		after_date = leaf.select_one("validity notAfter").text
		data['certs']['not_before'] = dateutil.parser.parse(before_date)
		data['certs']['not_after'] = dateutil.parser.parse(after_date)


		# Look at only served leaf and intermediate certificates
		signatures = target.select("certificateChain certificate[position=leaf],certificate[position=intermediate] signatureAlgorithm")
		any_sha1 = False
		for signature in signatures:
			if "sha1With" in signature.text:
				any_sha1 = True
		data['certs']['any_sha1'] = any_sha1


	return data

