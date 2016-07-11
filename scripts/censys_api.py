#!/usr/bin/env python

from scanners import utils
import csv
import os
import re
import time

# Drop output in a directory next to the script.
this_dir = os.path.dirname(__file__)
output = os.path.join(this_dir, "hostnames")
utils.mkdir_p(output)

out_filename = "censys.csv"
out_file = open(os.path.join(output, out_filename), 'w', newline='')
out_writer = csv.writer(out_file)

# pip install censys
import censys.certificates

options = utils.options()
debug = options.get("debug", False)
suffix = options.get("suffix", ".gov")

wildcard_pattern = re.compile("\*.")

# time to sleep between requests (defaults to 5s)
delay = int(options.get("delay", 5))

# Censys page size, fixed
page_size = 100

# If an --end page is given, override --max
start_page = int(options.get("start", 1))
end_page = int(options.get("end", start_page))
max_records = ((end_page - start_page) + 1) * page_size

suffix = options.get("suffix", ".gov")
suffix_pattern = "%s$" % suffix
if suffix_pattern.startswith("."):
    suffix_pattern = "\\%s" % suffix_pattern
suffix_pattern = re.compile(suffix_pattern)

uid = os.environ.get("CENSYS_UID", None)
api_key = os.environ.get("CENSYS_API_KEY", None)

hostnames_map = {}

def main():

    certificates = censys.certificates.CensysCertificates(uid, api_key)

    fields = [
        "parsed.subject.common_name",
        "parsed.extensions.subject_alt_name.dns_names"
    ]

    query = "parsed.subject.common_name:%s or parsed.extensions.subject_alt_name.dns_names:%s" % (suffix, suffix)
    print("Censys query:\n%s\n" % query)

    current_page = start_page

    print("Fetching up to %i records, starting at page %i." % (max_records, start_page))

    while current_page <= end_page:
        if current_page > start_page:
            print("(Waiting %is before fetching page %i.)" % (delay, current_page))
            time.sleep(delay)

        print("Fetching page %i." % current_page)

        for cert in certificates.search(query, fields=fields, page=current_page, max_records=page_size):
            # Common name + SANs
            names = cert['parsed.subject.common_name'] + cert['parsed.extensions.subject_alt_name.dns_names']

            if debug:
                print(names)

            for name in names:
                name = re.sub(wildcard_pattern, '', name).lower().strip()

                if suffix_pattern.search(name):
                    hostnames_map[name] = None

        current_page += 1


    print("Done fetching from API.")

    hostnames = list(hostnames_map.keys())
    hostnames.sort()

    print("Writing out CSV.")
    for hostname in hostnames:
        out_writer.writerow([hostname])

    print("Done.")

main()

