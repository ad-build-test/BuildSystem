"""
Desc: Deployment controller, handles deployments

Usage: python3 deployment_controller.py
note - this would have to run 24/7 as a service
"""
from contextlib import contextmanager
import os
import shutil
import uuid
from ruamel.yaml import YAML # Using ruamel instead of pyyaml because it keeps the comments
import logging
import ansible_api
import tarfile
import requests

import uvicorn
import json
import time
from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse, Response
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone, timedelta

"""
Ex api request
curl -X 'GET' 'https://ad-build-dev.slac.stanford.edu/api/deployment/' -H 'accept: application/json'
"""

app = FastAPI(debug=False, title="Deployment_controller", version='1.0.0')
logging.basicConfig(
    level=logging.DEBUG, # TODO: Change this to NOTSET when use in production
    format="%(levelname)s-%(name)s:[%(filename)s:%(lineno)s - %(funcName)s() ] %(message)s")

ANSIBLE_PLAYBOOKS_PATH = "/sdf/group/ad/eed/ad-build/build-system-playbooks/"
INVENTORY_FILE_PATH = ANSIBLE_PLAYBOOKS_PATH + 'global_inventory.ini'
CONFIG_FILE_PATH = ANSIBLE_PLAYBOOKS_PATH + "deployment_destinations.yaml"
SCRATCH_FILEPATH = "/sdf/group/ad/eed/ad-build/scratch"
is_prod = os.environ.get("AD_BUILD_PROD", "false").lower() in ("true", "1", "yes", "y")
if is_prod: BACKEND_URL = "https://ad-build.slac.stanford.edu/api/cbs/v1/"
else: BACKEND_URL = "https://ad-build-dev.slac.stanford.edu/api/cbs/v1/"
APP_PATH = "/app"
USED_OS_LIST = ["RHEL7", "ROCKY9"]
FACILITIES_LIST = ["LCLS", "FACET", "TESTFAC", "DEV", "S3DF"]

yaml = YAML()
yaml.default_flow_style = False  # Make the output more readable

# pydantic models =================================================================================
class Component(BaseModel):
    component_name: str

class IocDict(Component):
    facilities: Optional[list] = None  # Optional, defaults to None
    tag: str
    ioc_list: Optional[list] = None
    user: str
    dry_run: Optional[bool] = False # Optional

class PydmDict(Component):
    facilities: Optional[list] = None # Optional
    tag: str
    user: str
    dry_run: Optional[bool] = False # Optional
    subsystem: str # Ex: [mps, mgnt, vac, prof, etc.]

class InitialDeploymentDict(Component):
# Used for the initial deployment endpoint
    facility: str
    tag: str
    ioc_list: Optional[list] = None # Optional
    user: str
    type: str

class TagDict(Component):
    branch: str
    results: str
    tag: str
    user: str


def parse_yaml(filename: str) -> dict:
    with open(filename, 'r') as file:
        yaml_data = yaml.load(file)
    return yaml_data

def update_yaml(filename: str, data: dict):
    with open(filename, 'w') as file:
        yaml.dump(data, file)

def add_log_to_component(facility: str, timestamp: str, user: str, component_to_update: str, log_output: str) -> bool:
    # add entry to history
    deployment_log = {
        "log": log_output,
        "logDate": timestamp,
        "user": user,
    }
    endpoint = BACKEND_URL + f'deployments/{component_to_update}/{facility}/logs'
    response = requests.post(endpoint, json=deployment_log)
    return True

def add_new_component(facility: str, app_type: str, component_name: str,
                       tag: str, ioc_list: list = None) -> bool:
    """
    Function to add a new component in the deployment db
    """
    new_component = { "name": component_name,
        "facility": facility,
        "tag": tag,
        "type": app_type,
    }
    logging.debug(app_type)
    logging.debug(ioc_list)
    if (ioc_list):
        new_depends_on_list = [{'name': ioc, 'tag': tag} for ioc in ioc_list]
        logging.debug(f"new_depends_on_list: {new_depends_on_list}")
        new_component['dependsOn'] = new_depends_on_list
    if (app_type == 'ioc' and ioc_list == []): # Initialize an empty list for dependsOn if ioc app
        new_component['dependsOn'] = []
        logging.debug("Adding empty dependsOn list")

    logging.debug(f"new_component: {new_component}")
    endpoint = BACKEND_URL + 'deployments'
    response = requests.post(endpoint, json=new_component)
    return True

