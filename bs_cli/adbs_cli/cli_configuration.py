# Configuration for the cli
from enum import Enum
import sys
import os

# Note - this is a copy of ~/.cram_user_facilities.cfg for app type for now
class Api(str, Enum):
    BACKEND = 'core-build-system'
    DEPLOYMENT = 'deployment_controller'

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