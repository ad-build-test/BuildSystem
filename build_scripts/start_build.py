# TODO: move this over back to /BuildSystem once done prototyping
import json
import os
import yaml
# Demo Code
def parse_build_config():
    print('Hello World')
    print(os.getcwd())
    print('Print contents of build_config.json:')
    with open('../build_config.json') as f:
        d = json.load(f)
        print(d)

def parse_yaml(yaml_filepath: str) -> dict:

    # Load YAML data from file
    with open(yaml_filepath, 'r') as file:
        yaml_data = yaml.safe_load(file)

    # Print the parsed YAML data
    print("Parsed YAML data:")
    print(yaml_data)
    return yaml_data

def install_dependencies(dependencies: dict):
    print("Installing dependencies")
    print(dependencies)

if __name__ == "__main__":
    parse_build_config()
    release_yaml = parse_yaml('RELEASE.yaml')
    install_dependencies(release_yaml['dependencies'])


# Real code
# 1) Parse the contents of /config/build_config.json
    
# 2) Using the ADBS_COMPONENT and ADBS_BRANCH from build_config.json,
#     look into /mnt and find the src code dir

# 3) Then depending on the ADBS_BUILD_COMMAND
    # 3.1) if name of script, then run the script
    # 3.2) if ...
    # 3...)

# 4) Then run the function in start_test.py
    # 4.1) Which will look into certain directories and run those tests
    