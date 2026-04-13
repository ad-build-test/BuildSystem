"""
Desc: Deployment controller, handles deployments

Usage: python3 deployment_controller.py
note - this would have to run 24/7 as a service
"""
import os
import shutil
import uuid
from ruamel.yaml import YAML # Using ruamel instead of pyyaml because it keeps the comments
import logging
import ansible_api
import tarfile
import requests

import redis
import uvicorn
import json
import time
import asyncio
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from dateutil import parser

"""
Ex api request
curl -X 'GET' 'https://ad-build-dev.slac.stanford.edu/api/deployment/' -H 'accept: application/json'
"""

app = FastAPI(debug=False, title="Deployment_controller", version='1.0.0')
logging.basicConfig(
    level=logging.DEBUG, # TODO: Change this to NOTSET when use in production
    format="%(levelname)s-%(name)s:[%(filename)s:%(lineno)s - %(funcName)s() ] %(message)s")

SCRATCH_FILEPATH = "/sdf/group/ad/eed/ad-build/scratch"
TEST_INVENTORY = False # This gets set to true in test_deployment_controller.py
is_prod = os.environ.get("AD_BUILD_PROD", "false").lower() in ("true", "1", "yes", "y")
if is_prod: 
    BACKEND_URL = "https://ad-build.slac.stanford.edu/api/cbs/v1/"
    ELOG_ENDPOINT = "https://accel-webapp.slac.stanford.edu/api/elog-apptoken/v1/entries"
    ANSIBLE_PLAYBOOKS_PATH = "/sdf/group/ad/eed/ad-build/build-system-playbooks/"
    ELOG_URL_PREFIX = "https://accel-webapp.slac.stanford.edu/elog/"
    ELOG_URL_POSTFIX = "?logbooks=sw_log"
else: 
    BACKEND_URL = "https://ad-build-dev.slac.stanford.edu/api/cbs/v1/"
    ELOG_ENDPOINT = "https://accel-webapp-dev.slac.stanford.edu/api/elog-apptoken/v1/entries"
    ANSIBLE_PLAYBOOKS_PATH = "/sdf/group/ad/eed/ad-build/dev-build-system-playbooks/"
    ELOG_URL_PREFIX = "https://accel-webapp-dev.slac.stanford.edu/elog/"
    ELOG_URL_POSTFIX = "?logbooks=sw_log"

ELOG_USER_PASSWORD = os.getenv("ELOG_USER_PASSWORD")
ELOG_SW_LOG_ID = os.getenv("ELOG_SW_LOG_ID")
if (ELOG_USER_PASSWORD == None):
    raise ValueError("Missing environment variable - ELOG_USER_PASSWORD")
if (ELOG_SW_LOG_ID == None):
    raise ValueError("Missing environment variable - ELOG_SW_LOG_ID")
ELOG_HEADERS = {"x-vouch-idp-accesstoken": ELOG_USER_PASSWORD}

APP_PATH = "/app"
REQUEST_TIMEOUT = 60  # seconds, for all external HTTP calls

# Container deployment secrets are loaded per-app from environment variables.
# Naming convention: CONTAINER_{APP_KEY}_{SECRET}
# where APP_KEY = component_name uppercased with hyphens replaced by underscores
def get_container_secrets(component_name: str) -> dict:
    """Load per-app container secrets from environment variables."""
    app_key = component_name.upper().replace("-", "_")
    return {
        'database_url': os.getenv(f"CONTAINER_{app_key}_DATABASE_URL", ""),
        'redis_url': os.getenv(f"CONTAINER_{app_key}_REDIS_URL", ""),
        'ghcr_token': os.getenv(f"CONTAINER_{app_key}_GHCR_TOKEN", ""),
        'ghcr_user': os.getenv(f"CONTAINER_{app_key}_GHCR_USER", ""),
    }
# NOTE - ORDER MATTERS (Last item on the list "wins" if there are overlapping files when deploying for multiple OS)
# Please make sure latest OS is the last item.
USED_OS_LIST = ["rhel7", "rocky9"] 

FACILITIES_LIST = ["LCLS", "FACET", "TESTFAC", "DEV", "SANDBOX"]

yaml = YAML()
yaml.default_flow_style = False  # Make the output more readable

