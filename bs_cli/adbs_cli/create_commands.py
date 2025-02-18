import click
from adbs_cli.request import Request
from adbs_cli.auto_complete import AutoComplete
from adbs_cli.component import Component
import inquirer
from adbs_cli.cli_configuration import INPUT_PREFIX


@click.group()
def create():
    """Create a new [ repo | branch | issue ]"""
    pass

@create.command()
@click.option("-c", "--component", required=False, help="Component Name")
@click.option("-o", "--organization", required=False, help="Organization Name", prompt=INPUT_PREFIX + "Specify organization name")
@click.option("-t", "--testing-criteria", required=False, help="Testing Criteria", prompt=INPUT_PREFIX + "Specify testing criteria")
@click.option("-a", "--approval-rule", required=False, help="Approval Rule", prompt=INPUT_PREFIX + "Specify approval rule")
@click.option("-d", "--desc", required=False, help="Description", prompt=INPUT_PREFIX + "Specify component description")
@click.option("-i", "--issue-tracker", required=False, help="Issue tracking system", prompt=INPUT_PREFIX + "Specify issue tracking system [github | jira]")
@click.option("-j", "--jira-project-key", required=False, help="Jira project key")
@click.option("-u", "--url", required=False, help="Add existing component to build system")
@click.option("-v", "--verbose", is_flag=True, required=False, help="More detailed output")
def repo(component: str, organization: str, testing_criteria: str, approval_rule: str, desc: str, issue_tracker: str, jira_project_key: str, url: str, verbose: bool=False):
    """Create a new repo"""
    request = Request(Component(component))
    # args: (May make most of these prompted to user)
    # organization, template repo name, new repo owner (should be automatic),
    # name of repo, description, include_all_branches, private
    # Backend creates the repo, may make option for user to clone it directly after creating
    request.set_endpoint('component')
    request.set_component_name()
    request.add_to_payload("name", request.component.name)
    request.add_to_payload("description", desc)
    request.add_to_payload("testingCriteria", testing_criteria)
    request.add_to_payload("approvalRule", approval_rule)
    request.add_to_payload("organization", organization)
    issue_tracker = issue_tracker.lower()
    request.add_to_payload("issueTracker", issue_tracker)
    if (issue_tracker != 'jira' or issue_tracker != 'github'): 
        click.echo("== ADBS == issue tracker must be jira or github.")
    if (issue_tracker == 'jira'):
        if (jira_project_key == None):
            jira_project_key = input(INPUT_PREFIX + "Specify jira project key: ")
        request.add_to_payload("jiraProjectKey", jira_project_key)
    # TODO: Ask user to specify build os - This should be automatic assuming 
    # the build os(s) are specified in the config manifest
    question = [
    inquirer.Checkbox(
        "buildOs",
        message="What are the operating systems this app runs on? (Arrow keys for selection, enter if done)",
        choices=["ROCKY9", "UBUNTU", "RHEL8", "RHEL7", "RHEL6", "RHEL5"],
        default=[],
        ),
    ]
    build_os_list = inquirer.prompt(question)
    click.echo(build_os_list)
    request.add_dict_to_payload(build_os_list)
    if (url): request.add_to_payload("url", url)
    request.post_request(verbose)

    # Create another put request but to enable permissions for backend to receive events
    enable_envents_endpoint = 'component/' + request.component.name + '/event/true'
    request = Request(Component(component))
    request.set_endpoint(enable_envents_endpoint)
    request.put_request(log=verbose, msg="Add repo to component database")