def update_component_in_facility(facility: str, app_type: str, component_to_update: str,
                                  tag: str, iocs_to_update: list = None) -> bool:
    """
    Function to update an existing component in the deployment db
    """
    # 1) Find the component
    component = find_component_in_facility(facility, component_to_update)
    if (component is None):
        return False
    # 2) Update tag in original config dict
    component['tag'] = tag
    # 3) Update iocs (if applicable)
    logging.debug(component)
    if (app_type == 'ioc'):
        # TODO: New logic to add - basically update the tags that do exist, then for ones that don't
                # exist, add them.
        ioc_to_update_exists = False
        for ioc_to_update in iocs_to_update:
            for existing_ioc in component["dependsOn"]:
                if (ioc_to_update == existing_ioc['name']): # Update the tag for each existing ioc that we want
                    existing_ioc['tag'] = tag
                    ioc_to_update_exists = True
                    break
            if (not ioc_to_update_exists): # add new iocs onto existing list of iocs
                add_ioc = {"name": ioc_to_update, "tag": tag}
                component["dependsOn"].append(add_ioc)
            ioc_to_update_exists = False # Reset

    # 4) Update component in db
    logging.debug(component)
    endpoint = BACKEND_URL + f'deployments/{component_to_update}/{facility}'
    response = requests.put(endpoint, json=component)
    logging.debug(f"response.json(): {response.json()}")
    return True

def find_component_in_facility(facility: str, component_to_find: str) -> dict:
    """ Function to return component information """
    endpoint = BACKEND_URL + f'deployments/{component_to_find}/{facility}'
    response = requests.get(endpoint)
    if (response.ok):
        return response.json()['payload']
    else: 
        return None

def find_facility_an_ioc_is_in(ioc_to_find: str, component_with_ioc: str) -> str:
    """ Function to return the facility that the ioc is in """
    for facility in FACILITIES_LIST: # Loop through each facility
        component = find_component_in_facility(facility, component_with_ioc)
        if (component):
            for ioc in component['dependsOn']: # Loop through each ioc
                if (ioc_to_find in ioc['name']):
                    return facility
    return None

def extract_date(entry) -> datetime:
    return datetime.fromisoformat(entry['date'])

def change_directory(path):
    try:
        os.chdir(path)
        # print(f"Changed directory to {os.getcwd()}")
    except FileNotFoundError:
        raise FileNotFoundError(f"Directory {path} not found.")

def rename_directory(src_dir, dest_dir):
    try:
        if os.path.isdir(src_dir):
            os.rename(src_dir, dest_dir)
            print(f"Renamed directory {src_dir} to {dest_dir}")
        else:
            raise ValueError(f"Directory {src_dir} not found.")
    except Exception as e:
        raise ValueError(f"Error renaming directory: {e}")

def create_tarball(directory, tag):
    tarball_name = f"{tag}.tar.gz"
    try:
        with tarfile.open(tarball_name, "w:gz") as tar:
            tar.add(directory, arcname=os.path.basename(directory))
        print(f"Created tarball: {tarball_name}")
        return tarball_name
    except Exception as e:
        raise ValueError(f"Error creating tarball: {e}")

def parse_shebang(shebang_line: str):
    """ Function to extract architecture and binary name from the shebang line """
    # 1) Get the part of the shebang line after 'bin/'
    path = shebang_line.split('bin/')[1]  # Split after 'bin/'
    
    # 2) Split the path by '/' and get the relevant parts
    parts = path.split('/')
    
    if len(parts) >= 2:
        architecture = parts[0]  # First part is the architecture (e.g., rhel7-x86_64)
        binary_name = parts[1]    # Second part is the binary name (e.g., myApp)
        return architecture, binary_name
    else:
        print(f"Warning: Invalid path structure in shebang line: {shebang_line}")
        return None, None

