import importlib
import sys

# TODO: import utils
import logging
import datetime


# Central handler for all Lambda events.
def handler(event, context):
    start_time = local_now()

    domain = event.get('domain')
    options = event.get('options')
    name = event.get('scanner')

    # Might be acceptable to let this crash the module, in Lambda.
    try:
        scanner = importlib.import_module("scanners.%s" % name)
    except ImportError:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        logging.error("[%s] Scanner not found, or had an error during loading.\n\tERROR: %s\n\t%s" % (name, exc_type, exc_value))
        exit(1) # ?

    # Log all sent events, for the record.
    configure_logging(options)
    logging.warn(event)

    # Same method call as when run locally.
    rows = list(scanner.scan(domain, options))

    end_time = local_now()
    duration = end_time - start_time
    return {
        'lambda': {
            'log_group_name': context.log_group_name,
            'log_stream_name': context.log_stream_name,
            'request_id': context.aws_request_id,
            'memory_limit': context.memory_limit_in_mb,
            'start_time': start_time,
            'end_time': end_time,
            'measured_duration': duration
        },
        'data': rows
    }


# TODO: refer to from central utils when packaged
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


def local_now():
    return datetime.datetime.now().timestamp()
