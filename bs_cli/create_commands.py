import click
import requests
from auto_complete import AutoComplete
from cli_configuration import cli_configuration
from component import Component

@click.group()
@click.option("-c", "--component", required=False, help="Component Name")
@click.option("-b", "--branch", required=False, help="Branch Name")
@click.pass_context
def create(ctx, component, branch):
    """Create a new [ repo | branch | issue ]"""
    ctx.obj = Component(component, branch)
    pass

# TODO: this will be a common function shared amongst 
def check_working_dir():
    pass


@create.command()
@click.pass_obj # Grab 'component' object from create group
def repo(component): # TODO
    # TODO: 
    # 1) add option to add an existing repo to the component database
    """Create a new repo from a template repository"""
    # args: (May make most of these prompted to user)
    # organization, template repo name, new repo owner (should be automatic),
    # name of repo, description, include_all_branches, private
            
    # Pass in component and branch
    full_url = cli_configuration["server_url"] + 'component'
    send_payload = {"component": component_name,
                    "branch": branch_name,
                    "linux_username": cli_configuration["linux_uname"],
                    "github_username": cli_configuration["github_uname"] }
    # payload_received = requests.post(full_url, send_payload)
    # print(payload_received)

@create.command()
@click.pass_obj
def branch(component):
    """Create a new branch"""
    full_url = cli_configuration["server_url"] + 'component'
    send_payload = {"linux_username": cli_configuration["linux_uname"],
                    "github_username": cli_configuration["github_uname"] }
    
    # 1) If component options passed in, then use those
    if (component.name):
        if (component.branch_name == None):
            component.prompt_branch_name() 
    # 2) Else set working directory as the component
    else:
         if (component.set_cur_dir_component() == False):
            # 3) Else prompt user for component/branch
            component.prompt_name()
            component.prompt_branch_name()
            
    send_payload["component"]=component.name
    send_payload["branch"]=component.branch_name
    print(send_payload)
    return # TODO: TEMP HERE
    payload_received = requests.post(full_url, send_payload)
    print(payload_received)

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

    