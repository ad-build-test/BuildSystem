import click
import yaml
import os
import ansible_runner # TODO: Move to its own module once done testing
import inquirer
import json
import logging
import subprocess
import pathlib
from adbs_cli.component import Component
from adbs_cli.request import Request
from adbs_cli.cli_configuration import INPUT_PREFIX

# TODO: May make logic a single function since its the same for all 3
# make the endpoint an argument
@click.group()
def run():
    """Run a [ build | deployment | test ]"""
    pass

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

def parse_manifest() -> dict:
    # Parse manifest - filepath is only here, so if ever need to change its only one location
    yaml_filepath = 'CONFIG.yaml' 
    with open(yaml_filepath, 'r') as file:
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

def run_ansible_playbook(inventory, playbook, host_pattern, extra_vars):
    os.environ['ANSIBLE_FORCE_COLOR'] = 'true'
    command = [
        'ansible-playbook', 
        '-i', inventory,
        '-l', host_pattern,
        playbook
    ]

    if extra_vars:
        extra_vars_str = ' '.join(f'{k}={v}' for k, v in extra_vars.items())
        command += ['--extra-vars', extra_vars_str]

    # Use subprocess.Popen to forward output directly
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

@run.command()
@click.option("-c", "--component", required=False, help="Component Name")
@click.option("-b", "--branch", required=False, help="Branch Name")
@click.option("-l", "--local", is_flag=True, required=False, help="Local build")
@click.option("-r", "--remote", is_flag=True, required=False, help="Remote build")
@click.option("-cn", "--container", is_flag=True, required=False, help="Container build")
def build(component: str, branch: str, local: bool, remote: bool, container: bool):
    """Trigger a build (local | remote | container)"""
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
        manifest_data = parse_manifest()
        # 3) Run the script or build command
        # Assuming the script exists at the $TOP of the repo
        print("== ADBS == Running Build:")
        if (manifest_data['build'].endswith('.sh')):
            build_script = './' + manifest_data['build']
            result = subprocess.run(['bash', build_script], capture_output=True, text=True)
        elif (manifest_data['build'].endswith('.py')):
            build_script = manifest_data['build']
            result = subprocess.run(['python', build_script], capture_output=True, text=True)
        else: # Run the command directly
            build_command = manifest_data['build']
            result = subprocess.run([build_command], capture_output=True, text=True)
        print('== ADBS == output:', result.stdout)
        print('== ADBS == errors:', result.stderr)
        user_src_repo = request.component.git_get_top_dir()
        playbook_args = f'{{"component": "{request.component.name}", "branch": "{request.component.branch_name}", \
            "user_src_repo": "{user_src_repo}"}}'
        # Convert the JSON-formatted string to a dictionary
        playbook_args_dict = json.loads(playbook_args)
        adbs_playbooks_dir = "/sdf/home/p/pnispero/BuildSystem/ansible/ioc_module/" # TODO: Change this once official
        return_code = run_ansible_playbook(adbs_playbooks_dir + 'global_inventory.ini',
                                adbs_playbooks_dir + 'ioc_build.yml',
                                'S3DF',
                                playbook_args_dict)
        print("Playbook execution finished with return code:", return_code)

    ## Remote build
    elif (build_type == "REMOTE"):
        # 2) Send request to backend
        endpoint = 'build/component/' + request.component.name + '/branch/' + request.component.branch_name
        request.set_endpoint(endpoint)
        request.add_to_payload("ADBS_BUILD_TYPE", "normal")
        request.post_request(log=True)
        
    ## Container build
    elif (build_type == "CONTAINER"): # (NOTE - this feature will be long-term goal and is not priority atm)
        print("== ADBS == ** Container build is not ready, under development **")

@run.command()
@click.option("-c", "--component", required=False, help="Component Name")
@click.option("-b", "--branch", required=False, help="Branch Name")
def test(component: str, branch: str):
    """Trigger a test"""
    # 1) Set fields
    request = Request(Component(component, branch))
    request.set_component_fields()
    request.add_to_payload("ADBS_COMPONENT", request.component.name)
    request.add_to_payload("ADBS_BRANCH", request.component.branch_name)

    # 2) Send request to backend
    endpoint = 'test/component/' + request.component.name + '/branch/' + request.component.branch_name
    request.set_endpoint(endpoint)
    request.post_request(log=True)

