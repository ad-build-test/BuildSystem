import click
import git
from request import Request
from component import Component
import logging
import inquirer


@click.group()
def create():
    """Create a new [ repo | branch | issue ]"""
    pass

@create.command()
@click.option("-c", "--component", required=False, help="Component Name")
@click.option("-b", "--branch", required=False, help="Branch Name")
@click.option("-u", "--url", required=False, help="Add existing component to build system")
def repo(component: str, branch: str, url: str):
    """Create a new repo"""
    request = Request(Component(component))
    # args: (May make most of these prompted to user)
    # organization, template repo name, new repo owner (should be automatic),
    # name of repo, description, include_all_branches, private
    # TODO: May make the requests.post a function in request class as well since its repeating
    request.set_endpoint('repo')
    request.set_component_fields()
    if (url): request.add_to_payload("url", url)
    payload_received = request.post_request()

    logging.info(request.headers)
    logging.info(request.payload)
    logging.info(payload_received)
    

@create.command()
@click.option("-c", "--component", required=False, help="Component Name")
@click.option("-f", "--fix", type=int, required=False, help="Add fix branch based off issue number")
@click.option("-ft", "--feat", type=int, required=False, help="Add feature branch based off issue number")
@click.option("-d", "--dev", required=False, help="Add development branch")
@click.option("-b", "--branch", required=False, help="Specify which branch to branch from")
@click.option("-t", "--tag", required=False, help="Specify which tag to branch from")
@click.option("-ct", "--commit", required=False, help="Specify which tag to branch from")
def branch(component: str, fix: int, feat: int, dev: str, branch: str, tag: str, commit: str):
    """Create a new branch"""
    component_obj = Component(component)
    request = Request(component_obj)
    # TODO: May make the branch ourselves in this case not through backend
    # TODO: Force the user to enter the repository they want to create a branch in
    #       This will make it simpler to use git commands directly
    
    # dont do same logic as component where you look at what branch their sitting in
    # Just have option available or prompt user. 
    # We also want to create a branch off a 
    # branch (tip of branch),
    # tag (may want to add sanity check logic if there are newer tags
    #       than the user wants to branch off from),
    # or committ.
    
    # 1) First check that user is in repo
    if (not component_obj.set_cur_dir_component()):
        click.echo('fatal: not a git repository (or any of the parent directories)')
        return
    
    # TODO: Create logic to check if branch/tag/commit that user entered is valid, otherwise prompt
    # 2) See if branch, tag, committ option filled out, or prompt user
    if (branch): 
        branch_point_type = 'branch'
        branch_point_value = branch
    elif (tag): 
        branch_point_type = 'tag'
        branch_point_value = tag
    elif (commit): 
        branch_point_type = 'commit'
        branch_point_value = commit
    else:
        questions = [inquirer.List(
                    "branch_point",
                    message="Specify what to branch from",
                    choices=["branch", "tag", "commit"],)]
        branch_point_type = inquirer.prompt(questions)['branch_point']
        # TODO: Add logic to tab auto-complete for any of the types
        branch_point_value = input("Specify name of " + branch_point_type + ": ")

    # 3) See if fix, feat, or dev option filled out, or prompt user
    if (fix): 
        branch_type = 'fix'
        branch_type = fix
    elif (feat):
        branch_type = 'feat'
        branch_type = feat
    elif (dev):
        branch_type = 'dev'
        branch_type = dev
    else:
        branch_type = input("Specify type of branch to create (fix | feat | dev): ")
        branch_type_value = input("Specify name of issue number (or dev name): ")

    full_branch_name = branch_type + '-' + branch_type_value

    # 4) Write to database
    request.set_endpoint('branch')
    request.set_component_name()
    request.add_to_payload("branch", full_branch_name)
    payload_received = request.post_request()

    logging.info(request.headers)
    logging.info(request.payload)
    logging.info(payload_received)

    # 5) Create the branch using git and push
    component_obj.git_create_branch(branch_point_type, full_branch_name)
    component_obj.git_commit(request.github_uname)
    component_obj.git_push(full_branch_name)



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
    payload_received = requests.post(full_url, send_payload)
    print(payload_received)

    