import shutil
import click
import re
import json
import inquirer
import os
import subprocess
from adbs_cli.request import Request
from adbs_cli.component import Component
from adbs_cli.auto_complete import AutoComplete
from adbs_cli.cli_configuration import cli_configuration, Api, ApiEndpoints, INPUT_PREFIX
from adbs_cli.create_commands import branch

@click.group(hidden=True)
def admin():
    """admin [ onboard-repo | update-repo | update-deployment | delete-repo ]"""
    pass

def parse_ioc_deployments(content):
    # Initialize variables
    facilities = {}
    current_facility = None
    current_master_release = None
    
    # ANSI escape code pattern
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

    # Read the file
    for line in content.split('\n'):
        # Strip ANSI codes first, then whitespace
        line = ansi_escape.sub('', line).strip()
        
        # Skip empty lines
        if not line:
            continue
        
        # Check for facility line
        # ex: Current versions on facility: LCLS
        facility_match = re.match(r'Current versions on facility:\s*(\w+)', line)
        if facility_match:
            current_facility = facility_match.group(1).upper()
            facilities[current_facility] = {
                "facility": current_facility,
                "tag": None,
                "dependsOn": []
            }
            continue
        
        # Check for master release line
        # ex: Current master release => l2MpsLN-R5-4-6
        master_match = re.match(r'Current master release\s*=>\s*([\w\-\.]+)', line)
        if master_match and current_facility:
            current_master_release = master_match.group(1)
            facilities[current_facility]["tag"] = current_master_release
            continue
        
        # Check for IOC line
        # ex: IOC: sioc-b084-mp05 => l2MpsLN-R3-14-0
        ioc_match = re.match(r'IOC:\s*([\w\-]+)\s*=>\s*([\w\-\.]+)', line)
        if ioc_match and current_facility:
            ioc_name = ioc_match.group(1)
            ioc_tag = ioc_match.group(2)
            
            facilities[current_facility]["dependsOn"].append({
                "name": ioc_name,
                "tag": ioc_tag
            })
    
    # Remove empty facilities or those without IOCs
    # Expanded version of the one-liner
    filtered_facilities = {}
    for facility_name, facility_data in facilities.items():
        if facility_data["dependsOn"]:  # If the dependsOn list is not empty
            filtered_facilities[facility_name] = facility_data

    return filtered_facilities

def add_initial_deployment(component: str, verbose: bool = False):
    """Add an initial deployment configuration in the database (Useful for IOCS only) taken from existing cram output (CAUTION)"""

    # The logic is done through the deployment controller,
    # so if api ever changes, you don't need to update this function. 

    # Grab deployment info from cram ls
    click.echo("== ADBS == Adding initial deployment configuration")
    click.echo("== ADBS == Running 'cram ls'...")

    try:
        # Run the command and capture output
        cram_output = subprocess.run(
            ['cram', 'ls'],
            capture_output=True,
            text=True,
            check=True
        )
        
        # Parse the cram output
        # Transform the data and send to deployment controller to add to db
        result = parse_ioc_deployments(cram_output.stdout)
        
    except subprocess.CalledProcessError as e:
        click.echo(f"== ADBS == Error running cram ls: {e.stderr}")
        return

    # Print each facility as a separate JSON object
    for facility_name, facility_data in result.items():
        print(f"Facility: {facility_name}")
        print(json.dumps(facility_data, indent=2))
        print("\n" + "-"*50 + "\n")
    if (click.confirm("Does the above deployment info look correct")):
        question = [
        inquirer.List(
            "deploymentType",
            message="What type of deployment will this app use?",
            choices=["ioc", "hla", "tools", "matlab", "pydm", "container"]
            ),
        ]
        deployment_type = inquirer.prompt(question)['deploymentType']
        for facility, facility_data in result.items():
            data_to_write = {
                "facility": facility,
                "component_name": component,
                "tag": facility_data['tag'],
                "user": cli_configuration['github_uname'],
                "type": deployment_type
            }
            if (deployment_type == 'ioc'):
                data_to_write["ioc_list"] = facility_data['dependsOn']
            request = Request(Component(component), Api.DEPLOYMENT)
            request.set_endpoint(ApiEndpoints.DEPLOYMENT_INITIAL)
            request.add_dict_to_payload(data_to_write)
            request.put_request(log=verbose, msg="Add initial deployment for component in facility: " + facility)

