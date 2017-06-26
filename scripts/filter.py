#!/usr/bin/env python

from scanners import utils
import csv
import os
import re

##
#
# This script looks for any unique hostnames matching a given suffix.
# Expects suffixes to be able to be applied to the end of a given line.
#
# options:
#   _[0]: input file (required)
#
#   name: name of dataset (e.g. 'rdns', 'ct')
#   filter: name of filter to apply (defaults to value of --name)
#   suffix: suffix to filter on (e.g. '.gov')
#   encoding: input file encoding (defaults to 'latin-1')
#
#   max: cut off loop after this many lines
#   debug: display output when matching each line


def main():
    options = utils.options()

    debug = options.get('debug', False)
    encoding = options.get('encoding', 'latin-1')

    name = options.get('name', 'hostnames')
    filter_name = options.get('filter', name)
    filter = filters.get(filter_name, None)
    if filter is None:
        print("No filter by that name. Specify one with --filter.")
        exit(1)

    # Drop output in a directory next to the script.
    this_dir = os.path.dirname(__file__)
    output = os.path.join(this_dir, "hostnames")
    utils.mkdir_p(output)

    out_filename = "%s.csv" % name
    out_file = open(os.path.join(output, out_filename), 'w', newline='')
    out_writer = csv.writer(out_file)

    if len(options["_"]) < 1:
        print("Provide the name to an input file.")
        exit(1)

    input_filename = options["_"][0]

    if not os.path.exists(input_filename):
        print("Input file doesn't exist.")
        exit(1)

    suffix = options.get("suffix", ".gov")

    # if it has a ., make sure the . is escaped
    if suffix.startswith("."):
        suffix = "\\%s" % suffix
    pattern = re.compile("%s\n?$" % suffix)

    max = int(options.get("max", -1))

    # Proceed

    missed = 0
    matched = 0
    name_map = {}
    curr = 0

    with open(input_filename, encoding=encoding) as f:

        try:
            for line in f:

                if pattern.search(line):
                    hostname = filter(line)
                    if debug:
                        print("Match!!!! %s" % hostname)
                    matched += 1
                    name_map[hostname] = None
                else:
                    if debug:
                        print("Didn't match: %s" % line.strip())
                    missed += 1

                curr += 1
                if (max > 0) and (curr >= max):
                    print("Stopping at %i." % curr)
                    break

                if (curr % 1000000) == 0:
                    print("Processing: %i" % curr)
        except UnicodeDecodeError as e:
            print(curr)
            print(utils.format_last_exception())
            exit(1)

    hostnames = list(name_map.keys())
    hostnames.sort()

    print("Matched %i (%i unique), missed on %i." % (matched, len(hostnames), missed))

    print("Writing out CSV.")
    for hostname in hostnames:
        out_writer.writerow([hostname])

    print("Done.")

# Format-specific filters


# IP,hostname
# Used by: Rapid7 rdns
def filter_ip_pair(line):
    return str.split(line, ",")[-1].strip()


filters = {'ip_pair': filter_ip_pair}

main()
