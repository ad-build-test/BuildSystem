# Configuration for the cli
from enum import Enum

# Note - this is a copy of ~/.cram_user_facilities.cfg for app type for now
class Api(str, Enum):
    BACKEND = 'core-build-system'
    DEPLOYMENT = 'deployment_controller'

cli_configuration = {
    "server_url": "https://ad-build-dev.slac.stanford.edu/api/cbs/v1/",
    "deployment_controller_url": "http://172.24.8.139/" # TODO: Temporarily hard ip address, since havent got domain name added to DNS from s3df admins
}
# "server_url": "https://accel-webapp-dev.slac.stanford.edu/api/cbs/v1/"

INPUT_PREFIX = "[?] "