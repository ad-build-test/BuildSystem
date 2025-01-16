"""
Desc: Deployment controller, handles deployments

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
from artifact_api import ArtifactApi

import uvicorn
import json
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel
from datetime import datetime, timezone, timedelta
from copy import deepcopy

"""
Ex api request - curl -X 'GET' 'http://172.24.8.139/' -H 'accept: application/json'
curl -X 'GET' 'https://ad-build-dev.slac.stanford.edu/api/deployment/' -H 'accept: application/json'
"""

app = FastAPI(debug=False, title="Deployment_controller", version='1.0.0')
logging.basicConfig(
    level=logging.INFO, # TODO: Change this to NOTSET when use in production
    format="%(levelname)s-%(name)s:[%(filename)s:%(lineno)s - %(funcName)s() ] %(message)s")

ANSIBLE_PLAYBOOKS_PATH = "/mnt/eed/ad-build/build-system-playbooks/"
INVENTORY_FILE_PATH = ANSIBLE_PLAYBOOKS_PATH + 'deployment_controller_inventory.ini'
CONFIG_FILE_PATH = ANSIBLE_PLAYBOOKS_PATH + "deployment_destinations.yaml"
SCRATCH_FILEPATH = "/mnt/eed/ad-build/scratch"

yaml = YAML()
yaml.default_flow_style = False  # Make the output more readable

artifact_api = ArtifactApi()

class IocDict(BaseModel):
    facilities: list = None # Optional
    component_name: str
    tag: str
    ioc_list: list
    user: str

class TagDict(BaseModel):
    component_name: str
    branch: str
    results: str
    tag: str
    user: str

# TODO: Possible to just use IocDict but would have to make fields optional
    # And making the fields optional may not be good. 
class BasicIoc(BaseModel):
    component_name: str

def parse_yaml(filename: str) -> dict:
    with open(filename, 'r') as file:
        yaml_data = yaml.load(file)
    return yaml_data

def update_yaml(filename: str, data: dict):
    with open(filename, 'w') as file:
        yaml.dump(data, file)

def update_component_in_facility(facility: str, timestamp: str, user: str, app_type: str,
                                  component_to_update: str, tag: str, ioc_list: list = None) -> bool:
    """
    Function to update a component in the deployment db
    """
    config_dict = parse_yaml(CONFIG_FILE_PATH)

    for component in config_dict[facility][app_type]: # 1) Find the component
        if (component_to_update in component['name']):
            # 1) Update tag in original config dict
            component['tag'] = tag

            # 2) Update iocs (if applicable)
            if (app_type == 'ioc'):
                for ioc in component['iocs']:
                    if (ioc['name'] in ioc_list):
                        ioc['tag'] = tag
            
            # 3) Update the history = current component + user + date
            history = deepcopy(component)
            del history['name'] # remove the name from the history
            del history['history'] # remove the history from the history
            history['tag'] = tag
            history['date'] = timestamp
            history['user'] = user
            component['history'].insert(0, history) # insert history at the front
    update_yaml(CONFIG_FILE_PATH, config_dict)
    return True

def find_component_in_facility(facility: str, app_type: str, component_to_find: str) -> dict:
    """ Function to return component information """
    config_dict = parse_yaml(CONFIG_FILE_PATH)
    facility_config = config_dict[facility][app_type]
    for component in facility_config:
        if (component_to_find in component['name']):
            return component
    return None

def find_facility_an_ioc_is_in(ioc_to_find: str, component_with_ioc: str) -> str:
    """ Function to return the facility that the ioc is in """
    for facility in get_facilities_list(): # Loop through each facility
        component = find_component_in_facility(facility, 'ioc', component_with_ioc)
        if (component):
            for ioc in component['iocs']: # Loop through each ioc
                if (ioc_to_find in ioc['name']):
                    return facility
    return None

def get_facilities_list() -> list:
    config_dict = parse_yaml(CONFIG_FILE_PATH)
    return config_dict.keys()

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

def generate_ioc_deployment_summary(component_name: str, tag: str, user: str, timestamp: str,
                                     deployment_report_file: str, facilities_ioc_dict: dict, deployment_output: str, status: int) -> int:
    summary = \
    f"""#### Deployment report for {component_name} - {tag}####
    \n#### Date: {timestamp}
    \n#### User: {user}
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
    return status

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

def extract_ioc_cpu_shebang_info(tarball_path: str, app_dir_name: str) -> dict:
    """ Function to extract tarball and process the st.cmd files """
    # 1) Open and extract the tarball
    extract_to_dir = '/app'
    with tarfile.open(tarball_path, "r:gz") as tar:
        tar.extractall(path=extract_to_dir)
        print(f"Extracted tarball to {extract_to_dir}")

    # 2) The directory containing 'iocBoot' is inside the app directory (app_dir_name)
    app_dir = os.path.join(extract_to_dir, app_dir_name)
    iocBoot_dir = os.path.join(app_dir, 'iocBoot')
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

    # 5) Remove untarred folder
    shutil.rmtree(app_dir)
    
    return results

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
    if (not artifact_api.get_component_from_registry('/app', ioc_to_deploy.component_name, ioc_to_deploy.tag, os_env='null', extract=False)):
        return JSONResponse(content={"payload": {"Error": "artifact storage api is unreachable"}}, status_code=400)
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
    tarball_filepath = '/app/' + ioc_to_deploy.tag + '.tar.gz'
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
    playbook_args_dict['playbook_path'] = '/sdf/group/ad/eed/ad-build/build-system-playbooks/ioc_module'
    playbook_args_dict['user_src_repo'] = None
    status = 200
    deployment_report_file = '/app/deployment-report-' + ioc_to_deploy.component_name + '-' + ioc_to_deploy.tag + '.log'
    deployment_output = ""
    logging.info(f"facilities: {facilities}")
    for facility in facilities:
        logging.info(f"facility: {facility}")
        logging.info(f"facilities_ioc_dict: {facilities_ioc_dict}")
        # 5) If component doesn't exist in facility, then skip. This assumes that the component exists in at least ONE facility                                     
        if (find_component_in_facility(facility, 'ioc', ioc_to_deploy.component_name) is None):
            continue
        if (ioc_to_deploy.ioc_list[0].upper() == 'ALL'):
            # 3.2) If ioc = 'ALL' then create list of iocs based on facility
            component_info = find_component_in_facility(facility, 'ioc', ioc_to_deploy.component_name)
            facilities_ioc_dict[facility].extend([ioc['name'] for ioc in component_info['iocs']])

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
        stdout, stderr, return_code = ansible_api.run_ansible_playbook(INVENTORY_FILE_PATH, ioc_playbooks_path + '/ioc_deploy.yml',
                                        facility, playbook_args, return_output=True, no_color=True)
        # 5.1) Combine output
        deployment_output += "== Deployment output for " + facility + ' ==\n\n' + stdout
        if (return_code != 0):
            status = 400 # Deployment failed
            if (stderr != ''):
                deployment_output += "\n== Errors ==\n\n" + stderr
    
        # 6) Write new configuration to deployment db for each facility
        timezone_offset = -8.0  # Pacific Standard Time (UTC−08:00)
        tzinfo = timezone(timedelta(hours=timezone_offset))
        timestamp = datetime.now(tzinfo).isoformat()
        update_component_in_facility(facility, timestamp, ioc_to_deploy.user, 'ioc', ioc_to_deploy.component_name,
                                     ioc_to_deploy.tag, facilities_ioc_dict[facility])
    logging.info('Generating summary/report...')
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