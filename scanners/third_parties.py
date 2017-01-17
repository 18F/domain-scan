import logging
from scanners import utils
import json
import os
import re

##
# == third_parties ==
#
# Evaluate third party service usage with Phantomas.
#
# If data exists for a domain from `pshtt`, will:
# * not run if the domain just redirects externally
# * start with any detected (internal) redirect URL
#
# Options:
#
# * --timeout: Override default timeout of 60s.
# * --affiliated: A suffix (e.g. ".gov", "twimg.com") known to
#       be affiliated with the scanned domains.
#
# Looks for known, affiliated, and unknown services.

# Categories/Fields:
#
# * All external domains: All unique external domains that get pinged.
# * All subdomains: All unique subdomains that get pinged.
#
# * Affiliated domains: Service domains known to be affiliated.
# * Unknown domains: Any other external service domains.
#
# * [Known Service]: True / False
##

command = os.environ.get("PHANTOMAS_PATH", "phantomas")
init = None

# Should be able to handle the full complement.
workers = 10


######################################
#
# Bible of known third party services.
#
######################################

# TODO: Start using regexes.
# TODO: After adding regexes, have this be ordered, some
# rules should take precedence over others.
known_services = {
    'Google Analytics': ['www.google-analytics.com'],
    'Google Fonts': ['fonts.googleapis.com'],
    'Digital Analytics Program': ['dap.digitalgov.gov'],
}

######################################


def scan(domain, options):
    logging.debug("[%s][third_parties]" % domain)

    # Default timeout is 15s, too little.
    timeout = int(options.get("timeout", 60))

    # If we have data from pshtt, skip if it's not a live domain.
    if utils.domain_not_live(domain):
        logging.debug("\tSkipping, domain not reachable during inspection.")
        return None

    # If we have data from pshtt, skip if it's just a redirector.
    if utils.domain_is_redirect(domain):
        logging.debug("\tSkipping, domain seen as just an external redirector during inspection.")
        return None

    # phantomas needs a URL, not just a domain.
    if not (domain.startswith('http://') or domain.startswith('https://')):

        # If we have data from pshtt, use the canonical endpoint.
        if utils.domain_canonical(domain):
            url = utils.domain_canonical(domain)

        # Otherwise, well, whatever.
        else:
            url = 'http://' + domain
    else:
        url = domain

    calculated_domain = re.sub("https?:\/\/", "", url)

    # We'll cache prettified JSON from the output.
    cache = utils.cache_path(domain, "third_parties")

    # If we've got it cached, use that.
    if (options.get("force", False) is False) and (os.path.exists(cache)):
        logging.debug("\tCached.")
        raw = open(cache).read()
        data = json.loads(raw)
        if data.get('invalid'):
            return None

    # If no cache, or we should run anyway, do the scan.
    else:
        logging.debug("\t %s %s --modules=domains --reporter=json --timeout=%i --ignore-ssl-errors" % (command, url, timeout))
        raw = utils.scan([command, url, "--modules=domains", "--reporter=json", "--timeout=%i" % timeout, "--ignore-ssl-errors"], allowed_return_codes=[252])
        if not raw:
            utils.write(utils.invalid({}), cache)
            return None

        # It had better be JSON, which we can cache in prettified form.
        data = json.loads(raw)
        utils.write(utils.json_for(data), cache)

    services = services_for(data, domain, options)

    # Convert to CSV row
    known_names = list(known_services.keys())
    known_names.sort()
    known_matches = ['Yes' if host in services['known'] else 'No' for host in known_names]

    yield [
        serialize(services['external']),
        serialize(services['internal']),
        # services['affiliated'],
        # services['unknown']
    ] + known_matches

# Given a 'domains' array from phantomas output, create a data
# object with data on detected external, internal, and
# affiliated domains.
def services_for(data, domain, options):
    services = {
        'external': [],
        'internal': [],
        'known': [],
    }

    raw_domains = data['offenders']['domains']
    hosts = [string.split(": ")[0] for string in raw_domains]

    for host in hosts:
        if host.startswith("www."):
            www_host = host
            base_host = re.sub("^www.", "", host)
        else:
            www_host = "www.%s" % host
            base_host = host

        www_domain = "www.%s" % domain

        # skip if it's the same, or is www version
        if (
            (base_host == domain) or (www_host == domain) or
            (base_host == www_domain) or (www_host == www_domain)
            ):
            continue

        # internal if it shares the same base domain
        if (utils.base_domain_for(host) == utils.base_domain_for(domain)):
            services['internal'].append(host)
        # otherwise external
        else:
            services['external'].append(host)

        # compare this host to all known services
        for service in known_services:
            if host in known_services[service]:
                services['known'].append(service)

    return services


def clean_domain_output(output):
    return output.split(" ")[0]

# Jam multiple domains into one CSV cell.
def serialize(domains):
    return str.join(', ', domains)

base_fields = [
    'All External Domains',
    'All Internal Domains',
    # 'Affiliated External Domains',
    # 'Unknown External Domains',
]

service_names = list(known_services.keys())
service_names.sort()

headers = base_fields + service_names
