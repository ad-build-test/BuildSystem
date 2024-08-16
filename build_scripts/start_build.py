import json
import yaml
import os
import sys
import subprocess
import shutil
import requests
from start_test import Test

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
class Build(object):
    def __init__(self):
        self.registry_base_path = "/mnt/eed/ad-build/registry/"
        self.artifact_api_url = "http://artifact-api-service.artifact:8080/"
        self.get_environment()

    def parse_yaml(self, yaml_filepath: str) -> dict:

        # Load YAML data from file
        with open(yaml_filepath, 'r') as file:
            yaml_data = yaml.safe_load(file)

        # Print the parsed YAML data
        print("Parsed YAML data:")
        print(yaml_data)
        return yaml_data

    def get_environment(self):
        # 0) Get environment variables - assuming we're not using a configMap
        self.os_env = os.getenv("ADBS_OS_ENVIRONMENT")
        self.source_dir = os.getenv('ADBS_SOURCE') # This is full filepath, like /mnt/eed/ad-build/scratch/66721557fd891a5aac14b3d0-ROCKY9-test-ioc-dev-patrick/
        self.output_dir = os.getenv('ADBS_OUTPUT')
        self.component = os.getenv('ADBS_COMPONENT')
        self.branch = os.getenv('ADBS_BRANCH')
        env = {"os_env": self.os_env, "source_dir": self.source_dir, "output_dir": self.output_dir,
               "component":  self.component, "branch": self.branch}
        for key, value in env.items():
            if (value == None):
                # Raise exception
                raise ValueError("Missing environment variable - " + key)

    def parse_dependencies(self, config_yaml: dict) -> dict:
        try:
            if (config_yaml['format'] == 2):
                dependencies = config_yaml['environments'][self.os_env]['dependencies']
            else:
                dependencies = config_yaml['dependencies']
        except KeyError:
            return None
        return dependencies
    
    def find_file(self, name, path):
        for root, dirs, files in os.walk(path):
            if name in files:
                return os.path.join(root, name)
    
    def install_python_packages(self, config_yaml: dict) -> str:
        try:
            pkgs_file_name = config_yaml['python']
        except KeyError:
            return None
        # Search repo for the pkgs_file (like requirements.txt)
        pkgs_file = self.find_file(pkgs_file_name, self.source_dir)
        print("== ADBS == Installing python packages from " + pkgs_file_name)
        try:
            output_bytes = subprocess.check_output(['pip', 'install', '-r', pkgs_file], stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            output_bytes = e.output
        output = output_bytes.decode("utf-8")
        print(output)
        return pkgs_file


    def get_component_from_registry(self, component: str, tag: str) -> str:
        # TODO: Waiting on when registry is implemented
        # For now look into the /mnt/eed/ad-build/registry
        # rest api
        print(component, tag)     
        payload = {"component": component, "tag": tag, "arch": self.os_env}
        print(payload)
        print("== ADBS == Get component request to artifact storage...")
        response = requests.get(url=self.artifact_api_url + 'component', json=payload)
        response = response.json()
        print(response)
        # For now we can assume the component exists, otherwise the api builds and returns it
        component_path = response['component']
        return component_path
    
    def manual_copy_tree(self, src, dst):
        # This function is used if python < 3.8 where 'dirs_exist_ok' flag doesnt exist
        if not os.path.exists(dst):
            os.makedirs(dst)

        for item in os.listdir(src):
            s = os.path.join(src, item)
            d = os.path.join(dst, item)
            if os.path.isdir(s):
                # Recursively copy directories
                shutil.copytree(s, d, False, None)
            else:
                # Copy files
                shutil.copy2(s, d)

    def install_dependencies(self, dependencies: dict):
        print("== ADBS == Installing dependencies")
        print(dependencies)
        container_build_path = '/build/'
        for dependency in dependencies:
            for name,tag in dependency.items():
                    component_from_registry = self.get_component_from_registry(name, tag)
                    print("copying over ", component_from_registry, " to ", container_build_path)
                    if sys.version_info[1] < 8: # python minor version less than 8 doesnt have dirs_exist_ok
                        self.manual_copy_tree(component_from_registry, container_build_path)
                    else:
                        shutil.copytree(component_from_registry, container_build_path, dirs_exist_ok = True)
                # perform buildInstructions, and add to Dockerfile

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

    def run_build(self, config_yaml: dict):
        # Run the repo-defined build-script
        build_script = './' + config_yaml['build']
        print("== ADBS == Running Build:")
        try: # Used check_output() instead of run() since check_output is since py3.1 and run is 3.5
            build_output_bytes = subprocess.check_output(['sh', build_script], stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            build_output_bytes = e.output
        build_output = build_output_bytes.decode("utf-8")
        print(build_output)

    def create_docker_file(self, dependencies: dict, py_pkgs_file: str):
        # Create dockerfile with dependencies installed
        # Then send to artifact storage to be built
        py_pkgs_list = []
        if (py_pkgs_file):
            with open(py_pkgs_file, 'r') as f:
                for line in f:
                    py_pkgs_list.append(line)
        dockerfile_name = self.component + "-" + self.branch + "-" + self.os_env
        docker_full_filepath = self.registry_base_path + "dockerfiles/" + dockerfile_name
        with open(docker_full_filepath, "w") as f:   # Opens file and casts as f 
            f.write("FROM " + "pnispero/" + self.os_env + "-env:latest\n")       # base image
            for dependency in dependencies:
                for name,tag in dependency.items():
                    f.write("ADD " + self.registry_base_path + name + "/" + tag + " /build\n")
            if (py_pkgs_list):
                for pkg in py_pkgs_list:
                    f.write("RUN pip install " + pkg + "\n")
            # File closed automatically
        # Send api request to build
        payload = {"dockerfile": dockerfile_name, "arch": self.os_env}
        print(payload)
        print("== ADBS == Send image build request to artifact storage...")
        response = requests.post(url=self.artifact_api_url + 'image', json=payload)
        print(response.status_code)
        print(response.json())

if __name__ == "__main__":
    print("Dev Version")
    build = Build()
    # 1) Enter build directory
    os.chdir(build.source_dir)
    # 2) Parse yaml
    config_yaml = build.parse_yaml('configure/CONFIG.yaml')
    # 3) Parse dependencies
    dependencies = build.parse_dependencies(config_yaml)
    if (dependencies): # Possible an app has no dependencies
        # 4) Install dependencies
        build.install_dependencies(dependencies)
    # 4.1) Install python packages if available
    py_pkgs_file = build.install_python_packages(config_yaml)
    # 5) Run repo build script
    build.run_build(config_yaml)
    # 6) Run unit_tests
    test = Test()
    test.run_unit_tests(build.source_dir)
    # 7) Build dockerfile
    build.create_docker_file(dependencies, py_pkgs_file)
