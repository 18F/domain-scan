import os
import time
import datetime
import json
import logging
from scanners import utils

from google.cloud import bigquery
from google.oauth2 import service_account
import google.api_core.exceptions

# Options:
#
# --timeout: Override the 5m job completion timeout (specify in seconds).
# --cache: Use locally cached export data instead of hitting BigQuery.

# Gathers hostnames from Censys.io via the Google BigQuery API.
#
# Before using this, you need to:
#
# * give Censys.io a Google Cloud account to grant access to.
# * create a Project in Google Cloud, and associated API credentials.
# * connect this Google Cloud account to Censys.io's BigQuery datasets.
#
# For details, see:
#
# * https://support.censys.io/google-bigquery/bigquery-introduction
# * https://support.censys.io/google-bigquery/adding-censys-datasets-to-bigquery


def gather(suffixes, options, extra={}):

    # Returns a parsed, processed Google service credentials object.
    credentials = load_credentials()

    if credentials is None:
        logging.warn("No BigQuery credentials provided.")
        logging.warn("Set BIGQUERY_CREDENTIALS or BIGQUERY_CREDENTIALS_PATH environment variables.")
        exit(1)

    # When using this form of instantiation, the client won't pull
    # the project_id out of the creds, has to be set explicitly.
    client = bigquery.Client(
        project=credentials.project_id,
        credentials=credentials
    )

    # Default timeout to 5 minutes.
    default_timeout = 60 * 60 * 5
    timeout = int(options.get("timeout", default_timeout))

    # Construct the query.
    query = query_for(suffixes)
    logging.debug("Censys query:\n%s\n" % query)

    # Plan to store in cache/censys/export.csv.
    download_file = utils.cache_path("export", "censys", ext="csv")


    # Reuse of cached data can be turned on with --cache.
    cache = options.get("cache", False)
    if (cache is True) and os.path.exists(download_file):
        logging.warn("Using cached download data.")


    # But by default, fetch new data from the BigQuery API.
    else:
        logging.warn("Kicking off SQL query job.")

        rows = None

        # Actually execute the query.
        try:
            # Executes query and loads all results into memory.
            query_job = client.query(query)
            iterator = query_job.result(timeout=timeout)
            rows = list(iterator)
        except google.api_core.exceptions.Forbidden:
            logging.warn("Access denied to Censys' BigQuery tables.")
        except:
            logging.warn(utils.format_last_exception())
            logging.warn("Error talking to BigQuery, aborting.")

        print(rows[0])
        exit(1)

        # At this point, the job is complete and we need to download
        # the resulting CSV URL in results_url.
        logging.warn("Caching results of SQL query.")
        # TODO: cache in a CSV somewhere

    # Read in cached CSV file and yield one at a time.
    with open(download_file, newline='') as csvfile:
        for row in csv.reader(csvfile):
            if (not row[0]) or (row[0].lower().startswith("parsed_subject_common_name")):
                continue

            names = [row[0].lower(), row[1].lower()]
            # logging.debug(names)

            for name in names:
                if name:
                    yield name


# Constructs the query to run in BigQuery, against Censys'
# certificate datasets, for one or more suffixes.
#
# Example query:
#
# SELECT
#   parsed.subject.common_name,
#   parsed.extensions.subject_alt_name.dns_names
# FROM
#   `censys-io.certificates_public.certificates`,
#   UNNEST(parsed.subject.common_name) AS common_names,
#   UNNEST(parsed.extensions.subject_alt_name.dns_names) AS sans
# WHERE
#   (common_names LIKE "%.gov"
#     OR sans LIKE "%.gov")
#   OR (common_names LIKE "%.fed.us"
#     OR sans LIKE "%.fed.us");

def query_for(suffixes):

    select = """
    parsed.subject.common_name,
    parsed.extensions.subject_alt_name.dns_names
    """

    from_clause = """
    `censys-io.certificates_public.certificates`,
    UNNEST(parsed.subject.common_name) AS common_names,
    UNNEST(parsed.extensions.subject_alt_name.dns_names) AS sans
    """

    # Returns query fragment for a specific suffix.
    def suffix_query(suffix):
        return """
        (common_names LIKE \"%%%s\" OR sans LIKE \"%%%s\")
        """ % (suffix, suffix)

    # Join the individual suffix clauses into one WHERE clause.
    where = str.join(" OR ", [suffix_query(suffix) for suffix in suffixes])

    query = "SELECT %s FROM %s WHERE %s" % (select, from_clause, where)

    return query


# Load BigQuery credentials from either a JSON string, or
# a JSON file. Passed in via environment variables either way.
def load_credentials():
    creds = os.environ.get("BIGQUERY_CREDENTIALS", None)

    if creds is None:
        path = os.environ.get("BIGQUERY_CREDENTIALS_PATH", None)
        if path is not None:
            with open(path) as f:
                creds = f.read()

    if creds is None:
        return None

    parsed = json.loads(creds)
    return service_account.Credentials.from_service_account_info(parsed)
