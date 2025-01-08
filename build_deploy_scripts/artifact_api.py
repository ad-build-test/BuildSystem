# This class is the api to the artifact api
# used by both build and deployment
import requests
import tarfile
import os
import logging

logger = logging.getLogger('my_logger')

class ArtifactApi(object):
    def __init__(self):
        self.registry_base_path = "/mnt/eed/ad-build/registry/"
        self.artifact_api_url = "http://artifact-api-service.core-build-system:8080/"

    def download_file_response(self, download_dir: str, tag: str, response: requests.Response, extract: bool):
        # Download file from api, and extract to download_dir
        # Download the .tar.gz file
        tarball_filepath = download_dir + '/' + tag + '.tar.gz'
        if response.status_code == 200:
            # Download response to tarball file
            stream_size = 1024*1024 # Write in chunks (1MB) since tarball can be big
            with open(tarball_filepath, 'wb') as file: 
                for chunk in response.iter_content(chunk_size=stream_size): 
                    if (chunk):
                        file.write(chunk)
            logger.info('Tarball downloaded successfully')
            # Extract the .tar.gz file
            if (extract):
                logger.info('Extracting tarball...')
                with tarfile.open(tarball_filepath, 'r:gz') as tar:
                    tar.extractall(path=download_dir)
                logger.info(f'{tarball_filepath} extracted to {download_dir}')
                # Delete tarball after extracting
                os.remove(tarball_filepath)
        else:
            logger.info('Failed to retrieve the file. Status code:', response.status_code)


    def get_component_from_registry(self, download_dir: str, component: str, tag: str, os_env: str = 'null', extract: bool = True):   
        payload = {"component": component, "tag": tag, "arch": os_env}
        logger.info(f"Get component {component},{tag} request to artifact storage...")
        # stream=True in case it's a large tarball
        response = requests.get(url=self.artifact_api_url + 'component', json=payload, stream=True) 
        self.download_file_response(download_dir, tag, response, extract)
        # For now we can assume the component exists, otherwise the api builds and returns it