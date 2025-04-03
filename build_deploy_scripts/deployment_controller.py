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
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse, FileResponse, Response
from pydantic import BaseModel
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
FACILITIES = ['LCLS', 'FACET', 'TESTFAC', 'DEV', 'S3DF']

yaml = YAML()
yaml.default_flow_style = False  # Make the output more readable

# pydantic models =================================================================================
class Component(BaseModel):
    component_name: str

class IocDict(Component):
    facilities: list = None # Optional
    tag: str
    ioc_list: list
    user: str
    new: bool

class PydmDict(Component):
    facilities: list = None # Optional
    tag: str
    user: str
    new: bool

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
    if (ioc_list):
        new_depends_on_list = [{'name': ioc, 'tag': tag} for ioc in ioc_list]
        logging.debug(f"new_depends_on_list: {new_depends_on_list}")
        new_component['dependsOn'] = new_depends_on_list
    
    logging.debug(f"new_component: {new_component}")
    endpoint = BACKEND_URL + 'deployments'
    response = requests.post(endpoint, json=new_component)
    return True

def update_component_in_facility(facility: str, app_type: str, component_to_update: str,
                                  tag: str, ioc_list: list = None, new: bool = False) -> bool:
    """
    Function to update a component in the deployment db
    Note - new here is different than add_new_component(), because this assumes the component exists,
         but a new ioc(s) wants to be added
    """
    # 1) Find the component
    component = find_component_in_facility(facility, component_to_update)
    if (component is None):
        return False
    # 2) Update tag in original config dict
    component['tag'] = tag
    # 3) Update iocs (if applicable)
    if (app_type == 'ioc'):
        if (new): # If new component then add the new iocs
            new_depends_on_list = [{'name': ioc, 'tag': tag} for ioc in ioc_list]
            component['dependsOn'].extend(new_depends_on_list)
            logging.debug(new_depends_on_list)
        else:
            for ioc in component['dependsOn']:
                if (ioc['name'] in ioc_list):
                    ioc['tag'] = tag
    # 4) Update component in db
    logging.debug(component)
    endpoint = BACKEND_URL + f'deployments/{component_to_update}/{facility}'
    response = requests.put(endpoint, json=component)
    logging.debug(f"response.json(): {response.json()}")
    return True

def find_component_in_facility(facility: str, component_to_find: str) -> dict:
    """ Function to return component information """
    endpoint = BACKEND_URL + f'deployments/{component_to_find}/{facility}'
    logging.debug(f"find_component_in_facility endpoint: {endpoint}")
    response = requests.get(endpoint)
    if (response.ok):
        return response.json()['payload']
    else: 
        return None

def find_facility_an_ioc_is_in(ioc_to_find: str, component_with_ioc: str) -> str:
    """ Function to return the facility that the ioc is in """
    for facility in FACILITIES: # Loop through each facility
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

@contextmanager
def deployment_release_manager():
    """ Context manager for safe cleanup of temporary files (mainly the tarball for the tagged release). 
        With this, the temporary files will be deleted even if exceptions are thrown """
    # Create unique directory for this request
    request_id = str(uuid.uuid4())
    temp_download_dir = f"{APP_PATH}/tmp/{request_id}"
    try:
        # Create temp directory
        os.makedirs(temp_download_dir, exist_ok=True)
        yield temp_download_dir
    finally:
        # Clean up everything
        if os.path.exists(temp_download_dir):
            logging.info(f"Cleaning up temporary directory: {temp_download_dir}")
            shutil.rmtree(temp_download_dir, ignore_errors=True)

