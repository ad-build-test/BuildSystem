# This class is the api to the artifact api
# used by both build and deployment
import requests
import tarfile
import os
class Artifact_api(object):

    def download_file(self, component, tag, response, epics_base=False):
        moveed this function to its own class, so we can use it for both
        build and deploy.
        first test that that the start_build.py wasn't affected when using this instead
        then work on deployment image, and to test, can make the container
        ssh into local pc instead of lcls/facet kind of thing.
        then use 
        # Download file from api, and extract to ADBS_SOURCE
        # Download the .tar.gz file
        tarball_filename = tag + '.tar.gz'
        if response.status_code == 200:
            with open(tarball_filename, 'wb') as file:
                file.write(response.content)
            print('== ADBS == Tarball downloaded successfully')
            output_dir = self.root_dir
            if (epics_base): # Epics_base special case, path into root_dir/epics/base/<ver>
                output_dir = output_dir + '/epics/base'
                os.makedirs(output_dir)
                # Add epics to the LD_LIBRARY_PATH
                # TODO: For now, just hardcode the architecture
                self.env['LD_LIBRARY_PATH'] = output_dir + '/' + tag + '/lib/linux-x86_64/'
            else:
                # Create the directory for component
                output_dir = self.root_dir + '/' + component
                os.mkdir(output_dir)
            # Extract the .tar.gz file
            with tarfile.open(tarball_filename, 'r:gz') as tar:
                tar.extractall(path=output_dir)
            print(f'== ADBS == {tarball_filename} extracted to {output_dir}')
        else:
            print('== ADBS == Failed to retrieve the file. Status code:', response.status_code)

    def get_component_from_registry(self, component: str, tag: str):
        # For now look into the /mnt/eed/ad-build/registry
        # rest api
        print(component, tag)     
        payload = {"component": component, "tag": tag, "arch": self.os_env}
        print(payload)
        print(f"== ADBS == Get component {component},{tag} request to artifact storage...")
        response = requests.get(url=self.artifact_api_url + 'component', json=payload)
        if (component == 'epics-base'): # special case
            self.download_file(component, tag, response, epics_base=True)
        else:
            self.download_file(component, tag, response)
        # For now we can assume the component exists, otherwise the api builds and returns it