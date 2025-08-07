import click
import os
import git
import inquirer
import json
import logging
import subprocess
import pathlib
from datetime import datetime, timezone, timedelta
from adbs_cli.component import Component, SimpleProgress
from adbs_cli.request import Request
from adbs_cli.cli_configuration import INPUT_PREFIX, Api, ApiEndpoints, under_development, cli_configuration
from adbs_cli.auto_complete import AutoComplete

def clone_repo(request: Request):
    ## Helper function
    # If user is not in existing repo, ask user where to clone repo, to get the manifest
    #   and the custom playbook (if specified)
    # Get URL from database
    # Change into filepath of cloned repo
    if (not request.component.git_repo):
        clone_filepath = input(INPUT_PREFIX + "Specify filepath to clone repo temporarily: ")
        os.chdir(clone_filepath)
        component_info = request.get_component_from_db()
        request.component.git_clone(component_info['url'])

def find_tarball(base_path):
    # Define the base directory
    base_dir = pathlib.Path(base_path)

    # Search for RPM files
    for path in base_dir.rglob('*.tar.gz'):
        # Assuming there's only one tarball file
        return path
    
    return None

def run_process_real_time(command):
    # Use subprocess.Popen to forward output directly
    # click.echo(command)
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    # Print output in real-time
    for line in iter(process.stdout.readline, ''):
        click.echo(line, nl=False)  # Print each line as it is output

    # Ensure all stderr is also handled
    for line in iter(process.stderr.readline, ''):
        click.echo(line, nl=False)

    process.stdout.close()
    process.stderr.close()
    return_code = process.wait()
    return return_code

def run_ansible_playbook(inventory, playbook, host_pattern, extra_vars):
    os.environ['ANSIBLE_FORCE_COLOR'] = 'true'
    command = [
        'ansible-playbook', 
        '-i', inventory,
        '-l', host_pattern,
        playbook
    ]

    if extra_vars:
        # Convert extra_vars dictionary to JSON string
        extra_vars_str = json.dumps(extra_vars)
        # extra_vars_str = ' '.join(f'{k}={v}' for k, v in extra_vars.items())
        command += ['--extra-vars', extra_vars_str]
    logging.info(command)

    return run_process_real_time(command)

def get_remote_build_log(build_id: str, verbose: bool=False):
    request = Request()
    click.echo(f"== ADBS == Retrieving build log for {build_id}...\n")

    # 2) Get the log, if live then stream, otherwise compelete log will be returned
    request = Request()
    request.set_endpoint(ApiEndpoints.BUILD_LOG,
                         id=build_id)
    response = request.get_streaming_request(log=verbose)
    try:
        response.raise_for_status()
            
        for line in response.iter_lines(chunk_size=8192):
            if line:
                try:
                    line_str = line.decode('utf-8')
                    if verbose:
                        click.echo(f"Decoded line: {line_str}")
                        
                    log_entry = json.loads(line_str)

                    click.echo(log_entry['log'])

                except json.JSONDecodeError as e:
                    if verbose:
                        click.echo(f"JSON decode error: {e}")
                        click.echo(f"Failed to parse JSON from line: {line.decode('utf-8', errors='replace')}")
                except Exception as e:
                    if verbose:
                        click.echo(f"Error processing line: {e}")
    
    except Exception as e:
        click.echo(f"Error retrieving build log: {e}")
    
    click.echo(f"\n== ADBS == Build log retrieval completed for {build_id}")

