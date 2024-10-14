"""
Desc: Watchdog of the configuration file, as well as starting a new process
    for a deployment that needs to happen.

Usage: python3 deployment_controller.py
note - this would have to run 24/7. 
"""
import os
import subprocess
import time
import ast
import yaml
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from deepdiff import DeepDiff
from ansible_api import run_ansible_playbook
from artifact_api import ArtifactApi

CONFIG_FILE_PATH = "./deployment_config.yaml" # TODO: TEMP: Refer to local directory for testing
# CONFIG_FILE_PATH = "/mnt/eed/ad-build/deployment_config.yaml"
ANSIBLE_PLAYBOOKS_PATH = "../ansible/" # TODO: TEMP: Refer to local dir for testing
# ANSIBLE_PLAYBOOKS_PATH = "/sdf/group/ad/eed/ad-build/ansible_playbooks"

class ConfigFileHandler(FileSystemEventHandler):
    def __init__(self, playbook_path: str):
        self.previous_data = None
        self.playbook_path = playbook_path

    def parse_yaml(self, yaml_filepath: str) -> dict:
        # Load YAML data from file
        with open(yaml_filepath, 'r') as file:
            yaml_data = yaml.safe_load(file)
        return yaml_data
    
    def write_to_yaml(self, yaml_filepath: str, data_to_write: dict):
        """
        Function that writes the data from API call of CLI bs run deployment
        to the configuration yaml (db once done prototyping)
        """
        # 1) Get the data of the CLI api call, varies depending on app type
            # IOC app type:
            # playbook_args_dict = {
            # "initial": initial,
            # "component_name": request.component.name,
            # "tag": tag,
            # "user": linux_uname,
            # "tarball": tarball,
            # "ioc_dict": ioc_dict,
            # "output_path": playbook_output_path
            # }

        # 2) Make new data dictionary using self.previous_data 

        # 3) Replace dictionary appropiately with new data

        # 4) Call the ansible playbook 
        # (In this case i don't think we need to parse changes, since deployment will still 
        # be triggered manually - which simplifies this deployment_controller script)

    def get_index_for_field(self, key: str, field_name: str) -> int:
        """ Gets the index for a specific field in a complicated key format (due to deepdiff) """
        # Clean the key to prepare for processing
            # key ex: root['development']['ioc'][0]['tag']
            # becomes: [development[ioc[0[tag
        clean_key = key.replace("root", "").replace("'", "").replace("]","")
        fields = clean_key.split('[')

        found_field = False
        for field in fields:
            if field == field_name:
                found_field = True
            elif found_field and field.isdigit():  # Capture the index after the field
                return int(field)


    def parse_diff(self, diff: dict, new_data: dict):
        """ Parse the difference (Changes) to configuration 
            Note - This logic can be reapplied to mongodb, since its stored in JSON documents, its
                easily convertable to a python dict
        """
        changes = []
        # Check for values changed in the ioc tag
        if 'values_changed' in diff:
            for key, change in diff['values_changed'].items():
                if "['ioc']" in key: # Check if change to an ioc app
                    if "['iocs']" in key: # Check if change to an ioc within the ioc app
                        if "['tag']" in key: # Check if change to an ioc tag
                            print(f"key: {key},\n change: {change}")

                            ioc_app_index = self.get_index_for_field(key, 'ioc')
                            ioc_index = self.get_index_for_field(key, 'iocs')
                            
                            ioc_app = self.previous_data['development']['ioc'][ioc_app_index]
                            ioc = self.previous_data['development']['ioc'][ioc_app_index]['iocs'][ioc_index]
                            changes.append({
                                'type': 'ioc_tag_within_app_changed',
                                'ioc_app_name': ioc_app['name'],
                                'ioc_name': ioc['name'],
                                'old_tag': change['old_value'],
                                'new_tag': change['new_value']
                            })
                    elif "['tag']" in key:  # Check if change to an ioc app tag
                        print(f"key: {key},\n change: {change}")

                        ioc_app_index = self.get_index_for_field(key, 'ioc')
                        
                        ioc_app = self.previous_data['development']['ioc'][ioc_app_index]
                        changes.append({
                            'type': 'ioc_app_tag_changed',
                            'ioc_name': ioc_app['name'],
                            'old_tag': change['old_value'],
                            'new_tag': change['new_value']
                        })
                    

        # Check for added or removed IOCs
        if 'dictionary_item_added' in diff:
            for added_key in diff['dictionary_item_added']:
                if "['ioc']" in added_key:
                    new_ioc = new_data['development']['ioc'][-1]  # Last added
                    changes.append({
                        'type': 'ioc_added',
                        'ioc_name': new_ioc['name'],
                        'tag': new_ioc['tag']
                    })

        if 'dictionary_item_removed' in diff:
            for removed_key in diff['dictionary_item_removed']:
                if "['ioc']" in removed_key:
                    index = removed_key.split('[')[1].rstrip(']')
                    removed_ioc = self.previous_data['development']['ioc'][int(index)]
                    changes.append({
                        'type': 'ioc_removed',
                        'ioc_name': removed_ioc['name'],
                        'tag': removed_ioc['tag']
                    })
        print(f"All changes since previous version: {changes}")


    def compare_configs(self, new_data: dict):
        """Compare the previous and new configuration data."""
        if self.previous_data is None:
            self.previous_data = new_data
            return None

        diff = DeepDiff(self.previous_data, new_data)
        self.previous_data = new_data
        return diff
    
    def on_modified(self, event):
        # print(event)
        if event.src_path == CONFIG_FILE_PATH:
            print(f"Configuration file changed: {event.src_path}")
            new_data = self.parse_yaml(CONFIG_FILE_PATH)
            changes = self.compare_configs(new_data)
            if changes:
                print(f"Detected changes: {changes}")
                self.parse_diff(changes, new_data)
                

    def run_ansible_script(self):
        """Run the Ansible playbook."""
        print("Running Ansible playbook...")
        try:
            subprocess.run(['ansible-playbook', self.playbook_path], check=True)
            print("Ansible playbook executed successfully.")
        except subprocess.CalledProcessError as e:
            print(f"Ansible playbook failed with error: {e}")

if __name__ == "__main__":
    playbook_path = '/path/to/your/playbook.yml'  # Path to your Ansible playbook

    event_handler = ConfigFileHandler(playbook_path)
    observer = Observer()
    observer.schedule(event_handler, os.path.dirname("./"), recursive=False)

    print("Starting file observer...")
    observer.start()

    try:
        while True:
            time.sleep(1)  # Keep the script running
    except KeyboardInterrupt:
        print("Stopping file observer...")
        observer.stop()
    observer.join()
