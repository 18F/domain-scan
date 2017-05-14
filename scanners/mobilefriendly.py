import logging
from scanners import utils
import json
import os
import requests

##
# == pageload ==
#
# Evaluate page laod time information using Phantomas.
#
# If data exists for a domain from `inspect`, will use the
# previously detected "canonical" endpoint for a domain.
##

init = None

workers = 4

def scan(domain, options):
    logging.debug("[%s][pageload]" % domain)

    inspection = utils.data_for(domain, "inspect")
    
    # TODO: Factor out the next 22 lines.

    # If we have data from inspect, skip if it's not a live domain.
    if inspection and (not inspection.get("up")):
        logging.debug("\tSkipping, domain not reachable during inspection.")
        return None

    # If we have data from inspect, skip if it's just a redirector.
    if inspection and (inspection.get("redirect") is True):
        logging.debug("\tSkipping, domain seen as just a redirector during inspection.")
        return None

    # We need a URL, not just a domain.
    if not (domain.startswith('http://') or domain.startswith('https://')):

        # If we have data from inspect, use the canonical endpoint.
        if inspection and inspection.get("canonical"):
            url = inspection.get("canonical")

        # Otherwise, well, whatever.
        else:
            url = 'http://' + domain
    else:
        url = domain

    # We'll cache prettified JSON from the output.
    cache = utils.cache_path(domain, "mobilefriendly")

    # If we've got it cached, use that.
    if (options.get("force", False) is False) and (os.path.exists(cache)):
        logging.debug("\tCached.")
        raw = open(cache).read()
        data = json.loads(raw)
        if data.get('invalid'):
            return None

    # If no cache, or we should run anyway, do the scan.
    else:
        logging.debug("\t requests.get %s" % (url))
        params = {
#           'key': 'AIzaSyDkEX-f1JNLQLC164SZaobALqFv4PHV-kA',  # not needed
            'url': url
        }
        api_url = 'https://www.googleapis.com/pagespeedonline/v3beta1/mobileReady'
        try:
            response = requests.get(api_url, params=params)
        except requests.exceptions.RequestException as exc:
            logging.warn("\t No response from mobileReady API.")
            return None

        raw = response.text
        if not raw:
            utils.write(utils.invalid({}), cache)
            return None

        # It had better be JSON, which we can cache in prettified form.
        data = json.loads(raw)
        if 'error' in data:
            code = data['error']['code']
            message = data['error']['message']
            logging.warn('Error in response from API, %s, %s' % (code, message))
            return None

        utils.write(utils.json_for(data), cache)

    yield [data['ruleGroups']['USABILITY'][metric] for metric in interesting_metrics]


interesting_metrics = [
    'score',
    'pass',
]

headers = interesting_metrics
