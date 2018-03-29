import os
import json
import csv
import logging
from typing import List

from google.cloud import bigquery
from google.oauth2 import service_account
import google.api_core.exceptions

from utils import utils

# Options:
#
# --timeout: Override the 10 minute job timeout (specify in seconds).
# --cache: Use locally cached export data instead of hitting BigQuery.

# Gathers hostnames from Censys.io via the Google BigQuery API.
#
# Before using this, you need to:
#
# * create a Project in Google Cloud, and an associated service account
#   with access to create new jobs/queries and get their results.
# * give Censys.io this Google Cloud service account to grant access to.
#
# For details on concepts, and how to test access in the web console:
#
# * https://support.censys.io/google-bigquery/bigquery-introduction
# * https://support.censys.io/google-bigquery/adding-censys-datasets-to-bigquery
#
# Note that the web console access is based on access given to a Google account,
# but BigQuery API access via this script depends on access given to
# Google Cloud *service account* credentials.

# Defaults to 10 minute timeout.
default_timeout = 60 * 60 * 10


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

    # Allow override of default timeout (in seconds).
    timeout = int(options.get("timeout", default_timeout))

    # Construct the query.
    query = query_for(suffixes)
    logging.debug("Censys query:\n%s\n" % query)

    # Hardcode this for now:
    cache_dir = "./cache"
    # Plan to store in cache/censys/export.csv.
    download_path = utils.cache_path("export", "censys", ext="csv",
                                     cache_dir=cache_dir)

    # Reuse of cached data can be turned on with --cache.
    cache = options.get("cache", False)
    if (cache is True) and os.path.exists(download_path):
        logging.warn("Using cached download data.")

    # But by default, fetch new data from the BigQuery API,
    # and write it to the expected download location.
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

        # At this point, the job is complete and we need to download
        # the resulting CSV URL in results_url.
        logging.warn("Caching results of SQL query.")

        download_file = open(download_path, 'w', newline='')
        download_writer = csv.writer(download_file)
        download_writer.writerow(["Domain"])  # will be skipped on read

        # Parse the rows and write them out as they were returned (dupes
        # and all), to be de-duped by the central gathering script.
        for row in rows:
            domains = row['common_name'] + row['dns_names']
            for domain in domains:
                download_writer.writerow([domain])

        # End CSV writing.
        download_file.close()

    # Whether we downloaded it fresh or not, read from the cached data.
    for domain in utils.load_domains(download_path):
        if domain:
            yield domain


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
def query_for(suffixes: List[str]) -> str:

    select = "\n".join([
        "    parsed.subject.common_name,",
        "    parsed.extensions.subject_alt_name.dns_names",
    ])

    from_clause = "\n".join([
        "    `censys-io.certificates_public.certificates`,",
        "    UNNEST(parsed.subject.common_name) AS common_names,",
        "    UNNEST(parsed.extensions.subject_alt_name.dns_names) AS sans",
    ])

    # Returns query fragment for a specific suffix.
    def suffix_query(suffix):
        return "\n".join([
            "(common_names LIKE \"%%%s\"" % suffix,
            "      OR sans LIKE \"%%%s\")" % suffix,
        ])

    # Join the individual suffix clauses into one WHERE clause.
    where = str.join("\n    OR ", [suffix_query(suffix) for suffix in suffixes])

    query = "\n".join([
        "SELECT",
        select,
        "FROM",
        from_clause,
        "WHERE",
        "    %s" % where
    ])

    return query


def get_credentials_from_env_var_or_file(env_var: str="",
                                         env_file_var: str="") -> str:
    creds = os.environ.get(env_var, None)

    if creds is None:
        path = os.environ.get(env_file_var, None)
        if path is not None:
            with open(path) as f:
                creds = f.read()

    return creds


# Load BigQuery credentials from either a JSON string, or
# a JSON file. Passed in via environment variables either way.
def load_credentials():
    creds = get_credentials_from_env_var_or_file(
        env_var="BIGQUERY_CREDENTIALS",
        env_file_var="BIGQUERY_CREDENTIALS_PATH")

    if creds is None:
        return None

    parsed = json.loads(creds)
    return service_account.Credentials.from_service_account_info(parsed)
