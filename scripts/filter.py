#!/usr/bin/env python

import logging
from scanners import utils
import json
import csv
import sys
import os
import re
import urllib.parse

##
#
# This script looks for any unique hostnames matching a given suffix.
# Expects suffixes to be able to be applied to the end of a given line.
#
##

# options:
#   _[0]: input file
#
#   name: name of dataset (e.g. 'rdns', 'ct')
#   suffix: suffix to filter on (e.g. '.gov')
#   max: cut off loop after this many lines
#   debug: display output for matches and not matches
#   encoding: file encoding (defaults to 'latin-1')

def main():
  options = utils.options()

  debug = options.get('debug', False)
  encoding = options.get('encoding', 'latin-1')

  name = options.get('name', 'hostnames')

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

  ######## Proceed

  missed = 0
  matched = 0
  name_map = {}
  curr = 0

  with open(input_filename, encoding="latin-1") as f:

    try:
      for line in f:

        if pattern.search(line):
          hostname = filters[name](line)
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

# Rapid7 rdns format - IP,hostname
def filter_rdns(line):
  return str.split(line, ",")[-1].strip()

filters = {'rdns': filter_rdns}


main()
