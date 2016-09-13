import unittest
import json

from scripts.a11y.create_domains_file import CreateDomainsJSON

class TestCreateDomainsJSON(unittest.TestCase):
    def test_perform(self):
        domainsJSON = CreateDomainsJSON('tests/scripts/a11y/data/domains.csv',
                                 'tests/scripts/a11y/data/a11y.csv').perform()
        print(domainsJSON)

if __name__ == '__main__':
    unittest.main()

"""

{
  "data": [
    {
      "agency": "General Services Administration",
      "branch": "Executive",
      "canonical": "http:\/\/18f.gov",
      "domain": "18f.gov",
      "errors": 0,
      "errorlist": {
        "Alt Tag Errors": 0,
        "Color Contrast Errors": 0,
        "HTML\/Attribute Errors": 0
      }
    }
  ]
}

"""