def extract_ioc_cpu_shebang_info(app_dir_name: str) -> dict:
    """ Function to process the st.cmd files """
    # 1) Open and extract the tarball
    # The directory containing 'iocBoot' is inside the app directory (app_dir_name)
    iocBoot_dir = os.path.join(app_dir_name, 'iocBoot')
    # TODO: Need to check cpuBoot as well

    # 3) Check if the iocBoot directory exists
    if not os.path.exists(iocBoot_dir):
        print(f"Error: The directory {iocBoot_dir} does not exist in the extracted files.")
        return []
    
    results = []

    # 4) Iterate over the directories in iocBoot
    for root, dirs, files in os.walk(iocBoot_dir):
        # 4.1) Skip directories that do not contain st.cmd
        if 'st.cmd' not in files:
            continue  # Skip this directory

        # 4.2) Process st.cmd if it's found
        st_cmd_path = os.path.join(root, 'st.cmd')

        # 4.3) Read the st.cmd file and parse the shebang
        with open(st_cmd_path, 'r') as f:
            first_line = f.readline().strip()  # Read the first line (shebang)
            
            if first_line.startswith("#!"):
                architecture, binary_name = parse_shebang(first_line)
                if architecture and binary_name:
                    folder_name = os.path.basename(root)  # Get the folder name (e.g., ioc-b34-bs01)
                    results.append({
                        'folder_name': folder_name,
                        'architecture': architecture,
                        'binary': binary_name
                    })
            else:
                print(f"Warning: No shebang line in {st_cmd_path}")
    
    return results

def cleanup_temp_deployment_dir(directory: str):
    """ for safe cleanup of temporary files (mainly the tarball for the tagged release). 
        With this, the temporary files will be deleted even if exceptions are thrown"""
    try:
        # Wait a bit to ensure file has been sent
        time.sleep(5)  
        if os.path.exists(directory):
            logging.info(f"Cleaning up temporary directory: {directory}")
            shutil.rmtree(directory, ignore_errors=True)
    except Exception as e:
        logging.error(f"Error cleaning up directory {directory}: {str(e)}")

def download_release_helper(endpoint: str, download_dir: str, tarball_name: str, extract_tarball: bool):
    response = requests.get(endpoint)
    # Download file from api, and extract to download_dir
    # Download the .tar.gz file
    tarball_filepath = os.path.join(download_dir, tarball_name)
    if response.status_code == 200:
        # Download response to tarball file
        stream_size = 1024*1024 # Write in chunks (1MB) since tarball can be big
        with open(tarball_filepath, 'wb') as file: 
            for chunk in response.iter_content(chunk_size=stream_size): 
                if (chunk):
                    file.write(chunk)
        logging.info('Tarball downloaded successfully')
        logging.debug(f'Extract tarball: {extract_tarball}')
        logging.debug(f'download dir: {download_dir}')
        if (extract_tarball):
            # Extract the .tar.gz file
            logging.info('Extracting tarball...')
            
            with tarfile.open(tarball_filepath, 'r:gz') as tar:
                # Extract with modified permissions
                tar.extractall(path=download_dir, filter="data")
                logging.info(f'{tarball_filepath} extracted to {download_dir}')

        return True
    else:
        logging.info(f'Failed to retrieve the file. Status code: {response.status_code}')
        return False

def download_release(component_name: str, tag: str, download_dir: str, all_os: bool, extract_tarball: bool = False):
    """ Download a components tagged release from the backend -> github """

    endpoint = BACKEND_URL + f'component/{component_name}/release/{tag}'
    valid_tag_release = False
    if (all_os): # This is needed if app has a build for one or more OSes
        for current_os in USED_OS_LIST:
            new_endpoint = endpoint + f'?os={current_os}'
            tarball_name = f'{tag}-{current_os}.tar.gz'
            found_release = download_release_helper(new_endpoint, download_dir, tarball_name, extract_tarball)
            if (found_release): # Just need to find at least one release otherwise the tag or app doesn't exist
                valid_tag_release = True
        if (valid_tag_release):
            logging.info('Creating merged tarball from extracted contents...')
    
            # New tarball will be named after the tag
            merged_tarball_path = os.path.join(download_dir, f'{tag}.tar.gz')
            # The extracted directory name is just the tag
            extracted_dir = os.path.join(download_dir, tag)
            # Create new tarball with all extracted contents
            with tarfile.open(merged_tarball_path, 'w:gz') as tar:
                tar.add(extracted_dir, arcname=tag)
            logging.info(f'Merged tarball created: {merged_tarball_path}')
    else:
        tarball_name = f'{tag}.tar.gz'
        valid_tag_release = download_release_helper(endpoint, download_dir, tarball_name, extract_tarball)

    return valid_tag_release


    
