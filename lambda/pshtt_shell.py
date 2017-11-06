
import os
from pshtt import utils
from pshtt import pshtt
import subprocess

# Lambda function timeout overall is 45
timeout = 30

# Default user agent.
user_agent = "github.com/18f/domain-scan, pshtt, from Lambda"

# Debug logging.
utils.configure_logging(True)

# Uploaded package puts built pshtt executable relative to this file,
# but also needs to have its #! line rewritten to /usr/bin/env python3.
command = "./bin/pshtt"

def handler(event, context):
  print(event)

  # Results are yielded one by one.
  output = []

  # Read in domains from event.
  domains = event['domains']

  # Strip away protocols.
  domains = utils.format_domains(domains)

  for domain in domains:
    cmd = [
      os.path.realpath("./bin/pshtt"),
      domain,
      "--debug",
      "--json"
    ]
    try:
      raw = subprocess.check_output(cmd, shell=False, stderr=subprocess.STDOUT, env=None)
      print(str(response, encoding='UTF-8'))
    except subprocess.CalledProcessError as exc:
      print(str(exc.stdout, encoding='UTF-8'))
      print(str(exc.returncode))
      raw = None

    if not raw:
      print("No luck scanning!")
    else:
      result = json.loads(raw)
      print("Scanned: %s" % raw)
      output.append("HSTS for %s: %s" % (result['Domain'], result["HSTS Header"]))

  return "\n".join(output)
