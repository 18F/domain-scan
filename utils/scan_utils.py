import argparse
import codecs
import csv
import datetime
import errno
import importlib
import json
import logging
import os
import shutil
import subprocess
import sys
import traceback
from functools import singledispatch
from pathlib import Path
from typing import (
    Any,
    Iterable,
    List,
    Tuple,
    Union,
    cast,
)
from types import ModuleType
from urllib.error import URLError

import publicsuffix
import requests
import strict_rfc3339


MANDATORY_SCANNER_PROPERTIES = (
    "headers",
    "to_rows"
)
# global in-memory cache
suffix_list = None


# Time Conveniences #
# Now, in UTC, in seconds (with decimal microseconds).
def local_now() -> float:
    return datetime.datetime.now().timestamp()


def format_datetime(obj) -> Union[str, None]:
    if isinstance(obj, datetime.date):
        return obj.isoformat()
    elif isinstance(obj, str):
        return obj
    else:
        return None


# Cut off floating point errors, always output duration down to
# microseconds.
def just_microseconds(duration: float) -> str:
    if duration is None:
        return None
    return "%.6f" % duration


# RFC 3339 timestamp for a given UTC time.
# seconds can be a float, down to microseconds.
# A given time needs to be passed in *as* UTC already.
def utc_timestamp(seconds: Union[float, int]) -> Union[str, None]:
    if not seconds:
        return None
    return strict_rfc3339.timestamp_to_rfc3339_utcoffset(seconds)
# /Time Conveniences #


# Filesystem Conveniences #
# mkdir -p in python, from:
# https://stackoverflow.com/questions/600268/mkdir-p-functionality-in-python
def mkdir_p(path: str) -> None:
    try:
        os.makedirs(path)
    except OSError as exc:  # Python >2.5
        if exc.errno == errno.EEXIST:
            pass
        else:
            raise


def read(source):
    with open(source) as f:
        contents = f.read()
    return contents


def write(content: Union[bytes, str], destination: str,
          binary: bool=False) -> None:
    mkdir_p(os.path.dirname(destination))

    if binary:
        binary_content = cast(bytes, content)  # mypy wrangling
        with open(destination, "bw") as fb:
            fb.write(binary_content)
    else:
        string_content = cast(str, content)  # mypy wrangling
        with open(destination, "w", encoding="utf-8") as fs:
            fs.write(string_content)
# /Filesystem Conveniences #


# Error Conveniences #
def format_last_exception():
    exc_type, exc_value, exc_traceback = sys.exc_info()
    return "\n".join(traceback.format_exception(exc_type, exc_value,
                                                exc_traceback))
# Error Conveniences #


# Command Line Conveniences #
def scan(command: List[str], env: dict=None,
         allowed_return_codes: list=[]) -> Union[str, None]:
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
            logging.warning("Error running %s." % (str(command)))
            logging.warning("Error running %s." % (str(exc.output)))
            logging.warning(format_last_exception())
            return None


# test if a command exists, don't print output
def try_command(command):
    try:
        subprocess.check_call(["which", command], shell=False,
                              stdout=subprocess.DEVNULL,
                              stderr=subprocess.DEVNULL)
        return True
    except subprocess.CalledProcessError:
        logging.warning(format_last_exception())
        logging.warning("No command found: %s" % (str(command)))
        return False
# /Command Line Conveniences #


# JSON Conveniences #
# Format datetimes, sort keys, pretty-print.
def json_for(object: object) -> str:
    return json.dumps(object, sort_keys=True, indent=2, default=format_datetime)


# Mirror image of json_for.
def from_json(string):
    return json.loads(string)
# /JSON Conveniences #


# Logging Conveniences #
def configure_logging(options: Union[dict, None]=None) -> None:
    options = {} if not options else options
    if options.get('debug', False):
        log_level = "debug"
    else:
        log_level = options.get("log", "warn")

    if log_level not in ["debug", "info", "warn", "error"]:
        print("Invalid log level (specify: debug, info, warn, error).")
        sys.exit(1)

    logging.basicConfig(format='%(message)s', level=log_level.upper())
# /Logging Conveniences #


# CSV Handling #

# Sort a CSV by domain name, "in-place" (by making a temporary copy).
# This loads the whole thing into memory: it's not a great solution for
# super-large lists of domains.
def sort_csv(input_filename):
    logging.warning("Sorting %s..." % input_filename)

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


