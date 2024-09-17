import os
import json
import subprocess
from app_type import AppType
from artifact_api import ArtifactApi

class Deploy(object):
    def __init__(self):
        self.get_environment()
        self.root_dir = None # This is the root/top directory
        self.artifact_api = ArtifactApi()

    def run_ansible_playbook(self, inventory, playbook, host_pattern, extra_vars):
        os.environ['ANSIBLE_FORCE_COLOR'] = 'true'
        command = [
            'ansible-playbook', 
            '-i', inventory,
            '-l', host_pattern,
            playbook
        ]

        if extra_vars:
            # Convert extra_vars dictionary to JSON string
            extra_vars_str = json.dumps(extra_vars)
            # extra_vars_str = ' '.join(f'{k}={v}' for k, v in extra_vars.items())
            command += ['--extra-vars', extra_vars_str]
        # logging.info(command)
        print(command)

        # Use subprocess.Popen to forward output directly
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        # Print output in real-time
        for line in iter(process.stdout.readline, ''):
            print(line, end='')  # Print each line as it is output

        # Ensure all stderr is also handled
        for line in iter(process.stderr.readline, ''):
            print(line, end='')

        process.stdout.close()
        process.stderr.close()
        return_code = process.wait()
        return return_code

    def get_environment(self):
        # 0) Get environment variables - assuming we're not using a configMap
        # self.os_env = os.getenv("ADBS_OS_ENVIRONMENT") # From backend - TODO: Not sure if need this since build results contain all arches
        self.facilities = json.loads(os.getenv('ADBS_FACILITIES')) # From CLI
        self.initial_deployment = os.getenv('ADBS_INITIAL') # From CLI - see app_type.py
        self.app_type = os.getenv('ADBS_APP_TYPE') # From CLI - see app_type.py
        self.component = os.getenv('ADBS_COMPONENT') # From CLI
        self.tag = os.getenv('ADBS_TAG') # From CLI
        custom_env = {"ADBS_APP_TYPE": self.app_type, "ADBS_COMPONENT":  self.component, "ADBS_TAG": self.tag} # This env is just for sanity checking
        for key, value in custom_env.items():
            if (value == None):
                # Raise exception
                raise ValueError("Missing environment variable - " + key)
        # Copy the current environment
        self.env = os.environ.copy()
        # Update with new environment variables
        self.env.update(custom_env)

    def get_build_results(self):
        download_dir = '/build/' + self.component
        os.makedirs(download_dir)
        self.tarball = self.artifact_api.get_component_from_registry(download_dir, self.component, self.tag, extract=False)

    def call_deployment_playbook(self):
        playbook_output_path = '/build/ADBS_playbook_output/'
        isExist = os.path.exists(playbook_output_path)
        if not isExist:
            print(f"== ADBS == Adding a {playbook_output_path} dir for deployment playbook output. You may delete if unused")
            os.mkdir(playbook_output_path)
        if (self.app_type == AppType.IOC):
            self.ioc_dict = {
                "test-ioc-1": "test-ioc-1.0.0",
                "test-ioc-2": "test-ioc-1.0.0"
            } # TODO: For now Hardcode for testing, but in real deal grab ioc deployment config from deployment db
            playbook_args_dict = {
                "initial": self.initial_deployment,
                "component_name": self.component,
                "tag": self.tag,
                "user": 'adbuild',
                "tarball": self.tarball,
                "ioc_dict": self.ioc_dict, 
                "output_path": playbook_output_path
                }
            adbs_playbooks_dir = "/build/ioc_module/" # TODO: Change this once official
            for facility in self.facilities:
                print("== ADBS == Call deployment playbook for facility ", facility)
                return_code = self.run_ansible_playbook(adbs_playbooks_dir + 'global_inventory.ini',
                                            adbs_playbooks_dir + 'ioc_deploy.yml',
                                                "S3DF", # TODO: Temp hardcode for testing
                                                playbook_args_dict)
                # return_code = self.run_ansible_playbook(adbs_playbooks_dir + 'global_inventory.ini',
                #                             adbs_playbooks_dir + 'ioc_deploy.yml',
                #                                 facility,
                #                                 playbook_args_dict)
                print("Playbook execution finished with return code:", return_code)
        # TODO: Rest of app types
        elif (self.app_type == AppType.HLA):
            pass

if __name__ == "__main__":
    print("Dev Version")
    deploy = Deploy()
    # 1) Get the build results from artifact storage
    deploy.get_build_results()
    # 2) Call deployment playbook with the build results
    deploy.call_deployment_playbook()
    
