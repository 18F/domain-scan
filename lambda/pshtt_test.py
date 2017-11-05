
from pshtt import utils
from pshtt import pshtt

def handler(event, context):
  print(event)

  # Debug logging.
  utils.configure_logging(True)

  # Read in list of domains from event.
  domains = event['domains']

  # Strip away protocols.
  domains = utils.format_domains(domains)

  results = pshtt.inspect_domains(
    domains,

    # Lambda function timeout overall is 45
    {'timeout': 30}
  )

  # Results are yielded one by one.
  output = []
  for result in results:
    output.append("HSTS for %s: %s" % (result['Domain'], result["HSTS Header"]))

  return "\n".join(output)
