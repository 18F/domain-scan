import os
import logging

import requests

from gatherers.gathererabc import Gatherer
from utils import utils


class Gatherer(Gatherer):

    def gather(self):
        # Defaults to --url, but can be overridden.
        name = self.extra.get("name", "url")
        url = self.options.get(name)

        if url is None:
            logging.warn("A --url is required. (Can be a local path.)")
            exit(1)

        # remote URL
        if url.startswith("http:") or url.startswith("https:"):
            # Though it's saved in cache/, it will be downloaded every time.
            remote_path = os.path.join(self.cache_dir, "url.csv")

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
