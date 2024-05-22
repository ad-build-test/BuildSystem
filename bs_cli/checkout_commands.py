import click
import subprocess
import requests
import readline
from auto_complete import AutoComplete

@click.group()
def checkout():
    """checkout an existing [ component ]"""

    # TODO: Send a GET request to component db to get list of components
    server_url='https://accel-webapp-dev.slac.stanford.edu/api/cbs/v1/'
    component_list = requests.get(server_url + 'component')
    component_dict = component_list.json()
    payload = component_dict['payload']
    component_list = []
    for component in payload:
        component_list.append(component['name'])
    print(component_list)
    readline.set_completer(AutoComplete(component_list).complete)
    pass

@checkout.command()
# @click.option("--count", type=int, required=False, default=1, help="Number of greetings.")
# @click.option("--name", required=False, prompt="Your name", help="The person to greet.")
def component(): # TODO
    """Checkout an existing component/repo"""
    # args: (May make most of these prompted to user)
    # organization, template repo name, new repo owner (should be automatic),
    # name of repo, description, include_all_branches, private
    click.echo('Checkout new repo from template')
    # TODO:
    # 1) Maybe we can just use existing 'eco' function
    # OR
    # 1) Grab the list of components
    # 2) Make them all lower-case
    # 3) Then prompt the user for component name
        # 3.1) Should be tab autocomplete
    # 4) like 'eco' we should generate the configuration RELEASE_SITE file
    component_name = input('What is the component name? (<tab> for list)')
    # Send a request to get the url to the repo
    # then do a git clone if we are doing url, or otherwise copy from filepath