@run.command()
@click.option("-c", "--component", required=False, help="Component Name")
@click.option("-b", "--branch", required=False, help="Branch Name")
@click.option("-i", "--initial", is_flag=True, required=False, help="Initial deployment")
@click.option("-o", "--override", is_flag=True, required=False, help="Point deployment to your user-space repo")
def deployment(component: str, branch: str, initial: bool, override: bool):
    """Run a deployment"""
    # 1) Set fields
    request = Request(Component(component, branch))    
    request.set_component_fields()

    # For now assume the user is in the repo they want to deploy
    # TODO: Add logic for cloning repo or just the build results?
    # # 2) If user is not in repo, clone repo
    # clone_repo(request)

    # Parse yaml if user-defined deployment script
    # manifest_data = parse_manifest()

    # 3) Get fields
    print("== ADBS == At the moment, deployment only for IOCs is supported")
        # TODO: There are apps/components which host multiple IOCs, the logic right now assumes
    # 1 ioc for app, so CLI should parse which iocs are available (cram has this down),
    #  then suggest to user which iocs they want to deploy

    # TODO: Add logic for figuring out what type of deployment this is, maybe in config.yaml / database
    # question = [inquirer.List(
    #             "ioc_type",
    #             message="Specify type of ioc",
    #             choices=["SIOC", "HIOC", "VIOC"])]
    # ioc_type = inquirer.prompt(question)['ioc_type']
    question = [inquirer.List(
                "initial",
                message="Initial deployment?",
                choices=[True, False])]
    if (not initial):
        initial = inquirer.prompt(question)['initial']
    question = [inquirer.List(
                "override",
                message="Point deployment to your user-space repo?",
                choices=[True, False])]
    if (not override):
        override = inquirer.prompt(question)['override']
    question = [inquirer.Checkbox(
                "facility",
                message="What facilities to deploy to? (Arrow keys for selection, enter if done)",
                choices=["S3DF", "LCLS", "FACET", "TestFac"],
                default=[],
                ),]
    # TODO: Make the different facilities command line arguments
    facilities = inquirer.prompt(question)['facility']
    ioc_name = input(INPUT_PREFIX + "Specify name of ioc to deploy: ")
    tag = input(INPUT_PREFIX + "Specify full component tagname (ex: test-ioc-1.0.0): ")
    playbook_output_path = os.getcwd() + "/ADBS_TMP"
    linux_uname = os.environ.get('USER')
    user_src_repo = request.component.git_get_top_dir()
    tarball_path = user_src_repo + '/build_results/'
    tarball = find_tarball(tarball_path)
    if (tarball == None):
        print("== ADBS == No tarball found in " + tarball_path)

    playbook_args = f'{{"initial": "{initial}","component_name": "{request.component.name}", \
        "tag": "{tag}", "user": "{linux_uname}", "tarball": "{tarball}", \
        "ioc_name": "{ioc_name}", "output_path": "{playbook_output_path}"}}'
    # Convert the JSON-formatted string to a dictionary
    playbook_args_dict = json.loads(playbook_args)

    # 3) Run the playbook - call deployment playbook for every facility user chose
    for facility in facilities:
        playbook_args_dict['facility'] = facility
        if (override == True):
            # For now get local directory since we can assume that development version is on local dir
            # But also may exist on $APP
            playbook_args_dict['user_src_repo'] = user_src_repo

        print("== ADBS == " + str(playbook_args_dict))

        isExist = os.path.exists(playbook_output_path)
        if not isExist:
            print(f"= CLI = Adding a {playbook_output_path} dir for deployment playbook output. You may delete if unused")
            os.mkdir(playbook_output_path)
        adbs_playbooks_dir = "/sdf/home/p/pnispero/BuildSystem/ansible/ioc_module/" # TODO: Change this once official

        return_code = run_ansible_playbook(adbs_playbooks_dir + 'global_inventory.ini',
                                           adbs_playbooks_dir + 'ioc_deploy.yml',
                                            facility,
                                            playbook_args_dict)
        print("Playbook execution finished with return code:", return_code)
