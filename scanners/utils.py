import os
import errno
import subprocess
import sys
import traceback
import json
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


# read options from the command line
#   e.g. ./scan --inspect --debug
#     => {"since": "2012-03-04", "debug": True}
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
# http://stackoverflow.com/questions/600268/mkdir-p-functionality-in-python
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
            body = format_exception(body)

        logging.error(body)  # always print it

    except Exception as exception:
        print("Exception logging message to admin, halting as to avoid loop")
        print(format_exception(exception))


def format_exception(exception):
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


def scan(command):
    try:
        response = subprocess.check_output(command, shell=False)
        return str(response, encoding='UTF-8')
    except subprocess.CalledProcessError:
        logging.warn("Error running %s." % (str(command)))
        return None


# Predictable cache path for a domain and operation.
def cache_path(domain, operation):
    return os.path.join(cache_dir(), operation, ("%s.json" % domain))


# Used to quickly get cached data for a domain.
def data_for(domain, operation):
    path = cache_path(domain, operation)
    if os.path.exists(path):
        raw = open(path).read()
        return json.loads(raw)
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

# Load the first column of a CSV into memory as an array of strings.
def load_domains(domain_csv):
    domains = []
    with open(domain_csv, newline='') as csvfile:
        for row in csv.reader(csvfile):
            if (not row[0]) or (row[0].lower().startswith("domain")):
                continue
            domains.append(row[0].lower())
    return domains
