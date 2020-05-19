"""
Implements a Google Lighthouse scan.

https://developers.google.com/web/tools/lighthouse

To use, set the `LIGHTHOUSE_PATH` environment variable to the Lighthouse path.
"""

import os


# Can also be run in Lambda.
# NOTE: untested
lambda_support = False

# Signal that this is a JS-based scan using headless Chrome.
# The scan method will be defined in lighthouse.js instead.
scan_headless = True

LIGHTHOUSE_PATH = os.environ.get('LIGHTHOUSE_PATH', 'lighthouse')
LIGHTHOUSE_AUDITS = [
    'color-contrast',
    'font-size',
    'image-alt',
    'input-image-alt',
    'performance-budget',
    'tap-targets',
    'timing-budget',
    'total-byte-weight',
    'unminified-css',
    'unminified-javascript',
    'uses-text-compression',
    'viewport',
    'speed-index',
]
CHROME_PATH = os.environ.get('CHROME_PATH')


# Set a default number of workers for a particular scan type.
# Overridden by a --workers flag.
workers = 1


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
    ] for name, audit in data.items() if name != 'error']


# CSV headers for each row of data. Referenced locally.
headers = ['ID', 'Description', 'Title', 'Score', 'Score Display Mode']


#
# Below is an implementation that will spawn Lighthouse via its cli rather than
# use a Puppeteer-managed headless Chrome.
#

# def _url_for_domain(domain: str, cache_dir: str):
#     if domain.startswith('http://') or domain.startswith('https://'):
#         return domain

#     # If we have data from pshtt, use the canonical endpoint.
#     canonical = utils.domain_canonical(domain, cache_dir=cache_dir)
#     if canonical:
#         return canonical

#     # Otherwise, well, whatever.
#     return 'http://' + domain

# Required scan function. This is the meat of the scanner, where things
# that use the network or are otherwise expensive would go.
#
# Runs locally or in the cloud (Lambda).
# def scan(domain: str, environment: dict, options: dict) -> dict:
#     logging.debug('Scan function called with options: %s', options)

#     cache_dir = options.get('_', {}).get('cache_dir', './cache')

#     url = _url_for_domain(domain, cache_dir)
#     lighthouse_cmd = ' '.join([
#         LIGHTHOUSE_PATH,
#         url,
#         '--quiet',
#         '--output=json',
#         '--chrome-flags="--headless --no-sandbox"',
#         *(f'--only-audits={audit}' for audit in LIGHTHOUSE_AUDITS),
#     ])

#     logging.info('Running Lighthouse CLI...')

#     try:
#         response = subprocess.check_output(
#             lighthouse_cmd,
#             stderr=subprocess.STDOUT,
#             shell=True, env=None
#         )
#         raw = str(response, encoding='UTF-8')
#         logging.info('Done running Lighthouse CLI')
#         return json.loads(raw)['audits']
#     except subprocess.CalledProcessError:
#         logging.warning("Error running Lighthouse scan for URL %s." % url)
#         return {}

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
