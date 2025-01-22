"""
Desc: MOCK - Deployment controller, handles deployments. Purely used for testing
This uses the functions from deployment_controller.py, if there are any functions here,
they are customized for testing
Look for ## COMMENTED FOR TESTING

Usage: python3 deployment_controller.py
note - this would have to run 24/7 as a service
"""
import os
import shutil
import subprocess
from ruamel.yaml import YAML # Using ruamel instead of pyyaml because it keeps the comments
import logging
import ansible_api
import tarfile
import requests
from artifact_api import ArtifactApi

import uvicorn
import json
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel
from datetime import datetime, timezone, timedelta
from copy import deepcopy

from deployment_controller import *

"""
Ex api request - curl -X 'GET' 'http://172.24.8.139/' -H 'accept: application/json'
curl -X 'GET' 'https://ad-build-dev.slac.stanford.edu/api/deployment/' -H 'accept: application/json'
"""

app = FastAPI(debug=False, title="Deployment_controller", version='1.0.0')
logging.basicConfig(
    level=logging.INFO, # TODO: Change this to NOTSET when use in production
    format="%(levelname)s-%(name)s:[%(filename)s:%(lineno)s - %(funcName)s() ] %(message)s")

ANSIBLE_PLAYBOOKS_PATH = "/home/pnispero/build-system-playbooks/"
INVENTORY_FILE_PATH = ANSIBLE_PLAYBOOKS_PATH + 'deployment_controller_inventory.ini'
CONFIG_FILE_PATH = ANSIBLE_PLAYBOOKS_PATH + "deployment_destinations.yaml"
SCRATCH_FILEPATH = "/home/pnispero/scratch"
BACKEND_URL = "https://ad-build-dev.slac.stanford.edu/api/cbs/v1/"
APP_PATH = '/home/pnispero'

yaml = YAML()
yaml.default_flow_style = False  # Make the output more readable

artifact_api = ArtifactApi()

# Begin API functions =================================================================================

@app.get("/")
def read_root():
    return {"status": "Empty endpoint - somethings wrong with your api call."}

@app.get("/ioc/info")
async def get_ioc_component_info(ioc_request: BasicIoc):
    """
    Return information on an IOC app for every facility
    """
    # 1) Return dictionary of information for an App
    # TODO: Change this to get every facility
    error_msg = "== ADBS == ERROR - ioc not found, name or facility is wrong or missing."
    facilities = get_facilities_list()
    component_info_list = []
    try:
        found_ioc = False
        for facility in facilities:
            component_info = find_component_in_facility(facility, ioc_request.component_name)
            if (component_info):
                info = {f"{facility}": component_info}
                component_info_list.append(info)
                found_ioc = True
        if (not found_ioc): # 404 - Not found
            response_msg = {"payload": error_msg}
            return JSONResponse(content=response_msg, status_code=404)
    except Exception as e:
        error_msg = error_msg + str(e)
        logging.info(error_msg)
        response_msg = {"payload": error_msg}
        return JSONResponse(content=response_msg, status_code=404)
    
    response_msg = {"payload": component_info_list} # 200 - successful
    return JSONResponse(content=response_msg, status_code=200)

@app.post("/tag")
async def post_tag_creation(tag_request: TagDict):
    """
    Function to create a tag and push it to artifact storage
    """
    results_dir_top = os.path.join(SCRATCH_FILEPATH, tag_request.results, tag_request.component_name)

    # 1) Change to the 'build_results' directory
    build_results_dir = os.path.join(results_dir_top, "build_results")
    build_results = f"{tag_request.component_name}-{tag_request.branch}"
    change_directory(build_results_dir)

    # 2) Rename the specified directory to the tag
    build_results_full_path = os.path.join(build_results_dir, build_results)
    tagged_dir_path = os.path.join(build_results_dir, tag_request.tag)
    rename_directory(build_results_full_path, tagged_dir_path)

    # 3) Create a tarball of the renamed directory
    tarball_name = create_tarball(tagged_dir_path, tag_request.tag)
    full_tarball_path = os.path.join(build_results_dir, tarball_name)
    # 4) Push to artifact storage
    return_code = artifact_api.put_component_to_registry(tag_request.component_name, full_tarball_path, tag_request.tag)
    return JSONResponse(content={"payload": "Success"}, status_code=return_code)


@app.put("/ioc/deployment/revert")
async def revert_ioc_deployment(ioc_to_deploy: IocDict):
    # TODO:
    # This would require a log or some history data of the previous deployments,
    # we can store this in the deployment yaml for now.

    # 1) Figure out the previous component, tag, and the iocs and their tags.
    find_component_in_facility(ioc_to_deploy.facilities)
    # Previous component = most recent + 1, or always the second item in history. Better to sort the history by date just in case 
    # its not in order
    # 1.1) Get the history, and sort by date 
    # Define a function to extract and convert the date

    # Sort the history by the date field in descending order
    # sorted_history = sorted(['history'], key=extract_date, reverse=True)
    # Get the second item in history
    # TODO: need to alter ioc_deployment_logic to revert all iocs to the tags in the history item

