# Configuration for the cli
from enum import Enum
import sys

# Note - this is a copy of ~/.cram_user_facilities.cfg for app type for now
class Api(str, Enum):
    BACKEND = 'core-build-system'
    DEPLOYMENT = 'deployment_controller'

cli_configuration = {
    "server_url": "https://ad-build-dev.slac.stanford.edu/api/cbs/v1/",
    "deployment_controller_url": "https://ad-build-dev.slac.stanford.edu/api/deployment/",
    "build_system_filepath": "/sdf/group/ad/eed/ad-build/registry/BuildSystem/", # TODO: Temporarily spot
    "build_images_filepath": "/sdf/group/ad/eed/ad-build/registry/"
}
# "server_url": "https://accel-webapp-dev.slac.stanford.edu/api/cbs/v1/"

INPUT_PREFIX = "[?] "

def under_development():
    """ Function placeholder for unfinished logic """
    print("== This cli command is under development!! ==")
    sys.exit(0)