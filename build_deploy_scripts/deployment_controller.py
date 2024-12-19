"""
Desc: Deployment controller, handles deployments

Usage: python3 deployment_controller.py
note - this would have to run 24/7 as a service
"""
import os
import subprocess
import time
import yaml
import logging
import ansible_api
from artifact_api import ArtifactApi

import uvicorn
import json
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
from pydantic import BaseModel

"""
Ex api request - curl -X 'GET' 'http://172.24.8.139/' -H 'accept: application/json'
curl -X 'GET' 'https://ad-build-dev.slac.stanford.edu/api/deployment/' -H 'accept: application/json'
"""

app = FastAPI(debug=False, title="Deployment_controller", version='1.0.0')
logging.basicConfig(
    level=logging.INFO, # TODO: Change this to NOTSET when use in production
    format="%(levelname)s-%(name)s:[%(filename)s:%(lineno)s - %(funcName)s() ] %(message)s")

CONFIG_FILE_PATH = "./deployment_destinations.yaml" # TODO: TEMP: Refer to local directory for testing
# CONFIG_FILE_PATH = "/mnt/eed/ad-build/deployment_config.yaml"
ANSIBLE_PLAYBOOKS_PATH = "../ansible/" # TODO: TEMP: Refer to local dir for testing
# ANSIBLE_PLAYBOOKS_PATH = "/sdf/group/ad/eed/ad-build/ansible_playbooks"
INVENTORY_FILE_PATH = ANSIBLE_PLAYBOOKS_PATH + 'global_inventory.ini'

class IocDict(BaseModel):
    facility: str = None # Optional
    initial: bool
    component_name: str
    tag: str
    ioc_list: list
    user: str

# TODO: Possible to just use IocDict but would have to make fields optional
    # And making the fields optional may not be good. 
class BasicIoc(BaseModel):
    component_name: str

def parse_yaml(filename: str) -> dict:
    with open(filename, 'r') as file:
        yaml_data = yaml.safe_load(file)
    return yaml_data

def write_to_config_yaml(data_to_write: dict):
    """
    Function that writes the data from API call of CLI bs run deployment
    to the configuration yaml (db once done prototyping)
    """
    config_dict = parse_yaml(CONFIG_FILE_PATH)
    logging.info(config_dict)
    logging.info("unfinished function")
    pass

def find_component_in_facility(facility: str, app_type: str, component: str) -> dict:
    """ Function to return component information """
    config_dict = parse_yaml(CONFIG_FILE_PATH)
    facility_config = config_dict[facility][app_type]
    if (component in facility_config):
        return facility_config[component]
    return None

def find_facility_an_ioc_is_in(ioc: str, app_type: str, component: str) -> dict:
    """ Function to return the facility that the ioc is in """
    config_dict = parse_yaml(CONFIG_FILE_PATH)
    facility_config = config_dict[facility][app_type]
    if (component in facility_config):
        return facility_config[component]
    return None

def get_facilities_list() -> list:
    config_dict = parse_yaml(CONFIG_FILE_PATH)
    return config_dict.keys()

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
            component_info = find_component_in_facility(facility, 'ioc', ioc_request.component_name)
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

@app.put("/ioc/deployment/revert")
async def revert_ioc_deployment(data_to_write: IocDict):
    # TODO:
    # This would require a log or some history data of the previous deployments,
    # we can store this in the deployment yaml for now.

    # 1) Return dictionary of information for an App
    config_dict = parse_yaml(CONFIG_FILE_PATH)
    # 2) Using the component and ioc info
    # Either request the artifact from artifact storage, or mount the artifact storage directly

# Steps 3-5 can be abstracted to its own function since regular deploy_ioc() will be the same logic
    # 3) Call the appropriate playbook
    
    # 4) Update the deployment config

    # 5) Return status and log of the playbook in action
    pass

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

    # 2) Call to artifact api for component/tag
    problem - right now there is no logic that creates tags, pushes builds to artifact storage
    solution - so can just put in a tagged version of the app we want to deploy to storage for demo purposes
    ArtifactApi.get_component_from_registry('/build', ioc_to_deploy.component_name, ioc_to_deploy.tag)
    config_dict = parse_yaml(CONFIG_FILE_PATH)
    # 3) Logic for special cases
    facilities = get_facilities_list()
    facilities_ioc_dict = dict.fromkeys(facilities)
    if (ioc_to_deploy.ioc_list[0] == 'ALL'):
        # 3.1) If ioc = 'ALL' then create list of iocs based on facility
        component_info = find_component_in_facility(ioc_to_deploy.facility, 'ioc', ioc_to_deploy.component_name)
        facilities_ioc_dict[ioc_to_deploy.facility] += component_info['iocs']
    else:
        # 3.2) If not 'ALL' Figure out what facilities the iocs belong to
        # TODO: May want to just get the facilities from the db for flexibility
        for ioc in ioc_to_deploy.ioc_list:
            facility = find_facility_an_ioc_is_in(ioc, 'ioc', ioc_to_deploy.component_name)
            if (facility == None): # Means ioc doesnt exist (typo on user end)
                return JSONResponse(content={"payload": {"Error": "ioc not found - " + ioc}}, status_code=400)
            facilities_ioc_dict[facility] += ioc
    # 4) Call the appropriate ansible playbook for each applicable facility 
    playbook_args_dict = ioc_to_deploy.model_dump()
    tarball_filepath = '/build/' + ioc_to_deploy.tag
    playbook_args_dict['tarball'] = tarball_filepath
    status = 200
    for facility in facilities:
        # TODO: looping through every facility might be wrong, because this means the playbook will run
        # even if the app doesnt exist for that facility. maybe can add a check if the component
        # doesnt exist in the deployment db, then skip. 
        playbook_args_dict['ioc_list'] = facilities_ioc_dict[facility] # Update ioc list for each facility
    # 5) TODO: - may want to do a dry run first to see if there would be any fails.
        playbook_args = json.dumps(playbook_args_dict) # Convert dictionary to JSON string
        stdout, stderr, return_code = ansible_api.run_ansible_playbook(INVENTORY_FILE_PATH, ANSIBLE_PLAYBOOKS_PATH + 'ioc_module/ioc_deploy.yml',
                                        ioc_to_deploy.facility, playbook_args, return_output=True)
        should this be atmoic? Or just deploy what you can, if there are errors, mention to user 
        user can be the one to decide if they want to revert to undo their changes
        TODO: There should be a summary of success/fail for each facility.
            # may want to return a file which can be the deployment report
            # return the file directly, then in the CLI
            # can ask the user if they want to download the report.
        # TODO: Combine output
        if (return_code != 0):
            status = 400 # Deployment failed
        with open('deployment-report-' + ioc_to_deploy.component_name + '-' + ioc_to_deploy.tag + '.log', 'w') as report_file:
            ouput = "== Deployment output for " + facility,
            report_file.write(stdout)
    if (status == 200): # 0 means success
        # 6) Write new configuration to deployment db
        write_to_config_yaml(ioc_to_deploy)    
        response_msg = {"payload": {"Output": stdout}}
        # 6.1) TODO: Write history to deployment db
    else: # Failure
        response_msg = {"payload": {"Output": stdout, "Error": stderr}}
        status = 400
# 7) Cleanup - delete downloaded tarball
    os.remove(tarball_filepath)
    # 8) Return ansible playbook output to user
    return JSONResponse(content=response_msg, status_code=status)

if __name__ == "__main__":
    uvicorn.run('deployment_controller:app', host='0.0.0.0', port=80)
    # deployment_controller refers to file, and app is the app=fastapi()