def download_release(component_name: str, tag: str, download_dir: str, extract_tarball: bool = None):
    """ Download a components tagged release from the backend -> github """
    endpoint = BACKEND_URL + f'component/{component_name}/release/{tag}'
    tarball = f'{tag}.tar.gz'
    response = requests.get(endpoint)
    # Download file from api, and extract to download_dir
    # Download the .tar.gz file
    tarball_filepath = os.path.join(download_dir, tarball)
    if response.status_code == 200:
        # Download response to tarball file
        stream_size = 1024*1024 # Write in chunks (1MB) since tarball can be big
        with open(tarball_filepath, 'wb') as file: 
            for chunk in response.iter_content(chunk_size=stream_size): 
                if (chunk):
                    file.write(chunk)
        logging.info('Tarball downloaded successfully')
        if (extract_tarball):
            # Extract the .tar.gz file
            logging.info('Extracting tarball...')
            with tarfile.open(tarball_filepath, 'r:gz') as tar:
                tar.extractall(path=download_dir)
            logging.info(f'{tarball_filepath} extracted to {download_dir}')
            return True
    else:
        logging.info(f'Failed to retrieve the file. Status code: {response.status_code}')
        return False

def write_file(filepath: str, content: str):
    with open(filepath, 'w') as file:
        file.write(content)

def generate_report(component_name: str, tag: str, user: str, deployment_output: str, status: int, deployment_report_file: str, facilities_ioc_dict: dict=None):
    """ Generate a deployment report """
    timezone_offset = -8.0  # Pacific Standard Time (UTC−08:00)
    tzinfo = timezone(timedelta(hours=timezone_offset))
    timestamp = datetime.now(tzinfo).isoformat()
    summary = \
