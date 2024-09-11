## This is copied from /usr/local/lcls/epics/config/common_dirs.sh
# But altered for S3DF testing purposes
#
# common_dirs.sh
#
# Source in sh compatible login scripts
# such as ~/.profile or ~/.bashrc to define commonly used
# site specific directory paths.
#  Example:
#  source /usr/local/lcls/epics/config/common_dirs.sh
#
#  This file should not specify version numbers,
#  as choices about which versions of a specific
#  package to use should be handled by setup scripts
#  under $SETUP_SITE_TOP
#
export FACILITY=sdf
export FACILITY_ROOT=/$FACILITY/scratch/ad/build/lcls
export FACILITY_DATA=$FACILITY_ROOT
export WWW_ROOT=$FACILITY_ROOT
export COMMON=$FACILITY_ROOT
export IOC_OWNER=laci
export GIT_SITE_TOP=$FACILITY_ROOT

# The following are derived from the env variables defined above
export LCLS_ROOT=$FACILITY_ROOT
export LCLS_WWW=$WWW_ROOT/grp/$FACILITY/controls
export LCLS_DATA=$FACILITY_DATA
export EPICS_TOP=$FACILITY_ROOT/epics
export EPICS_CONFIG=$EPICS_TOP/config
export EPICS_SETUP=$EPICS_TOP/setup
export EPICS_IOCS=$EPICS_TOP/iocCommon
export EPICS_CPUS=$EPICS_TOP/cpuCommon
export PACKAGE_TOP=$FACILITY_ROOT/package
export PSPKG_ROOT=$PACKAGE_TOP/pkg_mgr
export TOOLS=$FACILITY_ROOT/tools
export GW_SITE_TOP=$FACILITY_ROOT/tools/gateway
export ALHTOP=$FACILITY_ROOT/tools/AlarmConfigsTop
export TFTPBOOT=$COMMON/tftpboot
export IOC_DATA=$FACILITY_DATA/epics/ioc/data
export TOOLS_DATA=$FACILITY_DATA/tools
export PHYSDATA=$FACILITY_DATA/physics

# Note: the follow env variables were setup for the photon group by Bruce Hill
export EPICS_SITE_TOP=$EPICS_TOP
export CONFIG_SITE_TOP=$EPICS_CONFIG
export SETUP_SITE_TOP=$EPICS_SETUP
export IOC_COMMON=$EPICS_IOCS
export PACKAGE_SITE_TOP=$PACKAGE_TOP
export TOOLS_SITE_TOP=$TOOLS

## ADBS - additional variables since i don't want to invoke a hundred scripts like on dev3
export IOC=$FACILITY_ROOT/epics/iocCommon
export APP=$FACILITY_ROOT/epics/iocTop
