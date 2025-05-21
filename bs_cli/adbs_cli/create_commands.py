import click
from adbs_cli.request import Request
from adbs_cli.auto_complete import AutoComplete
from adbs_cli.component import Component
import inquirer
from adbs_cli.cli_configuration import INPUT_PREFIX, ApiEndpoints


@click.group()
def create():
    """Create a new [ branch | issue ]"""
    pass

@create.command()
@click.option("-b", "--branch", required=False, help="Specify which branch to branch from")
@click.option("-t", "--tag", required=False, help="Specify which tag to branch from")
@click.option("-ct", "--commit", required=False, help="Specify which commit to branch from")
@click.option("-a", "--add", is_flag=True, required=False, help="Add an EXISTING branch to database")
@click.option("-v", "--verbose", is_flag=True, required=False, help="More detailed output")
def branch(branch: str, tag: str, commit: str, add: bool, verbose: bool=False):
    """Create a new branch. If you do not provide any options, a branch will be
      created based off the branch you are currently sitting in."""
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
    # Default branch point to branch user is currently sitting in
    branch_point_value = component_obj.git_get_current_branch()
    branch_point_type = 'branch'
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
            prompt_branch_from = "Specify branch point you branched off of"
            question = [inquirer.List(
            "branch_point",
            message=prompt_branch_from,
            choices=["branch", "tag", "commit"])]
            branch_point_type = inquirer.prompt(question)['branch_point']
            if (branch_point_type == 'branch'): AutoComplete.set_auto_complete_vals('branch', branches)
            elif (branch_point_type == 'tag'): AutoComplete.set_auto_complete_vals('tag', tags)
            
            branch_point_value = input("Specify name of " + branch_point_type + ": ")


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
    request.set_endpoint(ApiEndpoints.COMPONENT_BRANCH,
                         component_name=component_obj.name)
    request.add_to_payload("type", branch_point_type)
    request.add_to_payload("branchPoint", branch_point_value)
    request.add_to_payload("branchName", full_branch_name)
    request.put_request(log=verbose, msg="Add branch to component database")

@create.command()
@click.option("-c", "--component", required=False, help="Component Name")
@click.option("-ci", "--cater-id", required=False, help="CATER ID - when given, title and description is gathered from CATER")
@click.option("-t", "--issue-title", required=False, help="Issue title (if no CATER ID is provided)")
@click.option("-b", "--issue-body", required=False, help="Issue body (if no CATER ID is provided)")
@click.option("-v", "--verbose", is_flag=True, required=False, help="More detailed output")
def issue(component: str, cater_id: int, issue_title: str, issue_body: str, verbose: bool=False):
    """Create a new issue"""
    # TODO: CATER does not have an API, but will have it once the NEW CATER 

    # 1) Set fields
    request = Request(Component(component))
    request.set_component_name()
    component_info = request.get_component_from_db()
    issue_tracker = component_info['issueTracker']

    if (cater_id):
        click.echo("== ADBS == Cater API not yet available.")
        return
    
    if (issue_title == None): 
        issue_title = input("Specify issue title: ")
    if (issue_body == None): 
        issue_body = input("Specify issue body: ")

    # 1.1) If Jira, add project key to request
    if (issue_tracker == 'jira'):
        request.add_to_payload("projectKey", component_info['jiraProjectKey'])

    # 2) Make call to cater
    # TODO: Since CATER doesn't have API as of this comment written,
    # just put in placeholder info for demo
    # cater_link = "https://oraweb.slac.stanford.edu/apex/slacprod/f?p=194:4:8146126360777:::4:P4_PROB_ID,P4_DIV_CODE_ID,P4_RP:170777,1,3"
    # cater_title = "add EPICS control for oscilloscope scop-li20-ex04"
    # issue_title = f"CATER {cater_id} - {cater_title}"
    # if (issue_tracker == 'github'): # Different link formatting for both issue trackers
    #     cater_link = f"[{cater_id}]({cater_link})"
    # elif (issue_tracker == 'jira'):
    #     cater_link = f"[{cater_id}|{cater_link}]"
    # issue_body = f"Created to address CATER: {cater_link} by @{request.github_uname}"

    # 3) Add to payload
    request.add_to_payload("issueTitle", issue_title)
    request.add_to_payload("issueBody", issue_body)

    # 4) Send request to backend
    request.set_endpoint(ApiEndpoints.COMPONENT_ISSUE,
                         component_name=request.component.name,
                         issue_tracker=issue_tracker)
    request.post_request(log=verbose, msg="Create issue")

    