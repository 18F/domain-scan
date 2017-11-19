import os
import csv
import time
import datetime
import json
import logging
from scanners import utils
from censys import certificates, export
import censys

# censys
#
# Gathers hostnames from the Censys.io API.
#
# --censys_id: Censys API UID.
# --censys_key: Censys API key.
#
# To use the paginated search (which all accounts can do):
# --delay: How long to wait between requests. Defaults to 5s.
#          If you have researcher credentials, use 2s.
# --start: What page of results to start on. Defaults to 1.
# --end:   What page of results to end on. Defaults to last page.
# --force: Ignore cached pages.
#
# To use the SQL export (which "researcher" accounts can do):
# --export: Turn on export mode.
# --timeout: Override timeout for waiting on job completion (in seconds).
# --force: Ignore cached export data.
#
# Export mode is much more thorough and quick. It will execute a SQL
# query against Censys' export API. This will create a "job" in Censys'
# queue, which the script will then repeatedly check against until
# the job is done (or 20 minutes as a timeout). When the job is done,
# the resulting CSV file will be downloaded to disk and cached, and
# then read from for hostnames.
#
# However, export mode does require Censys credentials for an account
# that has been enabled as a "researcher". If you don't have that, but
# just have a regular free account, use the paginated mode. However,
# know that the paginated mode might top out at 250 pages, because
# the paginated mode talks to an Elasticsearch database which is
# configured to a maximum of 25,000 records (100 records per page).
#
# TODO: Right now this only handle one download file. In theory, the
# export API can return an array of multiple download files.


def gather(suffixes, options, extra={}):
    # Register a (free) Censys.io account to get a UID and API key.
    uid = options.get("censys_id", None)
    api_key = options.get("censys_key", None)

    if (uid is None) or (api_key is None):
        uid = os.environ.get("CENSYS_UID", None)
        api_key = os.environ.get("CENSYS_API_KEY", None)

    if (uid is None) or (api_key is None):
        logging.warn("No Censys credentials set. API key required to use the Censys API.")
        exit(1)

    if options.get("export", False):
        gather_method = export_mode
    else:
        gather_method = paginated_mode

    # Iterator doesn't buy much efficiency, since we paginated already.
    # Necessary evil to de-dupe before returning hostnames, though.
    for hostname in gather_method(suffixes, options, uid, api_key):
        yield hostname


def paginated_mode(suffixes, options, uid, api_key):
    certificate_api = certificates.CensysCertificates(uid, api_key)

    def suffix_query(suffix):
        return "parsed.subject.common_name:\"%s\" or parsed.extensions.subject_alt_name.dns_names:\"%s\"" % (suffix, suffix)

    if 'query' in options and options['query']:
        query = options['query']
    else:
        query = str.join(" or ", [suffix_query(suffix) for suffix in suffixes])

    logging.debug("Censys query:\n%s\n" % query)

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

    fields = [
        "parsed.subject.common_name",
        "parsed.extensions.subject_alt_name.dns_names"
    ]

    current_page = start_page

    logging.warn("Fetching up to %i records, starting at page %i." % (max_records, start_page))
    last_cached = False
    force = options.get("force", False)

    while current_page <= end_page:
        if (not last_cached) and (current_page > start_page):
            logging.debug("(Waiting %is before fetching page %i.)" % (delay, current_page))
            last_cached = False
            time.sleep(delay)

        logging.debug("Fetching page %i." % current_page)

        cache_page = utils.cache_path(str(current_page), "censys")
        if (force is False) and (os.path.exists(cache_page)):
            logging.warn("\t[%i] Cached page." % current_page)
            last_cached = True

            certs_raw = open(cache_page).read()
            certs = json.loads(certs_raw)
            if (certs.__class__ is dict) and certs.get('invalid'):
                continue
        else:
            try:
                certs = list(certificate_api.search(query, fields=fields, page=current_page, max_records=page_size))
                utils.write(utils.json_for(certs), cache_page)
            except censys.base.CensysException:
                logging.warn(utils.format_last_exception())
                logging.warn("Censys error, skipping page %i." % current_page)
                utils.write(utils.invalid({}), cache_page)
                continue
            except:
                logging.warn(utils.format_last_exception())
                logging.warn("Unexpected error, skipping page %i." % current_page)
                utils.write(utils.invalid({}), cache_page)
                exit(1)

        for cert in certs:
            # Common name + SANs
            names = cert.get('parsed.subject.common_name', []) + cert.get('parsed.extensions.subject_alt_name.dns_names', [])
            # logging.debug(names)

            for name in names:
                yield name

        current_page += 1

    logging.debug("Done fetching from API.")


