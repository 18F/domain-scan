
from pshtt import utils
from pshtt import pshtt

def handler(event, context):
  print(event)

  # Debug logging.
  utils.configure_logging(True)

  results = pshtt.inspect_domains(
    # Read in list of domains from event.
    event['domains'],

    # Lambda function timeout overall is 45
    {'timeout': 30}
  )

  # Results are yielded one by one.
  for result in results:
    print(result)

  print("Yay!")