f"""#### Deployment report for {component_name} - {tag} ####
#### Date: {timestamp}
#### User: {user}"""
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
    facilities = FACILITIES
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
async def deploy_ioc(ioc_to_deploy: IocDict):
    """
    Function to deploy an ioc component
    """
    # 1) Setup context manager
    with deployment_release_manager() as temp_download_dir:
        logging.info(f"New deployment request data: {ioc_to_deploy}")
        ioc_playbooks_path = ANSIBLE_PLAYBOOKS_PATH + 'ioc_module'
        # 2) Call to backend to get component/tag from github releases
        if (not download_release(ioc_to_deploy.component_name, ioc_to_deploy.tag, temp_download_dir, extract_tarball=True)):
            return JSONResponse(content={"payload": {"Error": "Deployment tag may not exist or software factory backend is broken"}}, status_code=400)

        # Special case - if adding new deployment
        deploy_new_iocs = False
        new_iocs = []
        deploy_new_component = False
        if (ioc_to_deploy.new):
            # Ensure only one facility is specified (ex: bs deploy --ioc sioc-b34-test1 --facility DEV )
            # Only one because how would we know which ioc belongs to what facility?
            if (len(ioc_to_deploy.facilities) == 1):
                # Check if deployment already exists
                component = find_component_in_facility(ioc_to_deploy.facilities[0], ioc_to_deploy.component_name)
                logging.debug(f"component: {component}")
                if (component):
                    # Extract ioc names from dictionaries
                    existing_iocs = {ioc["name"] for ioc in component['dependsOn']}

                    # Find iocs that are in user list but not in existing deployment
                    new_iocs = [ioc for ioc in ioc_to_deploy.ioc_list if ioc not in existing_iocs]
                    logging.debug(f"new_iocs: {new_iocs}")
                    if (new_iocs == None):
                        # Check if both the deployment and iocs exist, then return error to user.
                        return JSONResponse(content={"payload": {"Error": "Deployment and iocs already exist in deployment configuration/database"}}, status_code=400)
                    else:
                    # else user is trying to add a new ioc to 'dependsOn'
                        deploy_new_iocs = True
                else:
                    # Otherwise create a new entry to deployment database
                    deploy_new_component = True
        logging.debug(f"deploy_new_component: {deploy_new_component}")

        # 3) Logic for special cases
        facilities = ioc_to_deploy.facilities
        facilities_ioc_dict = dict.fromkeys(facilities, [])
        
        if (deploy_new_iocs): # set the ioc dict to new_iocs
            facilities_ioc_dict[facilities[0]] = new_iocs
        elif (deploy_new_component): # Add brand new iocs 
            facilities_ioc_dict[facilities[0]] = ioc_to_deploy.ioc_list
        # 3.1) If not 'ALL' Figure out what facilities the iocs belong to
        elif (ioc_to_deploy.ioc_list[0].upper() != 'ALL'):
                for ioc in ioc_to_deploy.ioc_list:
                    facility = find_facility_an_ioc_is_in(ioc, ioc_to_deploy.component_name)
                    if (facility == None): # Means ioc doesnt exist (typo on user end)
                        return JSONResponse(content={"payload": {"Error": "ioc not found - " + ioc}}, status_code=400)
                    facilities_ioc_dict[facility].append(ioc)
        # 3.2) Find the info needed to create the startup.cmd for each ioc
        extracted_tarball_filepath = os.path.join(temp_download_dir, ioc_to_deploy.tag)
        ioc_info = extract_ioc_cpu_shebang_info(extracted_tarball_filepath)
        tarball_filepath = extracted_tarball_filepath + '.tar.gz'
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
        playbook_args_dict['playbook_path'] = ioc_playbooks_path
        playbook_args_dict['user_src_repo'] = None
        status = 200
        deployment_report_file = temp_download_dir + '/deployment-report-' + ioc_to_deploy.component_name + '-' + ioc_to_deploy.tag + '.log'
        deployment_output = ""
        for facility in facilities:
            logging.info(f"facility: {facility}")
            logging.info(f"facilities_ioc_dict: {facilities_ioc_dict}")
            # 5) If component doesn't exist in facility, then skip. This assumes that the component exists in at least ONE facility                                     
            if (not deploy_new_component and find_component_in_facility(facility, ioc_to_deploy.component_name) is None):
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

            logging.info(f"facility_ioc_dict: {facility_ioc_dict}")
            playbook_args_dict['ioc_list'] = facility_ioc_dict # Update ioc list for each facility    
            playbook_args_dict['facility'] = facility
        # TODO: - may want to do a dry run first to see if there would be any fails.
            playbook_args = json.dumps(playbook_args_dict) # Convert dictionary to JSON string
            stdout, stderr, return_code = ansible_api.run_ansible_playbook(INVENTORY_FILE_PATH, ioc_playbooks_path + '/ioc_deploy.yml',
                                            facility, playbook_args, return_output=True, no_color=True)
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
        
            # 6) Write new configuration to deployment db for each facility
            timestamp = datetime.now().isoformat()
        # TODO: Add checks if any database operations fail, then bail and return to user
            # Special case - If new then add the new component
            if (deployment_success):
                if (deploy_new_component):
                    logging.debug("Adding new component")
                    add_new_component(facility, 'ioc', ioc_to_deploy.component_name, ioc_to_deploy.tag, facilities_ioc_dict[facility])
                else:
                    update_component_in_facility(facility, 'ioc', ioc_to_deploy.component_name, ioc_to_deploy.tag, facilities_ioc_dict[facility], ioc_to_deploy.new)
            add_log_to_component(facility, timestamp, ioc_to_deploy.user, ioc_to_deploy.component_name, current_output)
        
        # Error check - If deployment output is empty, then the component can't be found in deployment database
        if (deployment_output == ""):
            return JSONResponse(content={"payload": {"Error": "component not found in deployment database, name or facility is wrong or missing. Or component has never been deployed"}}, status_code=400)

        # 6) Generate summary for report
        summary = generate_report(ioc_to_deploy.component_name, ioc_to_deploy.tag, ioc_to_deploy.user, 
                                  deployment_output, status, deployment_report_file, facilities_ioc_dict)
        # 7) Return ansible playbook output to user
        if os.getenv('PYTHON_TESTING') == 'True':
            content = summary
            return Response(content=content, media_type="text/plain", status_code=status)
        else:
            return FileResponse(path=deployment_report_file, status_code=status)
    