def update_db_after_deployment(deployment_success: bool, new_component: bool, facility: str, app_type: str, component_name: str,
                               tag: str, user: str, current_output: str, ioc_list: list = None):
    # 6) Write new configuration to deployment db for each facility
    timestamp = datetime.now().isoformat()
    # TODO: Add checks if any database operations fail, then bail and return to user
    if (deployment_success):
        # case - If new component and/or new ioc then add_new_component
        if (new_component):
            logging.debug("Adding new component")
            add_new_component(facility, app_type, component_name, tag, ioc_list)
        else:
            # case - If new ioc but existing component then update_component_in_facility
            update_component_in_facility(facility, app_type, component_name, tag, ioc_list)
    add_log_to_component(facility, timestamp, user, component_name, current_output)


def write_file(filepath: str, content: str):
    with open(filepath, 'w') as file:
        file.write(content)

def generate_report(component_name: str, tag: str, user: str, deployment_output: str, status: int, deployment_report_file: str, facilities_ioc_dict: dict=None, dry_run: bool=False):
    """ Generate a deployment report """
    summary = \
f"""#### Deployment report for {component_name} - {tag} ####
#### User: {user}"""
    if (dry_run):
        summary += "\n#### Note - This was deployed as a DRY-RUN"
    if (facilities_ioc_dict):
        summary += f"\n#### IOCs deployed: {facilities_ioc_dict}"

    if (status == 200): # 200 means success
        # 6.2) Write summary of deployment to report at the top
        summary += "\n#### Overall status: Success\n\n" + deployment_output
        write_file(deployment_report_file, summary)
    else: # Failure
        status = 400
        summary += "\n#### Overall status: Failure - PLEASE REVIEW\n\n" + deployment_output
    logging.debug(deployment_report_file)
    write_file(deployment_report_file, summary)
    logging.debug(summary)
    return summary

# Begin API functions =================================================================================

@app.get("/")
def read_root():
    return {"status": "Empty endpoint - somethings wrong with your api call."}

@app.get("/deployment/info")
async def get_deployment_component_info(component: Component):
    """
    Return information on a requested deployment for every facility
    """
    # 1) Return dictionary of information for an App
    error_msg = "Deployment not found in deployment database, name or facility is wrong or missing. Or it has never been deployed"
    facilities = FACILITIES_LIST
    component_info_list = []
    try:
        found_ioc = False
        for facility in facilities:
            logging.info(f"get_deployment_component_info: component_name: {component.component_name}, facility: {facility}")
            component_info = find_component_in_facility(facility, component.component_name)
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
    return NotImplementedError
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
async def deploy_ioc(ioc_to_deploy: IocDict, background_tasks: BackgroundTasks):
    """
    Main entry point for IOC deployment API.
    Handles these deployment scenarios:
    1. Deploy tag to select existing IOCs 
        (IOCs specified, facility not required)
        ex: bs deploy -i sioc-sys0-bs01, sioc-sys0-bs02 R1.3.4
    2. Deploy tag to all existing IOCs 
        (IOCs specified, facility not required)
        2.1. Deploy tag to all existing IOCs but user specified which facilities they want to update. 
        This would end up being case 2, but the cli would need logic 
        to figure out which IOCs in the facilities to deploy
        ex: bs deploy -i ALL -f LCLS, FACET R1.3.4
    3. Deploy tag to new IOCs 
        (IOCs specified, facility required)
        ex: bs deploy -i sioc-sys0-bs01, sioc-sys0-bs02 -f LCLS R1.3.4
    4. Deploy tag to component 
        (no IOCs, facility required) - works for both new and existing components
        ex: bs deploy -f LCLS R1.3.4
    5. Deploy tag to new component AND new IOCs 
        (IOCs specified, facility required)
        ex: bs deploy -i sioc-sys0-bs01, sioc-sys0-bs02 -f LCLS R1.3.4
    """
    # Setup temporary directory for deployment contents
    request_id = str(uuid.uuid4())
    temp_download_dir = f"{APP_PATH}/tmp/{request_id}"
    os.makedirs(temp_download_dir, exist_ok=True)
    logging.info(f"New deployment request data: {ioc_to_deploy}")
    
    # Add cleanup as background task
    background_tasks.add_task(cleanup_temp_deployment_dir, temp_download_dir)
    
    # Handle component-only deployment
    if not ioc_to_deploy.ioc_list:
        logging.info("Component-only deployment")
        return deploy_component(ioc_to_deploy, temp_download_dir, background_tasks)
    
    # Handle IOC deployments
    if ioc_to_deploy.facilities:
        # Case 3: Deploy tag to new IOCs (IOCs specified, facility required)
        # Case 5: Deploy new component AND new IOCs (IOCs specified, facility required)
        logging.info("Deploy tag to new IOCs")
        return deploy_iocs_with_facility(ioc_to_deploy, temp_download_dir, background_tasks)
    else:
        # Cases 1 & 2: Deploy tag to existing IOCs (facility not required)
        logging.info("Deploy tag to existing IOCs (Cases 1 & 2)")
        return deploy_existing_iocs(ioc_to_deploy, temp_download_dir, background_tasks)


