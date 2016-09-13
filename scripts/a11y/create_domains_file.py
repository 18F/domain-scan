import json
import csv
from collections import defaultdict

class Base:
    def _writeFile(self, contents, outDir, filename):
        path = outDir + filename
        with open(path, 'w+') as outfile:
            json.dump(contents, outfile, indent = 2)

    def _readCsv(self, inputFile):
        outList = []
        with open(inputFile) as infile:
            reader = csv.reader(infile)
            firstRow = True
            for row in reader:
                if firstRow == True:
                    firstRow = False
                    continue
                else:
                    outList.append(row)
        return outList


class CreateDomainsJSON(Base):
    def __init__(self, domainsCsvPath, a11yCsvPath):
        self._a11yCsv = self._readCsv(a11yCsvPath)
        self._domainsCsv = self._readCsv(domainsCsvPath)

    def perform(self):
        return self._buildDomainsJSON(self._domainsCsv, self._a11yCsv)

    def _buildDomainsJSON(self, domainsCsv, a11yCsv):
        # format for each row in a11yCsv:
        # Domain,Base Domain,redirectedTo,typeCode,code,message,context,selector
        domains = defaultdict(list)
        for error in a11yCsv:
            domains[error[0]].extend(error[3:])

        output = {}
        output['data'] = [self._createDomainDict(domain, domains[domain]) for domain in domains]
        return json.dumps(output)

    def _createDomainDict(self, domain, errorList):
        return {
            "agency": self._agencyFromDomain(domain),
            "branch": self._branchFromDomain(domain),
            "canonical": domain,
            "errors": len(errorList),
            "errorList": {
                "Alt Tag Errors": self._altTagErrorCountsFromErrorList(errorList),
                "Color Contrast Errors": self._colorContrastErrorCountsFromErrorList(errorList),
                "HTML Attribute Errors": self._HTMLAttributeErrorCountsFromErrorList(errorList)
            }
        }

    def _agencyFromDomain(self, domain):
        print(len(self._a11yCsv))
        return 'fakeAgency'

    def _branchFromDomain(self, domain):
        return 'fakeBranch'

    def _altTagErrorCountsFromErrorList(self, errorList):
        return 1

    def _colorContrastErrorCountsFromErrorList(self, errorList):
        return 1

    def _HTMLAttributeErrorCountsFromErrorList(self, errorList):
        return 1
