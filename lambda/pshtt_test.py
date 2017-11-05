
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
  for result in results:
    print("Canonical URL: %s" % result['Canonical URL'])
    print(result)

  return ("Scanned %i domains!" % len(results))
