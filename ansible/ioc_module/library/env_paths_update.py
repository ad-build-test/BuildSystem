#!/usr/bin/python

# Copyright: (c) 2018, Terry Jones <terry.jones@example.org>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
"""
This script updates the envPaths of an IOC based off what facility it is in
Most of this logic is taken directly from CRAM at /afs/slac.stanford.edu/g/lcls/vol3/tools/script/release/multi_facility_deploy/V_1_0_74
Specifically:
- cdCommandsParser.py
- cpuEnvPathsParser.py
- envPathParser.py
- multi_facility_process_helper.py

"""
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

DOCUMENTATION = r'''
---
module: my_test

short_description: This is my test module. In order to run this once done, user needs to be logged into the appropiate k8s cluster

# If this is part of a collection, you need to use semantic versioning,
# i.e. the version is of the form "2.5.0" and not "2.4".
version_added: "1.0.0"

description: This is my longer description explaining my test module.

options:
    name:
        description: This is the message to send to the test module.
        required: true
        type: str
    new:
        description:
            - Control to demo if the result of this module is changed or not.
            - Parameter description can be a list as well.
        required: false
        type: bool
# Specify this value according to your collection
# in format of namespace.collection.doc_fragment_name
# extends_documentation_fragment:
#     - my_namespace.my_collection.my_doc_fragment_name

author:
    - Your Name (@yourGitHubHandle)
'''

EXAMPLES = r'''
# Pass in a message
- name: Test with a message
  my_namespace.my_collection.my_test:
    name: hello world

# pass in a message and have changed true
- name: Test with a message and changed output
  my_namespace.my_collection.my_test:
    name: hello world
    new: true

# fail the module
- name: Test failure of the module
  my_namespace.my_collection.my_test:
    name: fail me
'''

RETURN = r'''
# These are examples of possible return values, and in general should use other names for return values.
original_message:
    description: The original name param that was passed in.
    type: str
    returned: always
    sample: 'hello world'
message:
    description: The output message that the test module generates.
    type: str
    returned: always
    sample: 'goodbye'
'''

from ansible.module_utils.basic import AnsibleModule

# import os
# import re
# import sys
# import random
# import subprocess
# import logger

# import envPathsParser
# import cpuEnvPathsParser
# import cdCommandsParser

# """ ============ Begin - multi_facility_process_helper.py (Grabbed certain functions) ============ """

# def runPrePostDeployScript(scriptpath, name, type, releaseFolder, linkFolder, isMaster, facility, ioc, release):
#     '''Runs the named script in the releaseFolder for this release it is exists. For example, preDeploy is releaseFolder/<name>/<release>/bin/preDeploy
#     In this case, the scriptpath is bin/preDeploy
#     Several environment variables are passed in.
#     Environment variables being with CRAM_
#     '''
#     scriptPath = os.path.join(releaseFolder, name, release, scriptpath)
#     if os.path.exists(scriptPath):
#         if globals.verbose:
#             logger.debug("Executing script  {0} for {1} of type {2} in {3}" \
#                   " with links {4} {5} facility {6} ioc {7} and" \
#                   " release {8}".format(scriptpath, name, type, releaseFolder,
#                                         linkFolder, isMaster, facility, ioc, release))
#         myenvs = dict(os.environ)
#         myenvs['CRAM_SCRIPT'] = scriptpath
#         myenvs['CRAM_PACKAGENAME'] = name
#         myenvs['CRAM_PACKAGETYPE'] = type
#         myenvs['CRAM_RELEASEFOLDER'] = os.path.join(releaseFolder, name, release)
#         myenvs['CRAM_RELEASE'] = release
#         myenvs['CRAM_LINKFOLDER'] = linkFolder
#         myenvs['CRAM_ISMASTER'] = 'true' if isMaster else 'false'
#         myenvs['CRAM_FACILITY'] = facility
#         myenvs['CRAM_IOC'] = ioc
#         startingDir = os.path.realpath(os.curdir)
#         try:
#             os.chdir(os.path.join(releaseFolder, name, release))
#             ret = subprocess.Popen(scriptpath, env=myenvs, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
#             output, err = ret.communicate()
#             output = output.decode('utf-8')
#             err = err.decode('utf-8')
#             if globals.verbose:
#                 logger.debug("Return value from script is %s", ret)
#             return {'retcode' : ret.returncode, 'stdout' : output, 'stderr': err}
#         except Exception as e:
#             logger.exception("Exception when executing %s in folder %s", scriptpath, os.curdir)
#             raise e
#         else:
#             os.chdir(startingDir)
#     else:
#         if globals.verbose:
#             logger.debug("Not present script  {0} for {1} of type {2} in {3}" \
#                   " with links {4} {5} facility {6} ioc {7} and " \
#                   "release {8}".format(scriptpath, name, type, releaseFolder,
#                                        linkFolder, isMaster, facility, ioc, release))
#         return {'retcode' : 0, "reason": "Script %s not present" % (scriptpath)}