class DeploymentTask:
    def __init__(self, task_id, save_callback=None):
        self.task_id = task_id
        self.save_callback = save_callback
        self.status = "pending"
        self.progress = {"current_step": "Initializing", "percent": 0}
        self.started_at = datetime.now().isoformat()
        self.updated_at = self.started_at
        self.temp_dir = None
        self.result = None
        self.error = None

    def update_progress(self, step: str, percent: int, details: str = None):
        self.progress = {"current_step": step, "percent": percent, "details": details}
        self.updated_at = datetime.now().isoformat()
        self.status = "running"
        if self.save_callback:
            self.save_callback(self)  # Auto-save
    
    def complete(self, result):
        self.status = "completed"
        self.result = result
        self.progress["percent"] = 100
        if self.save_callback:
            self.save_callback(self)  # Auto-save
    
    def fail(self, error):
        self.status = "failed"
        self.error = error
        self.updated_at = datetime.now().isoformat()
        if self.save_callback:
            self.save_callback(self)  # Auto-save
        
# Redis for storing task information
redis_client = redis.Redis(
    host='redis',  # k8s service name
    port=6379,
    decode_responses=True,
    db=0
)

def save_task(task: DeploymentTask):
    """Save task to Redis"""
    task_dict = {
        "task_id": task.task_id,
        "status": task.status,
        "progress": task.progress,
        "started_at": task.started_at,
        "updated_at": task.updated_at,
        "result": task.result,
        "error": task.error
    }
    # Auto-expire after 10 mins
    redis_client.setex(f"task:{task.task_id}", 600, json.dumps(task_dict))

def get_task(task_id: str) -> DeploymentTask:
    """Load task from Redis"""
    data = redis_client.get(f"task:{task_id}")
    if not data:
        return None
    
    task_dict = json.loads(data)
    task = DeploymentTask(task_dict["task_id"], save_callback=save_task)
    task.status = task_dict["status"]
    task.progress = task_dict["progress"]
    task.result = task_dict["result"]
    task.error = task_dict["error"]
    # Restore datetime fields if needed
    return task

# pydantic models =================================================================================
class Component(BaseModel):
    component_name: str

class RevertDict(Component):
    user: str
    facility: str
    ioc_list: Optional[list] = None
    reboot_iocs: Optional[bool] = False

class DeployDict(Component):
    """Unified deployment request model. The playbook field determines app type and which
    Ansible playbook runs. Special logic is applied for ioc_module and pydm_module playbooks;
    everything else uses the generic handler (download release → run playbook)."""
    tag: str
    user: str
    playbook: str                          # e.g. "ioc_module/ioc_deploy.yml"
    facilities: Optional[list] = None
    dry_run: Optional[bool] = False
    return_elog: Optional[bool] = False
    # IOC-specific
    ioc_list: Optional[list] = None
    reboot_iocs: Optional[bool] = False
    # PyDM-specific
    subsystem: Optional[str] = ""
    # Container-specific
    force_deploy: Optional[bool] = False
    docker_network: Optional[str] = None
    migration_command: Optional[str] = None
    health_check_path: Optional[str] = "/health"
    database_url: Optional[str] = None
    redis_url: Optional[str] = None
    ghcr_token: Optional[str] = None
    ghcr_user: Optional[str] = None
    # Artifact-based deployments (e.g. Tauri desktop apps)
    artifact_url: Optional[str] = None     # GitHub release asset URL
    artifact_type: Optional[str] = None    # rpm, tar, zip
    # Generic extra vars forwarded to the playbook as-is
    extra_vars: Optional[dict] = None

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
    response = requests.post(endpoint, json=deployment_log, timeout=REQUEST_TIMEOUT)
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
    response = requests.post(endpoint, json=new_component, timeout=REQUEST_TIMEOUT)
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
    response = requests.put(endpoint, json=component, timeout=REQUEST_TIMEOUT)
    logging.debug(f"response.json(): {response.json()}")
    return True

def find_component_in_facility(facility: str, component_to_find: str) -> dict:
    """ Function to return component information """
    endpoint = BACKEND_URL + f'deployments/{component_to_find}/{facility}'
    response = requests.get(endpoint, timeout=REQUEST_TIMEOUT)
    if (response.ok):
        return response.json()['payload']
    else: 
        return None

