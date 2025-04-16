#!/bin/bash
# This is the official script for build containers with arguments for local build.

# Source the dev environment (This is needed for apps that have dependencies on the dev environment
# For example, apps that build for linuxRT have dependencies on certain library paths)
source /afs/slac/g/lcls/tools/script/ENVS64.bash

# Call the main python script to do the build
python3 /build/local_build.py $1 $2 $3 $4 $5