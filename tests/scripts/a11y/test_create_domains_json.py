import unittest

from scripts.a11y.create_domains_file import CreateDomainsJSON

class TestCreateDomainsJSON(unittest.TestCase):
    def test_perform(self):
        json = CreateDomainsJSON('tests/scripts/a11y/data/domains.csv',
                                 'tests/scripts/a11y/data/a11y.csv').perform()
        print(json)

if __name__ == '__main__':
    unittest.main()