def find_recent_deployment_for_component_facility(facility: str, component_to_find: str, deployment_index: int) -> dict:
    """ Function to return recent deployment information 
        deployment_index: 0 is the most recent, 1 is second most recent, etc.
    """
    endpoint = BACKEND_URL + f'deployments/{component_to_find}/{facility}/logs'
    response = requests.get(endpoint, timeout=REQUEST_TIMEOUT)
    if (response.ok):
        payload = response.json()['payload']
    else: 
        logging.debug(f"Unable to find deployment for {component_to_find}, at {facility}, at index {deployment_index}")
        return None
    # Check if we have at least 2 deployments occured
    if len(payload) < 2:
        return {}  # or raise an exception if you prefer
    
    # Sort by logDate in descending order (most recent first)
    sorted_payload = sorted(payload, 
                        key=lambda deployment: parser.parse(deployment['logDate']), 
                        reverse=True)
    
    return sorted_payload[deployment_index]

def find_facility_an_ioc_is_in(ioc_to_find: str, component_with_ioc: str) -> list:
    """ Function to return the facility(s) that the ioc is in """
    facilities_the_ioc_exist_in = []
    for facility in FACILITIES_LIST: # Loop through each facility
        component = find_component_in_facility(facility, component_with_ioc)
        if (component):
            for ioc in component['dependsOn']: # Loop through each ioc
                if (ioc_to_find in ioc['name']):
                    facilities_the_ioc_exist_in.append(facility)
    return facilities_the_ioc_exist_in

def extract_date(entry) -> datetime:
    return datetime.fromisoformat(entry['date'])

def create_tarball(directory, tag):
    tarball_name = f"{tag}.tar.gz"
    try:
        with tarfile.open(tarball_name, "w:gz") as tar:
            tar.add(directory, arcname=os.path.basename(directory))
        logging.debug(f"Created tarball: {tarball_name}")
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
        logging.warning(f"Invalid path structure in shebang line: {shebang_line}")
        return None, None

def extract_ioc_cpu_shebang_info(app_dir_name: str) -> dict:
    """ Function to process the st.cmd files """
    # 1) Open and extract the tarball
    # The directory containing 'iocBoot' is inside the app directory (app_dir_name)
    iocBoot_dir = os.path.join(app_dir_name, 'iocBoot')
    # TODO: Need to check cpuBoot as well

    # 3) Check if the iocBoot directory exists
    if not os.path.exists(iocBoot_dir):
        logging.error(f"Directory {iocBoot_dir} does not exist in the extracted files.")
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
                logging.warning(f"No shebang line in {st_cmd_path}")
    
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
    response = requests.get(endpoint, timeout=REQUEST_TIMEOUT)
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
        logging.debug(f'download tarball: {tarball_filepath}')
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

def get_inventory_path() -> str:
    """Return the Ansible inventory file path based on TEST_INVENTORY flag."""
    suffix = 'test_inventory.ini' if TEST_INVENTORY else 'global_inventory.ini'
    return ANSIBLE_PLAYBOOKS_PATH + suffix

def finalize_deployment(component_name: str, tag: str, user: str, facilities: list,
                        deployment_output: str, status: int, deployment_success: bool,
                        deployment_report_file: str, dry_run: bool,
                        facilities_ioc_dict: dict = None) -> dict:
    """Generate deployment report, write to ELOG, and return the standard result dict."""
    summary = generate_report(component_name, tag, user, deployment_output, status,
                              deployment_report_file, facilities_ioc_dict, dry_run)
    elog_url = ""
    if not dry_run:
        elog_url = send_deployment_to_elog(component_name, tag, facilities, summary) or ""
    return {"summary": summary, "report_file": deployment_report_file,
            "status": status, "success": deployment_success, "elog_url": elog_url}

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
        summary += "\n#### Overall status: Success\n\n" + deployment_output
    else: # Failure
        status = 400
        summary += "\n#### Overall status: Failure - PLEASE REVIEW\n\n" + deployment_output
    logging.debug(deployment_report_file)
    write_file(deployment_report_file, summary)
    logging.debug(summary)
    return summary

