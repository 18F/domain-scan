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
        with open(inputFile, 'rU') as infile:
            reader = csv.reader(infile)
            firstRow = True
            for row in reader:
                if firstRow == True:
                    firstRow = False
                    continue
                else:
                    outList.append(row)
        return outList


class CreateDomainsFile(Base):
    def __init__(self, domainsCsvPath, a11yCsvPath, outDir):
        self._domainsCsvPath = domainsCsvPath
        self._a11yCsvPath = a11yCsvPath
        self._outDir = outDir

    def perform(self):
        domainsCsv  = self._readCsv(self._domainsCsvPath)
        a11yCsv     = self._readCsv(self._a11yCsvPath)
        domainsJson = self._buildDomainsJson(domainsCsv, a11yCsv)

        self._writeFile(domainsJson, self._outDir, 'domains.json')

    def _buildDomainsJson(self, domainsCsv, a11yCsv):
        # format for each row in a11yCsv:
        # Domain,Base Domain,redirectedTo,typeCode,code,message,context,selector
        result = defaultdict(list)
        for error in a11yCsv[50:55]:
            result[error[0]].extend(error[3:])


        print(result['cfpa.gov'])

        data = []

        output = {}
        output['data'] = data
        return output

    def _buildDomainJsonObject(self):
        pass

CreateDomainsFile('/home/domains.csv',
                  '/home/results/a11y.csv',
                  '/home/scripts/a11y/pulse-results/').perform()