# Steps 2-5 can be abstracted to its own function since regular deploy_ioc() will be the same logic
    # ioc_deployment_logic(ioc_to_deploy)
    # TODO: add extra logic in there, for revert only, call normal_ioc_deploy.yml, as many times as needed, 
    # but group the iocs by tag, ex: if have 3 iocs at tag 1.1, and 2 iocs at tag 1.2. Call playbook only twice,
    # instead of one for each. and we dont need all logic in ioc deployment_logic, 

    # perhaps split it up into more functions and only use the ones that are needed, then the regular deployment can call 
    # all of them, while revert only calls some of them.


    # todo: alter deploy_ioc to use ioc_deplyoment_logic
    # 2) Using the component and ioc info
    # Either request the artifact from artifact storage, or mount the artifact storage directly

    # 3) Call the appropriate playbook
    
    # 4) Update the deployment config

    # 5) Return status and log of the playbook in action
@app.put("/ioc/deployment")
async def deploy_ioc(ioc_to_deploy: IocDict):
    """
    Function to deploy an ioc component
    """

    logging.info(f"data: {ioc_to_deploy}")
    # 1) Get the data of the CLI api call, varies depending on app type
        # IOC app type:
        # playbook_args_dict = {
        # "initial": initial,
        # "component_name": request.component.name,
        # "tag": tag,
        # "user": linux_uname,
        # "tarball": tarball,
        # "ioc_list": ioc_list,
        # }

    ioc_playbooks_path = ANSIBLE_PLAYBOOKS_PATH + 'ioc_module'

    # 2) Call to artifact api for component/tag
## COMMENT FOR TESTING 
    # if (not artifact_api.get_component_from_registry('/app', ioc_to_deploy.component_name, ioc_to_deploy.tag, os_env='null', extract=False)):
    #     return JSONResponse(content={"payload": {"Error": "artifact storage api is unreachable"}}, status_code=400)
    # 3) Logic for special cases
    facilities = ioc_to_deploy.facilities
    facilities_ioc_dict = dict.fromkeys(facilities, [])
    # 3.1) If not 'ALL' Figure out what facilities the iocs belong to
    if (ioc_to_deploy.ioc_list[0].upper() != 'ALL'):
        for ioc in ioc_to_deploy.ioc_list:
            facility = find_facility_an_ioc_is_in(ioc, ioc_to_deploy.component_name)
            if (facility == None): # Means ioc doesnt exist (typo on user end)
                return JSONResponse(content={"payload": {"Error": "ioc not found - " + ioc}}, status_code=400)
            facilities_ioc_dict[facility].append(ioc)

    # 3.2) Find the info needed to create the startup.cmd for each ioc
## COMMENT FOR TESTING 
    tarball_filepath = '/home/pnispero/BuildSystem/build_deploy_scripts/build_results.tar.gz'
    # tarball_filepath = '/app/' + ioc_to_deploy.tag + '.tar.gz'
    ioc_info = extract_ioc_cpu_shebang_info(tarball_filepath, ioc_to_deploy.tag)
    # 3.3) Figure out which startup.cmd to use for each ioc,
    ioc_info_list_dict = []
    for ioc in ioc_info:
        if ('linuxrt' in ioc['architecture'].lower()):
            if ('ioc' in ioc['folder_name']):
                startup_cmd_template = 'startup.cmd.linuxRT'
            else:
                startup_cmd_template = 'startup.cmd.cpu'
        elif ('rtems' in ioc['architecture'].lower()):
            startup_cmd_template = 'startup.cmd.rtems'
        else: # We can assume if not linuxrt or rtems, then it is a softioc/cpu
            if ('ioc' in ioc['folder_name'].lower()):
                startup_cmd_template = 'startup.cmd.soft.ioc' # TODO: or soft?
            else:
                startup_cmd_template = 'startup.cmd.soft.cpu'
        ioc_dict = {
            'name': ioc['folder_name'],
            'architecture': ioc['architecture'],
            'binary': ioc['binary'],
            'startup_cmd_template': startup_cmd_template
        }
        ioc_info_list_dict.append(ioc_dict)
    # in the loop below copy the ioc_dict, but only get the iocs within that facility (facilities_ioc_dict[facility])

    # 4) Call the appropriate ansible playbook for each applicable facility 
    playbook_args_dict = ioc_to_deploy.model_dump()
    playbook_args_dict['tarball'] = tarball_filepath
## COMMENT FOR TESTING     
    playbook_args_dict['playbook_path'] = '/home/pnispero/build-system-playbooks/ioc_module'
    # playbook_args_dict['playbook_path'] = '/sdf/group/ad/eed/ad-build/build-system-playbooks/ioc_module'
    playbook_args_dict['user_src_repo'] = None
    status = 200
