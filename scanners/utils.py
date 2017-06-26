import os
import re
import errno
import subprocess
import sys
import shutil
import traceback
import json
import urllib
import csv
import logging
import datetime
import strict_rfc3339


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
    return filename


# read options from the command line
#   e.g. ./scan --since=2012-03-04 --debug whatever.com
#     => {"since": "2012-03-04", "debug": True, "_": ["whatever.com"]}
def options():
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


def json_for(object):
    return json.dumps(object, sort_keys=True,
                      indent=2, default=format_datetime)


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


def report_dir():
    return options().get("output", "./")


def cache_dir():
    return os.path.join(report_dir(), "cache")


def results_dir():
    return os.path.join(report_dir(), "results")


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
        logging.warn("No command found: %s" % (str(command)))
        return False


def scan(command, env=None, allowed_return_codes=[]):
    try:
        response = subprocess.check_output(command, shell=False, env=env)
        return str(response, encoding='UTF-8')
    except subprocess.CalledProcessError as exc:
        if exc.returncode in allowed_return_codes:
            return str(exc.stdout, encoding='UTF-8')
        else:
            logging.warn("Error running %s." % (str(command)))
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
        raw = open(path).read()
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


# RFC 3339 timestamp for the current time when called
def utc_timestamp():
    return strict_rfc3339.now_to_rfc3339_utcoffset()


# return base domain for a subdomain
def base_domain_for(subdomain):
    return str.join(".", subdomain.split(".")[-2:])


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

    # TODO: kill this
    inspection = inspection[0]

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

    # TODO: kill this
    inspection = inspection[0]

    # We know the canonical URL, return True if it's www.
    url = inspection.get("Canonical URL")
    return (
        url.startswith("http://www") or
        url.startswith("https://www")
    )


# Check whether we have HTTP behavior data cached for a domain.
# If so, check if we know it's not live.
# Useful for skipping scans on non-live domains.
def domain_not_live(domain):
    # Make sure we have the data.
    inspection = data_for(domain, "pshtt")
    if not inspection:
        return False
    # TODO: kill this
    inspection = inspection[0]

    return (not inspection.get("Live"))


# Check whether we have HTTP behavior data cached for a domain.
# If so, check if we know it redirects.
# Useful for skipping scans on redirect domains.
def domain_is_redirect(domain):
    # Make sure we have the data.
    inspection = data_for(domain, "pshtt")
    if not inspection:
        return False
    # TODO: kill this
    inspection = inspection[0]

    return (inspection.get("Redirect") is True)


# Check whether we have HTTP behavior data cached for a domain.
# If so, check if we know its canonical URL.
# Useful for focusing scans on the right endpoint.
def domain_canonical(domain):
    # Make sure we have the data.
    inspection = data_for(domain, "pshtt")
    if not inspection:
        return False
    # TODO: kill this
    inspection = inspection[0]

    return (inspection.get("Canonical URL"))


# Load the first column of a CSV into memory as an array of strings.
def load_domains(domain_csv, whole_rows=False):
    domains = []
    with open(domain_csv, newline='') as csvfile:
        for row in csv.reader(csvfile):
            if (not row[0]) or (row[0].lower().startswith("domain")):
                continue

            row[0] = row[0].lower()

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
        if (row[0].lower().startswith("domain")):
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


# Given a user-input domain suffix, normalize it.
def normalize_suffix(suffix):
    if suffix is None:
        return None

    if not suffix.startswith("."):
        suffix = (".%s" % suffix)
    return suffix


# Given a domain suffix, provide a compiled regex.
# Assumes suffixes always begin with a dot.
def suffix_pattern(suffix):
    return re.compile("\\%s$" % suffix)
