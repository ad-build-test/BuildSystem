# Local build
import json
import sys
import os
from start_build import Build, initialize_logger
from start_test import Test

if __name__ == "__main__":
    if len(sys.argv) != 6:  # Ensure 5 arguments are passed
        print(f"arguments given: {sys.argv}")
        print("Usage: python3 local_build.py <manifest_data> <user_src_repo> <component> <branch> <build_os>")
        sys.exit(1)

    # Deserialize the JSON string back into a dictionary
    manifest_data = sys.argv[1]

    # Print raw argument for debugging (repr() shows invisible characters)
    print(f"Raw manifest_data: {repr(manifest_data)}")
    
    # Strip leading and trailing whitespace
    manifest_data = manifest_data.strip()

    try:
        manifest_data = json.loads(manifest_data)  # Deserialize JSON into a Python dictionary
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON: {e}")
        sys.exit(1)

    # 1) create build class
    # Set environment variables from command-line arguments
    os.environ["ADBS_SOURCE"] = sys.argv[2]      # user_src_repo
    os.environ["ADBS_COMPONENT"] = sys.argv[3]   # component
    os.environ["ADBS_BRANCH"] = sys.argv[4]      # branch
    os.environ["ADBS_OS_ENVIRONMENT"] = sys.argv[5]  # build_os
    os.environ["ADBS_BUILD_TYPE"] = "normal"     # Default for local builds
    initialize_logger(os.getenv('ADBS_SOURCE') + '/build.log')
    build = Build()

    # 2) Run local build
    build.run_build(manifest_data)

    # 3) Run unit tests
    test = Test()
    test.run_unit_tests(os.getenv('ADBS_SOURCE'))