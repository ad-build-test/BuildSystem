import shutil
import click
import re
import json
import inquirer
import os
from adbs_cli.request import Request
from adbs_cli.component import Component
from adbs_cli.auto_complete import AutoComplete
from adbs_cli.cli_configuration import cli_configuration, Api, ApiEndpoints, INPUT_PREFIX

@click.group(hidden=True)
def admin():
    """admin [ add-repo | delete-repo ]"""
    pass

@admin.command()
def configure_repo():
    """Configure repo to integrate into software factory"""
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
# Environments this app runs on
environments:
{chr(10).join('   - ' + env for env in build_os_list)}

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

    # Generate full filepath
    filepath = os.path.join(top_level, 'config.yaml')

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
        with open('.gitignore', 'r') as file:
            lines = file.readlines()

        # Remove the one line containing 'RELEASE_SITE'
        filtered_lines = [line for line in lines if 'RELEASE_SITE' not in line.strip()]

        # Write back
        with open('.gitignore', 'w') as file:
            file.writelines(filtered_lines)

        click.echo(f"Successfully removed RELEASE_SITE from .gitignore")
    

@admin.command()
@click.option("-v", "--verbose", is_flag=True, required=False, help="More detailed output")
def add_repo(verbose: bool=False):
    """Add a component to the component database"""
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
    build_os = {"buildOs": manifest_data["environments"]}
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
@click.option("-c", "--component", required=False, help="Component Name", prompt=INPUT_PREFIX + "Specify component name")
@click.option("-v", "--verbose", is_flag=True, required=False, help="More detailed output")
def delete_repo(component: str, verbose: bool):
    """Delete a component from the database (CAUTION)"""

    # Request to disable permissions for backend to receive events
    request = Request(Component(component))
    request.set_endpoint(ApiEndpoints.COMPONENT_EVENT,
                         component_name=component,
                         enable="false")
    request.put_request(log=verbose, msg="Disable events for component")

    # Request to add component to database
    request = Request(Component(component))
    component_id = request.get_component_from_db()['id']
    request.set_endpoint(ApiEndpoints.COMPONENT_ID,
                         id=component_id)
    request.delete_request(log=verbose, msg="Delete component from component database")

def parse_ioc_deployments(file_path):
    # Initialize variables
    facilities = {}
    current_facility = None
    current_master_release = None
    
    # Read the file
    with open(file_path, 'r') as file:
        for line in file:
            line = line.strip()
            
            # Check for facility line
            # ex: Current versions on facility: LCLS
            facility_match = re.match(r'Current versions on facility: (\w+)', line)
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
            master_match = re.match(r'Current master release => ([\w\-\.]+)', line)
            if master_match and current_facility:
                current_master_release = master_match.group(1)
                facilities[current_facility]["tag"] = current_master_release
                continue
            
            # Check for IOC line
            # ex: IOC: sioc-b084-mp05 => l2MpsLN-R3-14-0
            ioc_match = re.match(r'IOC: ([\w\-]+) => ([\w\-\.]+)', line)
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

@admin.command()
@click.option("-c", "--component", required=False, help="Component Name", prompt=INPUT_PREFIX + "Specify component name")
@click.option("-v", "--verbose", is_flag=True, required=False, help="More detailed output")
def add_initial_deployment(component: str, verbose: bool):
    """Add an initial deployment configuration in the database (Useful for IOCS only at the moment) (CAUTION)"""

    # The logic is done through the deployment controller,
    # so if api ever changes, you don't need to update this function. 

    # Grab deployment info from cram ls
    steps = """Instructions (Please read all first): 
    Go to dev3 and run "cram ls | sed -e 's/\x1b\[[0-9;]*m//g' > cram_deployment.txt"
    Then go to where you have access to bs cli and wherever you call
    bs admin add-initial-deployment, add the cram_deployment.txt there
    it'll be parsed, then added to software factory db, then you can delete the file.
            """
    click.echo(steps)
    if (click.confirm("Have you completed the steps?")):
        # Parse the cram output
        # Transform the data and send to deployment controller to add to db
        result = parse_ioc_deployments("cram_deployment.txt")
    
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
    else:
        click.echo("Please complete the instructions")



