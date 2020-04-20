"""
Implements a Google Lighthouse scan.

https://developers.google.com/web/tools/lighthouse

To use, set the `LIGHTHOUSE_PATH` environment variable to the Lighthouse path.
"""


import json
import logging
import os

from utils import utils


LIGHTHOUSE_PATH = os.environ.get('LIGHTHOUSE_PATH', 'lighthouse')
LIGHTHOUSE_AUDITS = [
    'color-contrast',
    'tap-targets',
    'image-alt',
    'input-image-alt',
    'font-size',
    'unminified-css',
    'unminified-javascript',
    'uses-text-compression',
    'total-byte-weight',
    'performance-budget',
    'timing-budget',
    'viewport',
]


# Set a default number of workers for a particular scan type.
# Overridden by a --workers flag.
workers = 2


# Optional one-time initialization for all scans.
# If defined, any data returned will be passed to every scan instance and used
# to update the environment dict for that instance
# Will halt scan execution if it returns False or raises an exception.
#
# Run locally.
# def init(environment: dict, options: dict) -> dict:
#     logging.debug("Init function.")

#     #cache_dir = options.get('_', {}).get('cache_dir', './cache')

#     return {'constant': 12345}


# Optional one-time initialization per-scan. If defined, any data
# returned will be passed to the instance for that domain and used to update
# the environment dict for that particular domain.
#
# Run locally.
# def init_domain(domain: str, environment: dict, options: dict) -> dict:
#     logging.debug("Init function for %s." % domain)
#     return {'variable': domain}


def _url_for_domain(domain: str, cache_dir: str):
    if domain.startswith('http://') or domain.startswith('https://'):
        return domain

    # If we have data from pshtt, use the canonical endpoint.
    canonical = utils.domain_canonical(domain, cache_dir=cache_dir)
    if canonical:
        return canonical

    # Otherwise, well, whatever.
    return 'http://' + domain


# Required scan function. This is the meat of the scanner, where things
# that use the network or are otherwise expensive would go.
#
# Runs locally or in the cloud (Lambda).
def scan(domain: str, environment: dict, options: dict) -> dict:
    logging.debug('Scan function called with options: %s' % options)

    cache_dir = options.get('_', {}).get('cache_dir', './cache')

    logging.info('Running Lighthouse CLI...')
    raw = utils.scan([
        LIGHTHOUSE_PATH,
        _url_for_domain(domain, cache_dir),
        '--quiet',
        '--output=json',
        '--chrome-flags="--headless"',
        *(f'--only-audits={audit}' for audit in LIGHTHOUSE_AUDITS),
    ])
    logging.info('Done running Lighthouse CLI')

    return json.loads(raw)['audits']


# Required CSV row conversion function. Usually one row, can be more.
#
# Run locally.
def to_rows(data):
    return [[
        audit['id'],
        audit['description'],
        audit['title'],
        audit['score'],
        audit['scoreDisplayMode']
    ] for audit in data.values()]


# CSV headers for each row of data. Referenced locally.
headers = ['ID', 'Description', 'Title', 'Score', 'Score Display Mode']


# TODO: Add ability to override default LIGHTHOUSE_AUDITS
# Optional handler for custom CLI parameters. Takes the args (as a list of
# strings) and returns a dict of the options values and names that the scanner
# expects, and a list of the arguments it didn't know how to parse.
#
# Should return a dict of the options parsed by this parser (not a mutated form
# of the opts that are passed to it) and a list of the remaining args that it
# didn't recognize.
# def handle_scanner_args(args, opts) -> Tuple[dict, list]:
#     parser = ArgumentParser(prefix_chars='--')
#     parser.add_argument('--noop-delay', nargs=1)
#     parsed, unknown = parser.parse_known_args(args)
#     dicted = vars(parsed)
#     should_be_single = ['noop_delay']
#     dicted = make_values_single(dicted, should_be_single)
#     dicted['noop_delay'] = int(dicted['noop_delay'], 10)
#     return dicted, unknown
