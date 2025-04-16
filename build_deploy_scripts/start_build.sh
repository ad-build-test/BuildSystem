#!/bin/bash
# This is the official script for build containers.

# Source the dev environment (This is needed for apps that have dependencies on the dev environment
# For example, apps that build for linuxRT have dependencies on certain library paths)
source /afs/slac/g/lcls/tools/script/ENVS64.bash

# Call the main python script to do the build
python3 /build/start_build.py