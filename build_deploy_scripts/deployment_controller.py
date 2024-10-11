"""
Desc: Watchdog of the configuration file, as well as starting a new process
    for a deployment that needs to happen.

Usage: python3 deployment_controller.py
note - this would have to run 24/7. 
"""
import os
import subprocess
import time
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
    def __init__(self, playbook_path):
        self.previous_data = None
        self.playbook_path = playbook_path

    def parse_yaml(self, yaml_filepath: str) -> dict:
        # Load YAML data from file
        with open(yaml_filepath, 'r') as file:
            yaml_data = yaml.safe_load(file)
        return yaml_data
    Patrick- when back see an's message reply thread
    but basically fix up the ipxe_config.yaml to get rid of the obsolete ones, 
    which are the ones on the list I sent him, except keep a few he mentioned.
    Then add in the other cpu's on his list that the ipxe_config.yaml doesnt have.
    Then ask Jerry about ssh thing you msged him, 
    Then go back here to the deployment controller
    # Function to parse DeepDiff output
    def parse_diff(self, diff: dict, new_data: dict):
        changes = []
        # Check for values changed in the ioc tag
        if 'values_changed' in diff:
            for key, change in diff['values_changed'].items():
                if "['tag']" in key:  # Check if the change is in an IOC tag
                    print(f"key: {key},\n change: {change}")

                    # Extract the index directly from the key
                    index_start = key.index("['ioc']") + len("['ioc'][")
                    index_end = key.index(']', index_start)
                    ioc_index = int(key[index_start:index_end])  # Get the index as an integer
                    
                    print(self.previous_data['development']['ioc'])
                    parent_ioc = self.previous_data['development']['ioc'][ioc_index]
                    changes.append({
                        'type': 'ioc_tag_changed',
                        'ioc_name': parent_ioc['name'],
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
        print(changes)


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