# def generateReplaceDictForEnvPaths(releaseFolder, name, release):
#     ''' Generate a replacement dictionary for envPaths based on iocTop, enviromnent variables and other parameters'''
#     replaceDict = {}
#     # TOP => The path to the release that we are upgrading to - <iocTop>/<package>/<version>
#     replaceDict['TOP'] =  os.path.join(releaseFolder, name, release)
#     # EPICS_SITE_TOP => Value of the environment variable EPICS_TOP
#     if 'EPICS_TOP' in os.environ:
#         replaceDict['EPICS_SITE_TOP'] = os.environ['EPICS_TOP']
#     # BASE_SITE_TOP => Value of the environment variable EPICS_BASE_TOP
#     if 'EPICS_BASE_TOP' in os.environ:
#         replaceDict['BASE_SITE_TOP'] = os.environ['EPICS_BASE_TOP']
#     # IOC_SITE_TOP => iocTop for this facility (as defined in the facilities.cfg)
#     replaceDict['IOC_SITE_TOP'] = releaseFolder
#     if 'PACKAGE_TOP' in os.environ:
#         replaceDict['PACKAGE_SITE_TOP'] = os.environ['PACKAGE_TOP']
#     if 'TOOLS' in os.environ:
#         replaceDict['TOOLS_SITE_TOP'] = os.environ['TOOLS']
#         replaceDict['ALARM_CONFIGS_TOP'] = os.path.join(os.environ['TOOLS'], 'AlarmConfigsTop')
#     return replaceDict

# def fixEnvPaths(name, type, releaseFolder, linkFolder, isMaster, facility, ioc, release):
#     '''This runs standard preDeploy scripts liking fixing envPaths, copying over display files etc
#     Currently, here's the list of actions in sequence
#     1) If this is an IOC app, we fix the envPaths for this IOC. This action does not run if this is an HLA or a PyDM display package. If this is an IOC master link, we fix the envPaths for all IOCs in this release.
#     '''
#     if type in ['SIOC', 'HIOC']:
#         for bootFolderName in ['iocBoot', 'cpuBoot', 'build', 'children']:
#             iocBootFolder = os.path.join(releaseFolder, name, release, bootFolderName)
#             if globals.verbose:
#                  logger.debug( "Changing envPaths for %s in %s", "ALL IOCs" if ioc == 'MASTER' else "IOC " + ioc,  iocBootFolder)
#             for root, dirs, files in os.walk(iocBootFolder):
#                 for file in files:
#                     if ioc != "MASTER" and os.path.split(root)[1] != ioc:
#                         logger.debug("Skipping changing envpaths for some other ioc %s", os.path.split(root)[1])
#                         continue
#                     if file == 'envPaths' or file == 'cpuEnv.sh':
#                         if globals.verbose:
#                              logger.debug( "Changing env paths in %s", os.path.join(root, file))
#                         replaceDict = generateReplaceDictForEnvPaths(releaseFolder, name, release)
#                         if file == 'envPaths':
#                             envPathsParser.parseAndReplaceEnvPathsFile(os.path.join(root, file), replaceDict)
#                         elif file == 'cpuEnv.sh':
#                             cpuEnvPathsParser.parseAndReplaceEnvPathsFile(os.path.join(root, file), replaceDict, 'PACKAGE_SITE_TOP')
#                     elif file == 'cdCommands':
#                         if globals.verbose:
#                              logger.debug( "Changing cdCommands in %s", os.path.join(root, file))
#                         replaceDict = generateReplaceDictForEnvPaths(releaseFolder, name, release)
#                         cdCommandsParser.parseAndReplaceCDCommandsFile(os.path.join(root, file), replaceDict)