def add_repo(verbose: bool=False):
    """Add a component and all its existing branches to the component database"""
    request = Request(Component())

    # === Lets make sure the admin is in a checked out copy of the repo,
    # then we can parse the manifest and only question to ask is the automated test part
    # 1) First check that user is in repo
    if (not request.component.set_cur_dir_component()):
        click.echo('fatal: not a git repository (or any of the parent directories)')
        return
    
    # 2) Parse manifest
    user_src_repo = request.component.git_get_top_dir()
    manifest_filepath = user_src_repo + '/config.yaml'
    manifest_data = request.component.parse_manifest(manifest_filepath)

    # 3) Populate the payload
    request.add_to_payload("name", manifest_data["repo"])
    request.add_to_payload("description", manifest_data["description"])
    request.add_to_payload("testingCriteria", manifest_data["testingCriteria"])
    request.add_to_payload("approvalRule", manifest_data["approvalRule"])
    organization = manifest_data["organization"]
    request.add_to_payload("organization", organization)
    issue_tracker = manifest_data["issueTracker"]
    request.add_to_payload("issueTracker", issue_tracker)
    if (issue_tracker != 'jira' and issue_tracker != 'github'): 
        click.echo("== ADBS == issue tracker must be jira or github.")
        return
    if (issue_tracker == 'jira'):
        request.add_to_payload("jiraProjectKey", manifest_data["jiraProjectKey"])

    build_os = {"buildOs": manifest_data.get("environments")}
    request.add_dict_to_payload(build_os)
    request.add_to_payload("url", f"https://github.com/{organization}/{request.component.name}")
    request.add_to_payload("ssh", f"git@github.com:{organization}/{request.component.name}.git")
    if (not click.confirm("Do you want to add automated build and tests?")):
        request.add_to_payload("skipBuildAndTests", True)
    
    request.set_endpoint(ApiEndpoints.COMPONENT)
    request.post_request(verbose, msg="Add component to component database")

    # Create another put request but to enable permissions for backend to receive events
    request = Request(request.component)
    request.set_endpoint(ApiEndpoints.COMPONENT_EVENT, 
                         component_name=request.component.name,
                         enable="true")
    request.put_request(log=verbose, msg="Enable events for component")

    # Add the main branch automatically
    request = Request(request.component)
    branches = request.component.git_get_branches()
    if ("main" in branches):
        main_branch = "main"
    elif ("master" in branches):
        main_branch = "master"
    request.set_endpoint(ApiEndpoints.COMPONENT_BRANCH,
                         component_name=request.component.name)
    request.add_to_payload("type", "branch")
    request.add_to_payload("branchName", main_branch)
    request.put_request(log=verbose, msg="Add branch to component database")

