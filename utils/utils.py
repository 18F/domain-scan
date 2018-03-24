import argparse
import os
import re
import errno
import subprocess
import sys
import gzip
import shutil
import traceback
import json
import urllib
import csv
import logging
import datetime
import strict_rfc3339
import codecs
from itertools import chain
from urllib.error import URLError

import publicsuffix
# global in-memory cache
suffix_list = None


# Wrapper to a run() method to catch exceptions.
def run(run_method, additional=None):
    cli_options = options()
    configure_logging(cli_options)

    if additional:
        cli_options.update(additional)

    try:
        return run_method(cli_options)
    except Exception as exception:
        notify(exception)


# TODO: Somewhat better error handling.
def download(url, destination):
    # make sure path is present
    mkdir_p(os.path.dirname(destination))

    filename, headers = urllib.request.urlretrieve(url, destination)

    # If it's a gzipped file, ungzip it and replace it
    if headers.get("Content-Encoding") == "gzip":
        print("hey")
        unzipped_file = filename + ".unzipped"

        with gzip.GzipFile(filename, 'rb') as inf:
            with open(unzipped_file, 'w') as outf:
                outf.write(inf.read().decode('utf-8'))

        shutil.copyfile(unzipped_file, filename)

    return filename


# read options from the command line
#   e.g. ./scan --since=2012-03-04 --debug whatever.com
#     => {"since": "2012-03-04", "debug": True, "_": ["whatever.com"]}
def xoptions_for_scan():
    # Parse options for the ``scan`` command.
    options = {"_": []}
    for arg in sys.argv[1:]:
        if arg.startswith("--"):

            if "=" in arg:
                key, value = arg.split('=')
            else:
                key, value = arg, "True"

            key = key.split("--")[1]
            if value.lower() == 'true':
                value = True
            elif value.lower() == 'false':
                value = False
            options[key.lower()] = value
        else:
            options["_"].append(arg)
    return options


def options_endswith(end):
    def func(arg):
        if arg.endswith(end):
            return arg
        raise argparse.ArgumentTypeError("value must end in '%s'" % end)
    return func


class ArgumentParser(argparse.ArgumentParser):
    """
    This lets us test for errors from argparse by overriding the error method.
    See https://stackoverflow.com/questions/5943249
    """
    def _get_action_from_name(self, name):
        """Given a name, get the Action instance registered with this parser.
        If only it were made available in the ArgumentError object. It is
        passed as its first arg...
        """
        container = self._actions
        if name is None:
            return None
        for action in container:
            if '/'.join(action.option_strings) == name:
                return action
            elif action.metavar == name:
                return action
            elif action.dest == name:
                return action

    def error(self, message):
        exc = sys.exc_info()[1]
        if exc:
            exc.argument = self._get_action_from_name(exc.argument_name)
            raise exc
        super(ArgumentParser, self).error(message)


def options():
    if sys.argv[0].endswith("gather"):
        return options_for_gather()
    elif sys.argv[0].endswith("scan"):
        return options_for_scan()


def build_gather_options_parser(services):
    usage_message = "".join([
        "%(prog)s GATHERERS --suffix [SUFFIX] "
        "--[GATHERER] [GATHERER OPTIONS] [options] ",
        "(GATHERERS and SUFFIX are comma-separated lists)\n",
        "For example:\n",
        "./gather dap --suffix=.gov ",
        "--dap=https://analytics.usa.gov/data/live/sites-extended.csv"
    ])
    parser = ArgumentParser(prefix_chars="--", usage=usage_message)

    for service in services:
        flag = "--%s" % service
        parser.add_argument(flag, nargs=1, required=True)

    parser.add_argument("--cache", action="store_true",
                        help="Use local filesystem cache (censys only).")
    parser.add_argument("--debug", action="store_true",
                        help="Show debug information.")
    parser.add_argument("--ignore-www", action="store_true",
                        help="Ignore the www. prefixes of hostnames.")
    parser.add_argument("--include-parents", action="store_true",
                        help="Include second-level domains.")
    parser.add_argument("--log", nargs=1)
    parser.add_argument("--parents", nargs=1, help="".join([
        "A path or URL to a CSV whose first column is second-level domains. ",
        "Any subdomain not contained within these second-level domains will ",
        "be excluded."
    ]))
    parser.add_argument("--sort", action="store_true", help="".join([
        "Sort result CSVs by domain name, alphabetically. (Note: this causes ",
        "the entire dataset to be read into memory.)",
    ]))
    parser.add_argument("--suffix", nargs=1, required=True, help="".join([
        "Comma-separated list of suffixes, e.g '.gov' ",
        "or '.fed.us' or '.gov,.gov.uk' (required)."
    ]))
    parser.add_argument("--timeout", nargs=1, help="".join([
        "Override the 10 minute job timeout (specify in seconds) ",
        "(censys only).",
    ]))
    return parser


