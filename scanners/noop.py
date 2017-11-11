import logging

###
# == noop ==
#
# Testing scan function. Does nothing time consuming or destructive,
# but exercises many of the main hooks of domain-scan.

# Default to 2 workers.
workers = 2


# No-op init function.
def init(options):
    logging.debug("Init function called with options: %s" % options)
    return True


# No-op scan function.
def scan(domain, options):
    logging.debug("\tScan function called with options: %s" % options)

    # Perform the "task".
    complete = True
    logging.warn("\tComplete!")

    # Returns one row at a time.
    yield [complete]


headers = ["No-op completed"]