# def upgrade(name, type, releaseFolder, linkFolder, isMaster, facility, ioc, release, user, message):
#     if globals.verbose:
#             logger.debug("Upgrading %s of type %s with release and link folders %s %s isMaster %s ioc/facilty %s %s to %s", name, type, releaseFolder, linkFolder, isMaster, ioc, facility, release)
#     if type in ['SIOC', 'HIOC']:
#         if isMaster:
#             newReleasePath = os.path.join(releaseFolder, name, release)
#             masterLinkPath = os.path.join(releaseFolder, name, 'current')
#             relpath = os.path.relpath(newReleasePath, os.path.dirname(masterLinkPath))
#             if globals.verbose:
#                 logger.debug( "Changing master - relative path is %s", relpath)
#             os.chdir(os.path.dirname(masterLinkPath))
#             preRunRes = runPrePostDeployScript('bin/preDeploy', name, type, releaseFolder, linkFolder, isMaster, facility, ioc, release)
#             fixEnvPaths(name, type, releaseFolder, linkFolder, isMaster, facility, ioc, release)
#             if os.path.lexists('current'):
#                 os.remove('current')
#             os.symlink(relpath, 'current')
#             postRunRes = runPrePostDeployScript('bin/postDeploy', name, type, releaseFolder, linkFolder, isMaster, facility, ioc, release)
#         else:
#             # We check to see is the new version is the same as the master release version.
#             # If so, we point to the master release.
#             masterLinkPath = os.path.join(releaseFolder, name, 'current')
#             masterRelease = os.path.basename(os.path.realpath(masterLinkPath))
#             if release == masterRelease:
#                 iocLinkPath = os.path.join(linkFolder, ioc, 'iocSpecificRelease')
#                 relpath = os.path.relpath(masterLinkPath, os.path.dirname(iocLinkPath))
#                 if globals.verbose:
#                     logger.debug( "Repointing to master - relative path is %s", relpath)
#                 os.chdir(os.path.dirname(iocLinkPath))
#                 preRunRes = runPrePostDeployScript('bin/preDeploy', name, type, releaseFolder, linkFolder, isMaster, facility, ioc, release)
#                 fixEnvPaths(name, type, releaseFolder, linkFolder, isMaster, facility, ioc, release)
#                 if os.path.lexists('iocSpecificRelease'):
#                     os.remove('iocSpecificRelease')
#                 os.symlink(relpath, 'iocSpecificRelease')
#                 postRunRes = runPrePostDeployScript('bin/postDeploy', name, type, releaseFolder, linkFolder, isMaster, facility, ioc, release)
#             else:
#                 newReleasePath = os.path.join(releaseFolder, name, release)
#                 iocLinkPath = os.path.join(linkFolder, ioc, 'iocSpecificRelease')
#                 relpath = os.path.relpath(newReleasePath, os.path.dirname(iocLinkPath))
#                 if globals.verbose:
#                     logger.debug( "Pointing IOC to specific release, relative path is %s", relpath)
#                 os.chdir(os.path.dirname(iocLinkPath))
#                 preRunRes = runPrePostDeployScript('bin/preDeploy', name, type, releaseFolder, linkFolder, isMaster, facility, ioc, release)
#                 fixEnvPaths(name, type, releaseFolder, linkFolder, isMaster, facility, ioc, release)
#                 if os.path.lexists('iocSpecificRelease'):
#                     os.remove('iocSpecificRelease')
#                 os.symlink(relpath, 'iocSpecificRelease')
#                 postRunRes = runPrePostDeployScript('bin/postDeploy', name, type, releaseFolder, linkFolder, isMaster, facility, ioc, release)
#     else:
#         # For PyDM displays, the link name is the subsystem, without "pydm-"
#         if type == 'PyDM' and name.startswith('pydm-'):
#             linkName = name.replace('pydm-', '', 1)
#         else:
#             linkName = name
#         newReleasePath = os.path.join(releaseFolder, name, release)
#         masterLinkPath = os.path.join(linkFolder, linkName)
#         relpath = os.path.relpath(newReleasePath, os.path.dirname(masterLinkPath))
#         if globals.verbose:
#             logger.debug( "Relative path is %s", relpath)
#         os.chdir(os.path.dirname(masterLinkPath))
#         preRunRes = runPrePostDeployScript('bin/preDeploy', name, type, releaseFolder, linkFolder, isMaster, facility, ioc, release)
#         fixEnvPaths(name, type, releaseFolder, linkFolder, isMaster, facility, ioc, release)
#         if os.path.lexists(linkName):
#             os.remove(linkName)
#         os.symlink(relpath, linkName)
#         postRunRes = runPrePostDeployScript('bin/postDeploy', name, type, releaseFolder, linkFolder, isMaster, facility, ioc, release)