@admin.command()
@click.pass_context
@click.option("-v", "--verbose", is_flag=True, required=False, help="More detailed output")
def onboard_repo(ctx, verbose: bool=False):
    """Command to onboard a repo to software factory.
    Creates config.yaml, adds component to database, adds initial deployment configuration (if existing IOC application)"""
    click.confirm("Ensure you did a 'kinit' before continuing.")

    # Create the config.yaml =====================================================
    # Get user input
    at_top = click.confirm("Are you at the TOP level of your repo?")
    if (at_top):
        top_level = os.getcwd()
        repo_name = os.path.basename(top_level)
    else: 
        top_level = input("Specify filepath to the TOP level of your repo: ")
        if os.path.exists(top_level):
            repo_name = os.path.basename(os.path.abspath(top_level))
        else:
            click.echo(f"Error: The specified path '{top_level}' does not exist.")
            return

    org_name = input(INPUT_PREFIX + "Specify name of GitHub organization: ")
    description = input(INPUT_PREFIX + "Specify repo description: ")
    build_command = input(INPUT_PREFIX + "Specify how to build (if applicable, can be as simple as 'make'): ")
    question = [
    inquirer.List(
        "issueTracker",
        message="What issue tracking system does this app use?",
        choices=["github", "jira"]
        ),
    ]
    issue_tracker = inquirer.prompt(question)['issueTracker']
    jira_project_key = 'n/a'
    if (issue_tracker == 'jira'):
        jira_project_key = input(INPUT_PREFIX + "Specify jira project key: ")
    question = [
    inquirer.Checkbox(
        "buildOs",
        message="What are the operating systems this app runs on?",
        choices=["ROCKY9", "RHEL7", "RHEL6", "RHEL5"],
        default=[],
        ),
    ]
    build_os_list = inquirer.prompt(question)['buildOs']
    question = [
    inquirer.List(
        "deploymentType",
        message="What type of deployment will this app use?",
        choices=["ioc", "hla", "tools", "matlab", "pydm", "container"]
        ),
    ]
    deployment_type = inquirer.prompt(question)['deploymentType']

    # Create the content
    content = f"""# [Required]
# Basic component information
repo: {repo_name}
organization: {org_name}
url: https://github.com/{org_name}/{repo_name}
description: {description}

# [Required]
# Continous integration
approvalRule: all
testingCriteria: all
issueTracker: {issue_tracker}
jiraProjectKey: {jira_project_key}

# [Required]
# Type of deployment
# Types: [ioc, hla, tools, matlab, pydm, container]
deploymentType: {deployment_type}

# [Optional] 
# Build method for building the component
# Can be a simple command like 'make'
"""
    if (build_command == ""):
        content += "# build: \n"
    else:
        content += f"build: {build_command}\n"

    if (build_os_list == []):
        content += """
# [Optional]
# Environments this app runs on
# environments:
"""
    else:
        content += f"""
# [Optional]
# Environments this app runs on
environments:
{chr(10).join('   - ' + env for env in build_os_list)}
"""
    runtime_dependencies = click.confirm("Are there any runtime dependencies?")
    if (runtime_dependencies):
        deps_input = click.prompt("Enter dependencies (comma-separated)")
        dependencies = [d.strip() for d in deps_input.split(',')]
        content += f"""
# [Optional]
# Directories and files needed to run application
runtimeDependencies:
{chr(10).join('   - ' + dependency for dependency in dependencies)}
"""
    else:
        content += f"""
# [Optional]
# Directories and files needed to run application
# runtimeDependencies:
"""

    # Generate full filepath
    filepath = os.path.join(top_level, 'config.yaml')

    # Write to file
    with open(filepath, 'w') as f:
        f.write(content)

    click.echo(f"File '{filepath}' has been generated successfully!")

    # Create the github actions deployment workflow file
    if (deployment_type == "pydm"):
        content = """name: Request Deployment - PyDM Display

on:
  workflow_dispatch:
    inputs:
      deploy_to_dev:
        description: 'DEV'
        required: false
        type: boolean
        default: false
      deploy_to_lcls:
        description: 'LCLS'
        required: false
        type: boolean
        default: false
      deploy_to_facet:
        description: 'FACET'
        required: false
        type: boolean
        default: false
      deploy_to_testfac:
        description: 'TESTFAC'
        required: false
        type: boolean
        default: false
      deploy_to_sandbox:
        description: 'SANDBOX'
        required: false
        type: boolean
        default: false
      tag:
        description: 'Tag to deploy'
        required: true
        type: string
        
permissions:
  deployments: write
  contents: read
  actions: read
  
jobs:
  deploy:
    uses: ad-build-test/build-system-playbooks/.github/workflows/request-deployment.yml@main
    with:
      deploy_to_dev: ${{ inputs.deploy_to_dev }}
      deploy_to_lcls: ${{ inputs.deploy_to_lcls }}
      deploy_to_facet: ${{ inputs.deploy_to_facet }}
      deploy_to_testfac: ${{ inputs.deploy_to_testfac }}
      tag: ${{ inputs.tag }}
      deployment_type: 'pydm'
"""

    # Generate full filepath
    filepath = os.path.join(top_level, '.github/workflows/deploy.yml')

    # Create the directory if it doesn't exist
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    # Write to file
    with open(filepath, 'w') as f:
        f.write(content)

    click.echo(f"File '{filepath}' has been generated successfully!")

    # If deployment type is IOC, then generate RELEASE_SITE, and remove .cram, and remove RELEASE_SITE from .gitignore
    if (deployment_type == 'ioc'):

        # Generate RELEASE_SITE
        release_site_contents = f"""
#==============================================================================
# RELEASE_SITE Location of EPICS_SITE_TOP, EPICS_MODULES, and BASE_MODULE_VERSION
# Run "gnumake clean uninstall install" in the application
# top directory each time this file is changed.

#==============================================================================
BASE_MODULE_VERSION=R7.0.3.1-1.0
EPICS_SITE_TOP=/afs/slac/g/lcls/epics
BASE_SITE_TOP=/afs/slac/g/lcls/epics/base
MODULES_SITE_TOP=/afs/slac/g/lcls/epics/R7.0.3.1-1.0/modules
EPICS_MODULES=/afs/slac/g/lcls/epics/R7.0.3.1-1.0/modules
IOC_SITE_TOP=/afs/slac/g/lcls/epics/iocTop
PACKAGE_SITE_TOP=/afs/slac/g/lcls/package
MATLAB_PACKAGE_TOP=/afs/slac/g/lcls/package/matlab
PSPKG_ROOT=/afs/slac/g/lcls/package/pkg_mgr
TOOLS_SITE_TOP=/afs/slac/g/lcls/tools
ALARM_CONFIGS_TOP=/afs/slac/g/lcls/tools/AlarmConfigsTop
#==============================================================================
"""
        # Generate full filepath
        filepath = os.path.join(top_level, 'RELEASE_SITE')

        # Write to file
        with open(filepath, 'w') as f:
            f.write(release_site_contents)

        click.echo(f"File '{filepath}' has been generated successfully!")

        # Remove .cram directory
        try:
            shutil.rmtree(".cram")
            click.echo(f"Successfully removed .cram directory")
        except FileNotFoundError:
            pass  # Already doesn't exist

        # Remove RELEASE_SITE from .gitignore
        # Read all lines
        if os.path.exists('.gitignore'):
            with open('.gitignore', 'r') as file:
                lines = file.readlines()

            # Remove the one line containing 'RELEASE_SITE'
            filtered_lines = [line for line in lines if 'RELEASE_SITE' not in line.strip()]

            # Write back
            with open('.gitignore', 'w') as file:
                file.writelines(filtered_lines)

            click.echo(f"Successfully removed RELEASE_SITE from .gitignore")

    add_repo(verbose)
        
    if (deployment_type == 'ioc'):
        if (click.confirm("Is this an existing IOC application?")):
            add_initial_deployment(repo_name, verbose)
        else:
            click.echo("No initial deployment configuration will be added since this is a NEW IOC application")        
    return # TEMP
    # Create software factory onboarding branch to push changes to
    click.echo("== ADBS == Creating software factory onboard branch to push changes to")
    ctx.invoke(
        branch,
        verbose=verbose
    )

    click.echo(f"**** Post Steps ****\n \
1. Please add repo to github app in {org_name}.\n \
2. Update RELEASE_NOTES.md file with new tag then commit changes and push\n \
3. Create new pull request and merge changes")

