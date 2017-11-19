from scanners import utils
import os
import requests
import logging

# url
#
# Gathers hostnames from a CSV at a given URL.
#
# --url: The URL to download. Can also be a local path.
#        Will be parsed as a CSV.
#


def gather(suffixes, options, extra={}):
    # Defaults to --url, but can be overridden.
    name = extra.get("name", "url")
    url = options.get(name)

    if url is None:
        logging.warn("A --url is required. (Can be a local path.)")
        exit(1)

    # remote URL
    if url.startswith("http:") or url.startswith("https:"):
        # Though it's saved in cache/, it will be downloaded every time.
        remote_path = os.path.join(utils.cache_dir(), "url.csv")

        try:
            response = requests.get(url)
            utils.write(response.text, remote_path)
        except:
            logging.error("Remote URL not downloaded successfully.")
            print(utils.format_last_exception())
            exit(1)

    # local path
    else:
        remote_path = url

    for domain in utils.load_domains(remote_path):
        yield domain
