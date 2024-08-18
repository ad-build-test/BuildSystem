import click
import yaml
import os
import ansible_runner # TODO: Move to its own module once done testing
import inquirer
import json
import logging
import subprocess
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
    if (not request.component.git_repo):
        clone_filepath = input(INPUT_PREFIX + "Specify filepath to clone repo temporarily: ")
        os.chdir(clone_filepath)
        component_info = request.get_component_from_db()
        request.component.git_clone(component_info['url'])

def parse_manifest() -> dict:
    # Parse manifest - filepath is only here, so if ever need to change its only one location
    yaml_filepath = 'configure/CONFIG.yaml' 
    with open(yaml_filepath, 'r') as file:
        yaml_data = yaml.safe_load(file)
    logging.info(yaml_data)
    return yaml_data


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

    ## Remote build
    elif (build_type == "REMOTE"):
        # 2) Send request to backend
        endpoint = 'build/component/' + request.component.name + '/branch/' + request.component.branch_name
        request.set_endpoint(endpoint)
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

    # 2) Send request to backend
    endpoint = 'test/component/' + request.component.name + '/branch/' + request.component.branch_name
    request.set_endpoint(endpoint)
    request.post_request(log=True)

@run.command()
@click.option("-c", "--component", required=False, help="Component Name")
@click.option("-b", "--branch", required=False, help="Branch Name")
def deployment(component: str, branch: str):
    """Run a deployment"""
    # 1) Set fields
    request = Request(Component(component, branch))    
    request.set_component_fields()

    """ASK ABOUT THIS: This may not make sense to clone manifest, since we 
    can assume that the repo the user is in, is the one they want to deploy
    answer: have both options, ideally they'd be in the repo they want to deploy,
    but user can specify another compononent (useful like if someone made a script
    to deploy a bunch of components). In that case, then you'd have to clone the repo
    to get the manifest and possibly a user-defined deployment script"""
    # 2) If user is not in repo, clone repo
    clone_repo(request)

    # Parse yaml
    manifest_data = parse_manifest()

    # 3) Run the playbook
    # TODO: Add logic for figuring out what type of deployment this is, maybe in config.yaml / database
    question = [inquirer.List(
                "deploy_type",
                message="Specify type of deployment",
                choices=["DEV", "PROD"])]
    deploy_type = inquirer.prompt(question)['deploy_type']
    question = [inquirer.List(
                "ioc_type",
                message="Specify type of ioc",
                choices=["SIOC", "HIOC", "VIOC"])]
    ioc_type = inquirer.prompt(question)['ioc_type']
    question = [inquirer.List(
                "initial",
                message="Initial deployment?",
                choices=[True, False])]
    initial = inquirer.prompt(question)['initial']
    ioc_name = input(INPUT_PREFIX + "Specify name of ioc to deploy: ")
    host_user = input(INPUT_PREFIX + "Specify host user account used to run screen\n(ex: laci@lcls-dev1): ")
    executable_path = input(INPUT_PREFIX + "Specify executable path\n(ex:/afs/slac/g/lcls/epics/iocCommon/sioc-sys0-al02/iocSpecificRelease/bin/rhel7-x86_64/alhPV): ")
    if (ioc_type == 'HIOC'):
        server_user_node_port = input(INPUT_PREFIX + "Specify terminal server user, node, port\n(ex: root@ts-b15-mg01:2001): ")
    else:
        server_user_node_port = None
    playbook_output_path = os.getcwd() + "/ADBS_TMP"
    ioc_common = os.environ.get('IOC')
    ioc_data = os.environ.get('IOC_DATA')
    linux_uname = os.environ.get('USER')

    # TODO: Delete these lines once done testing
    ioc_common = '/afs/slac.stanford.edu/u/cd/pnispero/ansible_test/iocCommon'
    ioc_data = '/afs/slac.stanford.edu/u/cd/pnispero/ansible_test/iocData'

    playbook_args = f'{{"initial": "{initial}","component_name": "{request.component.name}","deploy_type": "{deploy_type}", "user": "{linux_uname}", "iocCommon": "{ioc_common}", "iocData": "{ioc_data}",\
                     "ioc_type": "{ioc_type}", "ioc_name": "{ioc_name}", "host_user": "{host_user}",\
                     "server_user_node_port": "{server_user_node_port}", "executable_path": "{executable_path}",\
                     "output_path": "{playbook_output_path}"}}'
    # Convert the JSON-formatted string to a dictionary
    playbook_args_dict = json.loads(playbook_args)
                     
    print(playbook_args_dict)
    isExist = os.path.exists(playbook_output_path)
    if not isExist:
        print(f"= CLI = Adding a {playbook_output_path} dir for deployment playbook output. You may delete if unused")
        os.mkdir(playbook_output_path)
    adbs_playbooks_dir = "/afs/slac/u/cd/pnispero/BuildSystem/ansible/ioc_module/" # TODO: Change this once official
    # here - change localhost to mylocal, and host_pattern below to inventory to point to your inv
    # r = ansible_runner.run(private_data_dir=playbook_output_path, inventory=adbs_playbooks_dir + 'local_inventory', playbook=adbs_playbooks_dir + 'ioc_deploy.yml',
    #                        extravars=playbook_args_dict)
    r = ansible_runner.run(private_data_dir=playbook_output_path, host_pattern='localhost', playbook=adbs_playbooks_dir + 'ioc_deploy.yml',
                           extravars=playbook_args_dict)
    print("{}: {}".format(r.status, r.rc))
    if (r.rc != 0): # 0 means success
        print("Final status:")
        print(f"error output path: {r.stderr}")
        print(f"regular path: {r.stdout}")
    # todo: change deployment command to ask
    #     - first time deploying?
    #     - do the initial deployment playbook and get the arguments for that
    #     - otherwise go to regular deployment playbook and get the arguments
    #         which is just <tag> and <facility> 
    # 3) if not, check the database
        # 3.1) if not, ask user to add to database
    # 4) Run the playbook
    # hold off, work on steps to deploy build system entirely
    # 1) call the appropiate playbook - I believe we can store the component type in db,
    # then that can determine the type of deployment playbook to use
    # TODO: Where should we store these playbooks, same repo as CLI? 
        # If so, is that best practice? What if we make frequent playbook updates?
        # Do we roll out updates to /usr/bin frequent too?
        # Or do we want an API to take these requests like the rest of the commands here
        # If so, then the playbook would run on our cluster rather then on user space. Is that
        # what we want?
    # for the moment,
    # ? Upload the playbook and custom module to a collection then to the galaxy so its accessible
    # Specify the playbook in the test-ioc/configure/CONFIG.yaml manifest
    # And we can parse it locally here, eventually we will move this logic to backend
    #    grab the manifest from the component url, dont clone the whole thing
    #     just grab the manifest, (use wget/curl?)
    # Then if its not there, then we can check the deployment database if its spelled out
    # A user may make their own playbook if they want to, and then specify it in the manifest

    # TEMP - for now just use the test playbook
    # 2) 
