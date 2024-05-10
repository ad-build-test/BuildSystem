import requests, yaml, sys

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


def find_component_by_id(component_id: str):

    # Find component by id
    component_payload_receive = requests.get(server_url + 'component/' + component_id)

    # For now get print out the payload of component request
    print("Requested component payload:")
    print(component_payload_receive.text)


# 2) Start up new container with the image you retrieved from component db
# kubectl
    
# Find the key corresponding to a specific value
def find_key(dictionary, value):
    for key, val in dictionary.items():
        if val == value:
            return key
    return None

def main():
    yaml_data = parse_yaml()
    component_id = get_component_id(yaml_data['name'])
    find_component_by_id(component_id)

if __name__ == "__main__":
    main()