def options_for_gather():
    """
    Parse options for the ``gather`` command.

    The gather command requires a comma-separated list of one or more
    gatherers, and an argument (with a value) whose name corresponds to each
    gatherer, as well as a mandatory suffix value.

    ``./gather dap --suffix=.gov`` is insuffucient, because the present of the
    ``dap`` gatherer means that ``--dap=<someurl>`` is therefore required as an
    argument.

    Hence we look for the first argument before building the parser, so that
    the additional required arguments can be passed to it.

    The ``set_services`` are those services, like ``censys``, that don't have a
    matching argument, and the inclusion of the help flags is necessary here so
    that they don't get added as services.
    """
    set_services = (
        ",",
        "--help",
        "-h",
        "censys",
    )
    services = [s.strip() for s in sys.argv[1].split(",")
                if s not in set_services and s.strip()]
    if services and services[0].startswith("--"):
            raise argparse.ArgumentTypeError(
                "First argument must be a list of gatherers.")

    parser = build_gather_options_parser(services)
    parsed, remaining = parser.parse_known_args()

    for remainder in remaining:
        if remainder.startswith("--") or remainder == ",":
            raise argparse.ArgumentTypeError(
                "%s isn't a valid argument here." % remainder)
    opts = parsed.__dict__
    opts = {k: opts[k] for k in opts if opts[k] is not None}

    """
    The following expect a single argument, but argparse returns lists for them
    because that's how ``nargs=<n/'*'/'+'>`` works, so we need to extract the
    single values.
    """
    should_be_singles = [
        "parents",
        "suffix",
    ]
    for service in services:
        should_be_singles.append(service)

    for kwd in should_be_singles:
        if kwd in opts:
            opts[kwd] = opts[kwd][0]

    opts["gatherers"] = [g.strip() for g in
                         remaining[0].split(",") if g.strip()]
    if not opts["gatherers"]:
        raise argparse.ArgumentTypeError(
            "First argument must be a comma-separated list of gatherers")

    # Some of the flags should only be present if a given gatherer is present.
    matching_args = (
        {"args": ["cache", "timeout"], "gatherer": "censys"},
    )
    candidates = (ma for ma in matching_args
                  if ma["gatherer"] not in opts["gatherers"])

    for ma in candidates:
        for arg in ma["args"]:
            if arg in opts and opts[arg]:
                raise argparse.ArgumentTypeError(
                    "%s doesn't apply with the specified gatherers" % arg)

    # Some of the arguments expect single values on the command line, but those
    # values may contain comma-separated multiple values, so create the
    # necessary lists here.

    def fix_suffix(suffix: str) -> str:
        return suffix if suffix.startswith(".") else ".%s" % suffix

    opts["suffix"] = [fix_suffix(s.strip()) for s in opts["suffix"].split(",")
                      if s.strip()]
    return opts