## COMMENT FOR TESTING
    deployment_report_file = '/home/deployment-report-' + ioc_to_deploy.component_name + '-' + ioc_to_deploy.tag + '.log'
    # deployment_report_file = '/app/deployment-report-' + ioc_to_deploy.component_name + '-' + ioc_to_deploy.tag + '.log'
    deployment_output = ""
    logging.info(f"facilities: {facilities}")
    for facility in facilities:
        logging.info(f"facility: {facility}")
        logging.info(f"facilities_ioc_dict: {facilities_ioc_dict}")
        # 5) If component doesn't exist in facility, then skip. This assumes that the component exists in at least ONE facility                                     
        if (find_component_in_facility(facility, ioc_to_deploy.component_name) is None):
            continue
        if (ioc_to_deploy.ioc_list[0].upper() == 'ALL'):
            # 3.2) If ioc = 'ALL' then create list of iocs based on facility
            component_info = find_component_in_facility(facility, ioc_to_deploy.component_name)
            facilities_ioc_dict[facility].extend([ioc['name'] for ioc in component_info['dependsOn']])

        # Iterate over ioc_list_dict and add matching items to facility_ioc_dict
        facility_ioc_dict = []
        for ioc in ioc_info_list_dict:
            if ioc['name'] in facilities_ioc_dict[facility]:
                if ('cpu' in ioc['startup_cmd_template']): # Add the facility to startup.cmd template if cpu
                    ioc['startup_cmd_template'] += f'.{facility.lower()}'
                facility_ioc_dict.append(ioc)


        playbook_args_dict['ioc_list'] = facility_ioc_dict # Update ioc list for each facility    
        playbook_args_dict['facility'] = facility
    # TODO: - may want to do a dry run first to see if there would be any fails.
        playbook_args = json.dumps(playbook_args_dict) # Convert dictionary to JSON string
## COMMENT FOR TESTING         
        stdout, stderr, return_code = ansible_api.run_ansible_playbook(INVENTORY_FILE_PATH, ioc_playbooks_path + '/ioc_deploy.yml',
                                        'test', playbook_args, return_output=True, no_color=True)
        # stdout, stderr, return_code = ansible_api.run_ansible_playbook(INVENTORY_FILE_PATH, ioc_playbooks_path + '/ioc_deploy.yml',
        #                                 facility, playbook_args, return_output=True, no_color=True)
        # 5.1) Combine output
        current_output = ""
        current_output += "== Deployment output for " + facility + ' ==\n\n' + stdout
        if (return_code != 0):
            status = 400 # Deployment failed
            if (stderr != ''):
                current_output += "\n== Errors ==\n\n" + stderr
        deployment_output += current_output
    
        # 6) Write new configuration to deployment db for each facility
        timezone_offset = -8.0  # Pacific Standard Time (UTC−08:00)
        tzinfo = timezone(timedelta(hours=timezone_offset))
        timestamp = datetime.now(tzinfo).isoformat()
    # TODO: Add checks if any database operations fail, then bail and return to user
        update_component_in_facility(facility, timestamp, ioc_to_deploy.user, 'ioc', ioc_to_deploy.component_name,
                                     ioc_to_deploy.tag, current_output, facilities_ioc_dict[facility])
    logging.info('Generating summary/report...')
## COMMENT FOR TESTING 
    print(f"Output:\n{stdout}")
    print(f"Error:\n{stderr}")
    return
    # 6) Generate summary for report
    summary = \
f"""#### Deployment report for {ioc_to_deploy.component_name} - {ioc_to_deploy.tag} ####
#### Date: {timestamp}
#### User: {ioc_to_deploy.user}
\n#### IOCs deployed: {facilities_ioc_dict}"""

    if (status == 200): # 200 means success
        # 6.2) Write summary of deployment to report at the top
        with open(deployment_report_file, 'w') as report_file:
            summary += "\n#### Overall status: Success\n\n" + deployment_output
            report_file.write(summary)
    else: # Failure
        # response_msg = {"payload": {"Output": stdout, "Error": stderr}}
        status = 400
        with open(deployment_report_file, 'w') as report_file:
            summary += "\n#### Overall status: Failure - PLEASE REVIEW\n\n" + deployment_output
            report_file.write(summary)
    # 7) Cleanup - delete downloaded tarball
    os.remove(tarball_filepath)
    # 8) Return ansible playbook output to user
    return FileResponse(path=deployment_report_file, status_code=status)

if __name__ == "__main__":
    uvicorn.run('deployment_controller:app', host='0.0.0.0', port=8080, timeout_keep_alive=120)
    # timeout_keep_alive set to 120 seconds, in case deployment takes longer than usual
    # deployment_controller refers to file, and app is the app=fastapi()