@app.put("/pydm/deployment")
async def deploy_pydm(pydm_to_deploy: PydmDict):
    """
    Function to deploy a pydm "screen/display" component
    """
    # 1) Setup context manager
    with deployment_release_manager() as temp_download_dir:
        logging.info(f"New deployment request data: {pydm_to_deploy}")
        pydm_playbooks_path = ANSIBLE_PLAYBOOKS_PATH + 'pydm_module'
        # 2) Call to backend to get component/tag from github releases
        if (not download_release(pydm_to_deploy.component_name, pydm_to_deploy.tag, temp_download_dir)):
            return JSONResponse(content={"payload": {"Error": "Deployment tag may not exist or software factory backend is broken"}}, status_code=400)

        # 3) Logic for special cases
        facilities = pydm_to_deploy.facilities

        # Special case - if adding new deployment
        deploy_new_component = False
        if (pydm_to_deploy.new):
            # If adding to multiple facilities, loop through them
            for facility in facilities:
                # Check if deployment already exists
                component = find_component_in_facility(facility, pydm_to_deploy.component_name)
                logging.debug(f"component: {component}")
                if (component):
                    # then return error to user.
                    return JSONResponse(content={"payload": {"Error": "Deployment already exists in deployment configuration/database"}}, status_code=400)
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
        playbook_args_dict['playbook_path'] = pydm_playbooks_path
        playbook_args_dict['user_src_repo'] = None
        status = 200
        deployment_report_file = temp_download_dir + '/deployment-report-' + pydm_to_deploy.component_name + '-' + pydm_to_deploy.tag + '.log'
        deployment_output = ""
        for facility in facilities:
            logging.info(f"facility: {facility}")
            # 5) If component doesn't exist in facility, then skip. This assumes that the component exists in at least ONE facility                                     
            if (not deploy_new_component and find_component_in_facility(facility, pydm_to_deploy.component_name) is None):
                continue

            playbook_args_dict['facility'] = facility
        # TODO: - may want to do a dry run first to see if there would be any fails.
            playbook_args = json.dumps(playbook_args_dict) # Convert dictionary to JSON string
            stdout, stderr, return_code = ansible_api.run_ansible_playbook(INVENTORY_FILE_PATH, pydm_playbooks_path + '/pydm_deploy.yml',
                                            facility, playbook_args, return_output=True, no_color=True)
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
        
            # 6) Write new configuration to deployment db for each facility
            timestamp = datetime.now().isoformat()
        # TODO: Add checks if any database operations fail, then bail and return to user
            # Special case - If new then add the new component
            if (deployment_success):
                if (deploy_new_component):
                    logging.debug("Adding new component")
                    add_new_component(facility, 'pydm', pydm_to_deploy.component_name, pydm_to_deploy.tag)
                else:
                    update_component_in_facility(facility, 'pydm', pydm_to_deploy.component_name, pydm_to_deploy.tag, new=pydm_to_deploy.new)
            add_log_to_component(facility, timestamp, pydm_to_deploy.user, pydm_to_deploy.component_name, current_output)
        
        # Error check - If deployment output is empty, then the component can't be found in deployment database
        if (deployment_output == ""):
            return JSONResponse(content={"payload": {"Error": "component not found in deployment database, name or facility is wrong or missing. Or component has never been deployed"}}, status_code=400)
        
        # 6) Generate summary for report
        summary = generate_report(pydm_to_deploy.component_name, pydm_to_deploy.tag, pydm_to_deploy.user,
                                deployment_output, status, deployment_report_file)
        # 7) Return ansible playbook output to user
        if os.getenv('PYTHON_TESTING') == 'True':
            content = summary
            return Response(content=content, media_type="text/plain", status_code=status)
        else:
            return FileResponse(path=deployment_report_file, status_code=status)

if __name__ == "__main__":
    uvicorn.run('deployment_controller:app', host='0.0.0.0', port=8080, timeout_keep_alive=180)
    # timeout_keep_alive set to 180 seconds, in case deployment takes longer than usual
    # deployment_controller refers to file, and app is the app=fastapi()