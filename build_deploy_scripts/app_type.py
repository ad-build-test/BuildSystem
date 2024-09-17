from enum import Enum

# Note - this is a copy of ~/.cram_user_facilities.cfg for app type for now
class AppType(str, Enum):
    IOC = 'IOC'
    HLA = 'HLA'
    TOOLS = 'Tools'
    MATLAB = 'Matlab'
    PYDM = 'PyDM'