def send_deployment_to_elog(component_name: str, tag: str, facilities: list, summary_report: str):
    """
    Writes processed data to ELOG backend API based on the message type
    """
    logging.debug(f"Writing to the ELOG (SW_LOG) logbook through backend API for: {component_name} - {tag}")

    title = f"Deployment: {component_name} - {tag} {facilities}"
    text = f"<pre>{summary_report}</pre>"

    # Construct the payload
    payload = {
        "logbooks": [ELOG_SW_LOG_ID],
        "title": title,
        "text": text,
        "note": "",
        "attachments": [],
        # "summarizes": { # We can skip this field
        #     "shiftId": "",
        #     "date": summary_date
        # },
        # "eventAt": event_at,
        "userIdsToNotify": []
    }

    # Send the request
    try:
        logging.debug(f"Sending request to: {ELOG_ENDPOINT}")
        response = requests.post(ELOG_ENDPOINT, headers=ELOG_HEADERS, json=payload, timeout=REQUEST_TIMEOUT)
        
        logging.debug(f"Response status code: {response.status_code}")
        logging.debug(f"Response headers: {response.headers}")
        
        # Try to raise for status
        response.raise_for_status()
        
        logging.debug(f"Successfully sent to ELOG API: {response.status_code}")
        logging.debug(f"response: {response}")
        logging.debug(f"response payload: {response.json()['payload']}")
        elog_url = ELOG_URL_PREFIX + response.json()['payload'] + ELOG_URL_POSTFIX
        return elog_url
    except requests.exceptions.HTTPError as http_err:
        logging.error(f"HTTP Error: {http_err}")
        
        # Print detailed response information
        logging.error(f"Response status code: {response.status_code}")
        logging.error(f"Response reason: {response.reason}")
        
        # Try to get response text (may contain error details)
        try:
            logging.error(f"Response text: {response.text}")
        except:
            logging.error("Could not get response text")
        
        # Try to parse JSON response (may contain error details)
        try:
            logging.debug(f"Response JSON: {response.json()}")
        except:
            logging.error("Response is not valid JSON")
        
        logging.debug(f"Request URL: {response.request.url}")
        logging.debug(f"Request method: {response.request.method}")
        logging.debug(f"Request headers: {response.request.headers}")
        logging.debug(f"Request body: {response.request.body}")
        
        return False
    except requests.exceptions.ConnectionError as conn_err:
        logging.error(f"Connection Error: {conn_err}")
        return False
    except requests.exceptions.Timeout as timeout_err:
        logging.error(f"Timeout Error: {timeout_err}")
        return False
    except requests.exceptions.RequestException as req_err:
        logging.error(f"Request Error: {req_err}")
        return False
    except Exception as e:
        logging.error(f"General Error: {e}")
        logging.error(f"Failed payload: {payload}")
        return False

# Begin API functions =================================================================================
@app.get("/")
def read_root():
    return {"status": "Empty endpoint - somethings wrong with your api call."}

@app.get("/health") # Used for pod liveness probe
async def health():
    return {"status": "ok"}

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

@app.get("/deployment/{task_id}/status")
async def get_deployment_status(task_id: str):
    """Get deployment task status and progress"""
    task = get_task(task_id)
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    response = {
        "task_id": task.task_id,
        "status": task.status,
        "progress": task.progress,
        "started_at": task.started_at,
        "updated_at": task.updated_at
    }
    
    if task.status == "completed":
        response["result"] = {
            "summary": task.result.get("summary"),
            "elog_url": task.result.get("elog_url", "")
        }
    elif task.status == "failed":
        response["error"] = task.error
    
    return response

@app.get("/deployment/{task_id}/report")
async def download_deployment_report(task_id: str):
    """Download the deployment report file"""

    task = get_task(task_id)

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if task.status != "completed":
        raise HTTPException(status_code=409, detail="Deployment not completed yet")
    
    report_file = task.result.get("report_file")
    if not report_file or not os.path.exists(report_file):
        raise HTTPException(status_code=404, detail="Report file not found")
    
    return FileResponse(
        path=report_file,
        filename=os.path.basename(report_file),
        media_type='text/plain'
    )

