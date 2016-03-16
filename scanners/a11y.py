import logging
from scanners import utils
import json
import os

workers = 1
PA11Y_STANDARD = 'WCAG2AA'
pa11y = os.environ.get("PA11Y_PATH", "pa11y")
headers = [
    "type",
    "typeCode",
    "code",
    "message",
    "context",
    "selector"
]

def scan(domain, options):
    logging.debug("[%s][a11y]" % domain)
    # The '--level none' piece here is crucial.
    # By default, pa11y will return with a non-zero exit code if at least one
    # error is detected in the scan. Setting '--level none'
    command = [pa11y, domain, "--reporter", "json", "--standard", PA11Y_STANDARD, "--level", "none"]
    raw = utils.scan(command)

    results = json.loads(raw)
    for data in results:
        yield [
            data['type'],
            data['typeCode'],
            data['code'],
            data['message'],
            data['context'],
            data['selector']
        ]
