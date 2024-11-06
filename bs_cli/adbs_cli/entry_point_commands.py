import click
import yaml
import os
import git
import ansible_runner # TODO: Move to its own module once done testing
import inquirer
import json
import logging
import subprocess
import pathlib
from adbs_cli.component import Component
from adbs_cli.request import Request
from adbs_cli.cli_configuration import INPUT_PREFIX, Api, under_development, cli_configuration
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

def parse_manifest(filename: str) -> dict:
    # Parse manifest - filepath is only here, so if ever need to change its only one location
    with open(filename, 'r') as file:
        yaml_data = yaml.safe_load(file)
    logging.info(yaml_data)
    return yaml_data

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
    print(command)
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    # Print output in real-time
    for line in iter(process.stdout.readline, ''):
        print(line, end='')  # Print each line as it is output

    # Ensure all stderr is also handled
    for line in iter(process.stderr.readline, ''):
        print(line, end='')

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

@click.command()
def configure():
    """Configure to authorize commands"""
    linux_uname = os.environ.get('USER')
    # get github name from environment as well, if not then prompt user
    github_uname = os.environ.get('AD_BUILD_GH_USER')
    if (github_uname): 
        click.echo('CLI already configured.')
    else:
        github_uname = input('What is your github username? ')
        # TODO: Either write to bashrc from here, or have them put it themselves
        write_env = "\n\n# Build System CLI Configuration\
                    \nexport AD_BUILD_GH_USER=" + github_uname
        with open(os.path.expanduser("~/.bashrc"), "a") as outfile:
            # 'a' stands for "append"  
            outfile.write(write_env)
        click.echo("** Successfully added to .bashrc **\n" + \
                    "Please 'source ~" + linux_uname + "/.bashrc' or reload shell")

@click.command()
@click.option("-c", "--component", required=False, help="Component Name")
@click.option("-b", "--branch", required=False, help="Branch Name")
def clone(component: str, branch: str="main"):
    """Clone an existing component/branch"""

    # 1) Set fields
    request = Request()
    # request.set_component_fields()

    # 2) Request for all components
    endpoint = 'component'
    request.set_endpoint(endpoint)
    response = request.get_request(log=False)

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
    # 5) Get component URL and clone
        # Using list comprehension to filter dictionaries where the key matches the value
        component_dict = next((d for d in component_list_payload if d.get('name') == component), None)
        if (component_dict): # Found a match
            component_url = component_dict["url"]
            dir_path = os.path.join(os.getcwd(), component)
            git.Repo.clone_from(component_url, dir_path, branch=branch)
            print("Successfully cloned component " + component_url)
        else: # No match
            print(f"Value '{component}' not found in any of the dictionaries.")
        


@click.command()
@click.option("-c", "--component", required=False, help="Component Name")
@click.option("-b", "--branch", required=False, help="Branch Name")
@click.option("-l", "--local", is_flag=True, required=False, help="Local build")
@click.option("-r", "--remote", is_flag=True, required=False, help="Remote build")
@click.option("-cn", "--container", is_flag=True, required=False, help="Container build")
def build(component: str, branch: str, local: bool, remote: bool, container: bool):
    """Trigger a build [local | remote | container]"""
    # 1) Set fields
    request = Request(Component(component, branch))
    request.set_component_fields()
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
        manifest_data = parse_manifest(manifest_filepath)
        manifest_data = json.dumps(manifest_data) # Serialize dictionary to JSON string to pass
        # 3) #TODO: Shell into the build environment, and run local_build() in there
        # # TODO: For now just run the build on rhel7, can ask later what OS to use, or maybe both?
        build_os = "rhel7"
        build_img = cli_configuration["build_images_filepath"] + 'rhel7-env/rhel7-env_latest.sif'
        # manifest_data = f"'{manifest_data}'"
        user_src_repo_bind = user_src_repo + ":" + user_src_repo
        dependencies_bind = "/sdf/sw/:/sdf/sw/"
        # build_command = f"apptainer exec --bind {user_src_repo}:{user_src_repo} --bind /sdf/sw/:/sdf/sw/ {build_img} python3 /build/local_build.py {manifest_data} {user_src_repo} {request.component.name} {request.component.branch_name}"
        build_command = ["apptainer", "exec", "--bind", user_src_repo_bind, "--bind", 
                         dependencies_bind, build_img, "python3", "/build/local_build.py",
                         manifest_data, user_src_repo, request.component.name, request.component.branch_name, build_os]
        run_process_real_time(build_command)

    ## Remote build
    elif (build_type == "REMOTE"):
        # 2) Send request to backend
        endpoint = 'build/component/' + request.component.name + '/branch/' + request.component.branch_name
        request.set_endpoint(endpoint)
        request.add_to_payload("ADBS_BUILD_TYPE", "normal")
        request.post_request(log=True)
        
    ## Container build
    elif (build_type == "CONTAINER"): # (NOTE - this feature will be long-term goal and is not priority atm)
        under_development() # TODO