def deploy_component(ioc_to_deploy: IocDict, temp_download_dir: str, background_tasks: BackgroundTasks):
    """
    Handle component-only deployment
    - Deploy tag to component (either new or existing) with facility specified
    - No IOCs are deployed
    """
    # I think ioc_to_deploy will always only have one facility specified. if the facility field is used. 

    facilities_ioc_dict = {facility: [] for facility in ioc_to_deploy.facilities}
    
    # Determine if component is new or not
    for facility in ioc_to_deploy.facilities:
        component = find_component_in_facility(facility, ioc_to_deploy.component_name)
        if component is None:
            # New component for this facility
            new_component = True
        else:
            # Existing component for this facility
            new_component = False
    
    if new_component:
        logging.info(f"Creating new component {ioc_to_deploy.component_name} in facilities: {ioc_to_deploy.facilities}")
    else:
        logging.info(f"Updating existing component {ioc_to_deploy.component_name} in facilities: {ioc_to_deploy.facilities}")
    
    # Execute deployment with empty IOC lists - component only
    return execute_ioc_deployment(
        ioc_to_deploy, temp_download_dir,
        facilities_ioc_dict, new_component, background_tasks
    )

def deploy_existing_iocs(ioc_to_deploy: IocDict, temp_download_dir: str, background_tasks: BackgroundTasks):
    """
    Handle deployments to existing IOCs
    - Case 1: Deploy tag to select existing IOCs 
    - Case 2: Deploy tag to all existing IOCs
    
    Facility not required as we'll find where each IOC exists.
    """
    facilities_ioc_dict = {}
    
    # Process each IOC to find its facility
    # the cli should do a check if the iocs the user wants to deploy actually exist
    for ioc in ioc_to_deploy.ioc_list:
        facility = find_facility_an_ioc_is_in(ioc, ioc_to_deploy.component_name)
        logging.info(f"ioc: {ioc}, facility: {facility}")
        if not facility:
            return JSONResponse(content={"payload": {"Error": f"IOC not found in deployment database: {ioc}. (If new IOC then please deploy with a facility)"}}, status_code=400)
        if facility not in facilities_ioc_dict:
            facilities_ioc_dict[facility] = []
        facilities_ioc_dict[facility].append(ioc)
    
    # If we get here, we found facilities for all IOCs
    ioc_to_deploy.facilities = list(facilities_ioc_dict.keys())
    
    # Execute deployment with the IOCs we found
    return execute_ioc_deployment(
        ioc_to_deploy, temp_download_dir,
        facilities_ioc_dict, False, background_tasks  # No new components
    )