def write_rows(rows, domain, base_domain, scanner, csv_writer, meta={}):

    # If we didn't get any info, we'll still output information about why the scan failed.
    if rows is None:
        empty_row = [None] * len(scanner.headers)
        rows = [empty_row]

    # Always output Domain and Base Domain.
    standard_prefix = [
        domain,
        base_domain,
    ]

    # If requested, add local and Lambda scan data.
    meta_fields = []
    if bool(meta):
        meta_fields.append(" ".join(meta.get('errors', [])))
        meta_fields.append(utc_timestamp(meta.get("start_time")))
        meta_fields.append(utc_timestamp(meta.get("end_time")))
        meta_fields.append(just_microseconds(meta.get("duration")))

        if meta.get("lambda") is not None:
            meta_fields.append(meta['lambda'].get('request_id'))
            meta_fields.append(meta['lambda'].get('log_group_name'))
            meta_fields.append(meta['lambda'].get('log_stream_name'))
            meta_fields.append(utc_timestamp(meta['lambda'].get('start_time')))
            meta_fields.append(utc_timestamp(meta['lambda'].get('end_time')))
            meta_fields.append(meta['lambda'].get('memory_limit'))
            meta_fields.append(just_microseconds(meta['lambda'].get('measured_duration')))

    # Write out prefix, scan data, and meta scan data.
    for row in rows:
        csv_writer.writerow(standard_prefix + row + meta_fields)
# CSV Handling #


# Cache Handling #
def cache_single(filename, cache_dir="./cache"):
    return os.path.join(cache_dir, filename)


# Predictable cache path for a domain and operation.
def cache_path(domain, operation, ext="json", cache_dir="./cache"):
    return os.path.join(cache_dir, operation, ("%s.%s" % (domain, ext)))


# Used to quickly get cached data for a domain.
def data_for(domain, operation, cache_dir="./cache"):
    path = cache_path(domain, operation, cache_dir=cache_dir)
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


# Return base domain for a subdomain, factoring in the Public Suffix List.
def base_domain_for(subdomain, cache_dir="./cache"):
    global suffix_list

    """
    For "x.y.domain.gov", return "domain.gov".

    If suffix_list is None, the caches have not been initialized, so do that.
    """
    if suffix_list is None:
        suffix_list, discard = load_suffix_list(cache_dir=cache_dir)

    if suffix_list is None:
        logging.warning("Error downloading the PSL.")
        exit(1)

    return suffix_list.get_public_suffix(subdomain)


# Returns an instantiated PublicSuffixList object, and the
# list of lines read from the file.
def load_suffix_list(cache_dir="./cache"):

    cached_psl = cache_single("public-suffix-list.txt", cache_dir=cache_dir)

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
            logging.warning("Unable to download the Public Suffix List...")
            logging.debug("{}".format(err))
            return None, None

        content = cache_file.readlines()
        suffixes = publicsuffix.PublicSuffixList(content)

        # Cache for later.
        write(''.join(content), cached_psl)

    return suffixes, content
# /Cache Handling #


# Argument Parsing #
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