@click.command()
def configure_user():
    """Configure user to authorize commands"""
    # Create the ~/.profile.d directory if it doesn't exist
    profile_d_dir = os.path.expanduser("~/.profile.d")
    if (not os.path.exists(profile_d_dir)):
        click.echo("== ADBS == Error ~/.profile.d does not exist. Ensure you are on dev server")
        return
    
    # Path to the sw_factory.conf file
    conf_file = os.path.join(profile_d_dir, "sw_factory.conf")

    # Reset the sw_factory.conf if it already exists
    if os.path.exists(conf_file):
        os.remove(conf_file)

    github_uname = input(f"{INPUT_PREFIX}Specify GitHub username: ")

    # Content to write
    write_env = f"""# Build System CLI Configuration\nexport AD_BUILD_GH_USER={github_uname}\n
export AD_BUILD_SCRATCH="/sdf/group/ad/eed/ad-build/scratch"\n
export AD_BUILD_PROD=1
"""
    auto_complete_script = """
_bs_completion() {
local IFS=$'\n'
local response

response=$(env COMP_WORDS="${COMP_WORDS[*]}" COMP_CWORD=$COMP_CWORD _BS_COMPLETE=bash_complete $1)

for completion in $response; do
    IFS=',' read type value <<< "$completion"

    if [[ $type == 'dir' ]]; then
        COMPREPLY=()
        compopt -o dirnames
    elif [[ $type == 'file' ]]; then
        COMPREPLY=()
        compopt -o default
    elif [[ $type == 'plain' ]]; then
        COMPREPLY+=($value)
    fi
done

return 0
}

_bs_completion_setup() {
complete -o nosort -F _bs_completion bs
}

_bs_completion_setup;
"""
    write_env += auto_complete_script
    # Write to sw_factory.conf
    with open(conf_file, "a") as outfile:
        outfile.write(write_env)
    
    click.echo(f"** Successfully added to {conf_file} **")
    click.echo(f"Please source {conf_file} or reload your shell to apply changes.")

@click.command()
@click.option("-c", "--component", required=False, help="Component Name")
@click.option("-b", "--branch", required=False, help="Branch Name")
@click.option("-v", "--verbose", is_flag=True, required=False, help="More detailed output")
def clone(component: str, branch: str="main", verbose: bool=False):
    """Clone an existing component/branch"""

    # 1) Set fields
    request = Request()
    # request.set_component_fields()

    # 2) Request for all components
    request.set_endpoint(ApiEndpoints.COMPONENT)
    response = request.get_request(log=verbose)

    component_list_payload = response.json()['payload']

    # 3) Check for a match on component name, then get URL
    # Define the key you are searching for
    search_key = 'name'

    # 4) Prompt user if component not given, set autocomplete
    if (not component): 
    # Iterate over the list of dictionaries and get their names
        component_name_list = []
        for item in component_list_payload:
            if search_key in item:
                component_name_list.append(item[search_key])

        AutoComplete.set_auto_complete_vals('component', component_name_list)
        component = input("Specify name of component (tab-complete): ")
    
    if (component):
    # 5) Get component ssh url and clone
        # Using list comprehension to filter dictionaries where the key matches the value
        component_dict = next((d for d in component_list_payload if d.get('name') == component), None)
        if (component_dict): # Found a match
            component_url = component_dict["ssh"]
            dir_path = os.path.join(os.getcwd(), component)
            git.Repo.clone_from(component_url, dir_path, progress=SimpleProgress(), branch=branch)
            click.echo("Successfully cloned component " + component_url)
        else: # No match
            click.echo(f"Value '{component}' not found in any of the dictionaries.")
        