def deploy_iocs_with_facility(ioc_to_deploy: IocDict, temp_download_dir: str, background_tasks: BackgroundTasks):
    """
    Handle deployment of IOCs with facility specified
    - Case 3: Deploy tag to new IOCs (facility required)
    - Case 5: Deploy new component AND new IOCs (IOCs specified, facility required)
    """
    facilities_ioc_dict = {facility: [] for facility in ioc_to_deploy.facilities}

    # Check component existence in specified facilities
    for facility in ioc_to_deploy.facilities:
        component = find_component_in_facility(facility, ioc_to_deploy.component_name)
        if component is None:
            # New component for this facility
            new_component = True
            # Add all IOCs for this new component
            facilities_ioc_dict[facility] = ioc_to_deploy.ioc_list
        else:
            # Component exists - deploy all specified IOCs
            # Don't need to check if they're new, we'll deploy anyway
            new_component = False
            facilities_ioc_dict[facility] = ioc_to_deploy.ioc_list

    if new_component:
        logging.info(f"Creating new component {ioc_to_deploy.component_name} with IOCs in facilities: {facilities_ioc_dict}")

    # Execute deployment
    return execute_ioc_deployment(
        ioc_to_deploy, temp_download_dir,
        facilities_ioc_dict, new_component, background_tasks
    )


def execute_ioc_deployment(ioc_to_deploy: IocDict, temp_download_dir: str, 
                      facilities_ioc_dict: dict, new_component: bool, background_tasks: BackgroundTasks):
    """
    Called by the specific deployment functions after they determine what to deploy.
    """
    ioc_playbooks_path = ANSIBLE_PLAYBOOKS_PATH + 'ioc_module'
    playbook_args_dict = ioc_to_deploy.model_dump()
    playbook_args_dict['playbook_path'] = ioc_playbooks_path
    playbook_args_dict['user_src_repo'] = None
    status = 200
    deployment_report_file = temp_download_dir + '/deployment-report-' + ioc_to_deploy.component_name + '-' + ioc_to_deploy.tag + '.log'
    deployment_output = ""
    extracted_ioc_info = False

    # Download release
    if not download_release(ioc_to_deploy.component_name, ioc_to_deploy.tag, temp_download_dir, all_os=True, extract_tarball=True):
        return JSONResponse(content={"payload": {"Error": f"Deployment tag may not exist for app: {ioc_to_deploy.component_name}, tag: {ioc_to_deploy.tag} \
                                    . Or software factory backend is broken"}}, status_code=400)
    
    for facility in facilities_ioc_dict.keys():
        logging.info(f"Deploying to facility: {facility}")
        logging.info(f"IOCs to deploy: {facilities_ioc_dict[facility]}")
        
        # Skip facilities with empty IOC lists for component-only deployments
        is_component_only = len(facilities_ioc_dict[facility]) == 0
        
        # Extract IOC info (needed even for component-only to record component in DB)
        if not extracted_ioc_info:
            extracted_tarball_filepath = os.path.join(temp_download_dir, ioc_to_deploy.tag)
            ioc_info = extract_ioc_cpu_shebang_info(extracted_tarball_filepath)
            # Figure out which startup.cmd to use for each ioc
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
                        startup_cmd_template = 'startup.cmd.soft.ioc'
                    else:
                        startup_cmd_template = 'startup.cmd.soft.cpu'
                ioc_dict = {
                    'name': ioc['folder_name'],
                    'architecture': ioc['architecture'],
                    'binary': ioc['binary'],
                    'startup_cmd_template': startup_cmd_template
                }
                ioc_info_list_dict.append(ioc_dict)
            extracted_ioc_info = True

        # Add the tarball path
        extracted_tarball_filepath = os.path.join(temp_download_dir, ioc_to_deploy.tag)
        tarball_filepath = extracted_tarball_filepath + '.tar.gz'
        logging.info(f"tarball_filepath: {tarball_filepath}")
        playbook_args_dict['tarball'] = tarball_filepath

        # For IOC deployments, prepare facility_ioc_dict
        facility_ioc_dict = []
        if not is_component_only:
            # Iterate over ioc_list_dict and add matching items to facility_ioc_dict
            for ioc in ioc_info_list_dict:
                if ioc['name'] in facilities_ioc_dict[facility]:
                    if ('cpu' in ioc['startup_cmd_template']): # Add the facility to startup.cmd template if cpu
                        ioc['startup_cmd_template'] += f'.{facility.lower()}'
                    facility_ioc_dict.append(ioc)

        logging.info(f"facility_ioc_dict: {facility_ioc_dict}")
        playbook_args_dict['ioc_list'] = facility_ioc_dict # Update ioc list for each facility    
        playbook_args_dict['facility'] = facility
        
        playbook_args = json.dumps(playbook_args_dict) # Convert dictionary to JSON string
        stdout, stderr, return_code = ansible_api.run_ansible_playbook(INVENTORY_FILE_PATH, ioc_playbooks_path + '/ioc_deploy.yml',
                                    facility, playbook_args, return_output=True, no_color=True, check_mode=ioc_to_deploy.dry_run)
        # Combine output
        current_output = ""
        current_output += "== Deployment output for " + facility + ' ==\n\n' + stdout
        deployment_success = True
        if (return_code != 0):
            status = 400 # Deployment failed
            if (stderr != ''):
                current_output += "\n== Errors ==\n\n" + stderr
                deployment_success = False
        deployment_output += current_output
    
        if (not ioc_to_deploy.dry_run):
            # Write new configuration to deployment db for each facility
            # Determine new component if current facility is in new_component_facilities
            update_db_after_deployment(
                deployment_success, 
                new_component,
                facility, 
                'ioc', 
                ioc_to_deploy.component_name,
                ioc_to_deploy.tag, 
                ioc_to_deploy.user, 
                current_output, 
                facilities_ioc_dict[facility]
            )
        
    # Error check - If deployment output is empty, then nothing was deployed
    if (deployment_output == ""):
        return JSONResponse(content={"payload": {"Error": "No deployments performed. This may be due to empty IOC lists or invalid component/facility combinations."}}, status_code=400)

    # Generate summary for report
    summary = generate_report(ioc_to_deploy.component_name, ioc_to_deploy.tag, ioc_to_deploy.user, 
                            deployment_output, status, deployment_report_file, facilities_ioc_dict, ioc_to_deploy.dry_run)

    # Return ansible playbook output to user
    if os.getenv('PYTHON_TESTING') == 'True':
        content = summary
        return Response(content=content, media_type="text/plain", status_code=status)
    else:
        return FileResponse(path=deployment_report_file, status_code=status)
    