@app.put("/ioc/deployment/revert")
async def revert_ioc_deployment(ioc_to_deploy: RevertDict, background_tasks: BackgroundTasks):
    """
    Revert a deployment for an IOC application to the previous iteration.
    """
    current_deployment = find_recent_deployment_for_component_facility(ioc_to_deploy.facility, ioc_to_deploy.component_name, 0)
    previous_deployment = find_recent_deployment_for_component_facility(ioc_to_deploy.facility, ioc_to_deploy.component_name, 1)

    # 1) Check which IOCs tags have changed from the current deployment to the previous deployment
    # Get changed IOCs and revert tag
    iocs_that_changed = []
    revert_tag = None
    if current_deployment and previous_deployment:
        current_iocs = {ioc["name"]: ioc["tag"] for ioc in current_deployment.get("dependsOn", [])}
        previous_iocs = {ioc["name"]: ioc["tag"] for ioc in previous_deployment.get("dependsOn", [])}
        # ex: previous_iocs = {"sioc-b34-gtest02": "1.0.66", "sioc-b34-gtest01": "1.0.66"}
        logging.debug(f"current_iocs: {current_iocs}")
        logging.debug(f"previous_iocs: {previous_iocs}")
        # Find IOCs that have different tags
        for ioc_name, current_tag in current_iocs.items():
            # ex: ioc_name = "sioc-b34-gtest02", current_tag = "1.0.67"
            if ioc_name in previous_iocs and current_tag != previous_iocs[ioc_name]:
                # ex: previous_iocs["sioc-b34-gtest02"] = "1.0.66"
                iocs_that_changed.append(ioc_name)
        
        revert_tag = previous_deployment.get("tag")

    # 2) Deploy the reverted deployment for this facility
    if not revert_tag:
        return JSONResponse(status_code=400, content={"payload": "No previous deployment found to revert to"})
    revert_deployment = DeployDict(component_name=ioc_to_deploy.component_name,
                            facilities=[ioc_to_deploy.facility],
                            tag=revert_tag,
                            ioc_list=iocs_that_changed,
                            user=ioc_to_deploy.user,
                            playbook='ioc_module/ioc_deploy.yml')

    return await deploy(revert_deployment, background_tasks)

@app.put("/deployment")
async def deploy(deploy_request: DeployDict, background_tasks: BackgroundTasks):
    """Unified deployment endpoint. Routes to IOC, PyDM, container, or generic handler
    based on the playbook field (e.g. 'ioc_module/...', 'pydm_module/...', 'container_module/...')."""
    task_id = str(uuid.uuid4())
    task = DeploymentTask(task_id, save_callback=save_task)
    save_task(task)
    background_tasks.add_task(deploy_async, task_id, deploy_request)
    return JSONResponse(status_code=202, content={"task_id": task_id, "status": "pending"})

async def deploy_async(task_id: str, deploy_request: DeployDict):
    """Dispatch to the right deployment handler based on playbook path."""
    await asyncio.sleep(0.1)
    task = get_task(task_id)
    temp_dir = f"{APP_PATH}/tmp/{task_id}"
    os.makedirs(temp_dir, exist_ok=True)
    task.temp_dir = temp_dir
    try:
        if 'ioc_module' in deploy_request.playbook:
            result = await asyncio.get_running_loop().run_in_executor(None, deploy_ioc_sync, deploy_request, temp_dir, task)
        elif 'container_module' in deploy_request.playbook:
            result = await asyncio.get_running_loop().run_in_executor(None, deploy_container_sync, deploy_request, temp_dir, task)
        else:
            result = await asyncio.get_running_loop().run_in_executor(None, run_generic_deployment, deploy_request, temp_dir, task)
        task.complete(result)
    except Exception as e:
        logging.exception(f"Deployment {task_id} failed")
        task.fail(str(e))
        cleanup_temp_deployment_dir(temp_dir)

def deploy_ioc_sync(ioc_to_deploy: DeployDict, temp_download_dir: str, task: DeploymentTask):
    """
    IOC deployment logic. Handles these scenarios:
    1. Deploy tag to select existing IOCs (IOCs specified, facility not required)
    2. Deploy tag to all existing IOCs
    3. Deploy tag to new IOCs (IOCs specified, facility required)
    4. Deploy tag to component only (no IOCs, facility required)
    5. Deploy new component AND new IOCs
    """
    logging.info(f"New IOC deployment request: {ioc_to_deploy}")
    # Handle component-only deployment
    if not ioc_to_deploy.ioc_list:
        logging.info("Component-only deployment")
        task.update_progress("Component-only deployment", 10)
        return deploy_component(ioc_to_deploy, temp_download_dir, task)
    # IOC deployments with facility specified (new IOCs or new component)
    elif ioc_to_deploy.facilities:
        logging.info("Deploy tag to new IOCs")
        task.update_progress("Deploying to new IOCs", 10)
        return deploy_iocs_with_facility(ioc_to_deploy, temp_download_dir, task)
    else:
        logging.info("Deploy tag to existing IOCs")
        task.update_progress("Deploying to existing IOCs", 10)
        return deploy_existing_iocs(ioc_to_deploy, temp_download_dir, task)

def deploy_component(ioc_to_deploy: DeployDict, temp_download_dir: str, task: DeploymentTask):
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
        facilities_ioc_dict, new_component, task
    )

