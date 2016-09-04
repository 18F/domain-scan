from scanners import utils
import os
import re
import time
import requests
import logging

# Take in command line flags,
# yield hostnames.
def gather(suffix, options):
  url = options.get("url")
  if url is None:
    logging.warn("A --url is required.")
    exit(1)

  # Though it's saved in cache/, it will be downloaded every time.
  remote_path = os.path.join(utils.cache_dir(), "url.csv")

  try:
      response = requests.get(url)
      utils.write(response.text, remote_path)
  except:
      logging.error("Remote URL not downloaded successfully.")
      print(utils.format_last_exception())
      exit(1)

  for domain in utils.load_domains(remote_path):
      yield domain
