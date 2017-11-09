import logging
from scanners import utils

###
# == noop ==
#
# Testing scan function. Does nothing time consuming or destructive,
# but exercises all the main hooks of domain-scan.

# No command.

# Default to 2 workers.
workers = 2

# No-op init function.
def init(options):
  logging.warn("Init function called with options: %s" % options)
  return True


# No-op scan function.
def scan(domain, options):
  logging.debug("\tScan function called with options: %s" % options)

  logging.warn("\tComplete!")

  # Returns one row at a time.
  yield [True]

headers = ["No-op completed"]