def export_mode(suffixes, options, uid, api_key):

    # Default timeout to 20 minutes.
    default_timeout = 60 * 60 * 20
    timeout = int(options.get("timeout", default_timeout))

    # Wait 5 seconds between checking on the job.
    between_jobs = 5

    try:
        export_api = export.CensysExport(uid, api_key)
    except censys.base.CensysUnauthorizedException:
        logging.warn("The Censys.io Export API rejected the provided Censys credentials. The credentials may be inaccurate, or you may need to request access from the Censys.io team.")
        exit(1)

    def suffix_query(suffix):
        return "parsed.subject.common_name LIKE \"%%%s\" OR parsed.extensions.subject_alt_name.dns_names LIKE \"%%%s\"" % (suffix, suffix)

    # Uses a FLATTEN command in order to work around a BigQuery
    # error around multiple "repeated" fields. *shrug*
    body = str.join(" OR ", [suffix_query(suffix) for suffix in suffixes])
    query = "SELECT parsed.subject.common_name, parsed.extensions.subject_alt_name.dns_names from FLATTEN([certificates.certificates], parsed.extensions.subject_alt_name.dns_names) where %s;" % (body)
    logging.debug("Censys query:\n%s\n" % query)

    download_file = utils.cache_path("export", "censys", ext="csv")

    force = options.get("force", False)

    if (force is False) and os.path.exists(download_file):
        logging.warn("Using cached download data.")
    else:
        logging.warn("Kicking off SQL query job.")
        results_url = None

        try:
            job = export_api.new_job(query, format='csv', flatten=True)
            job_id = job['job_id']

            started = datetime.datetime.now()
            while True:
                elapsed = (datetime.datetime.now() - started).seconds

                status = export_api.check_job(job_id)
                if status['status'] == 'error':
                    logging.warn("Error from Censys: %s" % status['error'])
                    exit(1)

                # Not expected, but better to explicitly handle.
                elif status['status'] == 'expired':
                    logging.warn("Results are somehow expired, bailing.")
                    exit(1)

                elif status['status'] == 'pending':
                    logging.debug("[%is] Job still pending." % elapsed)
                    time.sleep(between_jobs)

                elif status['status'] == 'success':
                    logging.warn("[%is] Job complete!" % elapsed)
                    results_url = status['download_paths'][0]
                    break

                if (elapsed > timeout):
                    logging.warn("Timeout waiting for job to complete.")
                    exit(1)

        except censys.base.CensysException:
            logging.warn(utils.format_last_exception())
            logging.warn("Censys error, aborting.")

        # At this point, the job is complete and we need to download
        # the resulting CSV URL in results_url.
        logging.warn("Downloading results of SQL query.")
        utils.download(results_url, download_file)

    # Read in downloaded CSV file, run any hostnames in each line
    # through the sanitizer, and de-dupe using the map.
    with open(download_file, newline='') as csvfile:
        for row in csv.reader(csvfile):
            if (not row[0]) or (row[0].lower().startswith("parsed_subject_common_name")):
                continue

            names = [row[0].lower(), row[1].lower()]
            # logging.debug(names)

            for name in names:
                if name:
                    yield name


# Hit the API once just to get the last available page number.
def get_end_page(query, certificate_api):
    metadata = certificate_api.metadata(query)
    if metadata is None:
        return None
    return metadata.get('pages')