@admin.command()
@click.option("-c", "--component", required=False, help="Component Name", prompt=INPUT_PREFIX + "Specify component name")
@click.option("-o", "--organization", required=False, help="Organization Name", prompt=INPUT_PREFIX + "Specify organization name")
@click.option("-t", "--testing-criteria", required=False, help="Testing Criteria", prompt=INPUT_PREFIX + "Specify testing criteria")
@click.option("-a", "--approval-rule", required=False, help="Approval Rule", prompt=INPUT_PREFIX + "Specify approval rule")
@click.option("-d", "--desc", required=False, help="Description", prompt=INPUT_PREFIX + "Specify component description")
@click.option("-i", "--issue-tracker", required=False, help="Issue tracking system", prompt=INPUT_PREFIX + "Specify issue tracking system [github | jira]")
@click.option("-j", "--jira-project-key", required=False, help="Jira project key")
@click.option("-v", "--verbose", is_flag=True, required=False, help="More detailed output")
def update_repo(component: str, organization: str, testing_criteria: str, approval_rule: str, desc: str, issue_tracker: str, jira_project_key: str, verbose: bool=False):
    """Update a component in the component database"""
    get_component_request = Request(Component(component))
    get_component_request.set_component_name()
    component_id = get_component_request.get_component_from_db()['id']
    
    request = Request(Component(component))
    request.set_endpoint(ApiEndpoints.COMPONENT_ID,
                         id=component_id)
    request.add_to_payload("name", request.component.name)
    request.add_to_payload("description", desc)
    request.add_to_payload("testingCriteria", testing_criteria)
    request.add_to_payload("approvalRule", approval_rule)
    request.add_to_payload("organization", organization)
    issue_tracker = issue_tracker.lower()
    request.add_to_payload("issueTracker", issue_tracker)
    if (issue_tracker != 'jira' and issue_tracker != 'github'): 
        click.echo("== ADBS == issue tracker must be jira or github.")
        return
    if (issue_tracker == 'jira'):
        if (jira_project_key == None):
            jira_project_key = input(INPUT_PREFIX + "Specify jira project key: ")
        request.add_to_payload("jiraProjectKey", jira_project_key)
    question = [
    inquirer.Checkbox(
        "buildOs",
        message="What are the operating systems this app runs on?",
        choices=["ROCKY9", "RHEL7", "RHEL6", "RHEL5"],
        default=[],
        ),
    ]
    build_os_list = inquirer.prompt(question)
    request.add_dict_to_payload(build_os_list)
    request.add_to_payload("url", f"https://github.com/{organization}/{request.component.name}")
    request.add_to_payload("ssh", f"git@github.com:{organization}/{request.component.name}.git")
    if (not click.confirm("Do you want to add automated build and tests?")):
        request.add_to_payload("skipBuildAndTests", True)
    
    
    request.put_request(verbose, msg="Update component in component database")

