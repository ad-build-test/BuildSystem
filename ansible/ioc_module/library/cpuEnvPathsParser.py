""" ============ Begin - cpuEnvPathsParser.py (No changes) ============ """

"""This provides a cpuEnv.sh parser and a utility to parse and replace cpuEnv.sh values with a provided dict"""

import os
import re
import random

# Form regex patterns for the two possible forms
cpuEnvSetPatterns = []
patternComponentLists = [
    ['export ', r'([^=\s]+)="([^"]+)"'],  # export EPICS_SITE_TOP="/afs/slac/g/lcls/epics"
    ['export ', r'([^=\s]+)=(\S+)'],      # export CPU=cpu-b34-mc23
]
for patternComponents in patternComponentLists:
    # Allow spaces between components and comments at the end
    pattern = r'^\s*{}\s*(?:#.*)?$'.format(r'\s*'.join(patternComponents))
    cpuEnvSetPatterns.append(re.compile(pattern))

def multiRegexMatch(regexPatterns, text):
    '''Matches text against multiple regex patterns'''
    for pattern in regexPatterns:
        result = pattern.match(text)
        if result:
            return result

    return None

def parseAndReplaceEnvPathsFile(envPathsPath, replaceMap, replaceName):
    '''Parse the envPaths file into a list of tuples that represents the name/value.
    Replace the value of any name that is present in replaceMap with the value from the map.
    Replace the value of any name below replaceName whose value contains the old value of replaceName
    Finally update the specified file with the new set of values
    '''
    tempFilePath = os.path.join(os.path.dirname(envPathsPath), "_tmp_multifacility" + str(int(random.random()*1000000)))
    while os.path.exists(tempFilePath):
        stderr.write("Generating a new name for the temporary file\n")
        tempFilePath = os.path.join(os.path.dirname(envPathsPath), "_tmp_multifacility" + str(int(random.random()*1000000)))

    NVPairs = {}
    replaceEnvPairs = {}
    with open(tempFilePath, 'w') as out:
        with open(envPathsPath, 'r') as f:
            oldReplaceNameValue = None
            newReplaceNameValue = replaceMap.get(replaceName)
            for line in f.read().splitlines():
                result = multiRegexMatch(cpuEnvSetPatterns, line)
                if result:
                    name, value = result.group(1), result.group(2)
                    if name == replaceName:
                        oldReplaceNameValue = value

                    if name in replaceMap:
                        NVPairs[name] = replaceMap[name]
                        out.write('export ' + name + '=' + replaceMap[name] + "\n")

                    else:
                        # Replace subsequent instances of the old value of replaceName with its new value
                        if oldReplaceNameValue and oldReplaceNameValue in value:
                            if newReplaceNameValue and replaceName in replaceMap:
                                newPath = value.replace(oldReplaceNameValue, newReplaceNameValue)
                            else:
                                newPath = value

                            replaceEnvPairs[name] = newPath

                        else:
                            newPath = value

                        NVPairs[name] = newPath
                        out.write('export ' + name + '=' + newPath + "\n")
                else:
                    out.write(line + "\n")

        os.rename(tempFilePath, envPathsPath)
        return NVPairs, replaceEnvPairs
""" ============ End - cpuEnvPathsParser.py ============ """