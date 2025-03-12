import click
import inquirer
from adbs_cli.request import Request
from adbs_cli.component import Component
from adbs_cli.auto_complete import AutoComplete
from adbs_cli.cli_configuration import under_development,  Api
from adbs_cli.cli_configuration import INPUT_PREFIX

@click.group(hidden=True)
def admin():
    """admin [ add-repo | delete-repo ]"""
    pass

@admin.command()
@click.option("-c", "--component", required=False, help="Component Name", prompt=INPUT_PREFIX + "Specify component name")
@click.option("-o", "--organization", required=False, help="Organization Name", prompt=INPUT_PREFIX + "Specify organization name")
@click.option("-t", "--testing-criteria", required=False, help="Testing Criteria", prompt=INPUT_PREFIX + "Specify testing criteria")
@click.option("-a", "--approval-rule", required=False, help="Approval Rule", prompt=INPUT_PREFIX + "Specify approval rule")
@click.option("-d", "--desc", required=False, help="Description", prompt=INPUT_PREFIX + "Specify component description")
@click.option("-i", "--issue-tracker", required=False, help="Issue tracking system", prompt=INPUT_PREFIX + "Specify issue tracking system [github | jira]")
@click.option("-j", "--jira-project-key", required=False, help="Jira project key")
@click.option("-v", "--verbose", is_flag=True, required=False, help="More detailed output")
def add_repo(component: str, organization: str, testing_criteria: str, approval_rule: str, desc: str, issue_tracker: str, jira_project_key: str, verbose: bool=False):
    """Add a component to the component database"""
    request = Request(Component(component))
    request.set_endpoint('component')
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
    request.post_request(verbose, msg="Add commponent to component database")

    # Create another put request but to enable permissions for backend to receive events
    enable_envents_endpoint = 'component/' + request.component.name.lower() + '/event/true'
    request = Request(Component(component))
    request.set_endpoint(enable_envents_endpoint)
    request.put_request(log=verbose, msg="Enable events for component")

    # Add the main branch automatically
    request = Request(Component(component))
    endpoint = 'component/' + request.component.name.lower() + '/branch'
    request.set_endpoint(endpoint)
    request.add_to_payload("type", "branch")
    request.add_to_payload("branchName", "main")
    request.put_request(log=verbose, msg="Add branch to component database")

@admin.command()
@click.option("-c", "--component", required=False, help="Component Name", prompt=INPUT_PREFIX + "Specify component name")
@click.option("-v", "--verbose", is_flag=True, required=False, help="More detailed output")
def delete_repo(component: str, verbose: bool):
    """Delete a component from the database (CAUTION)"""

    # Request to disable permissions for backend to receive events
    component = component.lower()
    enable_envents_endpoint = 'component/' + component + '/event/false'
    request = Request(Component(component))
    request.set_endpoint(enable_envents_endpoint)
    request.put_request(log=verbose, msg="Disable events for component")

    # Request to add component to database
    request = Request(Component(component))
    component_id = request.get_component_from_db()['id']
    endpoint = f'component/{component_id}'
    request.set_endpoint(endpoint)
    request.delete_request(log=verbose, msg="Delete component from component database")




