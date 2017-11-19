import json
import logging


# Reverse DNS
#
# Given a path to a (local) "JSON Lines" formatted file,
# based on Rapid7's Reverse DNS data, pull out the domains
# that match the given suffixes.
#
# Bearing in mind that the gathering system currently loads
# all domains into memory in order to dedupe them, it may be
# easiest to use this on a file that has been pre-filtered in
# some way (such as by grepping for the intended suffix).

def gather(suffixes, options, extra={}):
    path = options.get("rdns")

    if path is None:
        logging.warn("--rdns is required to be a path to a local file.")
        exit(1)

    # May become useful to allow URLs in future.
    if path.startswith("http:") or path.startswith("https:"):
        logging.warn("--rdns is required to be a path to a local file.")
        exit(1)

    with open(path) as lines:
        logging.debug("\tReading %s..." % path)

        for line in lines:
            record = json.loads(line)
            # logging.debug("\t%s" % record["value"])
            yield record["value"]