#     try:
#         updateHistory(name, type, releaseFolder, ioc, release, user, message)
#     except:
#         logger.exception("Unexpected exception adding release to history db")
#         logger.debug( "Files in current folder %s", os.listdir(os.getcwd()))
#         pass

#     return {'status' : True, 'preDeployResults' : preRunRes, 'postDeployResults' : postRunRes}

# """ ============ End - multi_facility_process_helper.py  ============ """

def ansible_run_module():
    """
    This is the default ansible module boilerplate code + some custom args
    In order to run it through a playbook
    """

# """ TODO: Use these args from multi_facility_process.helper.py - upgrade()"""

#     '''All the steps necessary for upgrading a release
#     As inputs, we can expect a dict with
#     name - package name
#     type - package type
#     releaseFolder - The folder where the releases are stored for this package
#     linkFolder - The folder containing the softlinks
#     isMaster - Are we switching the master link? In the case of HLA applications and PyDM displays, this is always true.
#     facility - The facility that this IOC belongs to. Being passed here so that we can pass it to the preDeploy and postDeploy
#     ioc - The name of the IOC for which we are upgrading. In case of the master link or HLA applications and PyDM displays, this will be MASTER
#     release - The release we want to go to.
#     user - The user who initiated this command
#     message - The message for this upgrade
#     What we do.
#     1) Call the predeploy if it exists
#     2) Switch the link - we use a relative link.
#     3) Custom processing that's built into cram - like copying over EDM displays etc, updating the path for EPICS base.
#     4) Call the postdeploy if it exists
#     We return True if this succeeded.
#     '''
#     name = arg['name']
#     type = arg['type']
#     releaseFolder = arg['releaseFolder']
#     linkFolder = arg['linkFolder']
#     isMaster = arg['isMaster']
#     facility = arg['facility']
#     ioc = arg['ioc']
#     release = arg['release']
#     user = arg['user']
#     message = arg['message']

# """ ============================================ """


    # define available arguments/parameters a user can pass to the module
    module_args = dict(
        deploy_type=dict(type='str', required=True),
        ioc_type=dict(type='str', required=False),
        ioc_name=dict(type='str', required=False),
        dev=dict(type='bool', required=False, default=False),
        prod=dict(type='bool', required=False, default=False),
        new=dict(type='bool', required=False, default=False)
    )
    # seed the result dict in the object
    # we primarily care about changed and state
    # changed is if this module effectively modified the target
    # state will include any data that you want your module to pass back
    # for consumption, for example, in a subsequent task
    result = dict( 
        changed=False
        # custom_output=dict
    )
    # the AnsibleModule object will be our abstraction working with Ansible
    # this includes instantiation, a couple of common attr would be the
    # args/params passed to the execution, as well as if the module
    # supports check mode
    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True
    )
    # os.chdir(module.params['output_path'])
    # result['custom_output'] = deploy_ioc(module.params)
    
    # if the user is working with this module in only check mode we do not
    # want to make any changes to the environment, just return the current
    # state with no modifications
    if module.check_mode:
        module.exit_json(**result)
    # use whatever logic you need to determine whether or not this module
    # made any modifications to your target
    if module.params['new']:
        result['changed'] = True
    # during the execution of the module, if there is an exception or a
    # conditional state that effectively causes a failure, run
    # AnsibleModule.fail_json() to pass in the message and the result
    if module.params['ioc_name'] == 'fail me':
        module.fail_json(msg='You requested this to fail', **result)
    # in the event of a successful module execution, you will want to
    # simple AnsibleModule.exit_json(), passing the key/value results
    module.exit_json(**result)

def main():
    ansible_run_module()

if __name__ == '__main__':
    main()