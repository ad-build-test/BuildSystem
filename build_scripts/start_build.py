import json
import yaml
import os
import subprocess
import shutil
import requests
from start_test import run_unit_tests

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
        self.artifact_api_url = "http://artifact-api-service:8080/"

    def parse_yaml(self, yaml_filepath: str) -> dict:

        # Load YAML data from file
        with open(yaml_filepath, 'r') as file:
            yaml_data = yaml.safe_load(file)

        # Print the parsed YAML data
        print("Parsed YAML data:")
        print(yaml_data)
        return yaml_data

    def get_environment(self) -> dict:
        # 0) Get environment variables - assuming we're not using a configMap
        os_env = os.getenv("ADBS_OS_ENVIRONMENT")
        source_dir = os.getenv('ADBS_SOURCE')
        output_dir = os.getenv('ADBS_OUTPUT')
        component = os.getenv('ADBS_COMPONENT')
        branch = os.getenv('ADBS_BRANCH')
        env_config = {"os_env": os_env, "source_dir": source_dir, "output_dir": output_dir,
                    "component": component, "branch": branch}
        return env_config

    def parse_dependencies(self, config_yaml: dict, env: dict) -> dict:
        try:
            if (config_yaml['format'] == 2):
                dependencies = config_yaml['environments'][env['os_env']]['dependencies']
            else:
                dependencies = config_yaml['dependencies']
        except KeyError:
            return None
        return dependencies

    def get_component_from_registry(self, component: str, tag: str, os_env: str):
        # TODO: Waiting on when registry is implemented
        # For now look into the /mnt/eed/ad-build/registry
        # rest api
        print(component, tag)     
        # Plan:
        """
        0) MAKE a prototype 'registry' which will be on the /mnt//mnt/eed/ad-build/registry
        But make the code infrastructure here for it. but substitute with 'just look into dir'
        Split tree into registry/component/OS/tag
        1) Look into the registry (its a cache basically) for the component if it exists
            1.1) if exists, then just grab it
            1.2) if not exist, then start_build.py is responsible for building it
                1.2.1) Look into the config yaml, for the component dependency name, 
                        and an additional 'build' field on how to build the component. 
                1.2.2) 
        2) Once you have the compiled component, do we put it in /lib of the repo?
            Or put it in the container /usr/local
        """
        component_path = '/mnt/eed/ad-build/registry/' + component + '/' + tag + '/'
        container_build_path = '/build/'
        print("component path: ", component_path)
        if (os.path.exists(component_path)):
            print("Registry has component - ", component, tag)
            # For now, copy it directly to /build
            print("copying over ", component_path, " to ", container_build_path)
            shutil.copytree(component_path, container_build_path, dirs_exist_ok = True)
            # Then if epics (need to specify somewhere in config.yaml?)
            # NOTE - this only needed if running scripts, can still build without these vars
            # if (component == 'epics-base'):
            #     os.environ['EPICS_BASE']="/build/epics-base"
            #     os.environ['EPICS_HOST_ARCH']="/build/epics-base"
            #     os.environ['PATH']="/build/epics-base:" + os.environ['PATH']
            #     # export EPICS_BASE=/build/epics-base
            #     # export EPICS_HOST_ARCH=$(${EPICS_BASE}/startup/EpicsHostArch)
            #     # export PATH=${EPICS_BASE}/bin/${EPICS_HOST_ARCH}:${PATH}
            # to active terminal and to .bashrc if this is dev image
        else:
            print("Registry doesn't have component - ", component, tag)
            print("TODO: build the component")

        # Then see if we should clone to registry, and put a BOM with build instructions
            # or should we put it in database just in case it is external component
            # That we cannot add a BOM to.
        # Should the build instrutions in the component tell where the output is?
        # For C/C++
        # Do we automatically put the .so/.a files in /usr/lib64? 
            # then call ldconfig, and their build instructions hopefully has gcc ... -l<component>
                # how can their makefile reference the CONFIG.yaml for components?
                    # a: have this function output into one large string like '-lepics -lsqlite3' Then pass that
                    # into the MakeFile $LIBS, then in MakeFile gcc -o $(OBJECTS) $(LIBS)
            # AND get the binaries, like if its epics, we would want the epics binaries to run iocConsole for ex
            # And can update $LD_LIBRARY_PATH (for lib) and/or $PATH (for bin)
            # or currently, $TOOLS/script provides epics scripts.

    def install_dependencies(self, dependencies: dict, env: dict):
        print("Installing dependencies")
        print(dependencies)
        for dependency in dependencies:
            for name,tag in dependency.items():
                    component_from_registry = self.get_component_from_registry(name, tag, env['os_env'])
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
        print("Running Build:")
        try:
            build_output_bytes = subprocess.check_output(['sh', build_script], stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            build_output_bytes = e.output
        build_output = build_output_bytes.decode("utf-8")
        print(build_output)


    def create_docker_file(self, dependencies: dict, env: dict):
        # Create dockerfile with dependencies installed
        # Then send to artifact storage to be built
        dockerfile_name = env["component"] + "-" + env["branch"] + "-" + env["os_env"]
        docker_full_filepath = self.registry_base_path + "dockerfiles/" + dockerfile_name
        with open(docker_full_filepath, "w") as f:   # Opens file and casts as f 
            f.write("FROM " + "pnispero/" + env["os_env"] + "-env:latest\n")       # base image
            for dependency in dependencies:
                for name,tag in dependency.items():
                    f.write("ADD " + self.registry_base_path + name + "/" + tag + " /build\n")
            # File closed automatically
        # Send api request to build
        payload = {"dockerfile": dockerfile_name}
        print("Send image build request to artifact storage...")
        response = requests.post(self.artifact_api_url + 'image', payload)
        print(response.status_code)
        print(response.json())


if __name__ == "__main__":
    print("Dev Version")
    build = Build()
    # 1) Enter build directory
    env = build.get_environment()
    os.chdir(env['source_dir'])
    # 2) Parse yaml
    config_yaml = build.parse_yaml('configure/CONFIG.yaml')
    # 3) Parse dependencies
    dependencies = build.parse_dependencies(config_yaml, env)
    if (dependencies):
        # 4) Install dependencies
        build.install_dependencies(dependencies, env)
    # 5) Run repo build script
    build.run_build(config_yaml)
    # 6) Run unit_tests
    run_unit_tests()
    # 7) Build dockerfile
    build.create_docker_file(dependencies, env)
