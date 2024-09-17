import yaml
import os
import subprocess
import requests
from artifact_api import ArtifactApi
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
        self.get_environment()
        self.root_dir = None # This is the root/top directory
        self.artifact_api = ArtifactApi()

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
        self.os_env = os.getenv("ADBS_OS_ENVIRONMENT") # From backend
        self.build_type = os.getenv('ADBS_BUILD_TYPE') # From CLI - Either 'normal' or 'container'
        self.source_dir = os.getenv('ADBS_SOURCE') # From backend - This is full filepath, like /mnt/eed/ad-build/scratch/component-a-branch1-RHEL8-66c4e8cb1dabd45f50f3112f/component-a
        self.component = os.getenv('ADBS_COMPONENT') # From CLI
        self.branch = os.getenv('ADBS_BRANCH') # From CLI
        custom_env = {"ADBS_OS_ENVIRONMENT": self.os_env, "ADBS_BUILD_TYPE": self.build_type, "ADBS_SOURCE": self.source_dir,
               "ADBS_COMPONENT":  self.component, "ADBS_BRANCH": self.branch} # This env is just for sanity checking
        for key, value in custom_env.items():
            if (key == "ADBS_BUILD_TYPE"):
                if (value == None): # Special case, default to 'normal'
                    custom_env["ADBS_BUILD_TYPE"] = 'normal'
                    self.build_type = 'normal'
            elif (value == None):
                # Raise exception
                raise ValueError("Missing environment variable - " + key)
        # Copy the current environment
        self.env = os.environ.copy()
        # Update with new environment variables
        self.env.update(custom_env)

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
    
    def install_dependencies(self, dependencies: dict):
        print("== ADBS == Installing dependencies")
        print(dependencies)
        for dependency in dependencies:
            for name,tag in dependency.items():
                    if (name == 'epics-base'): # Epics_base special case, path into root_dir/epics/base/<ver>
                        download_dir = self.root_dir + '/epics/base' # Create the directory for component
                        os.makedirs(download_dir)
                        # Add epics to the LD_LIBRARY_PATH
                        # TODO: For now, just hardcode the architecture
                        self.env['LD_LIBRARY_PATH'] = download_dir + '/' + tag + '/lib/linux-x86_64/'
                        self.artifact_api.get_component_from_registry(download_dir, name, tag)
                    else:
                        download_dir = self.root_dir + '/' + name # Create the directory for component
                        os.mkdir(download_dir)
                        self.artifact_api.get_component_from_registry(download_dir, name, tag)

    def update_release_site(self):
        # This only applies to IOCs for REMOTE builds
        # 1) Update the release site to point to the repos here
        # TODO: in the install_dependencies(), make sure it creates <component>/ dirs
        pass
        # BASE_MODULE_VERSION=7.0.3.1-1.0
        # EPICS_SITE_TOP=/mnt/eed/ad-build/scratch/test-ioc-main-pnispero/epics
        # BASE_SITE_TOP=${EPICS_SITE_TOP}/base
        # EPICS_MODULES=${EPICS_SITE_TOP}/${BASE_MODULE_VERSION}/modules
        # IOC_SITE_TOP=${EPICS_SITE_TOP}/iocTop
        # PACKAGE_SITE_TOP=/afs/slac/g/lcls/package
        # MATLAB_PACKAGE_TOP=/afs/slac/g/lcls/package/matlab
        # PSPKG_ROOT=/afs/slac/g/lcls/pkg_mgr
        # TOOLS_SITE_TOP=/afs/slac/g/lcls/tools
        # ALARM_CONFIGS_TOP=/afs/slac/g/lcls/tools/AlarmConfigsTop
    
        # 1) Read the file and parse the key-value pairs
        filename = 'RELEASE_SITE'
        with open(filename, 'r') as file:
            lines = file.readlines()

        # 2) Create a dictionary to store the current key-value pairs
        release_site_dict = {}
        for line in lines:
            if '=' in line:
                key, value = line.strip().split('=', 1)
                release_site_dict[key] = value

        # 3) Update the dictionary with new values
        # TODO: Once s3df figures out other dirs, update paths after IOC_SITE_TOP
        # check if we have to emulate exactly the structure of how it looks,
        # Because we don't want to alter the RELEASE for remote builds, just a RELEASE_SITE
        # Ideally all modules including epics are on the same level, but its not in this format
        new_release_site = {
            'BASE_MODULE_VERSION': release_site_dict['BASE_MODULE_VERSION'], # Keep the same
            'EPICS_SITE_TOP': self.root_dir + '/epics', # Point to modules next to the where app being built
            'BASE_SITE_TOP': "${EPICS_SITE_TOP}/base",
            'EPICS_MODULES': self.root_dir,
            'IOC_SITE_TOP': "${EPICS_SITE_TOP}/iocTop"
        }
        release_site_dict.update(new_release_site)

        # 4) Write the updated key-value pairs back to the file
        with open(filename, 'w') as file:
            for key, value in release_site_dict.items():
                file.write(f'{key}={value}\n')

    def run_build(self, config_yaml: dict):
        # Run the repo-defined build-script
        build_script = './' + config_yaml['build']
        print("== ADBS == Running Build:")
        try: # Used check_output() instead of run() since check_output is since py3.1 and run is 3.5
            print("os.environ=" + str(os.environ))
            print("self.env=" + str(self.env))
            build_output_bytes = subprocess.check_output(['sh', build_script], stderr=subprocess.STDOUT, env=self.env)
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
    # ex: /mnt/eed/ad-build/scratch/test-ioc-main-pnispero/test-ioc-main
    os.chdir(build.source_dir)
    build.root_dir = os.path.dirname(build.source_dir)
    print("== ADBS == Current dir: " + str(os.getcwd()))
    print("== ADBS == Root dir: " + build.root_dir)
    # 2) Parse yaml
    config_yaml = build.parse_yaml('configure/CONFIG.yaml')
    # 3) Parse dependencies
    dependencies = build.parse_dependencies(config_yaml)
    if (dependencies): # Possible an app has no dependencies
        # 4) Install dependencies
        build.install_dependencies(dependencies)
    # 4.1) Install python packages if available
    py_pkgs_file = build.install_python_packages(config_yaml)
    # 5) Update RELEASE_SITE if EPICS IOC
    # TODO: Update logic to figure out what kind of app were building, for now focus on IOC
    if (dependencies):
        build.update_release_site()
    # 5) Run repo build script
    build.run_build(config_yaml)
    # 6) Run unit_tests
    test = Test()
    test.run_unit_tests(build.source_dir)

    # 7) If container build - Build dockerfile
    if (build.build_type.lower() == 'container'):
        pass
        # TODO: Don't release this yet until done with regular remote build
        # build.create_docker_file(dependencies, py_pkgs_file)