@click.command()
@click.option("-c", "--component", required=False, help="Component Name")
@click.option("-b", "--branch", required=False, help="Branch Name")
@click.option("-l", "--log", is_flag=True, required=False, help="Retrieve log of a remote build")
# @click.option("-lc", "--local", is_flag=True, required=False, help="Local build")
# @click.option("-r", "--remote", is_flag=True, required=False, help="Remote build")
# @click.option("-cn", "--container", is_flag=True, required=False, help="Container build")
@click.option("-v", "--verbose", is_flag=True, required=False, help="More detailed output")
def build(component: str, branch: str, log: bool, remote: bool=True, local: bool=False, container: bool=False, verbose: bool=False):
    """Trigger a remote build"""
    ## Commented out Local and Container options for now, just default to remote builds
    request = Request(Component(component, branch))
    request.set_component_fields()
    # 0) Special case, if log only
    if (log):
        # Get user input
        know_id = click.confirm("Do you know the build ID?")
        if know_id:
            build_id = input(f"{INPUT_PREFIX} Specify build id: ")
        else:
            # Get all the build ids available, then show the top 5 most recent ones 
            # and ask user to select which one they want to view
            request.set_endpoint(ApiEndpoints.BUILD_BRANCH,
                                 component_name=request.component.name,
                                 branch_name=request.component.branch_name)
            response = request.get_request(log=verbose).json()
            builds = response['payload']
            
            if not builds:
                click.echo("== ADBS == No recent builds found.")
                return

            # Sort builds by createdDate in descending order and get the top 5 builds
            sorted_builds = sorted(builds, key=lambda x: x.get('createdDate', ''), reverse=True)[:5]

            # (for header) - Find the maximum width for each column
            max_date_width = max(len(build['createdDate']) for build in sorted_builds)
            max_id_width = max(len(build['id']) for build in sorted_builds)
            max_status_width = max(len(build['buildStatus']) for build in sorted_builds)
            max_os_width = max(len(build['buildOs']) for build in sorted_builds)

            # Print the header
            click.echo("Recent builds:")
            click.echo(f"{'#':<3} {'Date':<{max_date_width}} | {'Build ID':<{max_id_width}} | {'Status':<{max_status_width}} | {'OS':<{max_os_width}}")
            click.echo("-" * (3 + max_date_width + max_id_width + max_status_width + max_os_width + 9))  # 9 for extra spaces and |

            # Print the builds
            for idx, build in enumerate(sorted_builds, 1):
                click.echo(f"{idx:<3} {build['createdDate']:<{max_date_width}} | {build['id']:<{max_id_width}} | {build['buildStatus']:<{max_status_width}} | {build['buildOs']:<{max_os_width}}")
            
            while True:
                choice = click.prompt("Choose a build number", type=int)
                if 1 <= choice <= len(sorted_builds):
                    build_id = sorted_builds[choice - 1]['id']
                    break
                click.echo("Invalid choice. Please try again.")

        get_remote_build_log(build_id, verbose)
        return

    # 1) Set fields
    request.add_to_payload("ADBS_COMPONENT", request.component.name)
    request.add_to_payload("ADBS_BRANCH", request.component.branch_name)
    # 2) Prompt if local or remote build
    if (not local and not remote and not container):
        question = [inquirer.List(
                "build_type",
                message="Specify type of build",
                choices=["LOCAL", "REMOTE", "CONTAINER"])]
        build_type = inquirer.prompt(question)['build_type']
    elif (local):
        build_type = "LOCAL"
    elif (remote):
        build_type = "REMOTE"
    elif (container):
        build_type = "CONTAINER"

    ## Local build
    if (build_type == "LOCAL"):
        # 1) Clone repo if doesn't exist in user space
        clone_repo(request)
        # 2) Parse manifest
        user_src_repo = request.component.git_get_top_dir()
        manifest_filepath = user_src_repo + '/config.yaml'
        manifest_data = request.component.parse_manifest(manifest_filepath)
        build_os_list = manifest_data["environments"]
        manifest_data = json.dumps(manifest_data) # Serialize dictionary to JSON string to pass
        # 3) shell into the build environment, and run local_build() in there
        for build_os in build_os_list:
            build_os = build_os.lower()
            click.echo(f"== ADBS == Building for architecture: {build_os}")
            if (build_os == "rocky9"):
                build_os == "rhel9"
            build_img = cli_configuration["build_images_filepath"] + build_os + '-env/' + build_os + '-env_latest.sif'
            # manifest_data = f"'{manifest_data}'"
            user_src_repo_bind = user_src_repo + ":" + user_src_repo
            dependencies_bind = "/sdf/sw/:/sdf/sw/"
            afs_dependencies_bind = "/afs/:/afs/"
            ad_group_bind = "/sdf/group/ad/:/mnt/"
            build_command = ["apptainer", "exec", "--writable-tmpfs", "--bind", afs_dependencies_bind, "--bind", user_src_repo_bind, "--bind", 
                            dependencies_bind, "--bind", ad_group_bind, build_img, "bash", "/build/local_build.sh",
                            manifest_data, user_src_repo, request.component.name, request.component.branch_name, build_os]
            run_process_real_time(build_command)

    ## Remote build
    elif (build_type == "REMOTE"):
        # 2) Send request to backend
        request.set_endpoint(ApiEndpoints.BUILD_BRANCH,
                        component_name=request.component.name,
                        branch_name=request.component.branch_name)
        request.add_to_payload("ADBS_BUILD_TYPE", "normal")
        payload = request.post_request(log=verbose, msg="Start remote build id")
        build_id = payload.json()['payload'][0] # TODO: This payload returns list of build ids, but since we only expect one os for now, get the first item

        # 3) Get the live log output:
        get_remote_build_log(build_id, verbose)

    ## Container build
    elif (build_type == "CONTAINER"): # (NOTE - this feature will be long-term goal and is not priority atm)
        under_development() # TODO