def build_scan_options_parser(services):
    parser = ArgumentParser(prefix_chars="--")
    parser.add_argument("domains", help="".join([
        "Either a comma-separated list of domains or the path to a local CSV ",
        "file containing the domains to be scanned. The CSV's header row ",
        "will be ignored if the first cell starts with \"Domain\" ",
        "(case-insensitive).",
    ]))
    parser.add_argument("--cache", action="store_true", help="".join([
        "Use previously cached scan data to avoid scans hitting the network ",
        "where possible.",
    ]))
    parser.add_argument("--debug", action="store_true",
                        help="Print out more stuff. Useful with '--serial'")
    parser.add_argument("--lambda", action="store_true", help="".join([
        "Run certain scanners inside Amazon Lambda instead of locally.",
    ]))
    parser.add_argument("--lambda-profile", nargs=1, help="".join([
        "When running Lambda-related commands, use a specified AWS named ",
        "profile. Credentials/config for this named profile should already ",
        "be configured separately in the execution environment.",
    ]))
    parser.add_argument("--meta", action="store_true", help="".join([
        "Append some additional columns to each row with information about ",
        "the scan itself. This includes start/end times and durations, as ",
        "well as any encountered errors. When also using '--lambda', ",
        "additional, Lambda-specific information will be appended.",
    ]))
    parser.add_argument("--scan", nargs=1, required=True,
                        help="Comma-separated list of scanners (required).")
    parser.add_argument("--sort", action="store_true", help="".join([
        "Sort result CSVs by domain name, alphabetically. (Note: this causes ",
        "the entire dataset to be read into memory.)",
    ]))
    parser.add_argument("--serial", action="store_true", help="".join([
        "Disable parallelization, force each task to be done simultaneously. ",
        "Helpful for testing and debugging.",
    ]))

    parser.add_argument("--suffix", nargs=1, help="".join([
        "Add a suffix to all input domains. For example, a --suffix of ",
        "'virginia.gov' will add '.virginia.gov' to the end of all ",
        "input domains."
    ]))
    parser.add_argument("--output", nargs=1, help="".join([
        "Where to output the 'cache/' and 'results/' directories. ",
        "Defaults to './'.",
    ]))
    parser.add_argument("--workers", nargs=1,
                        help="Limit parallel threads per-scanner to a number.")
    # TODO: Should output and workers have default values?

    return parser


def options_for_scan():
    # Parse options for the ``scan`` command.
    parser = build_scan_options_parser([])
    parsed = parser.parse_args()

    opts = parsed.__dict__
    opts = {k: opts[k] for k in opts if opts[k] is not None}
    opts["_"] = opts["domains"]
    del opts["domains"]

    if opts.get("lambda_profile") and not opts.get("lambda"):
            raise argparse.ArgumentTypeError(
                "Can't set lambda profile unless lambda flag is set.")

    should_be_singles = [
        "lambda_profile",
        "output",
        "scan",
        "suffix",
        "workers",
    ]

    for kwd in should_be_singles:
        if kwd in opts:
            opts[kwd] = opts[kwd][0]

    return opts


def configure_logging(options=None):
    options = {} if not options else options
    if options.get('debug', False):
        log_level = "debug"
    else:
        log_level = options.get("log", "warn")

    if log_level not in ["debug", "info", "warn", "error"]:
        print("Invalid log level (specify: debug, info, warn, error).")
        sys.exit(1)

    logging.basicConfig(format='%(message)s', level=log_level.upper())


# mkdir -p in python, from:
# https://stackoverflow.com/questions/600268/mkdir-p-functionality-in-python
def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc:  # Python >2.5
        if exc.errno == errno.EEXIST:
            pass
        else:
            raise


# Format datetimes, sort keys, pretty-print.
def json_for(object):
    return json.dumps(object, sort_keys=True, indent=2, default=format_datetime)


# Mirror image of json_for.
def from_json(string):
    return json.loads(string)


def format_datetime(obj):
    if isinstance(obj, datetime.date):
        return obj.isoformat()
    elif isinstance(obj, str):
        return obj
    else:
        return None


def write(content, destination, binary=False):
    mkdir_p(os.path.dirname(destination))

    if binary:
        f = open(destination, 'bw')
    else:
        f = open(destination, 'w', encoding='utf-8')
    f.write(content)
    f.close()


def read(source):
    with open(source) as f:
        contents = f.read()
    return contents


def report_dir():
    return options().get("output", "./")


def cache_dir():
    return os.path.join(report_dir(), "cache")


def results_dir():
    return os.path.join(report_dir(), "results")


# Read in JSON file of known third party services.
def known_services():
    return from_json(read(os.path.join("./utils/known_services.json")))


def notify(body):
    try:
        if isinstance(body, Exception):
            body = format_last_exception()

        logging.error(body)  # always print it

    except Exception:
        print("Exception logging message to admin, halting as to avoid loop")
        print(format_last_exception())


def format_last_exception():
    exc_type, exc_value, exc_traceback = sys.exc_info()
    return "\n".join(traceback.format_exception(exc_type, exc_value,
                                                exc_traceback))


