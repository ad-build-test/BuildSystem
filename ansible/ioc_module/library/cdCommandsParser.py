""" ============ Begin - cdCommandsParser.py (No changes) ============ """

"""This provides a cdCommands parser and a utility to parse and replace cdCommands values with a provided dict
cdCommands looks like so
top = "/afs/slac.stanford.edu/g/lcls/vol8/epics/iocTop/CAMAC/MAIN_TRUNK"
putenv("TOP=/afs/slac.stanford.edu/g/lcls/vol8/epics/iocTop/CAMAC/MAIN_TRUNK")
"""

import os
import re
import random

# Form regex patterns for the two possible forms
cdCommandPatternDict = {}
patternComponentLists = [
    ('variableassignment', [r'(\S+)', '=', '"([^"]+)"']),                       # top = "something"
    ('putenv',             ['putenv', r'\(', r'"([^"=\s]+)=([^"]+)"', r'\)']),  # putenv("TOP=something")
]
for commandType, patternComponents in patternComponentLists:
    # Allow spaces between components and comments at the end
    pattern = r'^\s*{}\s*(?:#.*)?$'.format(r'\s*'.join(patternComponents))
    cdCommandPatternDict[commandType] = re.compile(pattern)

def multiRegexMatch(regexPatternDict, text):
    '''Matches text against multiple regex patterns'''
    for label, pattern in regexPatternDict.items():
        result = pattern.match(text)
        if result:
            return label, result

    return None, None

def writeOutReplacedVal(out, name, value, commandtype):
    '''Write out a putenv or a n=v based on the commandtype'''
    if commandtype == 'putenv':
        out.write('putenv("' + name + '=' + value + '")' + "\n")
    elif commandtype == 'variableassignment':
        out.write(name + ' = "' + value + '"\n')
    else:
        raise Exception("Cannot determine if this is a putenv or a name=value")

def parseAndReplaceCDCommandsFile(cdCommandsPath, replaceMap):
    '''Parse the cdCommands file into a list of tuples that represents the name/value.
    Replace the value of any name that is present in replaceMap with the value from the map.
    Finally update the specified file with the new set of values
    '''
    tempFilePath = os.path.join(os.path.dirname(cdCommandsPath), "_tmp_multifacility" + str(int(random.random()*1000000)))
    while os.path.exists(tempFilePath):
        stderr.write("Generating a new name for the temporary file\n")
        tempFilePath = os.path.join(os.path.dirname(cdCommandsPath), "_tmp_multifacility" + str(int(random.random()*1000000)))

    NVPairs = {}
    with open(tempFilePath, 'w') as out:
        with open(cdCommandsPath, 'r') as f:
            for line in f.read().splitlines():
                commandType, result = multiRegexMatch(cdCommandPatternDict, line)
                if result:
                    name, value = result.group(1), result.group(2)
                    mapName = name.upper()

                    if mapName in replaceMap:
                        NVPairs[name] = replaceMap[mapName]
                        writeOutReplacedVal(out, name, replaceMap[mapName], commandType)
                    else:
                        NVPairs[name] = value
                        writeOutReplacedVal(out, name, value, commandType)

                else:
                    out.write(line + "\n")

        os.rename(tempFilePath, cdCommandsPath)
        return NVPairs

""" ============ End - cdCommandsParser.py ============ """
