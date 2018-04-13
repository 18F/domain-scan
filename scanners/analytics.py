import argparse
import logging
import os
from pathlib import Path
from typing import Tuple
from urllib.parse import urlparse

from utils import utils, scan_utils

# Check whether a domain is present in a CSV, set in --analytics.


# The domains in --analytics will have been downloaded and
# loaded in options['analytics_domains'].
def scan(domain: str, environment: dict, options: dict):
    analytics_domains = options["analytics_domains"]
    return {
        'participating': (domain in analytics_domains)
    }


def to_rows(data):
    return [
        [data['participating']]
    ]


headers = ["Participates in Analytics"]


def handle_scanner_args(args, opts) -> Tuple[dict, list]:
    """
    --analytics: file path or URL to a CSV of participating domains.

    This function also handles checking for the existence of the file,
    downloading it succesfully, and reading the file in order to populate the
    list of analytics domains.
    """
    parser = scan_utils.ArgumentParser(prefix_chars="--")
    parser.add_argument("--analytics", nargs=1, required=True)
    parsed, unknown = parser.parse_known_args(args)
    dicted = parsed.__dict__
    should_be_single = ["analytics"]
    dicted = scan_utils.make_values_single(dicted, should_be_single)
    resource = dicted.get("analytics")
    if not resource.endswith(".csv"):
        no_csv = "".join([
            "--analytics should be the file path or URL to a CSV of participating",
            " domains and end with .csv, which '%s' does not" % resource
        ])
        logging.error(no_csv)
        raise argparse.ArgumentTypeError(no_csv)
    try:
        parsed_url = urlparse(resource)
    except:
        raise
    if parsed_url.scheme and parsed_url.scheme in ("http", "https"):
        analytics_path = Path(opts["_"]["cache_dir"], "analytics.csv").resolve()
        try:
            utils.download(resource, str(analytics_path))
        except:
            logging.error(utils.format_last_exception())
            no_csv = "--analytics URL %s not downloaded successfully." % resource
            logging.error(no_csv)
            raise argparse.ArgumentTypeError(no_csv)
    else:
        if not os.path.exists(resource):
            no_csv = "--analytics file %s not found." % resource
            logging.error(no_csv)
            raise FileNotFoundError(no_csv)
        else:
            analytics_path = resource

    analytics_domains = utils.load_domains(analytics_path)
    dicted["analytics_domains"] = analytics_domains
    del dicted["analytics"]

    return (dicted, unknown)
