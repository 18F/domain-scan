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
        self._domainsCsvPath = domainsCsvPath
        self._a11yCsvPath = a11yCsvPath

    def perform(self):
        domainsCsv = self._readCsv(self._domainsCsvPath)
        a11yCsv = self._readCsv(self._a11yCsvPath)
        return self._buildDomainsJSON(domainsCsv, a11yCsv)

    def _buildDomainsJSON(self, domainsCsv, a11yCsv):
        # format for each row in a11yCsv:
        # Domain,Base Domain,redirectedTo,typeCode,code,message,context,selector
        result = defaultdict(list)
        for error in a11yCsv:
            result[error[0]].extend(error[3:])

        data = []

        output = {}
        output['data'] = data
        return output
