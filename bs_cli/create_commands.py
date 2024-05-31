import click
import requests
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

@create.command()
@click.option("-u", "--url", required=False, help="Add existing component to build system")
@click.pass_obj # Grab 'component' object from create group
def repo(component, url):
    """Create a new repo"""
    # args: (May make most of these prompted to user)
    # organization, template repo name, new repo owner (should be automatic),
    # name of repo, description, include_all_branches, private
# make a payload class to avoid this payload repeated code
    full_url = cli_configuration["server_url"]
    send_payload = {"linux_username": cli_configuration["linux_uname"],
                    "github_username": cli_configuration["github_uname"] }
    
    component.set_component_fields()

    send_payload["component"]=component.name
    send_payload["branch"]=component.branch_name
    if (url):
        send_payload["url"]=url
    print(send_payload)
    payload_received = requests.post(full_url + 'repo', send_payload)
    print(payload_received)

@create.command()
@click.pass_obj
def branch(component):
    """Create a new branch"""
    full_url = cli_configuration["server_url"]
    send_payload = {"linux_username": cli_configuration["linux_uname"],
                    "github_username": cli_configuration["github_uname"] }
    
    component.set_component_fields()
            
    send_payload["component"]=component.name
    send_payload["branch"]=component.branch_name
    print(send_payload)
    payload_received = requests.post(full_url + 'component', send_payload)
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

    