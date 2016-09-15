import unittest
import json

from scripts.a11y.create_domains_file import CreateDomainsJSON

class TestCreateDomainsJSON(unittest.TestCase):
    def test_perform(self):
        domainsJSON = CreateDomainsJSON('tests/scripts/a11y/data/domains.csv',
                                        'tests/scripts/a11y/data/a11y.csv').perform()


        self.assertTrue('data' in domainsJSON)

        data = domainsJSON

        self.assertEqual(data.__class__, list)

if __name__ == '__main__':
    unittest.main()