@click.command()
@click.option("-c", "--component", required=False, help="Component Name")
@click.option("-b", "--branch", required=False, help="Branch Name")
def test(component: str, branch: str):
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
    request.post_request(log=True)

@click.command()
@click.option("-c", "--component", required=False, help="Component Name")
@click.option("-b", "--branch", required=False, help="Branch Name")
@click.option("-f", "--facility", required=False, help="Deploy only to the specified facility(s). Put 'ALL' for all facilities. | Options: [s3df, lcls, facet, testfac] Seperate iocs by comma, ex: s3df,lcls")
@click.option("-t", "--type", required=False, help="App Type | Options: [ioc, hla, tools, matlab, pydm]")
@click.option("-i", "--ioc", required=False, help="Deploy only to the specified ioc(s). If 'ALL', all iocs in facilities specified by facility arg will be deployed. Seperate iocs by comma, ex: sioc-sys0-test1,sioc-sys0-test2. *Under construction - bs figure out what facility the IOC belongs to")
@click.argument("tag")
@click.option("-in", "--initial", is_flag=True, required=False, help="Initial deployment (required if never deployed app/ioc - idempotent)")
@click.option("-o", "--override", is_flag=True, required=False, help="Point local DEV deployment to your user-space repo")
def deploy(component: str, branch: str, facility: str, type: str,
                ioc: str, tag: str, initial: bool, override: bool):
    """Trigger a deployment. Automatically deploys app and ioc(s) to the tag you choose. Facility is automatically determined by ioc.
        Will automatically pickup app in the directory you're sitting in.
    """
    # 1) Set fields
    deployment_request = Request(Component(component, branch), Api.DEPLOYMENT)    
    deployment_request.set_component_fields()

    # 2) Get fields
    print("== ADBS == At the moment, deployment only for IOCs is supported")

    # TODO: Add logic for figuring out what type of deployment this is, maybe in config.yaml / database
    # question = [inquirer.List(
    #             "app_type",
    #             message="Specify type of ioc",
    #             choices=["SIOC", "HIOC", "VIOC"])]
    # ioc_type = inquirer.prompt(question)['ioc_type']
    # Unnecessary to prompt for this
    # question = [inquirer.List(
    #             "initial",
    #             message="Initial deployment?",
    #             choices=[True, False])]
    # if (not initial):
    #     initial = inquirer.prompt(question)['initial']
    # Unnecessary to prompt for this
    # question = [inquirer.List(
    #             "override",
    #             message="Point deployment to your user-space repo?",
    #             choices=[True, False])]
    # if (not override):
    #     override = inquirer.prompt(question)['override']
    question = [inquirer.Checkbox(
                "facility",
                message="What facilities to deploy to? (Arrow keys for selection, enter if done)",
                choices=["S3DF", "LCLS", "FACET", "TESTFAC"],
                default=[],
                ),]
    # 3) Get ioc list for each facility
    if (ioc):
        ioc_list = ioc.split(',')

    # TODO: Temporarily commented out for demo
    # # TODO: Add logic so every facility has their own list of iocs
    # if (ioc.upper() == "ALL"):
    #     # 3.1) If 'ALL' then determine which facilities for all iocs the user wants
    #     if (not facility):
    #         facilities = inquirer.prompt(question)['facility']
    #         pass
    #     else:
    #         facilities = facility.split(',')
    #         print(f'facilities: {facilities}')
    #     facilities = [facility.upper() for facility in facilities] # Uppercase every facility

    #     facility_ioc_dict = {}
    #     for facility in facilities: # Get list of iocs from every facility user chose for this app
    #         ioc_list_request = Request(api=Api.DEPLOYMENT)
    #         ioc_list_request.set_endpoint(f'ioc/info')
    #         ioc_list_request.add_to_params("name", deployment_request.component.name)
    #         ioc_list_request.add_to_params("facility", facility)
    #         response = ioc_list_request.get_request()
    #         if (response.status_code == 200):
    #             ioc_list = response.json()['info']['iocs']
    #             facility_ioc_dict[facility] = ioc_list
    #     logging.info(f"ALL ioc's in facilities you specified: {facility_ioc_dict}")
    #     pass
    # elif (ioc_list == []):
    #     # 3.2) Possible user just wants to deploy app and not any ioc
    #     print("== ADBS == No IOC's were specified, only deploying application")
    # else:
    #     if (initial):
    #         # 3.3) TODO: If initial deployment, ask user for facility they want to deploy specified ioc's
    #         pass
    #     else:
    #         # 3.4) if not 'ALL', then figure out what ioc's specified by user belong to what facilities
    #         # TODO: logic to determine what ioc belongs in which facility, if iocs are not found in any facility
    #         # THEN WARN USER NOT FOUND, and ask if initial deployment or if a typo on their end
    #         pass

    # <<<<<<<< TODO: Temporary placeholder code for a basic local deployment
    if (not facility):
        facilities = inquirer.prompt(question)['facility']
    else:
        facilities = facility.split(',')
        print(f'facilities: {facilities}')
    facilities = [facility.upper() for facility in facilities] # Uppercase every facility
    # >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>

    # 4) Set the arguments needed for playbook
    linux_uname = os.environ.get('USER')
    playbook_args_dict = {
        "facility": None, # Get's set later
        "initial": initial,
        "component_name": deployment_request.component.name,
        "tag": tag,
        "user": linux_uname,
        "ioc_list": ioc_list
    }

    # 5) Call the deployment controller to deploy for each facility (unless dev then call locally)
    for facility in facilities:
        print(f"== ADBS == Deploying to facility: {facility}\n")
        playbook_args_dict['facility'] = facility
            
    # 5.1) If deploying on DEV, then just call playbook directly here, then api call to deployment to add to db
        if ('S3DF' in facilities):
            playbook_output_path = os.getcwd() + "/ADBS_TMP"
            user_src_repo = deployment_request.component.git_get_top_dir()
            tarball_path = user_src_repo + '/build_results/'
            tarball = str(find_tarball(tarball_path))
            if (tarball == None):
                print("== ADBS == No tarball found in " + tarball_path)
            playbook_args_dict['tarball'] = tarball
            playbook_args_dict['user_src_repo'] = None
            if (override == True):
                playbook_args_dict['user_src_repo'] = user_src_repo

            isExist = os.path.exists(playbook_output_path)
            if not isExist:
                print(f"== ADBS == Adding a {playbook_output_path} dir for deployment playbook output. You may delete if unused")
                os.mkdir(playbook_output_path)
            adbs_playbooks_dir = cli_configuration["build_system_filepath"] + "ansible/ioc_module/" # TODO: Change this once official

            return_code = run_ansible_playbook(adbs_playbooks_dir + 'global_inventory.ini',
                                            adbs_playbooks_dir + 'ioc_deploy.yml',
                                                facility,
                                                playbook_args_dict)
            print("Playbook execution finished with return code:", return_code)
            # TODO: API call to deployment controller to add deployment info to db
        else: # 5.2) Otherwise deployment controller will deploy to production facilities
            deployment_request.set_endpoint('ioc/deployment')
            deployment_request.add_dict_to_payload(playbook_args_dict)
            deployment_request.put_request(log=True)
        if (initial):
            print("== ADBS == Please create startup.cmd manually!")