def deploy_existing_iocs(ioc_to_deploy: DeployDict, temp_download_dir: str, task: DeploymentTask):
    """
    Handle deployments to existing IOCs
    - Case 1: Deploy tag to select existing IOCs 
    - Case 2: Deploy tag to all existing IOCs
    
    Facility not required as we'll find where each IOC exists.
    """
    facilities_ioc_dict = {} # This dict will contain all the iocs that exist in their corresponding facility
    
    # Process each IOC to find its facility(s)
    # the cli should do a check if the iocs the user wants to deploy actually exist
    for ioc in ioc_to_deploy.ioc_list:
        facilities = find_facility_an_ioc_is_in(ioc, ioc_to_deploy.component_name)
        logging.info(f"ioc: {ioc}, facilities: {facilities}")
        if len(facilities) == 0: # Empty list
            return JSONResponse(content={"payload": {"Error": f"IOC not found in deployment database: {ioc}. (If new IOC then please deploy with a facility)"}}, status_code=400)
        for facility in facilities: # Add the ioc to facilities_ioc_dict
            if facility not in facilities_ioc_dict:
                facilities_ioc_dict[facility] = []
            facilities_ioc_dict[facility].append(ioc)
    
    # If we get here, we found facilities for all IOCs
    ioc_to_deploy.facilities = list(facilities_ioc_dict.keys())
    
    # Execute deployment with the IOCs we found
    return execute_ioc_deployment(
        ioc_to_deploy, temp_download_dir,
        facilities_ioc_dict, False, task # No new components
    )

def deploy_iocs_with_facility(ioc_to_deploy: DeployDict, temp_download_dir: str, task: DeploymentTask):
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
        facilities_ioc_dict, new_component, task
    )