# test if a command exists, don't print output
def try_command(command):
    try:
        subprocess.check_call(["which", command], shell=False,
                              stdout=subprocess.DEVNULL,
                              stderr=subprocess.DEVNULL)
        return True
    except subprocess.CalledProcessError:
        logging.warn(format_last_exception())
        logging.warn("No command found: %s" % (str(command)))
        return False


def scan(command, env=None, allowed_return_codes=[]):
    try:
        response = subprocess.check_output(
            command,
            stderr=subprocess.STDOUT,
            shell=False, env=env
        )
        return str(response, encoding='UTF-8')
    except subprocess.CalledProcessError as exc:
        if exc.returncode in allowed_return_codes:
            return str(exc.stdout, encoding='UTF-8')
        else:
            logging.warn("Error running %s." % (str(command)))
            logging.warn("Error running %s." % (str(exc.output)))
            logging.warn(format_last_exception())
            return None

# Turn shell on, when shell=False won't work.


def unsafe_execute(command):
    try:
        response = subprocess.check_output(command, shell=True)
        return str(response, encoding='UTF-8')
    except subprocess.CalledProcessError:
        logging.warn("Error running %s." % (str(command)))
        return None

# Predictable cache path for a domain and operation.


def cache_path(domain, operation, ext="json"):
    return os.path.join(cache_dir(), operation, ("%s.%s" % (domain, ext)))


# cache a single one-off file, not associated with a domain or operation
def cache_single(filename):
    return os.path.join(cache_dir(), filename)


# Used to quickly get cached data for a domain.
def data_for(domain, operation):
    path = cache_path(domain, operation)
    if os.path.exists(path):
        raw = read(path)
        data = json.loads(raw)
        if isinstance(data, dict) and (data.get('invalid', False)):
            return None
        else:
            return data
    else:
        return {}


# marker for a cached invalid response
def invalid(data=None):
    if data is None:
        data = {}
    data['invalid'] = True
    return json_for(data)


# RFC 3339 timestamp for a given UTC time.
# seconds can be a float, down to microseconds.
# A given time needs to be passed in *as* UTC already.
def utc_timestamp(seconds):
    if not seconds:
        return None
    return strict_rfc3339.timestamp_to_rfc3339_utcoffset(seconds)


# Convert a RFC 3339 timestamp back into a local number of seconds.
def utc_timestamp_to_local_now(timestamp):
    return strict_rfc3339.rfc3339_to_timestamp(timestamp)


# Now, in UTC, in seconds (with decimal microseconds).
def local_now():
    return datetime.datetime.now().timestamp()


# Cut off floating point errors, always output duration down to
# microseconds.
def just_microseconds(duration):
    if duration is None:
        return None
    return "%.6f" % duration


# Return base domain for a subdomain, factoring in the Public Suffix List.
def base_domain_for(subdomain):
    global suffix_list

    """
    For "x.y.domain.gov", return "domain.gov".

    If suffix_list is None, the caches have not been initialized, so do that.
    """
    if suffix_list is None:
        suffix_list, discard = load_suffix_list()

    if suffix_list is None:
        logging.warn("Error downloading the PSL.")
        exit(1)

    return suffix_list.get_public_suffix(subdomain)


# Returns an instantiated PublicSuffixList object, and the
# list of lines read from the file.
def load_suffix_list():

    cached_psl = cache_single("public-suffix-list.txt")

    if os.path.exists(cached_psl):
        logging.debug("Using cached Public Suffix List...")
        with codecs.open(cached_psl, encoding='utf-8') as psl_file:
            suffixes = publicsuffix.PublicSuffixList(psl_file)
            content = psl_file.readlines()
    else:
        # File does not exist, download current list and cache it at given location.
        logging.debug("Downloading the Public Suffix List...")
        try:
            cache_file = publicsuffix.fetch()
        except URLError as err:
            logging.warn("Unable to download the Public Suffix List...")
            logging.debug("{}".format(err))
            return None, None

        content = cache_file.readlines()
        suffixes = publicsuffix.PublicSuffixList(content)

        # Cache for later.
        write(''.join(content), cached_psl)

    return suffixes, content


