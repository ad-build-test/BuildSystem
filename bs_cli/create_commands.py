import click
from request import Request
from auto_complete import AutoComplete
from component import Component
import logging
import inquirer
from cli_configuration import INPUT_PREFIX


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
@click.option("-u", "--url", required=False, help="Add existing component to build system")
def repo(component: str, organization: str, testing_criteria: str, approval_rule: str, desc: str, url: str):
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
    print(build_os_list)
    request.add_dict_to_payload(build_os_list)
    if (url): request.add_to_payload("url", url)
    request.post_request(log=True)
    

@create.command()
@click.option("-f", "--fix", type=int, required=False, help="Add fix branch based off issue number")
@click.option("-ft", "--feat", type=int, required=False, help="Add feature branch based off issue number")
@click.option("-d", "--dev", required=False, help="Add development branch")
@click.option("-b", "--branch", required=False, help="Specify which branch to branch from")
@click.option("-t", "--tag", required=False, help="Specify which tag to branch from")
@click.option("-ct", "--commit", required=False, help="Specify which commit to branch from")
@click.option("-a", "--add", is_flag=True, required=False, help="Add an EXISTING branch to database")
def branch(fix: int, feat: int, dev: str, branch: str, tag: str, commit: str, add: bool):
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

    # 3) See if fix, feat, or dev option filled out, or prompt user
    if (fix): 
        branch_type = 'fix'
        branch_type_value = fix
    elif (feat):
        branch_type = 'feat'
        branch_type_value = feat
    elif (dev):
        branch_type = 'dev'
        branch_type_value = dev
    else:
        # If adding existing branch, skip asking type of branch to create
        if (add):
            AutoComplete.set_auto_complete_vals('branch', branches)
            full_branch_name = input("Specify name of existing branch: ")
        else:
            question = [inquirer.List(
                        "branch_type",
                        message="Specify type of branch to create",
                        choices=["fix", "feat", "dev"])]
            branch_type = inquirer.prompt(question)['branch_type']
            branch_type_value = input("Specify name of issue number (or dev name): ")
            full_branch_name = branch_type + '-' + branch_type_value

    # 4) Write to database
    endpoint = 'component/' + component_obj.name + '/branch'
    request.set_endpoint(endpoint)
    request.add_to_payload("type", branch_point_type)
    request.add_to_payload("branchPoint", branch_point_value)
    request.add_to_payload("branchName", full_branch_name)
    request.put_request(log=True)

    # 5) Create the branch using git and push
    if (not add): # Dont create branch if user just wants to add to database
        component_obj.git_create_branch(branch_point_type, branch_point_value, full_branch_name)
        component_obj.git_commit(full_branch_name)
        if (component_obj.git_push(full_branch_name)):
            click.echo('Successfully created branch: ' + full_branch_name)



@create.command()
def issue(): 
    # BLOCKED: CATER does not have an API, but will have it once the NEW CATER 
    # Claudio is working on is finished
    # TODO: 
    # 1) get link to CATER, or see if CATER has API
    # 2) Then use that to generate the issue.
    # 3) May use gh api instead of gh issue so we can avoid prompting user each field
    """Create a new issue"""
    click.echo('Create new issue based off cater')
    cater_id = click.prompt('What is the cater ID?')
    type = click.prompt('Which system do you want your issue in? [Github | Jira]').lower()
    print(type)
    full_url = cli_configuration["server_url"] + 'component'
    send_payload = {"component": component_name,
                    "branch": branch_name,
                    "issueTracker": type,
                    "linux_username": cli_configuration["linux_uname"],
                    "github_username": cli_configuration["github_uname"] }
    response = requests.post(full_url, send_payload)
    print(response)

    