def execute_ioc_deployment(ioc_to_deploy: DeployDict, temp_download_dir: str, 
                      facilities_ioc_dict: dict, new_component: bool, task: DeploymentTask):
    """
    Called by the specific deployment functions after they determine what to deploy.
    """
    task.update_progress("Preparing deployment", 20)

    playbook_args_dict = ioc_to_deploy.model_dump()
    playbook_args_dict['user_src_repo'] = None
    status = 200
    deployment_report_file = temp_download_dir + '/deployment-report-' + ioc_to_deploy.component_name + '-' + ioc_to_deploy.tag + '.log'
    deployment_output = ""
    extracted_ioc_info = False

    # Download release
    task.update_progress("Downloading release artifacts", 25)
    if not download_release(ioc_to_deploy.component_name, ioc_to_deploy.tag, temp_download_dir, all_os=True, extract_tarball=True):
        return JSONResponse(content={"payload": {"Error": f"Deployment tag may not exist for app: {ioc_to_deploy.component_name}, tag: {ioc_to_deploy.tag} \
                                    . Or software factory backend is broken"}}, status_code=400)
    facility_num = 1
    for facility in facilities_ioc_dict.keys():
        logging.info(f"Deploying to facility: {facility}")
        logging.info(f"IOCs to deploy: {facilities_ioc_dict[facility]}")
        percent = 40 + (facility_num * 10 // len(facilities_ioc_dict))
        task.update_progress(f"Deploying to {facility}", percent, f"Running playbook for {facility}")
        
        ioc_playbooks_path = ANSIBLE_PLAYBOOKS_PATH + 'ioc_module'
        playbook_args_dict['playbook_path'] = ioc_playbooks_path
        local_ioc_playbooks_path = ANSIBLE_PLAYBOOKS_PATH + 'ioc_module'
        inventory_file_path = get_inventory_path()

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
                        startup_cmd_template = 'startup.cmd.soft'
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
        stdout, stderr, return_code = ansible_api.run_ansible_playbook(inventory_file_path, local_ioc_playbooks_path + '/ioc_deploy.yml',
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
        
    if deployment_output == "":
        raise ValueError("No deployments performed. This may be due to empty IOC lists or invalid component/facility combinations.")

    task.update_progress("Generating deployment report", 90)
    if not ioc_to_deploy.dry_run:
        task.update_progress("Writing to ELOG", 95)
    return finalize_deployment(
        ioc_to_deploy.component_name, ioc_to_deploy.tag, ioc_to_deploy.user,
        list(facilities_ioc_dict.keys()), deployment_output, status, deployment_success,
        deployment_report_file, ioc_to_deploy.dry_run, facilities_ioc_dict
    )

def deploy_container_sync(container_to_deploy: DeployDict, temp_dir: str, task: DeploymentTask):
    """Container deployment logic. No source tarball needed — just runs the container playbook."""
    logging.info(f"New container deployment request: {container_to_deploy}")

    env_secrets = get_container_secrets(container_to_deploy.component_name)
    secrets = {
        'database_url': container_to_deploy.database_url or env_secrets['database_url'],
        'redis_url': container_to_deploy.redis_url or env_secrets['redis_url'],
        'ghcr_token': container_to_deploy.ghcr_token or env_secrets['ghcr_token'],
        'ghcr_user': container_to_deploy.ghcr_user or env_secrets['ghcr_user'],
    }
    if not secrets['database_url']:
        app_key = container_to_deploy.component_name.upper().replace("-", "_")
        raise ValueError(f"database_url not provided and CONTAINER_{app_key}_DATABASE_URL env var not set")

    inventory_file_path = get_inventory_path()

    # Build extra-vars for Ansible (app_name comes from component_name)
    # Only include optional fields that are configured
    playbook_args_dict = {
        'app_name': container_to_deploy.component_name,
        'image_tag': container_to_deploy.tag,
        'database_url': secrets['database_url'],
        'force_deploy': container_to_deploy.force_deploy,
        'health_check_path': container_to_deploy.health_check_path,
    }
    if container_to_deploy.docker_network:
        playbook_args_dict['docker_network'] = container_to_deploy.docker_network
    if container_to_deploy.migration_command:
        playbook_args_dict['migration_command'] = container_to_deploy.migration_command
    if secrets['redis_url']:
        playbook_args_dict['redis_url'] = secrets['redis_url']
    if secrets['ghcr_token']:
        playbook_args_dict['ghcr_token'] = secrets['ghcr_token']
    if secrets['ghcr_user']:
        playbook_args_dict['ghcr_user'] = secrets['ghcr_user']

    facilities = container_to_deploy.facilities
    status = 200
    deployment_output = ""
    deployment_success = True
    deployment_report_file = os.path.join(temp_dir, f'deployment-report-{container_to_deploy.component_name}-{container_to_deploy.tag}.log')
    full_playbook_path = os.path.join(ANSIBLE_PLAYBOOKS_PATH, container_to_deploy.playbook)

    for facility in facilities:
        logging.info(f"Deploying container to facility: {facility}")
        playbook_args = json.dumps(playbook_args_dict)
        stdout, stderr, return_code = ansible_api.run_ansible_playbook(
            inventory_file_path,
            full_playbook_path,
            facility,
            playbook_args,
            return_output=True,
            no_color=True
        )

        current_output = "== Container deployment output for " + facility + ' ==\n\n' + stdout
        if (return_code != 0):
            status = 400
            if (stderr != ''):
                current_output += "\n== Errors ==\n\n" + stderr
            deployment_success = False
        deployment_output += current_output

        update_db_after_deployment(deployment_success, True, facility, 'container',
                                  container_to_deploy.component_name, container_to_deploy.tag,
                                  container_to_deploy.user, current_output)

    if deployment_output == "":
        raise ValueError("No deployments performed")

    return finalize_deployment(
        container_to_deploy.component_name, container_to_deploy.tag, container_to_deploy.user,
        facilities, deployment_output, status, deployment_success,
        deployment_report_file, container_to_deploy.dry_run
    )


def run_generic_deployment(deploy_request: DeployDict, temp_dir: str, task: DeploymentTask):
    """Generic deployment: download tagged release tarball, then run the specified playbook.
    Handles pydm, HLA, TOOLS, and any other app type without IOC or container-specific logic."""
    logging.info(f"Generic deployment request: {deploy_request}")

    # Default subsystem for pydm apps if not provided
    if 'pydm_module' in deploy_request.playbook and not deploy_request.subsystem:
        deploy_request.subsystem = deploy_request.component_name.replace("pydm-", "").replace("-displays", "")

    # Derive app_type for the deployment DB from the playbook path
    if 'pydm_module' in deploy_request.playbook:
        app_type = 'pydm'
    else:
        app_type = deploy_request.playbook.split('/')[0]  # e.g. 'hla_module' -> 'hla_module'

    task.update_progress("Downloading release", 20)

    # Artifact-based deployment (e.g. Tauri desktop apps with RPM from GitHub releases)
    if deploy_request.artifact_url:
        logging.info(f"Artifact-based deployment: downloading from {deploy_request.artifact_url}")
        artifact_filename = f"{deploy_request.component_name}-{deploy_request.tag}.artifact"
        artifact_filepath = os.path.join(temp_dir, artifact_filename)

        github_token = os.environ.get("GITHUB_TOKEN", "")
        headers = {"Accept": "application/octet-stream"}
        if github_token:
            headers["Authorization"] = f"token {github_token}"

        try:
            response = requests.get(deploy_request.artifact_url, headers=headers, stream=True, allow_redirects=True)
            if response.status_code != 200:
                raise ValueError(f"Failed to download artifact from {deploy_request.artifact_url}: HTTP {response.status_code}")
            with open(artifact_filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=1024*1024):
                    if chunk:
                        f.write(chunk)
            logging.info(f"Artifact downloaded to {artifact_filepath}")
        except requests.RequestException as e:
            raise ValueError(f"Failed to download artifact: {str(e)}")
    else:
        if not download_release(deploy_request.component_name, deploy_request.tag, temp_dir, all_os=False, extract_tarball=True):
            raise ValueError(f"Failed to download release for {deploy_request.component_name} tag {deploy_request.tag}")

    full_playbook_path = os.path.join(ANSIBLE_PLAYBOOKS_PATH, deploy_request.playbook)
    inventory_file_path = get_inventory_path()

    facilities = deploy_request.facilities or []
    tarball_filepath = os.path.join(temp_dir, f"{deploy_request.tag}.tar.gz")
    deployment_report_file = os.path.join(temp_dir, f'deployment-report-{deploy_request.component_name}-{deploy_request.tag}.log')

    playbook_args_dict = {
        'component_name': deploy_request.component_name,
        'tag': deploy_request.tag,
        'user': deploy_request.user,
    }
    if deploy_request.artifact_url:
        playbook_args_dict['artifact_path'] = artifact_filepath
        playbook_args_dict['artifact_type'] = deploy_request.artifact_type or 'rpm'
    else:
        playbook_args_dict['tarball'] = tarball_filepath
    if deploy_request.subsystem:
        playbook_args_dict['subsystem'] = deploy_request.subsystem
    if deploy_request.extra_vars:
        playbook_args_dict.update(deploy_request.extra_vars)

    status = 200
    deployment_output = ""
    deployment_success = True
    elog_url = ""
    for i, facility in enumerate(facilities):
        task.update_progress(f"Deploying to {facility}", 30 + int(60 * i / max(len(facilities), 1)))
        playbook_args_dict['facility'] = facility
        playbook_args = json.dumps(playbook_args_dict)
        stdout, stderr, return_code = ansible_api.run_ansible_playbook(
            inventory_file_path, full_playbook_path, facility, playbook_args,
            return_output=True, no_color=True, check_mode=deploy_request.dry_run)
        current_output = f"== Deployment output for {facility} ==\n\n{stdout}"
        deployment_success = True
        if return_code != 0:
            status = 400
            if stderr:
                current_output += f"\n== Errors ==\n\n{stderr}"
            deployment_success = False
        deployment_output += current_output
        if not deploy_request.dry_run:
            is_new_component = find_component_in_facility(facility, deploy_request.component_name) is None
            update_db_after_deployment(deployment_success, is_new_component, facility, app_type,
                                       deploy_request.component_name, deploy_request.tag,
                                       deploy_request.user, current_output)

    if deployment_output == "":
        raise ValueError("No deployments performed — check facilities list and component name")

    task.update_progress("Generating report", 92)
    if not deploy_request.dry_run:
        task.update_progress("Writing to ELOG", 96)
    return finalize_deployment(
        deploy_request.component_name, deploy_request.tag, deploy_request.user,
        facilities, deployment_output, status, deployment_success,
        deployment_report_file, deploy_request.dry_run
    )


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
    response = requests.post(endpoint, json=new_component, timeout=REQUEST_TIMEOUT)
    add_log_to_component(initial_deployment.facility, timestamp, initial_deployment.user,
                          initial_deployment.component_name, "Initial deployment entry added by software factory admins")
    return JSONResponse(content={"payload": {"Success": "Deployment added to database"}}, status_code=200)

if __name__ == "__main__":
    uvicorn.run('deployment_controller:app', workers=4, host='0.0.0.0', port=8080, timeout_keep_alive=600)
    # timeout_keep_alive set to 600 seconds, in case deployment takes longer than usual
    # deployment_controller refers to file, and app is the app=fastapi()
    # 4 workers run in parallel, so if a worker is blocked on a request that takes a while, then the others will still accept requests