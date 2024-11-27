# Configuration for the cli
from enum import Enum
import sys

# Note - this is a copy of ~/.cram_user_facilities.cfg for app type for now
class Api(str, Enum):
    BACKEND = 'core-build-system'
    DEPLOYMENT = 'deployment_controller'

cli_configuration = { # TODO: TEMP set to localhost for testing
    "server_url": "http://localhost:8080/v1/", #"https://ad-build-dev.slac.stanford.edu/api/cbs/v1/",
    "deployment_controller_url": "http://172.24.8.139/", # TODO: Temporarily hard ip address, since havent got domain name added to DNS from s3df admins
    "build_system_filepath": "/sdf/group/ad/eed/ad-build/registry/BuildSystem/", # TODO: Temporarily spot
    "build_images_filepath": "/sdf/group/ad/eed/ad-build/registry/"
}
# "server_url": "https://accel-webapp-dev.slac.stanford.edu/api/cbs/v1/"

INPUT_PREFIX = "[?] "

def under_development():
    """ Function placeholder for unfinished logic """
    click.echo("== This cli command is under development!! ==")
    sys.exit(0)