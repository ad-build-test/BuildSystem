""" ============ Begin - envPathsParser.py (No changes) ============ """

"""This provides a envPaths parser and a utility to parse and replace envPaths values with a provided dict"""

import os
import re
import random

# Form regex patterns for the four possible forms
epicsEnvSetPatterns = []
patternComponentLists = [
    ['epicsEnvSet', r'\(', '"([^"]+)"', ',', '"([^"]+)"', r'\)'],  # epicsEnvSet("IOC","sioc-li20-pm20")
    ['epicsEnvSet', r'\(', r'(\S+)', ',', '"([^"]+)"', r'\)'],     # epicsEnvSet(IOC,"sioc-li20-pm20")
    ['epicsEnvSet ', r'(\S+) ', '"([^"]+)"'],                      # epicsEnvSet IOC_SUFF "PM20"
    ['epicsEnvSet ', r'(\S+) ', r'(\S+)'],                         # epicsEnvSet ID 695
]
for patternComponents in patternComponentLists:
    # Allow spaces between components and comments at the end
    pattern = r'^\s*{}\s*(?:#.*)?$'.format(r'\s*'.join(patternComponents))
    epicsEnvSetPatterns.append(re.compile(pattern))

def multiRegexMatch(regexPatterns, text):
    '''Matches text against multiple regex patterns'''
    for pattern in regexPatterns:
        result = pattern.match(text)
        if result:
            return result

    return None

def parseAndReplaceEnvPathsFile(envPathsPath, replaceMap):
    '''Parse the envPaths file into a list of tuples that represents the name/value. 
    Replace the value of any name that is present in replaceMap with the value from the map.
    Finally update the specified file with the new set of values
    '''
    tempFilePath = os.path.join(os.path.dirname(envPathsPath), "_tmp_multifacility" + str(int(random.random()*1000000)))
    while os.path.exists(tempFilePath):
        stderr.write("Generating a new name for the temporary file\n")
        tempFilePath = os.path.join(os.path.dirname(envPathsPath), "_tmp_multifacility" + str(int(random.random()*1000000)))

    NVPairs = {}
    with open(tempFilePath, 'w') as out:
        with open(envPathsPath, 'r') as f:
            for line in f.read().splitlines():
                result = multiRegexMatch(epicsEnvSetPatterns, line)
                if result:
                    name, value = result.group(1), result.group(2)

                    if name in replaceMap:
                        NVPairs[name] = replaceMap[name]
                        out.write('epicsEnvSet("' + name + '","' + replaceMap[name] + '")' + "\n")
                    else:
                        NVPairs[name] = value
                        out.write('epicsEnvSet("' + name + '","' + value + '")' + "\n")

                else:
                    out.write(line + "\n")

        os.rename(tempFilePath, envPathsPath)
        return NVPairs

""" ============ End - envPathsParser.py  ============ """