@app.put("/pydm/deployment")
async def deploy_pydm(pydm_to_deploy: PydmDict, background_tasks: BackgroundTasks):
    """
    Function to deploy a pydm "screen/display" component
    """
    # 1) Setup temporary directory for deployment contents
    request_id = str(uuid.uuid4())
    temp_download_dir = f"{APP_PATH}/tmp/{request_id}"
    os.makedirs(temp_download_dir, exist_ok=True)
    logging.info(f"New deployment request data: {pydm_to_deploy}")
    pydm_playbooks_path = ANSIBLE_PLAYBOOKS_PATH + 'pydm_module'
    # 2) Call to backend to get component/tag from github releases
    if (not download_release(pydm_to_deploy.component_name, pydm_to_deploy.tag, temp_download_dir, all_os=False)):
        return JSONResponse(content={"payload": {"Error": "Deployment tag may not exist or software factory backend is broken"}}, status_code=400)

    # 3) Logic for special cases
    facilities = pydm_to_deploy.facilities

    # Special case - if adding new deployment
    deploy_new_component = False
    # If adding to multiple facilities, loop through them
    for facility in facilities:
        # Check if deployment already exists
        component = find_component_in_facility(facility, pydm_to_deploy.component_name)
        logging.debug(f"component: {component}")
        if (component):
            deploy_new_component = False
        else:
            # Otherwise create a new entry to deployment database
            deploy_new_component = True
    logging.debug(f"deploy_new_component: {deploy_new_component}")

    tarball = f'{pydm_to_deploy.tag}.tar.gz'
    tarball_filepath = os.path.join(temp_download_dir, tarball)
    
    # in the loop below copy the ioc_dict, but only get the iocs within that facility (facilities_ioc_dict[facility])
    # 4) Call the appropriate ansible playbook for each applicable facility 
    playbook_args_dict = pydm_to_deploy.model_dump()
    playbook_args_dict['tarball'] = tarball_filepath
    status = 200
    deployment_report_file = temp_download_dir + '/deployment-report-' + pydm_to_deploy.component_name + '-' + pydm_to_deploy.tag + '.log'
    deployment_output = ""
    for facility in facilities:
        logging.info(f"facility: {facility}")
        # 5) If component doesn't exist in facility and not a new component, then skip.
        if (not deploy_new_component and find_component_in_facility(facility, pydm_to_deploy.component_name) is None):
            continue

        playbook_args_dict['facility'] = facility
    # TODO: - may want to do a dry run first to see if there would be any fails.
        playbook_args = json.dumps(playbook_args_dict) # Convert dictionary to JSON string
        stdout, stderr, return_code = ansible_api.run_ansible_playbook(INVENTORY_FILE_PATH, pydm_playbooks_path + '/pydm_deploy.yml',
                                        facility, playbook_args, return_output=True, no_color=True, check_mode=pydm_to_deploy.dry_run)
        # 5.1) Combine output
        current_output = ""
        current_output += "== Deployment output for " + facility + ' ==\n\n' + stdout
        deployment_success = True
        if (return_code != 0):
            status = 400 # Deployment failed
            if (stderr != ''):
                current_output += "\n== Errors ==\n\n" + stderr
                deployment_success = False
        deployment_output += current_output


        if (not pydm_to_deploy.dry_run):
            # 6) Write new configuration to deployment db for each facility
            update_db_after_deployment(deployment_success, deploy_new_component, facility, 'pydm', pydm_to_deploy.component_name,
                                        pydm_to_deploy.tag, pydm_to_deploy.user, current_output)
    
    # Error check - If deployment output is empty, then the component can't be found in deployment database
    if (deployment_output == ""):
        return JSONResponse(content={"payload": {"No deployments performed. This may be due to invalid component/facility combinations"}}, status_code=400)
    
    # 6) Generate summary for report
    summary = generate_report(pydm_to_deploy.component_name, pydm_to_deploy.tag, pydm_to_deploy.user,
                            deployment_output, status, deployment_report_file, dry_run=pydm_to_deploy.dry_run)
    # Add cleanup
    background_tasks.add_task(cleanup_temp_deployment_dir, temp_download_dir)

    # 7) Return ansible playbook output to user
    if os.getenv('PYTHON_TESTING') == 'True':
        content = summary
        return Response(content=content, media_type="text/plain", status_code=status)
    else:
        return FileResponse(path=deployment_report_file, status_code=status)
    
