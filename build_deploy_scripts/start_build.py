import sys
import yaml
import os
import subprocess
import requests
from ansible_api import run_ansible_playbook, run_process
from artifact_api import ArtifactApi
from start_test import Test
from logger_setup import setup_logger, switch_log_file

# Define exit codes
EXIT_SUCCESS = 0
EXIT_BUILD_FAILURE = 1

# Initialize a default logger that will be replaced when setup_logger is called
logger = None

# Export this function to set up the logger
def initialize_logger(log_file_path):
    global logger
    logger = setup_logger(log_file_path)
    return logger

class Build(object):
    def __init__(self):
        self.get_environment()
        self.root_dir = None # This is the root/top directory
        self.artifact_api = ArtifactApi()
        self.ANSIBLE_PLAYBOOKS_PATH = "/mnt/eed/ad-build/build-system-playbooks"

    def parse_yaml(self, yaml_filepath: str) -> dict:

        # Load YAML data from file
        with open(yaml_filepath, 'r') as file:
            yaml_data = yaml.safe_load(file)
        return yaml_data

    def get_environment(self):
        # 0) Source dev environment 
        # Path to the mounted script
        init_script = "/afs/slac/g/lcls/tools/script/ENVS64.bash"
        self.env = os.environ.copy()
        
        if os.path.exists(init_script):
            logger.info(f"Sourcing dev env script: {init_script}")
            command = ['sh', init_script]
            stdout, stderr, return_code = run_process(command, self.env, return_output=True)
            logger.info(f"Source dev env script return code: {return_code}")
        else:
            print(f"No initialization script found at {init_script}")

        # 1) Get environment variables - assuming we're not using a configMap
        self.os_env = os.getenv("ADBS_OS_ENVIRONMENT") # From backend
        self.build_type = os.getenv('ADBS_BUILD_TYPE') # From CLI - Either 'normal' or 'container'
        self.source_dir = os.getenv('ADBS_SOURCE') # From backend - This is full filepath, like /mnt/eed/ad-build/scratch/component-a-branch1-RHEL8-66c4e8cb1dabd45f50f3112f/component-a
        self.component = os.getenv('ADBS_COMPONENT') # From CLI
        self.branch = os.getenv('ADBS_BRANCH') # From CLI
        if (self.os_env.lower() == 'rocky9'):
            self.os_env = 'rhel9' # Special case: need to change rocky9 to rhel9 because thats the name used for epics modules
        self.epics_host_arch = self.os_env.lower() + '-x86_64' # TODO: For now hardcode it to os x86
        custom_env = {"ADBS_OS_ENVIRONMENT": self.os_env, "ADBS_BUILD_TYPE": self.build_type, "ADBS_SOURCE": self.source_dir,
               "ADBS_COMPONENT":  self.component, "ADBS_BRANCH": self.branch, "EPICS_HOST_ARCH": self.epics_host_arch} # This env is just for sanity checking
        for key, value in custom_env.items():
            if (key == "ADBS_BUILD_TYPE"):
                if (value == None): # Special case, default to 'normal'
                    custom_env["ADBS_BUILD_TYPE"] = 'normal'
                    self.build_type = 'normal'
            elif (value == None):
                # Raise exception
                raise ValueError("Missing environment variable - " + key)
        custom_env['HOME'] = '/build/' # Needed for ansible to run as non-root
        # Copy the current environment
        self.env = os.environ.copy()
        # Update with new environment variables
        self.env.update(custom_env)

    def parse_dependencies(self, config_yaml: dict) -> dict:
        try:
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
        logger.info("Installing python packages from " + pkgs_file_name)
        if (self.os_env.lower() == 'rhel7'):
            try:
                output_bytes = subprocess.check_output(['python3', '-m', 'pip', 'install', '-r', pkgs_file], stderr=subprocess.STDOUT)
            except subprocess.CalledProcessError as e:
                output_bytes = e.output
        else:
            try:
                output_bytes = subprocess.check_output(['pip', 'install', '-r', pkgs_file], stderr=subprocess.STDOUT)
            except subprocess.CalledProcessError as e:
                output_bytes = e.output
        output = output_bytes.decode("utf-8")
        logger.info(output)
        return pkgs_file
    
    def install_dependencies(self, dependencies: dict):
        logger.info("Installing dependencies")
        logger.info(dependencies)
        for dependency in dependencies:
            for name,tag in dependency.items():
                    if (name == 'epics-base'): # Epics_base special case, path into root_dir/epics/base/<ver>
                        download_dir = self.root_dir + '/epics/base' # Create the directory for component
                        os.makedirs(download_dir, exist_ok=True)
                        # Add epics to the LD_LIBRARY_PATH
                        # TODO: For now, just hardcode the architecture
                        # self.env['LD_LIBRARY_PATH'] = download_dir + '/' + tag + '/lib/linux-x86_64/'
                        self.artifact_api.get_component_from_registry(download_dir, name, tag, self.os_env)
                    else:
                        download_dir = self.root_dir + '/' + name # Create the directory for component
                        os.mkdir(download_dir)
                        self.artifact_api.get_component_from_registry(download_dir, name, tag, self.os_env)

    def create_release_site(self, config_yaml: dict):
        # This only applies to IOCs for REMOTE builds

        # TODO: Once s3df figures out other dirs, update paths after IOC_SITE_TOP
        # check if we have to emulate exactly the structure of how it looks,
        # Because we don't want to alter the RELEASE for remote builds, just a RELEASE_SITE
        # Ideally all modules including epics are on the same level, but its not in this format
        # 1) Create release_site
        dependencies = config_yaml['dependencies']
        # Get the value for "epics-base"
        for dep in dependencies:
            if 'epics-base' in dep:
                epics_base_version = dep['epics-base']
                break
        release_site_dict = {
            "BASE_MODULE_VERSION": epics_base_version,
            "EPICS_SITE_TOP": "/afs/slac/g/lcls/epics",
            "BASE_SITE_TOP": "$(EPICS_SITE_TOP)/base",
            "EPICS_MODULES": "$(EPICS_SITE_TOP)/$(BASE_MODULE_VERSION)/modules",
            "IOC_SITE_TOP": "$(EPICS_SITE_TOP)/iocTop",
            "PACKAGE_SITE_TOP": "/afs/slac/g/lcls/package",
            "MATLAB_PACKAGE_TOP": "/afs/slac/g/lcls/package/matlab",
            "PSPKG_ROOT": "/afs/slac/g/lcls/package/pkg_mgr",
            "TOOLS_SITE_TOP": "/afs/slac/g/lcls/tools",
            "ALARM_CONFIGS_TOP": "/afs/slac/g/lcls/tools/AlarmConfigsTop"
        }

        # 4) Write the dictionary in the new file
        with open('RELEASE_SITE', 'w') as file:
            for key, value in release_site_dict.items():
                file.write(f'{key}={value}\n')
            # Special line
            epics_host_arch = """ifeq ($(origin EPICS_HOST_ARCH), undefined)
EPICS_HOST_ARCH     := $(shell $(EPICS_SITE_TOP)/base/$(BASE_MODULE_VERSION)/startup/EpicsHostArch)
endif"""
            file.write(f'{epics_host_arch}\n')

    def update_config_site(self):
        # This only applies to IOCs for REMOTE builds
        # 1) Update the config site to set CHECK_RELEASE = NO
        file_path = 'configure/CONFIG_SITE'
        # Read the current contents of the config file
        if not os.path.exists(file_path):
            return  # Exit the function if the file doesn't exist (not an IOC)
        with open(file_path, 'r') as file:
            lines = file.readlines()

        # Modify the target line
        for i, line in enumerate(lines):
            # Strip whitespace and check if it's a comment or empty line
            stripped_line = line.strip()
            if stripped_line.startswith('#') or not stripped_line:
                continue
            
            # Check if the line contains the target key
            if stripped_line.startswith("CHECK_RELEASE"):
                lines[i] = f"CHECK_RELEASE = NO\n"
                break

        # Write the modified contents back to the file
        with open(file_path, 'w') as file:
            file.writelines(lines)

    def run_build(self, config_yaml: dict, verbose: bool=False):
        build_method = config_yaml['build']
        if (verbose):
            logger.debug("Build environment:")
            logger.debug("self.env=" + str(self.env))
        logger.info("Running Build:")
        # Create a shell command string that sources the environment and runs the build


        # TODO: We got a problem
        # 1) Essentially if you source the dev enviornment in dev-rhel9 theres some 
        # os eval going on in there where it now recognizes you are in a rhel9 os,
        # and it will try to build for rhel9, even if you started your rhel7 container.
        # And creates an error when trying to build locally. 
        # 2) But for a remote build, if you sourced the dev environment and build, there are no 
        # issues. 


        if build_method.endswith('.sh'):
            # For shell script builds
            build_script = './' + config_yaml['build']
            shell_command = f"source {self.init_script} && sh {build_script}"
        else:
            # For direct command builds
            shell_command = f"source {self.init_script} && {build_method}"
        
        # Run the combined command through bash
        command = ['bash', '-c', shell_command]
            
        return_code = run_process(command, self.env)

        if (return_code != 0):
            logger.info("Build process FAILED!")
            sys.exit(EXIT_BUILD_FAILURE)
        else:
            user_src_repo = self.source_dir
            playbook_args = f'{{"component": "{self.component}", "branch": "{self.branch}", \
                "user_src_repo": "{user_src_repo}"}}'
            ioc_playbooks_dir = os.path.join(self.ANSIBLE_PLAYBOOKS_PATH, 'ioc_module')
            return_code = run_ansible_playbook(self.ANSIBLE_PLAYBOOKS_PATH + '/global_inventory.ini',
                                    ioc_playbooks_dir + '/ioc_build.yml',
                                    'S3DF',
                                    playbook_args,
                                    self.env)
            logger.info(f"Playbook execution finished with return code: {return_code}")

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
            f.write("FROM " + "ghcr.io/ad-build-test/" + self.os_env + "-env:latest\n")       # base image
            for dependency in dependencies:
                for name,tag in dependency.items():
                    f.write("ADD " + self.registry_base_path + name + "/" + tag + " /build\n")
            if (py_pkgs_list):
                for pkg in py_pkgs_list:
                    f.write("RUN pip install " + pkg + "\n")
            # File closed automatically
        # Send api request to build
        payload = {"dockerfile": dockerfile_name, "arch": self.os_env}
        logger.info(payload)
        logger.info("Send image build request to artifact storage...")
        response = requests.post(url=self.artifact_api_url + 'image', json=payload)
        logger.info(response.status_code)
        logger.info(response.json())

if __name__ == "__main__":
    build = Build()
    # 1) Enter build directory
    # ex: /mnt/eed/ad-build/scratch/test-ioc-main-pnispero/test-ioc-main
    os.chdir(build.source_dir)
    build.root_dir = os.path.dirname(build.source_dir)
    logger = setup_logger(build.source_dir + '/build.log')
    logger.info("Current dir: " + str(os.getcwd()))
    logger.info("Root dir: " + build.root_dir)
    # 2) Parse yaml
    config_yaml = build.parse_yaml('config.yaml')
    # 3) Install python packages (if applicable)
    py_pkgs_file = build.install_python_packages(config_yaml)
    # 4) Run repo build script
    build.run_build(config_yaml, verbose=True)
    # 5) Run unit_tests
    switch_log_file(build.source_dir + '/tests.log')
    test = Test()
    test.run_unit_tests(build.source_dir)

    # 6) If container build - Build dockerfile
    if (build.build_type.lower() == 'container'):
        pass
        # TODO: Don't release this yet until done with regular remote build
        # build.create_docker_file(dependencies, py_pkgs_file)
    
    # 7)  Done
    logger.info("Remote build finished.")
    sys.exit(EXIT_SUCCESS)
