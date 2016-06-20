import logging
from scanners import utils
import json
import sys
import os
import re
import urllib.parse

##
#
# This script looks through bulk data downloaded from censys.io. scans.io.
# and Certificate Transparency logs, for any unique hostnames matching a
# given suffix.
#
##

# Drop output in a directory next to the script.
this_dir = os.path.dirname(__file__)
output = os.path.join(this_dir, "output")
utils.mkdir_p(output)

rdns = "data/censys/20160309-rdns"
rdns_out = "rdns.csv"

if len(sys.argv) < 2:
  print("Specify a suffix.")
  exit(1)

suffix = sys.argv[1]
if suffix.startswith("."):
  suffix = "\\%s" % suffix
pattern = re.compile("%s\n?$" % suffix)

with open(rdns) as f:
  with open(rdns_out, "w") as out:
    for line in f:
      if pattern.search(line):
        hostname = str.split(line, ",")[-1]
        print(hostname)
        out.write(hostname)
      # else:
      #   print("Didn't match: %s" % line)

print("Done.")