@create.command()
@click.option("-b", "--branch", required=False, help="Specify which branch to branch from")
@click.option("-t", "--tag", required=False, help="Specify which tag to branch from")
@click.option("-ct", "--commit", required=False, help="Specify which commit to branch from")
@click.option("-a", "--add", is_flag=True, required=False, help="Add an EXISTING branch to database")
@click.option("-v", "--verbose", is_flag=True, required=False, help="More detailed output")
def branch(branch: str, tag: str, commit: str, add: bool, verbose: bool=False):
    """Create a new branch"""
    component_obj = Component()
    request = Request(component_obj)

    # 1) First check that user is in repo
    if (not component_obj.set_cur_dir_component()):
        click.echo('fatal: not a git repository (or any of the parent directories)')
        return

    # 2) See if branch, tag, committ option filled out, or prompt user
    branches = component_obj.git_get_branches()
    tags = component_obj.git_get_tags()
    # commits = component_obj.git_get_commits() # TODO: query branch for commit OR get the list of commits from every branch
    if (branch): 
        if (branch in branches):
            branch_point_type = 'branch'
            branch_point_value = branch
        else:
            click.echo('fatal: invalid branch name!')
            return
    elif (tag): 
        if (tag in tags):
            branch_point_type = 'tag'
            branch_point_value = tag
        else:
            click.echo('fatal: invalid tag name!')
            return
    elif (commit): 
        branch_point_type = 'commit'
        branch_point_value = commit
        # if (commit in commits):
        #     branch_point_type = 'commit'
        #     branch_point_value = commit
        # else:
        #     click.echo('fatal: invalid commit name!')
        #     return
    else:
        # Change prompt if adding an existing branch
        if (add):
            prompt_branch_from = "Specify branch point you branched off of (skip if main)"
        else:
            prompt_branch_from = "Specify what to branch from"

        question = [inquirer.List(
                    "branch_point",
                    message=prompt_branch_from,
                    choices=["branch", "tag", "commit"])]
        branch_point_type = inquirer.prompt(question)['branch_point']
        if (branch_point_type == 'branch'): AutoComplete.set_auto_complete_vals('branch', branches)
        elif (branch_point_type == 'tag'): AutoComplete.set_auto_complete_vals('tag', tags)
        
        branch_point_value = input("Specify name of " + branch_point_type + ": ")

    # 3) 
    full_branch_name = None
    # If adding existing branch, skip asking type of branch to create
    if (add):
        AutoComplete.set_auto_complete_vals('branch', branches)
        full_branch_name = input("Specify name of existing branch: ")
    else:
        issue_num = input("Specify issue number (or branch name): ")
        try: # Get issue tracker if issue number
            issue_num = int(issue_num)
            component_info = request.get_component_from_db()
            issue_tracker = component_info['issueTracker']
            if (issue_tracker == 'github'):
                full_branch_name = f'issue-{issue_num}'
            elif (issue_tracker == 'jira'):
                full_branch_name = f"{component_info['jiraProjectKey']}-{issue_num}"
        except ValueError: # otherwise branch name already given
            full_branch_name = issue_num

    # 4) Create the branch using git and push
    if (not add): # Dont create branch if user just wants to add to database
        component_obj.git_create_branch(branch_point_type, branch_point_value, full_branch_name)
        component_obj.git_commit(full_branch_name)
        if (component_obj.git_push(full_branch_name)):
            click.echo('Successfully created branch: ' + full_branch_name)

    # 5) Write to database
    endpoint = 'component/' + component_obj.name + '/branch'
    request.set_endpoint(endpoint)
    request.add_to_payload("type", branch_point_type)
    request.add_to_payload("branchPoint", branch_point_value)
    request.add_to_payload("branchName", full_branch_name)
    request.put_request(log=verbose, msg="Add branch to component database")

@create.command()
@click.option("-c", "--component", required=False, help="Component Name")
@click.option("-ci", "--cater-id", required=True, help="CATER ID")
@click.option("-v", "--verbose", is_flag=True, required=False, help="More detailed output")
def issue(component: str, cater_id: int, verbose: bool=False):
    """Create a new issue based off CATER ID"""
    # TODO: CATER does not have an API, but will have it once the NEW CATER 

    # 1) Set fields
    click.echo("THIS COMMAND IS ONLY used for demo purposes for now (New CATER under development)")
    request = Request(Component(component))
    request.set_component_name()
    component_info = request.get_component_from_db()
    issue_tracker = component_info['issueTracker']

    # 1.1) If Jira, add project key to request
    if (issue_tracker == 'jira'):
        request.add_to_payload("projectKey", component_info['jiraProjectKey'])

    # 2) Make call to cater
    # TODO: Since CATER doesn't have API as of this comment written,
    # just put in placeholder info for demo
    cater_link = "https://oraweb.slac.stanford.edu/apex/slacprod/f?p=194:4:8146126360777:::4:P4_PROB_ID,P4_DIV_CODE_ID,P4_RP:170777,1,3"
    cater_title = "add EPICS control for oscilloscope scop-li20-ex04"
    issue_title = f"CATER {cater_id} - {cater_title}"
    if (issue_tracker == 'github'): # Different link formatting for both issue trackers
        cater_link = f"[{cater_id}]({cater_link})"
    elif (issue_tracker == 'jira'):
        cater_link = f"[{cater_id}|{cater_link}]"
    issue_body = f"Created to address CATER: {cater_link} by @{request.github_uname}"

    # 3) Add to payload
    request.add_to_payload("issueTitle", issue_title)
    request.add_to_payload("issueBody", issue_body)

    # 4) Send request to backend
    endpoint = 'component/' + request.component.name + '/issue/' + issue_tracker
    request.set_endpoint(endpoint)
    request.post_request(log=verbose, msg="Create issue")

    