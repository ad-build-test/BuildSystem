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
    yaml_filepath = 'configure/CONFIG.yaml' 
    with open(yaml_filepath, 'r') as file:
        yaml_data = yaml.safe_load(file)
    logging.info(yaml_data)
    return yaml_data

def find_rpm(base_path):
    # Assuming theres only ONE rpm
    # Define the base directory
    base_dir = pathlib.Path(base_path)

    # Search for RPM files
    for path in base_dir.rglob('*.rpm'):
        # Assuming there's only one RPM file
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
        # 4) Copy over build results to build_results/
        #   # 4.1) mkdir -p build_results/<component-version>
        #   # 4.2) cp -r bin/ db/ dbd/ iocBoot/ build_results/<component-version> # This piece may be an ansible script
        # 5) Build the rpm package for the app
            # 5.1) cd build_results
            # 5.2) tar czf component-version.tar.gz <component-branch>
            # 5.3) mkdir rpm && cd rpm/
            # 5.4) mkdir BUILD BUILDROOT RPMS SOURCES SPECS
            # 5.5) mv ../component-version.tar.gz SOURCES
            # 5.) Create component-version.spec
                # Refer to the prototype one in test-ioc for how we can make this
            # 6) Build the rpm
                # Build the src rpm first
                    # rpmbuild -bs --define "_topdir $(pwd)" SPECS/test-ioc.spec
                # Then build the binary rpm 
                    # rpmbuild -bb --define "_topdir $(pwd)" SPECS/test-ioc.spec
                # Or just use -ba for both
                    # rpmbuild -ba --define "_topdir $(pwd)" SPECS/test-ioc.spec
            # Current issues:
            # PATRICK HERE - Look into deployment (Actually deploying this built rpm),
            # skip this for now
        
                # 1) TODO: can only build using the architecture where the build is 
                # 2) solved - can't make the rpm package relocatable for some reason
                    # and documentaion is dated and limited on this
                    # Figured it out, use '--relocate /ioctop=path/to/top' when installing
                    # rpm -i test-ioc-1.0.0-1.el7_9.x86_64.rpm --relocate /iocTop=/afs/slac/u/cd/pnispero/bs_test/ --nodeps
                # 3) TODO: I get failed dependencies, should i specify dependencies in Require?
                    # And these are different dependencies than the manifest.yaml
                    # Fow now: can just use --nodeps
                    # When scripting we may just get output of ldd bin/<os>/test-ioc to put into
                        # 'Requires' field of the .spec
                # 4) TODO: Can only install rpms as root
                    # Either get a VM or build a container for this
                
            # 7) In deployment script
                # NEeds to be relocatable since we never actually install iocs in a cpu
                # Instead cpu's just have the afs or nfs filesystem mounted
                # s3df prefix: rpm -i test-ioc.rpm --prefix /sdf/scratch/ad/build/lcls/epics/iocTop
                # dev3 prefix: rpm -i test-ioc-1.0.0-1.el7_9.x86_64.rpm --prefix /afs/slac/u/cd/pnispero/bs_test/
            # 6) To solve the problem of different filepaths to install to, here are the options:
                # a) create multiple rpms, each with a slightly different .spec to install in certain dir
                # b) Have rpm's install in standard directory like /opt/rpm_installs
                    # But that directory is pointed to from standard deployment locations with symlinks
                # c) install rpm in standard directory, but have a post-installation script
                    # that will copy the installation to the desired deployment destination
            # todo: need to figure out the envPaths problem, just reuse cram logic?
                # a) possible options besides slicing that piece of cram
                # a) union of envPaths, with if (facility) then (var)
                # b) define one crucial environment var, which is the facility which would be added in st.cmd
                # c) Or just make a post-process script that uses that part of cram.
                

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
    # For now assume the user is in the repo they want to deploy
    # TODO: Add logic for cloning repo or just the build results?
    # # 2) If user is not in repo, clone repo
    # clone_repo(request)

    # Parse yaml if user-defined deployment script
    manifest_data = parse_manifest()

    # 3) Run the playbook
    print("== ADBS == At the moment, deployment only for IOCs is supported")
        # TODO: There are apps/components which host multiple IOCs, the logic right now assumes
    # 1 ioc for app, so CLI should parse which iocs are available (cram has this down),
    #  then suggest to user which iocs they want to deploy

    # TODO: Add logic for figuring out what type of deployment this is, maybe in config.yaml / database
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
    question = [inquirer.Checkbox(
                "facility",
                message="What facilities to deploy to? (Arrow keys for selection, enter if done)",
                choices=["S3DF", "LCLS", "FACET", "TestFac"],
                default=[],
                ),]
    # TODO: Make the different facilities command line arguments
    facilities = inquirer.prompt(question)['facility']
    print(facilities)
    ioc_name = input(INPUT_PREFIX + "Specify name of ioc to deploy: ")
    playbook_output_path = os.getcwd() + "/ADBS_TMP"
    linux_uname = os.environ.get('USER')
    rpm_path = os.getcwd() + '/build_results/rpm/RPMS' # Assuming were in the component $TOP
    rpm_pkg = find_rpm(rpm_path)
    if (rpm_pkg == None):
        print("== ADBS == No RPM found in " + rpm_path)

    playbook_args = f'{{"initial": "{initial}","component_name": "{request.component.name}", "user": "{linux_uname}",\
        "rpm_pkg": "{rpm_pkg}", "ioc_type": "{ioc_type}", "ioc_name": "{ioc_name}", \
        "output_path": "{playbook_output_path}"}}'
    # Convert the JSON-formatted string to a dictionary
    playbook_args_dict = json.loads(playbook_args)

    # call deployment playbook for every facility user chose
    for facility in facilities:
        playbook_args_dict['facility'] = facility
        if (facility == 'S3DF'):
            # For now get local directory since we can assume that development version is on local dir
            # But also may exist on $APP
            src_repo = request.component.git_get_top_dir()
            print(src_repo)
            playbook_args_dict['src_repo'] = src_repo
            
            # PATRICK HERE
            # check if we specify what cpu we deploy on, because i think most of that is in screeniocs
            # we don't actually install anything on a test stand, mostly just mount /afs to cpu?

        print(playbook_args_dict)
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
        # result = subprocess.run(['ansible-playbook', '-i', adbs_playbooks_dir + 'global_inventory.ini',
        #                          adbs_playbooks_dir + 'ioc_deploy.yml', '-l', facility],
        #                          capture_output=True, text=True)
        # print('== ADBS == output:', result.stdout)
        # print('== ADBS == errors:', result.stderr)
        # ansible-playbook -i global_inventory.ini  ioc_deploy.yml -l <facility>

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
