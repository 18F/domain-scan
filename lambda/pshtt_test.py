
import requests

def handler(event, context):
  print(event)

  response = requests.get(event['url'])
  print(response.content)

  print("Yay!")