@app.put("/initial/deployment")
async def initial_deployment(initial_deployment: InitialDeploymentDict):
    """
    Function to add an initial deployment to the database (Does not deploy - only adds to database)
    This endpoint is intended to be used by software factory admins only
    """
    # Check if component already exists in deployment database
    component = find_component_in_facility(initial_deployment.facility, initial_deployment.component_name)
    if (component): return JSONResponse(content={"payload": {"Error": "Deployment already exists in deployment configuration/database"}}, status_code=400)

    # add an entry to deployment database
    timestamp = datetime.now().isoformat()
    new_component = { "name": initial_deployment.component_name,
        "facility": initial_deployment.facility,
        "tag": initial_deployment.tag,
        "type": initial_deployment.type,
    }
    new_component['dependsOn'] = initial_deployment.ioc_list
    logging.debug(f"new_component: {new_component}")
    endpoint = BACKEND_URL + 'deployments'
    response = requests.post(endpoint, json=new_component)
    add_log_to_component(initial_deployment.facility, timestamp, initial_deployment.user,
                          initial_deployment.component_name, "Initial deployment entry added by software factory admins")
    return JSONResponse(content={"payload": {"Success": "Deployment added to database"}}, status_code=200)

if __name__ == "__main__":
    uvicorn.run('deployment_controller:app', host='0.0.0.0', port=8080, timeout_keep_alive=180)
    # timeout_keep_alive set to 180 seconds, in case deployment takes longer than usual
    # deployment_controller refers to file, and app is the app=fastapi()