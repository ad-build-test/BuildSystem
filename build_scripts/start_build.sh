#!/bin/bash
# This is the official entrypoint script for build pods.
set -e

# If ADBS_COMMAND is set, run it directly (new config.yaml flow).
# The command from config.yaml is what runs — no hidden steps.
if [ -n "$ADBS_COMMAND" ]; then
    cd "$ADBS_SOURCE"
    echo "=== CBS Build ==="
    echo "Component: $ADBS_COMPONENT"
    echo "Branch: $ADBS_BRANCH"
    echo "Command: $ADBS_COMMAND"
    echo "================="
    eval "$ADBS_COMMAND"
    exit $?
fi

# Legacy fallback: source dev environment and run start_build.py
source /afs/slac/g/lcls/tools/script/ENVS64.bash
python3 /build/start_build.py