@click.command()
@click.option("-c", "--component", required=False, help="Component Name")
@click.option("-b", "--branch", required=False, help="Branch Name")
@click.option("-q", "--quick", is_flag=True, required=False, help="Quick tests")
@click.option("-m", "--main", is_flag=True, required=False, help="Main tests")
@click.option("-v", "--verbose", is_flag=True, required=False, help="More detailed output")
def test(component: str, branch: str, quick: bool, main: bool, verbose: bool=True):
    """Trigger a test"""
    under_development() # TODO
    # 1) Set fields
    request = Request(Component(component, branch))
    request.set_component_fields()
    request.add_to_payload("ADBS_COMPONENT", request.component.name)
    request.add_to_payload("ADBS_BRANCH", request.component.branch_name)

    # 2) Send request to backend
    endpoint = 'test/component/' + request.component.name + '/branch/' + request.component.branch_name
    request.set_endpoint(endpoint)
    request.post_request(log=verbose, msg="Test")

@click.command()
@click.option("-c", "--component", required=False, help="Component Name")
@click.option("-f", "--facility", required=False, help="Deploy only to the specified facility(s). Put 'ALL' for all facilities. | Options: [dev, lcls, facet, testfac] Seperate facilties by comma, ex: dev,lcls")
@click.option("-ts", "--test", is_flag=True, required=False, help="Deploy to test stand")
@click.option("-i", "--ioc", required=False, help="Deploy only to the specified ioc(s). If 'ALL', all iocs in facilities specified by facility arg will be deployed. Seperate iocs by comma, ex: sioc-sys0-test1,sioc-sys0-test2.")
@click.argument("tag", required=False)
@click.option("-ls", "--list", is_flag=True, required=False, help="List the active releases")
# @click.option("-l", "--local", is_flag=True, required=False, help="Deploy local directory instead of the artifact storage")
@click.option("-r", "--revert", is_flag=True, required=False, help="Revert to previous version")
# @click.option("-o", "--override", is_flag=True, required=False, help="Point local DEV deployment to your user-space repo")
@click.option("-n", "--dry-run", is_flag=True, required=False, help="Print the commands that would be executed, but do not execute them.")
@click.option("-v", "--verbose", is_flag=True, required=False, help="More detailed output")
def deploy(component: str, facility: str, test: bool, ioc: str, tag: str, list: bool,
            revert: bool, dry_run: bool, verbose: bool):
    """Trigger a deployment. Automatically deploys app and ioc(s) to the tag you choose. Facility is automatically determined by ioc.
        Will automatically pickup app in the directory you're sitting in.
    """
    # 1) Set fields
    deployment_request = Request(Component(component), Api.DEPLOYMENT)    
    deployment_request.set_component_name()

    # Get app type
    user_src_repo = deployment_request.component.git_get_top_dir()
    manifest_filepath = user_src_repo + '/config.yaml'
    manifest_data = deployment_request.component.parse_manifest(manifest_filepath)
    deployment_type = manifest_data['deploymentType'].lower()

    # 1.1) Option - test
    if (test):
        under_development()

    # 1.2) Option - local
    # if (local):
    #     under_development()

    # 1.3) Option - revert
    if (revert):
        under_development()

    # 1.2) Option - list
    if (list):
        deployment_request.add_to_payload("component_name", deployment_request.component.name)
        deployment_request.set_endpoint(ApiEndpoints.DEPLOYMENT_INFO)
        response = deployment_request.get_request(log=verbose)
        if (not response.ok):
            click.echo(f"== ADBS == Error - {response.json()}")
            return
        payload = response.json()['payload']
        # Loop through the list of deployment entries (one for each facility if exists)
        for deployment in payload:
            # Extract the inner dictionary (assuming there's only one item at the top level)
            for facility, details in deployment.items():
                # Print the facility with color
                click.echo("Current versions on facility: ", nl=False)
                click.echo(click.style(details['facility'], fg = 'cyan'))
                # Print the current master release
                click.echo(f"Current master release => {details['tag']}")
                # Loop through the 'dependsOn' list and print each entry
                if (deployment_type == 'ioc'):
                    if (details['dependsOn']):
                        sorted_deps = sorted(details['dependsOn'], key=lambda ioc: ioc['name'])
                        for dep in sorted_deps:
                            click.echo(f"IOC: {dep['name']} => {dep['tag']}")
        return
    # 2) Get fields
    question = [inquirer.Checkbox(
                "facility",
                message="What facilities to deploy to?",
                choices=["DEV", "LCLS", "FACET", "TESTFAC"],
                default=[],
                ),]
    # 4) Error check
    if (deployment_type == 'ioc'):
        if (not facility and not ioc):
            click.echo("== ADBS == Please supply the facility and/or the iocs")
            return
    if (not tag):
        click.echo("== ADBS == Please provide a tag")
        return
    # 5) Get facilities (if applicable)
    user_specified_facilities = []
    if (facility):
        user_specified_facilities = facility.split(',')
        user_specified_facilities = [facility.upper() for facility in user_specified_facilities] # Uppercase every facility

    # 6) Set the arguments needed for playbook
    linux_uname = os.environ.get('USER')
    playbook_args_dict = {
        "facilities": user_specified_facilities,
        "component_name": deployment_request.component.name,
        "tag": tag,
        "user": linux_uname,
        "dry_run": dry_run
    }

    # 7) Figure out what the deployment type is and set the endpoint accordingly
    user_src_repo = deployment_request.component.git_get_top_dir()
    manifest_filepath = user_src_repo + '/config.yaml'

    # 6) Error check - If user specified iocs - Confirm with database that every ioc found in the source tree is in the database.
    if (deployment_type == 'ioc' and ioc): 
        # 6.1) First check that user is in repo
        if (not deployment_request.component.set_cur_dir_component()):
            click.echo('fatal: not a git repository (or any of the parent directories)')
            return
        # 6.2) Get top of git dir
        top_level = deployment_request.component.git_get_top_dir()
        # 6.3) Enter iocBoot/ dir
        ioc_boot_dir = os.path.join(top_level, 'iocBoot')
        os.chdir(ioc_boot_dir)
        # 6.4) get a list of all directories that start with ioc/eioc/sioc/vioc 
        all_ioc_dirs = []
        for item in os.listdir('.'):
            if os.path.isdir(item) and (item.startswith('ioc') or 
                                    item.startswith('eioc') or 
                                    item.startswith('sioc') or 
                                    item.startswith('vioc')):
                all_ioc_dirs.append(item)

        facilities_to_loop = ["DEV", "LCLS", "FACET", "TESTFAC", "S3DF"]    
        all_iocs_in_db = []
        user_specified_facilities_iocs_in_db = [] 
        for facility in facilities_to_loop: # Get every ioc from each facility
            iocs_in_db = []
            active_deployment_request = Request(deployment_request.component.name)
            active_deployment_request.set_endpoint(ApiEndpoints.DEPLOYMENT_FACILITIY,
                                                    component_name=deployment_request.component.name,
                                                    facility=facility)
            response = active_deployment_request.get_request(log=verbose)
            if (not response.ok): # Skip if no ioc found in facility
                continue

            payload = response.json()['payload']
            # Extract IOCs from the dependsOn list in the payload
            for entry in payload.get('dependsOn', []):
                iocs_in_db.append(entry.get('name'))

            all_iocs_in_db += iocs_in_db
            if (len(user_specified_facilities) > 0):
                if (facility in user_specified_facilities): # If user specified facilities, then only deploy to all IOCs in those facilities
                    user_specified_facilities_iocs_in_db += iocs_in_db

        if (ioc.upper() != "ALL"): # User specified IOCs
            ioc_list = ioc.split(',')
            missing_iocs = [user_specified_ioc for user_specified_ioc in ioc_list if user_specified_ioc not in all_ioc_dirs]
            if (missing_iocs):
                # Error check - there is an ioc that user specified that does not exist in the source tree
                click.echo("== ADBS == ERROR: The following IOCs are not in your application iocBoot/ dir:")
                for ioc in missing_iocs:
                    click.echo(f"  - {ioc}")
                click.echo("== ADBS == Please double check if you made a typo.")
                return
            
            # Error check - If IOC specified but no facility (then its an existing IOC). Make sure it exists in the db
            if (len(user_specified_facilities) < 1):
                new_iocs = [user_specified_ioc for user_specified_ioc in ioc_list if user_specified_ioc not in all_iocs_in_db]
                if new_iocs:
                    click.echo("== ADBS == The following IOCs are not in the deployment database:")
                    for ioc in new_iocs:
                        click.echo(f"  - {ioc}")
                    click.echo("== ADBS == The new IOCs need to be deployed seperately with only one facility specified")
                    return
                
            elif (len(user_specified_facilities) > 1):
                # Can't have more than one facility for new IOCs.
                click.echo("== ADBS == ERROR: Can't deploy new IOC(s) to more than one facility. Please specify only one facility for your new IOC(s)")
                return
            playbook_args_dict["ioc_list"] = ioc_list

        # If user specified ALL iocs, then check if facilities specified
        if (ioc.upper() == "ALL"):
            # 6.6) Find IOCs that are in our directory but not in the deployment database
                # Which means these are new IOCs
            new_iocs = [ioc for ioc in all_ioc_dirs if ioc not in all_iocs_in_db]

            # Set the ioc_list to deploy
            if (len(user_specified_facilities) > 0):
                ioc_list = user_specified_facilities_iocs_in_db
            else:
                ioc_list = all_iocs_in_db
            
            if new_iocs:
                click.echo("== ADBS == The following IOCs are not in the deployment database:")
                for ioc in new_iocs:
                    click.echo(f"  - {ioc}")
                if (len(user_specified_facilities) == 1):
                    if (click.confirm("Do you want to deploy ALL iocs *including* the new ones listed above?")):
                        ioc_list += new_iocs
                        playbook_args_dict["ioc_list"] = ioc_list
                    else:
                        if (click.confirm("Do you want to deploy ALL iocs *excluding* the new ones listed above?")):
                            playbook_args_dict["ioc_list"] = ioc_list
                        else:
                            click.echo("== ADBS == Please specify which IOCs you want to deploy if not ALL")          
                            return
                else: # Either more than one facility or no faciltiies specified and there are new iocs found
                    if (not click.confirm("Do you want to proceed deploying ALL iocs *excluding* the new ones listed above?")):
                        click.echo("== ADBS == The new IOCs need to be deployed seperately with only one facility specified")
                        return
                playbook_args_dict["ioc_list"] = ioc_list

    # Set subsystem for pydm
    if (deployment_type == 'pydm'):
        subsystem = deployment_request.component.name.replace("pydm-", "") # Remove "pydm-"
        playbook_args_dict["subsystem"] = subsystem
        # Error check - For pydm deployments, there can be a pydm subsystem for more than one facility
        # So user_specified_facilities is required.
        if (len(user_specified_facilities) < 1):
            click.echo("== ADBS == ERROR: Please specify the facility(s)")

    # 7) If revert then send deployment revert request to deployment controller
    if (revert):
        # TODO: Revert endpoint
        deployment_request.set_endpoint(ApiEndpoints.DEPLOYMENT_REVERT,
                                        deployment_type=deployment_type)
    else:
        # 8) Send deployment request to deployment controller
        deployment_request.set_endpoint(ApiEndpoints.DEPLOYMENT,
                                        deployment_type=deployment_type)
    deployment_request.add_dict_to_payload(playbook_args_dict)
    if (len(user_specified_facilities) > 0):
        click.echo("== ADBS == Deploying to " + str(user_specified_facilities) + "...")
    else:
        click.echo("== ADBS == Deploying...")
    click.echo("== ADBS == This may take a minute (or longer if there are many iocs)")
    response = deployment_request.put_request(log=verbose)
    if (not response.ok):
        try:
            click.echo(f"== ADBS == Error: {response.json()}")
            return
        except Exception:
            pass
    # 9) Prompt user if they want to download and view the report
    # Get the file content from the response
    file_content = response.content.decode('utf-8')
    # Get the home directory of the current user
    home_directory = os.path.expanduser("~")
    # Get the local timezone of the computer
    local_tz = datetime.now().astimezone().tzinfo
    timestamp = datetime.now(local_tz).strftime("%Y-%m-%dT%H-%M-%S")
    file_path = f"{home_directory}/deployment-report-{deployment_request.component.name}-{tag}-{timestamp}.log"
    click.echo(f"== ADBS == Deployment finished, report will be downloaded at {file_path}")
    new_file_path = input(INPUT_PREFIX + "Confirm by 'enter', or specify alternate path:")
    if (new_file_path):
        file_path = new_file_path
    with open(file_path, "w") as report_file:
        report_file.write(file_content)
        # Read out the head of the report
    with open(file_path, "r") as report_file:
        summary = [report_file.readline() for _ in range(7)]
    click.echo("Report head:")
    for line in summary:
        click.echo(line, nl=False)
    click.echo(f"\nReport downloaded successfully to {file_path}")

    # 5) Call the deployment controller to deploy for each facility (unless dev then call locally)
    # TODO: Local deployment - if want local deployment, then user must follow the steps to ensure ansible can ssh from s3df to prod. 
    # The steps are outlined in Jira issue EEDSWCM-69. but if its local deployment, then its essentially cram.
    # if (local):
    # for facility in facilities:
    #     click.echo(f"== ADBS == Deploying to facility: {facility}\n")
    #     playbook_args_dict['facility'] = facility
            
    # TODO: Come back to this logic here for local directory deployments
    # # 5.1) If deploying on DEV, then just call playbook directly here, then api call to deployment to add to db
    #     if ('S3DF' in facilities):
    #         playbook_output_path = os.getcwd() + "/ADBS_TMP"
    #         user_src_repo = deployment_request.component.git_get_top_dir()
    #         tarball_path = user_src_repo + '/build_results/'
    #         tarball = str(find_tarball(tarball_path))
    #         if (tarball == None):
    #             click.echo("== ADBS == No tarball found in " + tarball_path)
    #         playbook_args_dict['tarball'] = tarball
    #         playbook_args_dict['user_src_repo'] = None
    #         if (override == True):
    #             playbook_args_dict['user_src_repo'] = user_src_repo

    #         isExist = os.path.exists(playbook_output_path)
    #         if not isExist:
    #             click.echo(f"== ADBS == Adding a {playbook_output_path} dir for deployment playbook output. You may delete if unused")
    #             os.mkdir(playbook_output_path)
    #         adbs_playbooks_dir = cli_configuration["build_system_filepath"] + "ansible/ioc_module/" # TODO: Change this once official

    #         return_code = run_ansible_playbook(adbs_playbooks_dir + 'global_inventory.ini',
    #                                         adbs_playbooks_dir + 'ioc_deploy.yml',
    #                                             facility,
    #                                             playbook_args_dict)
    #         click.echo("Playbook execution finished with return code:", return_code)
    #         # TODO: API call to deployment controller to add deployment info to db
    #     else: # 5.2) Otherwise deployment controller will deploy to production facilities
    #         deployment_request.set_endpoint('ioc/deployment')
    #         deployment_request.add_dict_to_payload(playbook_args_dict)
    #         click.echo("== ADBS == Deploying to " + facility + "...")
    #         deployment_request.put_request(log=verbose, msg="Remote deployment")
    #     if (initial):
    #         click.echo("== ADBS == Please create startup.cmd manually!")

@click.command()
@click.option("-c", "--component", required=False, help="Component Name")
@click.option("-b", "--branch", required=False, help="Branch Name")
@click.option("-cl", "--clear", is_flag=True, required=False, help="Clear branch readiness status")
@click.option("-v", "--verbose", is_flag=True, required=False, help="More detailed output")
def mark(component: str, branch: str, clear: bool, verbose: bool=False):
    """Mark a branch as ready for review/complete"""
    # 1) Set fields
    request = Request(Component(component, branch))
    request.set_component_fields()

    # 2) Send request to backend
    endpoint = 'component/' + request.component.name + '/branch/' + request.component.branch_name + '/ready/'
    if (clear):
        endpoint += 'false'
    else:
        endpoint += 'true'
    request.set_endpoint(endpoint)
    if (clear):
        request.put_request(log=verbose, msg="Mark branch clear")
    else:
        request.put_request(log=verbose, msg="Mark branch")