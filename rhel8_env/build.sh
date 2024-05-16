#!/bin/bash

# Build script - For now, 1 of 2 options

# 1) run the build instructions script
# 2) vanilla make clean, then make

# Only one argument to this script
    # build_instructions: [name of script, make]
echo "Running build.sh "$1

BUILD_INSTRUCTIONS=$1
if [[ "$BUILD_INSTRUCTIONS" != "make" ]]; then
    chmod +x $BUILD_INSTRUCTIONS
    ./$BUILD_INSTRUCTIONS
    exit
fi

make clean
make
