import re
import logging
import datetime

# Recommended total Lambda task timeout.
timeout = 10

def handler(event, context):
  # TODO: move this into a central handler place
  start_time = local_now()
  configure_logging(event.get('options'))
  logging.warn(event)

  # Task content.
  complete = True
  logging.warn("Complete!")

  # TODO: wrap this in a central handler place
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
    'data': [ [complete] ]
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
