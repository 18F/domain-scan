import os
import re
import time
import logging
from censys import certificates

### censys
#
# Gathers hostnames from the Censys.io API.
#
# --delay: How long to wait between requests. Defaults to 5s.
#          If you have researcher credentials, use 2s.
# --start: What page of results to start on. Defaults to 1.
# --end:   What page of results to end on. Defaults to last page.
#

# Register a (free) Censys.io account to get a UID and API key.
uid = os.environ.get("CENSYS_UID", None)
api_key = os.environ.get("CENSYS_API_KEY", None)

def gather(suffix, options):
    certificate_api = certificates.CensysCertificates(uid, api_key)

    query = "parsed.subject.common_name:%s or parsed.extensions.subject_alt_name.dns_names:%s" % (suffix, suffix)
    logging.debug("Censys query:\n%s\n" % query)

    # Hostnames beginning with a wildcard prefix will have the prefix stripped.
    wildcard_pattern = re.compile("^\*.")

    # time to sleep between requests (defaults to 5s)
    delay = int(options.get("delay", 5))

    # Censys page size, fixed
    page_size = 100

    # Start page defaults to 1.
    start_page = int(options.get("start", 1))

    # End page defaults to whatever the API says is the last one.
    end_page = options.get("end", None)
    if end_page is None:
        end_page = get_end_page(query, certificate_api)
        if end_page is None:
            logging.warn("Error looking up number of pages.")
            exit(1)
    else:
        end_page = int(end_page)


    max_records = ((end_page - start_page) + 1) * page_size

    # Cache hostnames in a dict for de-duping.
    hostnames_map = {}

    fields = [
        "parsed.subject.common_name",
        "parsed.extensions.subject_alt_name.dns_names"
    ]

    current_page = start_page

    logging.warn("Fetching up to %i records, starting at page %i." % (max_records, start_page))

    while current_page <= end_page:
        if current_page > start_page:
            logging.debug("(Waiting %is before fetching page %i.)" % (delay, current_page))
            time.sleep(delay)

        logging.debug("Fetching page %i." % current_page)

        for cert in certificate_api.search(query, fields=fields, page=current_page, max_records=page_size):
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

# Hit the API once just to get the last available page number.
def get_end_page(query, certificate_api):
    metadata = certificate_api.metadata(query)
    if metadata is None:
        return None
    return metadata.get('pages')
