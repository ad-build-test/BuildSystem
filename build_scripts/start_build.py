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
    os.chdir(env['source_dir'] + '/configure')

    # 2) Parse yaml
    release_yaml = parse_yaml('RELEASE.yaml')
    if (release_yaml['format'] == 2):
        dependencies = release_yaml['environments'][env['os_env']]['dependencies']
    else:
        dependencies = release_yaml['dependencies']
    return dependencies

def install_dependencies(dependencies: dict):
    print("Installing dependencies")
    print(dependencies)
# Plan:
"""
1) Look into the registry (its a cache basically) for the component if it exists
    1.1) if exists, then just grab it
    1.2) if not exist, then start_build.py is responsible for building it
        1.2.1) Look into the config yaml, for the component dependency name, 
                and an additional 'build' field on how to build the component. 
        1.2.2) 
2) Once you have the compiled component, do we put it in /lib of the repo?
    Or put it in the container /usr/local
"""
    # 3) For each dependency
        # Do we have these prebuilt somewhere, and we can grab them from registry?
        # If not exists, then we can send request to backend to build that dependency
        # Currently, every dependency exists somewhere on afs prebuilt, and we reference
            # those in the ioc-config file, specifying the filepath to the dependency,
            # and the /{ARCH}/lib and /{ARCH}/include folders.
            # this is shared libraries/dynamic linking. Another option is static linking
        # 3.1) Clone the repo

        # 3.2) Usually its just a 'make', creates the /lib/*.so compiled shared object files

        # 3.3) But how do we package that? I think we just move all of it to /lib of the repo?

def run_build():
    # 4) Run the repo-defined build-script
    pass

def create_docker_file():
    # 5) Create dockerfile with dependencies installed. then push to /output
    pass

if __name__ == "__main__":
    # parse_build_config()
    # release_yaml = parse_yaml('RELEASE.yaml')
    dependencies = parse_dependencies()
    install_dependencies(dependencies)

