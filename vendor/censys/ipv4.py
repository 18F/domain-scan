from __future__ import print_function
import unittest

from .base import CensysAPIBase, CensysIndex, CensysException


class CensysIPv4(CensysIndex):

    INDEX_NAME = "ipv4"

class CensysIPv4Tests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls._api = CensysIPv4()

    def testGet(self):
        self._api.view("84.206.102.184")

    def testEmptySearch(self):
        with self.assertRaises(CensysException):
            self._api._post("search/ipv4", data={"query1": "query"})

    def testSearch(self):
        list(self._api.search("*", max_records=10))

    def testSearchExplicitPage(self):
        list(self._api.search("*", page=3, max_records=10))

    def testBadPageSearch(self):
        with self.assertRaises(Exception):
            list(self._api.search("*", page="x", max_records=10))

    def testBadFieldsSearch(self):
        with self.assertRaises(CensysException):
            list(self._api.search("*", fields="test",  max_records=10))

    #def testReport(self):
    #    self._api.report("*", "protocols", 5)


if __name__ == "__main__":
    unittest.main()
