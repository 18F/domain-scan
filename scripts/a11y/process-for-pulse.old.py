import csv
import re
import json
import collections

def readData(inputFile):
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

def writeJson(inputData, fileName):
    with open(fileName, 'w+') as outfile:
        json.dump(inputData, outfile, indent = 4)

def makeAgencyOutput(inputList, errorDict, errorTypeDict):
    output = []
    for row in inputList:
        subSet = row[1]
        subDict = collections.OrderedDict({})
        subDict['Agency'] = row[0]
        subDict['Errors'] = errorDict[row[0]]
        for key, value in errorTypeDict.items():
            k = key
            try:
                subDict[k] = subSet[value]
            except KeyError:
                subDict[k] = 0
            except TypeError:
                subDict[k] = 0
        output.append(subDict)
    return output

def getKey(item):
    return item[0]

def trimErrorField(errorField):
    pieces = re.split('.*(Guideline)', errorField)
    shortened = pieces[-1]
    pieces = shortened.split('.')
    num = pieces[0]
    return num

def categorize(dataset, referenceDict, colNum, altName):
    for row in dataset:
        if row[colNum] in referenceDict.keys():
            row.append(referenceDict[row[colNum]])
        else:
            row.append(altName)
    return dataset

def countDict(dataset, colIndex):
    output = {}
    for row in dataset:
        if row[colIndex] in output:
            output[row[colIndex]] += 1
        else:
            output[row[colIndex]] = 1
    return output

#Read in a11y.csv for errors and domains.csv for agencies
ally1 = readData('home/results/a11y.csv')
domains = readData('home/domains.csv')
#need to remove ussm.gov, whistleblower.gov, and safeocs.gov from ally due to discrepancies between the datasets. Solve at some point
ally = []
for row in ally1:
    if row[0] != 'safeocs.gov' and row[0] != 'whistleblower.gov' and row[0] != 'ussm.gov':
        ally.append(row)

#Truncate the a11y file so that it's a bit more manageable. Need the domain name [0] and the principle [4]
main = []
for row in ally:
    main.append([row[0], trimErrorField(row[4])])

#Add the information on the agency [1] and branch [2]
for error in main:
    for domain in domains:
        if error[0] == domain[0].lower():
            error.append(domain[1])
            error.append(domain[2])

#Dictionaries; branches = branch lookup, errorCats = error category lookup
branches = {"Library of Congress":"Legislative","The Legislative Branch (Congress)":"Legislative",
"Government Printing Office":"Legislative","Congressional Office of Compliance":"Legislative",
"The Judicial Branch (Courts)":"Judicial"}
errorCats = {'1_4':'Color Contrast Error', '1_1':'Alt Tag Error', '4_1':'HTML/Attribute Error', '1_3':'Form Error'}

#define branches for the 'main' and 'domains' sets, define error categories for 'main'
main = categorize(main, branches, -1, 'Executive')
domains = categorize(domains, branches, 2, 'Executive')
main = categorize(main, errorCats, 1, 'Other Error')

totalErrorsByDomain = countDict(main, 0)
totalErrorsByAgency = countDict(main, 3)

#createe dict of base vs. canonical domains
canonicals = {}
for row in ally:
    try:
        if row[0] in canonicals.keys():
            continue
        else:
            canonicals[row[0]] = row[1]
    except KeyError:
        continue


noErrors = []
errors = []
for domain in domains:
    if not domain[0].lower() in totalErrorsByDomain.keys():
        noErrors.append(domain)
    else:
        errors.append(domain)

for row in noErrors:
    row.append(0)
    row.append({})
    try:
        if row[0] in canonicals.keys():
            row.append('http://' + canonicals[row[0].lower()])
        else:
            row.append('http://' + row[0].lower())
    except TypeError:
        continue

for row in errors:
    row.append(totalErrorsByDomain[row[0].lower()])
    subset = []
    for line in main:
        if line[0] == row[0].lower():
            subset.append(line)
    errorDict = countDict(subset, -1)
    row.append(errorDict)
    try:
        if row[0] in canonicals.keys():
            row.append('http://' + canonicals[row[0].lower()])
        else:
            row.append('http://' + row[0].lower())
    except TypeError:
        continue

domains = errors + noErrors
domains = sorted(domains, key = getKey)

dictList = []
for row in domains:
    subDict = collections.OrderedDict({})
    subDict['agency'] = row[2]
    subDict['branch'] = row[5]
    subDict['canonical'] = row[8]
    subDict['domain'] = row[0].lower()
    subDict['errors'] = row[6]
    subDict['errorlist'] = row[7]
    dictList.append(subDict)

finalDict = {}
finalDict['data'] = dictList

writeJson(finalDict, 'home/scripts/a11y/pulse-results/domains.json')

agencyList = []
for row in main:
    if row[3] in agencyList:
        continue
    else:
        agencyList.append(row[3])

agencyErrorSets = []
for agency in agencyList:
    subList = []
    sub = {}
    for row in main:
        if row[3] == agency:
            if row[-1] in sub:
                sub[row[-1]] += 1
            else:
                sub[row[-1]] = 1
    subList.append(agency)
    subList.append(sub)
    agencyErrorSets.append(subList)

errorTypes = {'Color Contrast Errors':'Color Constrast Error', 'HTML/Attribute Errors':'HTML/Attribute Error',
'Form Errors':'Form Error', 'Alt Tag Errors':'Alt Tag Error', 'Other Errors':'Other Error'}

output = makeAgencyOutput(agencyErrorSets, agencyErrorDict, errorTypes)
finalOutput = {}
finalOutput['data'] = output

writeJson(finalOutput, 'home/scripts/a11y/pulse-results/agencies.json')
