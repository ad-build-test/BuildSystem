# Configuration for the cli
from enum import Enum
import sys
import os

class Api(str, Enum):
    BACKEND = 'core-build-system'
    DEPLOYMENT = 'deployment_controller'

# https://accel-webapp-dev.slac.stanford.edu/api-doc/?urls.primaryName=Core%20Build%20System#/
class ApiEndpoints(str, Enum):
    # From core build system api
    COMPONENT = "component" # Used for GET, POST
    COMPONENT_ID = "component/{id}" # Used for GET, PUT, DELETE
    COMPONENT_BRANCH = "component/{component_name}/branch"
    COMPONENT_EVENT = "component/{component_name}/event/{enable}"
    COMPONENT_ISSUE = "component/{component_name}/issue/{issue_tracker}"
    BUILD_LOG = "build/{id}/log/tail"
    BUILD_BRANCH = "build/component/{component_name}/branch/{branch_name}"

    # From deployment controller api
    DEPLOYMENT = "{deployment_type}/deployment"
    DEPLOYMENT_REVERT = "{deployment_type}/deployment/revert" 
    DEPLOYMENT_INFO = "deployment/info"
    DEPLOYMENT_FACILITIY = "deployments/{component_name}/{facility}"
    DEPLOYMENT_INITIAL = "initial/deployment"
    
    def format(self, **kwargs):
        """Format the endpoint with the provided parameters. (If applicable)"""
        return self.value.format(**kwargs)

# Define both configurations
dev_config = {
    "server_url": "https://ad-build-dev.slac.stanford.edu/api/cbs/v1/",
    "deployment_controller_url": "https://ad-build-dev.slac.stanford.edu/api/deployment/",
    "build_system_filepath": "/sdf/group/ad/eed/ad-build/registry/BuildSystem/",
    "build_images_filepath": "/sdf/group/ad/eed/ad-build/registry/"
}

prod_config = {
    "server_url": "https://ad-build.slac.stanford.edu/api/cbs/v1/",
    "deployment_controller_url": "https://ad-build.slac.stanford.edu/api/deployment/",
    "build_system_filepath": "/sdf/group/ad/eed/ad-build/registry/BuildSystem/",
    "build_images_filepath": "/sdf/group/ad/eed/ad-build/registry/"
}

# Select configuration based on environment variable
is_prod = os.environ.get("AD_BUILD_PROD", "false").lower() in ("true", "1", "yes", "y")
if (not is_prod):
    print("== ADBS == Warning: CLI pointed to dev cluster")
cli_configuration = prod_config if is_prod else dev_config

# Set cli_configuration with linux_uname and gh_uname
linux_uname = os.environ.get('USER')
github_uname = os.environ.get('AD_BUILD_GH_USER')
cli_configuration["linux_uname"] = linux_uname
cli_configuration["github_uname"] = github_uname

INPUT_PREFIX = "[?] "

def under_development():
    """ Function placeholder for unfinished logic """
    print("== This cli command is under development!! ==")
    sys.exit(0)