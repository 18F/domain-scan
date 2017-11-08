import re

from pshtt import utils
from pshtt import pshtt

# Debug logging.
utils.configure_logging(True)

# Recommended total Lambda task timeout.
timeout = 300

# 30 second timeouts for each individual request used by pshtt.
pshtt_timeout = 30

def handler(event, context):
  print(event)

  options = event.get("options", {})

  domain = event['domain']
  domain = format_domain(domain)

  results = pshtt.inspect_domains(
    [domain],
    {'timeout': pshtt_timeout}
  )

  # Should only be one.
  result = results[0]
  print(result)

  row = []
  for field in headers:
      value = result[field]

      # TODO: Fix this upstream
      if (field != "HSTS Header") and (field != "HSTS Max Age") and (field != "Redirect To"):
          if value is None:
              value = False

      row.append(value)

  # Currently expects multiple rows.
  return [row]

headers = [
    "Canonical URL", "Live", "Redirect", "Redirect To",
    "Valid HTTPS", "Defaults to HTTPS", "Downgrades HTTPS",
    "Strictly Forces HTTPS", "HTTPS Bad Chain", "HTTPS Bad Hostname",
    "HTTPS Expired Cert", "HTTPS Self Signed Cert",
    "HSTS", "HSTS Header", "HSTS Max Age", "HSTS Entire Domain",
    "HSTS Preload Ready", "HSTS Preload Pending", "HSTS Preloaded",
    "Base Domain HSTS Preloaded", "Domain Supports HTTPS",
    "Domain Enforces HTTPS", "Domain Uses Strong HSTS", "Unknown Error",
]

def format_domain(domain):
  return re.sub("^(https?://)?(www\.)?", "", domain)
