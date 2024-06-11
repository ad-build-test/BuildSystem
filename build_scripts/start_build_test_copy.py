import json
import yaml
import os

# Flow
# 1) Parse the contents of /config/build_config.json
    
# 2) Using the ADBS_COMPONENT and ADBS_BRANCH from build_config.json,
#     look into /mnt and find the src code dir

# 3) Then depending on the ADBS_BUILD_COMMAND
    # 3.1) if name of script, then run the script
    # 3.2) if ...
    # 3...)

# 4) Then run the function in start_test.py
    # 4.1) Which will look into certain directories and run those tests
    

def parse_build_config():
    with open('build_config.json') as f:
        d = json.load(f)
        print('Print contents of build_config.json:')
        print(d)

def parse_yaml(yaml_filepath: str) -> dict:

    # Load YAML data from file
    with open(yaml_filepath, 'r') as file:
        yaml_data = yaml.safe_load(file)

    # Print the parsed YAML data
    print("Parsed YAML data:")
    print(yaml_data)
    return yaml_data

def get_environment() -> dict:
    # 0) Get environment variables - assuming we're not using a configMap
    os_env = os.getenv("ADBS_OS_ENVIRONMENT")
    source_dir = os.getenv('ADBS_SOURCE')
    output_dir = os.getenv('ADBS_OUTPUT')
    env_config = {"os_env": os_env, "source_dir": source_dir, "output_dir": output_dir}
    return env_config

def parse_dependencies() -> dict:
    # 1) Enter build directory
    env = get_environment()
    # os.chdir(env['source_dir'])

    # 2) Parse yaml
    config_yaml = parse_yaml('CONFIG.yaml')
    if (config_yaml['format'] == 2):
        dependencies = config_yaml['environments'][env['os_env']]['dependencies']
    else:
        dependencies = config_yaml['dependencies']
    return dependencies

def get_component_from_registry(component: str, tag: str):
    # TODO: Waiting on when registry is implemented
    print(component, tag)
    pass

def install_dependencies(dependencies: dict):
    print("Installing dependencies")
    print(dependencies)
    for dependency in dependencies:
        for name,value in dependency.items():
            if (name != 'build'):
                component = get_component_from_registry(name, value)
            else:
                buildInstructions = value
        print(buildInstructions)

    # 3) For each dependency
        # 3.1) Clone the repo

        # 3.2) Usually its just a 'make'

        # 3.3) But how do we package that? I think all of it goes to a folder

if __name__ == "__main__":
    # parse_build_config()
    # config_yaml = parse_yaml('RELEASE.yaml')
    dependencies = parse_dependencies()
    install_dependencies(dependencies)