@admin.command()
@click.option("-v", "--verbose", is_flag=True, required=False, help="More detailed output")
def update_deployment(verbose: bool=False):
    """(CAUTION) For IOCS: If deployment out of sync because cram was still accidentally utlized. Then this command with parse cram ls, and 
update the deployment db entry."""
    request = Request(Component())

    # === Lets make sure the admin is in a checked out copy of the repo,
    # then we can parse the manifest and only question to ask is the automated test part
    # 1) First check that user is in repo
    if (not request.component.set_cur_dir_component()):
        click.echo('fatal: not a git repository (or any of the parent directories)')
        return
    # 2) Parse manifest
    user_src_repo = request.component.git_get_top_dir()
    manifest_filepath = user_src_repo + '/config.yaml'
    manifest_data = request.component.parse_manifest(manifest_filepath)

    repo_name = manifest_data["repo"]
    # 3) Add deployment entry
    add_initial_deployment(repo_name, verbose)
    
@admin.command()
@click.option("-c", "--component", required=False, help="Component Name", prompt=INPUT_PREFIX + "Specify component name")
@click.option("-v", "--verbose", is_flag=True, required=False, help="More detailed output")
def delete_repo(component: str, verbose: bool):
    """(CAUTION) Delete a component from the database"""

    # Request to disable permissions for backend to receive events
    request = Request(Component(component))
    request.set_endpoint(ApiEndpoints.COMPONENT_EVENT,
                         component_name=component,
                         enable="false")
    request.put_request(log=verbose, msg="Disable events for component")

    # Request to delete component from database
    request = Request(Component(component))
    component_id = request.get_component_from_db()['id']
    request.set_endpoint(ApiEndpoints.COMPONENT_ID,
                         id=component_id)
    request.delete_request(log=verbose, msg="Delete component from component database")


