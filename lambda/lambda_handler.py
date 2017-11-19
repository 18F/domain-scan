import importlib
import sys
import logging

from scanners import utils

# Central handler for all Lambda events.
def handler(event, context):
    start_time = utils.local_now()

    domain = event.get('domain')
    options = event.get('options')
    name = event.get('scanner')
    environment = event.get('environment')

    # Log all sent events, for the record.
    utils.configure_logging(options)
    logging.warn(event)

    # Might be acceptable to let this crash the module, in Lambda.
    try:
        scanner = importlib.import_module("scanners.%s" % name)
    except ImportError:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        logging.error("[%s] Scanner not found, or had an error during loading.\n\tERROR: %s\n\t%s" % (name, exc_type, exc_value))
        exit(1) # ?

    # Same method call as when run locally.
    data = scanner.scan(domain, environment, options)

    # We capture start and end times locally as well, but it's
    # useful to know the start/end from Lambda's vantage point.
    end_time = utils.local_now()
    duration = end_time - start_time
    response = {
        'lambda': {
            'log_group_name': context.log_group_name,
            'log_stream_name': context.log_stream_name,
            'request_id': context.aws_request_id,
            'memory_limit': context.memory_limit_in_mb,
            'start_time': start_time,
            'end_time': end_time,
            'measured_duration': duration
        },
        'data': data
    }

    # Serialize and re-parse the JSON, so that we run our own
    # date transform functions in one place, using the same function
    # that runs locally.
    return utils.from_json(utils.json_for(response))

