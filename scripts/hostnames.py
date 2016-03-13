import logging
from scanners import utils
import json
import sys
import os
import urllib.parse

##
#
# This script looks through bulk data downloaded from censys.io. scans.io.
# and Certificate Transparency logs, for any unique hostnames matching a
# given pattern (regex).
#
##

# Drop output in a directory next to the script.
this_dir = os.path.dirname(__file__)
output = os.path.join(this_dir, "output")
utils.mkdir_p(output)

rdns = "20160309-rdns"


if len(sys.argv) < 2:
  print("Specify a pattern.")
  exit(1)

pattern = sys.argv[1]


# with open(rdns) as f:
#   for line in f:
#     if line

print("Done.")
