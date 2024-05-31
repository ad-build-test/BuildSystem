import click
from request import Request
from component import Component
import logging

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
def branch(component: str, fix: int, feat: int, dev: str, branch: str):
    """Create a new branch"""
    request = Request(Component(component))
    # TODO: May make the branch ourselves in this case not through backend
    # TODO: Force the user to enter the repository they want to create a branch in
    #       This will make it simpler to use git commands directly
    
    dont do same logic as component where you look at what branch their sitting in
    Just have option available or prompt user. 
    We also want to create a branch off a branch (tip of branch),
    tag (may want to add sanity check logic if there are newer tags
          than the user wants to branch off from),
    or committ.
    
    branch_name=''
    request.component.prompt_branch_name('Branch name to branch from? (<tab>-complete) ')
    # Commands to use
    # git commit --allow-empty -m "initial commit"
    # git push -u origin <branch_name>

    request.set_endpoint('branch')
    request.set_component_name()
    payload_received = request.post_request()

    logging.info(request.headers)
    logging.info(request.payload)
    logging.info(payload_received)

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

    