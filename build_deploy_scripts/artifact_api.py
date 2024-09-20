# This class is the api to the artifact api
# used by both build and deployment
import requests
import tarfile

class ArtifactApi(object):
    def __init__(self):
        self.registry_base_path = "/mnt/eed/ad-build/registry/"
        self.artifact_api_url = "http://artifact-api-service.artifact:8080/"

    def download_file_response(self, download_dir: str, tag: str, response: requests.Response, extract):
        # Download file from api, and extract to download_dir
        # Download the .tar.gz file
        tarball_filepath = download_dir + '/' + tag + '.tar.gz'
        if response.status_code == 200:
            # Download response to tarball file
            with open(tarball_filepath, 'wb') as file: 
                file.write(response.content)
            print('== ADBS == Tarball downloaded successfully')
            if (extract):
                # Extract the .tar.gz file
                with tarfile.open(tarball_filepath, 'r:gz') as tar:
                    tar.extractall(path=download_dir)
                print(f'== ADBS == {tarball_filepath} extracted to {download_dir}')
            return tarball_filepath
        else:
            print('== ADBS == Failed to retrieve the file. Status code:', response.status_code)
            return None


    def get_component_from_registry(self, download_dir: str, component: str, tag: str, extract=True):
        # For now look into the /mnt/eed/ad-build/registry
        # rest api
        print(component, tag)     
        os_env = 'linux-x86_64' # TODO: Hardcode for now, don't know yet if arch is important if build results has all arches
        payload = {"component": component, "tag": tag, "arch": os_env}
        print(payload)
        print(f"== ADBS == Get component {component},{tag} request to artifact storage...")
        response = requests.get(url=self.artifact_api_url + 'component', json=payload)
        return self.download_file_response(download_dir, tag, response, extract)
        # For now we can assume the component exists, otherwise the api builds and returns it