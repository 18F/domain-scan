import logging
from scanners import utils
import json
import os

##
# == pageload ==
#
# Evaluate page laod time information using Phantomas.
#
# If data exists for a domain from `inspect`, will use the
# previously detected "canonical" endpoint for a domain.
##

init = None

# Since these are finely time-sensitive metrics, I think we want
# to make the default number of workers small.
workers = 2


def scan(domain, options):
    logging.debug("[%s][pageload]" % domain)

    inspection = utils.data_for(domain, "inspect")

    # If we have data from inspect, skip if it's not a live domain.
    if inspection and (not inspection.get("up")):
        logging.debug("\tSkipping, domain not reachable during inspection.")
        return None

    # If we have data from inspect, skip if it's just a redirector.
    if inspection and (inspection.get("redirect") is True):
        logging.debug("\tSkipping, domain seen as just a redirector during inspection.")
        return None

    # phantomas needs a URL, not just a domain.
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
    cache = utils.cache_path(domain, "pageload")

    # If we've got it cached, use that.
    if (options.get("force", False) is False) and (os.path.exists(cache)):
        logging.debug("\tCached.")
        raw = open(cache).read()
        data = json.loads(raw)
        if data.get('invalid'):
            return None

    # If no cache, or we should run anyway, do the scan.
    else:
        command = ["docker", "run", "18fgsa/phantomas", url, "--reporter=json", "--ignore-ssl-errors"]
        logging.debug("\t %s" % " ".join(command))
        raw = utils.scan(command)
        if not raw:
            utils.write(utils.invalid({}), cache)
            return None

        # It had better be JSON, which we can cache in prettified form.
        data = json.loads(raw)
        utils.write(utils.json_for(data), cache)

    yield [data['metrics'][metric] for metric in interesting_metrics]


# All of the available metrics are listed here:
# https://www.npmjs.com/package/phantomas#metrics

# There are many other interesting metrics generated by Phantomas. For now,
# we'll just return some related to page load performance...
interesting_metrics = [
    'requests',
    'httpsRequests',
    'timeToFirstByte',
    'timeToLastByte',
    'httpTrafficCompleted',
    'domContentLoaded',
    'domComplete',
    'timeBackend',
    'timeFrontend',
]

headers = interesting_metrics
