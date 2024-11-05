import click
import requests
import os
import git
from adbs_cli.auto_complete import AutoComplete
from adbs_cli.request import Request
from adbs_cli.component import Component
from adbs_cli.cli_configuration import under_development

@click.group()
def checkout():
    """Checkout an existing [ component/branch ]"""

@checkout.command()
@click.argument("component")
@click.option("-b", "--branch", required=False, help="Branch Name")
def component(component: str, branch: str="main"):
    """Checkout an existing component/branch"""

    # 1) Set fields
    request = Request()
    # request.set_component_fields()

    # 2) Request for all components
    endpoint = 'component'
    request.set_endpoint(endpoint)
    response = request.get_request(log=True)

    component_list = response.json()['payload']
    print(f'Component_list: {component_list}')

    # 3) Check for a match on component name, then get URL
    # Define the key you are searching for
    search_key = 'name'

    # Iterate over the list of dictionaries and check for the key
    found = False
    for item in component_list:
        if search_key in item:
            if item[search_key] == component:
                found = True
                component_url = item["url"]
                print(component_url)
                break  # If you only want the first match, use 'break'
            
    if not found:
        print(f"Value '{component}' not found in any of the dictionaries.")

    # 4) Git clone the URL
    dir_path = os.path.join(os.getcwd(), component)
    git.Repo.clone_from(component_url, dir_path, branch=branch)

    