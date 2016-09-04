import os
import re
import time
import logging

# Until 0.0.6+ is released to pip:
# git clone https://github.com/Censys/censys-python
# cd censys-python && python setup.py install
import censys.certificates

# Register a (free) Censys.io account to get a UID and API key.
uid = os.environ.get("CENSYS_UID", None)
api_key = os.environ.get("CENSYS_API_KEY", None)


def gather(suffix, options):
    # Hostnames beginning with a wildcard prefix will have the prefix stripped.
    wildcard_pattern = re.compile("^\*.")

    # time to sleep between requests (defaults to 5s)
    delay = int(options.get("delay", 5))

    # Censys page size, fixed
    page_size = 100

    # If an --end page is given, override --max
    start_page = int(options.get("start", 1))
    end_page = int(options.get("end", start_page))
    max_records = ((end_page - start_page) + 1) * page_size

    # Cache hostnames in a dict for de-duping.
    hostnames_map = {}


    certificates = censys.certificates.CensysCertificates(uid, api_key)

    fields = [
        "parsed.subject.common_name",
        "parsed.extensions.subject_alt_name.dns_names"
    ]

    query = "parsed.subject.common_name:%s or parsed.extensions.subject_alt_name.dns_names:%s" % (suffix, suffix)
    logging.debug("Censys query:\n%s\n" % query)

    current_page = start_page

    logging.warn("Fetching up to %i records, starting at page %i." % (max_records, start_page))

    while current_page <= end_page:
        if current_page > start_page:
            logging.debug("(Waiting %is before fetching page %i.)" % (delay, current_page))
            time.sleep(delay)

        logging.debug("Fetching page %i." % current_page)

        for cert in certificates.search(query, fields=fields, page=current_page, max_records=page_size):
            # Common name + SANs
            names = cert.get('parsed.subject.common_name', []) + cert.get('parsed.extensions.subject_alt_name.dns_names', [])
            logging.debug(names)

            for name in names:
                # Strip off any wildcard prefix.
                name = re.sub(wildcard_pattern, '', name).lower().strip()
                hostnames_map[name] = None

        current_page += 1

    logging.debug("Done fetching from API.")

    # Iterator doesn't buy much efficiency, since we paginated already.
    # Necessary evil to de-dupe before returning hostnames, though.
    for hostname in hostnames_map.keys():
        yield hostname
