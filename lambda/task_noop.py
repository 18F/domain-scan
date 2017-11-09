import re
import logging

# Recommended total Lambda task timeout.
timeout = 10

def handler(event, context):
  configure_logging(event.get('options'))
  logging.warn(event)

  logging.warn("Complete!")

  # Return one row.
  return {
    'lambda': {
      'log_group_name': context.log_group_name,
      'log_stream_name': context.log_stream_name,
      'request_id': context.aws_request_id
    },
    'data': [ [True] ]
  }

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