def build_scan_options_parser() -> ArgumentParser:
    """ Builds the argparse parser object. """
    parser = ArgumentParser(prefix_chars="--")
    parser.add_argument("domains", help="".join([
        "Either a comma-separated list of domains or the url of a CSV ",
        "file/path to a local CSV file containing the domains to be ",
        "domains to be scanned. The CSV's header row will be ignored ",
        "if the first cell starts with \"Domain\" (case-insensitive).",
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
    parser.add_argument("--output", nargs=1, default=["./"], help="".join([
        "Where to output the 'cache/' and 'results/' directories. ",
        "Defaults to './'.",
    ]))
    parser.add_argument("--workers", nargs=1,
                        help="Limit parallel threads per-scanner to a number.")
    # TODO: Should workers have a default value?
    parser.add_argument("--no-fast-cache", action="store_true", help="".join([
        "Do not use fast caching even if a scanner supports it.  This option ",
        "will cause domain-scan to use less memory, but some scans may be ",
        "repeated."
    ]))
    # TODO: Move the scanner-specific argument parsing to each scanner's code.

    # a11y:
    parser.add_argument("--a11y-config",
                        help="a11y: Location of pa11y config file (used with a11y scanner.")

    parser.add_argument("--a11y-redirects",
                        help="a11y: Location of YAML file with redirects to inform the a11y scanner.")
    # sslyze:
    parser.add_argument("--sslyze-serial",
                        help="sslyze: If set, will use a synchronous (single-threaded in-process) scanner. Defaults to true.")
    parser.add_argument("--sslyze-certs",
                        help="sslyze: If set, will use the CertificateInfoScanner and return certificate info. Defaults to true.")
    # trustymail:
    parser.add_argument("--starttls", help="".join([
        "trustymail: Only check mx records and STARTTLS support.  ",
        "(Implies --mx.)"
    ]))
    parser.add_argument("--timeout", help="".join([
        "trustymail: The DNS lookup timeout in seconds. (Default is 5.)"
    ]))
    parser.add_argument("--smtp-timeout", help="".join([
        "trustymail: The SMTP connection timeout in seconds. (Default is 5.)"
    ]))
    parser.add_argument("--smtp-localhost", help="".join([
        "trustymail: The hostname to use when connecting to SMTP ",
        "servers.  (Default is the FQDN of the host from ",
        "which trustymail is being run.)"
    ]))
    parser.add_argument("--smtp-ports", help="".join([
        "trustymail: A comma-delimited list of ports at which to look ",
        "for SMTP servers.  (Default is '25,465,587'.)"
    ]))
    parser.add_argument("--dns", help="".join([
        "trustymail: A comma-delimited list of DNS servers to query ",
        "against.  For example, if you want to use ",
        "Google's DNS then you would use the ",
        "value --dns-hostnames='8.8.8.8,8.8.4.4'.  By ",
        "default the DNS configuration of the host OS ",
        "(/etc/resolv.conf) is used.  Note that ",
        "the host's DNS configuration is not used at all "
        "if this option is used."
    ]))
    parser.add_argument("--no-smtp-cache", help="".join([
        "trustymail: Do not cache SMTP results during the run.  This",
        "may results in slower scans due to testing the ",
        "same mail servers multiple times."
    ]))
    parser.add_argument("--mx", help="".join([
        "trustymail: Only check MX records"
    ]))
    parser.add_argument("--spf", help="".join([
        "trustymail: Only check SPF records"
    ]))
    parser.add_argument("--dmarc", help="".join([
        "trustymail: Only check DMARC records"
    ]))

    return parser


def options() -> Tuple[dict, list]:
    """
    Parse options for the ``scan`` command.

    Impure
        Reads from sys.argv.
    """
    parser = build_scan_options_parser()
    parsed, unknown = parser.parse_known_args()

    opts = {k: v for k, v in vars(parsed).items() if v is not None}

    if opts.get("lambda_profile") and not opts.get("lambda"):
            raise argparse.ArgumentTypeError(
                "Can't set lambda profile unless lambda flag is set.")

    # We know we want one value, but the ``nargs`` flag means we get a list.
    should_be_singles = (
        "lambda_profile",
        "output",
        "scan",
        "suffix",
        "workers",
    )
    opts = make_values_single(opts, should_be_singles)

    # Derive some options not set directly at CLI:
    opts["_"] = {
        "cache_dir": os.path.join(opts.get("output", "./"), "cache"),
        "report_dir": opts.get("output", "./"),
        "results_dir": os.path.join(opts.get("output", "./"), "results"),
    }

    return (opts, unknown)


def make_values_single(dct: dict, should_be_singles: Iterable[str]) -> dict:
    for key in (k for k in should_be_singles if k in dct):
        dct[key] = dct[key][0]
    return dct


def handle_scanner_arguments(scans: List[ModuleType], opts: dict, unknown: List[str]):
    for scan in scans:
        if hasattr(scan, "handle_scanner_args"):
            scan_opts, unknown = scan.handle_scanner_args(unknown, opts)  # type: ignore
            opts.update(scan_opts)
    return (opts, unknown)
# /Argument Parsing #


def build_scanner_list(names: List[str],
                       mod: str="scanners") -> List[ModuleType]:
    """
    Given a list of names, load modules corresponding to those names from the
    scanners directory. Also verify that they have the required properties.
    """
    scans = []

    for name in names:
        try:
            scan = importlib.import_module(
                "%s.%s" % (mod, name))
            verify_scanner_properties(scan)
        except ImportError:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            errmsg = "\n".join([
                "[%s] Scanner not found, or had an error during loading." % name,
                "\tERROR: %s" % exc_type,
                "\t%s" % exc_value,
            ])
            logging.error(errmsg)
            raise ImportError(errmsg)

        scans.append(scan)

    return scans


def verify_scanner_properties(scanner: ModuleType) -> None:
    name = scanner.__name__
    for prop in MANDATORY_SCANNER_PROPERTIES:
        if not hasattr(scanner, prop):
            raise ImportError("%s lacks required %s property" % (name, prop))

    # If the scan has a canonical command, make sure it exists.
    # mypy doesn't handle optional properties well, it seems.
    if hasattr(scan, "command") and scan.command and (not try_command(scan.command)):  # type: ignore
        errmsg = "[%s] Command not found: %s" % (name, scan.command)  # type: ignore
        logging.error(errmsg)
        raise ImportError(errmsg)


def begin_csv_writing(scanner: ModuleType, options: dict,
                      base_hdrs: Tuple[List[str], List[str], List[str]]) -> dict:
    """
    Determine the CSV output file path for the scanner, open the file at that
    path, instantiate a CSV writer for it, determine whether or not to use
    lambda, determine what the headers are, write the headers to the CSV.

    Return a dict containing the above.
    """
    PREFIX_HEADERS, LOCAL_HEADERS, LAMBDA_HEADERS = base_hdrs
    name = scanner.__name__.split(".")[-1]  # e.g. 'pshtt'
    results_dir = options["_"]["results_dir"]
    meta = options.get("meta")
    lambda_mode = options.get("lambda")
    use_lambda = lambda_mode and \
        hasattr(scanner, "lambda_support") and \
        scanner.lambda_support  # type: ignore  # it's an optional variable.

    # Write the header row, factoring in Lambda detail if needed.
    headers = PREFIX_HEADERS + scanner.headers  # type: ignore  # optional again
    # Local scan timing/errors.
    if meta:
        headers += LOCAL_HEADERS
    # Lambda scan timing/errors. (At this step, only partial fields.)
    if meta and use_lambda:
        headers += LAMBDA_HEADERS

    scanner_csv_path = Path(results_dir, "%s.csv" % name).resolve()
    scanner_file = scanner_csv_path.open('w', newline='')
    scanner_writer = csv.writer(scanner_file)

    scanner_writer.writerow(headers)

    return {
        'name': name,
        'file': scanner_file,
        'filename': str(scanner_csv_path),
        'writer': scanner_writer,
        'headers': headers,
        'use_lambda': use_lambda,
    }


def determine_scan_workers(scanner: ModuleType, options: dict, w_default: int,
                           w_max: int) -> int:
    """
    Given a number of inputs, determines the right number of workers to set
    when running scans.
    """
    if options.get("serial"):
        workers = 1
    elif hasattr(scanner, "workers"):
        workers = scanner.workers  # type: ignore # The subclass objects set this sometimes.
    else:
        # mypy has trouble with this, presumably because we're using a dict
        workers = int(options.get("workers", w_default))  # type: ignore

    # Enforce a local worker maximum as a safety valve.
    return min(workers, w_max)


# Yield domain names from a single string, or a CSV of them.
@singledispatch
def domains_from(arg: Any, domain_suffix=None) -> Iterable[str]:
    raise TypeError("'%s' is not a recognized source for domains." % arg)


@domains_from.register(str)
def _df_str(arg: str, domain_suffix: Union[str, None]=None) -> Iterable[str]:
    # TODO: how do we handle domain_suffix here?
    if domain_suffix is not None:
        errmsg = "Passing in domains at CLI not compatible with --suffix."
        raise argparse.ArgumentError(errmsg)

    for x in arg.split(","):
        yield x


@domains_from.register(Path)
def _df_path(arg: Path, domain_suffix: Union[str, None]=None) -> Iterable[str]:
    if arg.suffix == ".csv":
        with arg.open(encoding='utf-8', newline='') as csvfile:
            for row in csv.reader(csvfile):
                if (not row[0]) or (row[0].lower() == "domain") or (row[0].lower() == "domain name"):
                    continue
                domain = row[0].lower()
                if domain_suffix:
                    sep = "."
                    if domain_suffix.startswith("."):
                        sep = ""
                    yield "%s%s%s" % (domain, sep, domain_suffix)
                else:
                    yield domain
    else:
        # Note: the path referred to below will be the path to the local cached
        # download and not to the original URL. It shouldn't be possible to get
        # here with that being a problem, but noting it anyway.
        msg = "\n".join([
            "Domains should be specified as a comma-separated list ",
            "or as the URL or path to a .csv file. ",
            "%s does not appear to be any of those." % arg
        ])
        raise TypeError(msg)


def handle_domains_argument(domains: str, cache_dir: Path) -> Union[Path, str]:
    # `domains` can be either a path or a domain name.
    # It can also be a URL, and if it is we want to download it now,
    # and then adjust the value to be the path of the cached download.
    # Note that the cache_dir is basically guaranteed to exist by the time
    # we reach this point in the execution path.
    if domains.startswith("http:") or domains.startswith("https:"):
        domains_path = Path(cache_dir, "domains.csv")
        try:
            response = requests.get(domains)
            write(response.text, str(domains_path))
        except requests.exceptions.RequestException as err:
            msg = "\n".join([
                "Domains URL not downloaded successfully; RequestException",
                str(err),
            ])
            logging.error(msg)
            raise IOError(msg)

        return domains_path
    elif domains.endswith(".csv"):
        # Assume file is either absolute or relative from current dir.
        try:
            domains_path = Path(os.path.curdir, domains).resolve()
            if not domains_path.exists():
                raise FileNotFoundError
            return domains_path
        except FileNotFoundError as err:
            msg = "\n".join([
                "Domains CSV file not found.",
                "(Curdir: %s CSV file: %s)" % (os.path.curdir, domains),
                str(err),
            ])
            logging.error(msg)
            raise FileNotFoundError(msg)
    return domains
