import click
import inquirer
from adbs_cli.request import Request
from adbs_cli.component import Component
from adbs_cli.auto_complete import AutoComplete
from adbs_cli.cli_configuration import under_development,  Api, ApiEndpoints
from adbs_cli.cli_configuration import INPUT_PREFIX

@click.group(hidden=True)
def admin():
    """admin [ add-repo | delete-repo ]"""
    pass

@admin.command()
@click.option("-v", "--verbose", is_flag=True, required=False, help="More detailed output")
def add_repo(verbose: bool=False):
    """Add a component to the component database"""
    component_obj = Component()
    request = Request(Component(component_obj))

    # === Lets make sure the admin is in a checked out copy of the repo,
    # then we can parse the manifest and only question to ask is the automated test part
    # 1) First check that user is in repo
    if (not component_obj.set_cur_dir_component()):
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
    if (not click.confirm("Do you want to add automated build and tests?")):
        request.add_to_payload("skipBuildAndTests", True)
    
    request.set_endpoint(ApiEndpoints.COMPONENT)
    request.post_request(verbose, msg="Add component to component database")

    # Create another put request but to enable permissions for backend to receive events
    request = Request(Component(request.component))
    request.set_endpoint(ApiEndpoints.COMPONENT_EVENT, 
                         component_name=request.component.name.lower(),
                         enable="true")
    request.put_request(log=verbose, msg="Enable events for component")

    # Add the main branch automatically
    request = Request(Component(request.component))
    branches = request.component.git_get_branches()
    if ("main" in branches):
        main_branch = "main"
    elif ("master" in branches):
        main_branch = "master"
    request.set_endpoint(ApiEndpoints.COMPONENT_BRANCH,
                         component_name=request.component.name.lower())
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
    get_component_request.set_component_name(lower_case=True)
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
    if (not click.confirm("Do you want to add automated build and tests?")):
        request.add_to_payload("skipBuildAndTests", True)
    
    
    request.put_request(verbose, msg="Update component in component database")

@admin.command()
@click.option("-c", "--component", required=False, help="Component Name", prompt=INPUT_PREFIX + "Specify component name")
@click.option("-v", "--verbose", is_flag=True, required=False, help="More detailed output")
def delete_repo(component: str, verbose: bool):
    """Delete a component from the database (CAUTION)"""

    # Request to disable permissions for backend to receive events
    component = component.lower()
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




