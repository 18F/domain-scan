import json
import csv
from collections import defaultdict

class Base:
    def _writeFile(self, contents, outDir, filename):
        path = outDir + filename
        with open(path, 'w+') as outfile:
            json.dump(contents, outfile, indent = 2)

    def _readCsv(self, inputFile):
        output = []
        with open(inputFile, newline='') as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                output.append(row)
        return output


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
            domains[error[0]].append(error[3:])

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
                "Alt Tag Errors": self._errorCountsFromErrorList('Alt Tag Errors', errorList),
                "Color Contrast Errors": self._errorCountsFromErrorList('Color Contrast Errors', errorList),
                "HTML Attribute Errors": self._errorCountsFromErrorList('HTML Attribute Errors', errorList)
            }
        }

    def _branchFromAgency(self, agency):
        if agency in [
            "Library of Congress",
            "The Legislative Branch (Congress)",
            "Government Printing Office",
            "Government Publishing Office",
            "Congressional Office of Compliance",
            "Stennis Center for Public Service",
            "U.S. Capitol Police"
        ]:
            return "legislative"

        if agency in [
            "The Judicial Branch (Courts)",
            "The Supreme Court",
            "U.S Courts"
        ]:
            return "judicial"

        if agency in ["Non-Federal Agency"]:
            return "non-federal"

        else:
            return "executive"

    def _domainsToAgencyDict(self):
        domainsDict = {}
        for row in self._domainsCsv:
            domainsDict[row[0].lower()] = row[2]
        return domainsDict

    def _domainsToBranchDict(self):
        domainsDict = {}
        for row in self._domainsCsv:
            domainsDict[row[0].lower()] = self._branchFromAgency(row[2])
        return domainsDict

    def _agencyFromDomain(self, domain):
        return self._domainsToAgencyDict()[domain]

    def _branchFromDomain(self, domain):
        return self._domainsToBranchDict()[domain]

    def _errorCountsFromErrorList(self, categoryName, errorList):
        count = 0
        for error in errorList:
            categoryCode = self._errorCategoryCodeFromError(error)
            code = self._errorMapping()[categoryName]
            if categoryCode == code:
                count = count + 1
        return count

    def _errorCategoryCodeFromError(self, error):
        return error[1].split('.')[2].split('Guideline')[1]

    def _errorMapping(self):
        return {
            'Color Contrast Errors':'1_4',
            'Alt Tag Errors':'1_1',
            'HTML Attribute Errors':'4_1',
            'Form Errors':'1_3'
        }
