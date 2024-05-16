import requests, yaml, sys, subprocess, re
from datetime import datetime

# Run: python3 start_build.py /path/to/build.yaml

def parse_yaml() -> dict:
    try:
        yaml_filepath = sys.argv[1]
    except:
        raise Exception("yaml filepath/file.yaml not specified")

    # Load YAML data from file
    with open(yaml_filepath, 'r') as file:
        yaml_data = yaml.safe_load(file)

    # Print the parsed YAML data
    print("Parsed YAML data:")
    print(yaml_data)
    return yaml_data

server_url='https://accel-webapp-dev.slac.stanford.edu/api/cbs/v1/'

# 1) Send request to component db

def get_component_id(component_name: str, component_branch: str="", component_environment: str="") -> str:

    # list components
    component_list = requests.get(server_url + 'component')
    component_dict = component_list.json()
    payload = component_dict['payload']
    print("payload:") # TEMP
    print(payload)  # TEMP
    print(payload[1]) # TEMP

    # Convert the list of dictionaries into a dictionary
    payload_dictionary = {}

    # Iterate over the data and populate the payload_dictionary dictionary
    for item in payload:
        id_value = item["id"]
        name_value = item["name"]
        if name_value not in payload_dictionary:
            payload_dictionary[name_value] = []
        payload_dictionary[name_value].append(id_value)
    payload_dictionary = {item["id"]: item["name"] for item in payload}

    # Return id
    return find_key(payload_dictionary, component_name)


def find_component_by_id(component_id: str) -> dict:

    # Find component by id
    requested_component = requests.get(server_url + 'component/' + component_id)

    # For now get print out the payload of component request
    print("Requested component payload:")
    print(requested_component.text)
    requested_component_dict = requested_component.json()
    payload = requested_component_dict["payload"]
    return payload

# Find the key corresponding to a specific value
def find_key(dictionary, value):
    for key, val in dictionary.items():
        if val == value:
            return key
    return None

def find_image_by_environment(environment: str) -> str:
    if (environment == 'rhel8'):
        # TODO: Temporarily return the one in your dockerhub registry
        image_url = "pnispero/rhel8-env:latest"
    return image_url

# function to start the build container
def start_build_container(repo_name: str, runner_name: str, image_url: str, build_instructions: str):

    # 1) Check build instructions is valid
    if (build_instructions == ""):
        raise Exception("ERROR: buildInstructions is empty!")
    
    # 2) Ensure only lowercase alphanumeric values and dashes are on repo name, otherwise replace (because runner name only accepts lowercase alphanumeric and dash)
    repo_name = repo_name.lower()
    repo_name = re.sub('[^0-9a-zA-Z]+', '-', repo_name)

    # 3) Get a unique name for the build container
    now = datetime.now()
    # just minutes and secs is enough to be unique (since one runner can't run this 
    # script more than once within a second)
    dt_string = now.strftime("%M%S")
    unique_container_name = repo_name + "-" + runner_name + "-" + dt_string

    # 4) TODO: after s3df is accessible, ensure to copy that repo
    # to where ./build.sh lives - note this may be done within build.sh instead

    # 5) Start the container
    subprocess.run(['kubectl', 'run', unique_container_name, '--image=' + image_url, '--command', './build.sh', './' + build_instructions])

    # 6) If made it here, then success
    print("Build successfully started, please see container: " + unique_container_name)


def main():
    yaml_data = parse_yaml()
    # TEMP for prototyping ================================
    if (sys.argv[2] == "test"): # check if testing (if so then ignore component db)
        image_url = "pnispero/rhel8-env:latest"
        start_build_container('simple-ioc', 'gh-runner1', image_url, "make")
        return
    # =========================================================

    component_id = get_component_id(yaml_data['reponame'])
    component_payload = find_component_by_id(component_id)
    image_url = component_payload['environment']
    build_instructions = component_payload['buildInstructions']
    start_build_container(yaml_data['reponame'], yaml_data['runner'], image_url, build_instructions)

if __name__ == "__main__":
    main()