# Check whether we have HTTP behavior data cached for a domain.
# If so, check if we know it doesn't support HTTPS.
# Useful for saving time on TLS-related scanning.
def domain_doesnt_support_https(domain):
    # Make sure we have the cached data.
    inspection = data_for(domain, "pshtt")
    if not inspection:
        return False

    if (inspection.__class__ is dict) and inspection.get('invalid'):
        return False

    https = inspection.get("endpoints").get("https")
    httpswww = inspection.get("endpoints").get("httpswww")

    def endpoint_used(endpoint):
        return endpoint.get("live") and (not endpoint.get("https_bad_hostname"))

    return (not (endpoint_used(https) or endpoint_used(httpswww)))


# Check whether we have HTTP behavior data cached for a domain.
# If so, check if we know it canonically prepends 'www'.
def domain_uses_www(domain):
    # Don't prepend www to www.
    if domain.startswith("www."):
        return False

    # Make sure we have the data.
    inspection = data_for(domain, "pshtt")

    if not inspection:
        return False
    if (inspection.__class__ is dict) and inspection.get('invalid'):
        return False

    # We know the canonical URL, return True if it's www.
    url = inspection.get("Canonical URL")
    return (
        url.startswith("http://www") or
        url.startswith("https://www")
    )


def domain_mail_servers_that_support_starttls(domain):
    retVal = []
    data = data_for(domain, 'trustymail')
    if data:
        starttls_results = data.get('Domain Supports STARTTLS Results')
        if starttls_results:
            retVal = starttls_results.split(', ')

    return retVal


# Check whether we have HTTP behavior data cached for a domain.
# If so, check if we know it's not live.
# Useful for skipping scans on non-live domains.
def domain_not_live(domain):
    # Make sure we have the data.
    inspection = data_for(domain, "pshtt")
    if not inspection:
        return False

    return (not inspection.get("Live"))


# Check whether we have HTTP behavior data cached for a domain.
# If so, check if we know it redirects.
# Useful for skipping scans on redirect domains.
def domain_is_redirect(domain):
    # Make sure we have the data.
    inspection = data_for(domain, "pshtt")
    if not inspection:
        return False

    return (inspection.get("Redirect") is True)


# Check whether we have HTTP behavior data cached for a domain.
# If so, check if we know its canonical URL.
# Useful for focusing scans on the right endpoint.
def domain_canonical(domain):
    # Make sure we have the data.
    inspection = data_for(domain, "pshtt")
    if not inspection:
        return False

    return (inspection.get("Canonical URL"))


# Load the first column of a CSV into memory as an array of strings.
def load_domains(domain_csv, whole_rows=False):
    domains = []
    with open(domain_csv, newline='') as csvfile:
        for row in csv.reader(csvfile):
            # Skip empty rows.
            if (not row) or (not row[0].strip()):
                continue

            row[0] = row[0].lower()

            # Skip any header row.
            if (not domains) and (row[0].startswith("domain")):
                continue

            if whole_rows:
                domains.append(row)
            else:
                domains.append(row[0])
    return domains


# Sort a CSV by domain name, "in-place" (by making a temporary copy).
# This loads the whole thing into memory: it's not a great solution for
# super-large lists of domains.
def sort_csv(input_filename):
    logging.warn("Sorting %s..." % input_filename)

    input_file = open(input_filename, encoding='utf-8', newline='')
    tmp_filename = "%s.tmp" % input_filename
    tmp_file = open(tmp_filename, 'w', newline='')
    tmp_writer = csv.writer(tmp_file)

    # store list of domains, to sort at the end
    domains = []

    # index rows by domain
    rows = {}
    header = None

    for row in csv.reader(input_file):
        # keep the header around
        if (row[0].lower() == "domain"):
            header = row
            continue

        # index domain for later reference
        domain = row[0]
        domains.append(domain)
        rows[domain] = row

    # straight alphabet sort
    domains.sort()

    # write out to a new file
    tmp_writer.writerow(header)
    for domain in domains:
        tmp_writer.writerow(rows[domain])

    # close the file handles
    input_file.close()
    tmp_file.close()

    # replace the original
    shutil.move(tmp_filename, input_filename)


# Given a domain suffix, provide a compiled regex.
# Assumes suffixes always begin with a dot.
#
# e.g. [".gov", ".gov.uk"] -> "(?:\\.gov|\\.gov.uk)$"
def suffix_pattern(suffixes):
    prefixed = [suffix.replace(".", "\\.") for suffix in suffixes]
    center = str.join("|", prefixed)
    return re.compile("(?:%s)$" % center)


def flatten(l):
    return list(chain.from_iterable(l))
