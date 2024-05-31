import click
import requests
from auto_complete import AutoComplete
from cli_configuration import cli_configuration

@click.group()
def checkout():
    """checkout an existing [ component/branch ]"""

@checkout.command()
def component(): # TODO
    """Checkout an existing component/branch"""
    # TODO:
    # 0) Do we need the branch if were using git to checkout existing branch?
    # 1) Maybe we can just use existing 'eco' function
    # OR
    # 1) Grab the list of components
    # 2) Make them all lower-case
    # 3) Then prompt the user for component name
        # 3.1) Should be tab autocomplete
    # 4) like 'eco' we should generate the configuration RELEASE_SITE file
    AutoComplete.set_auto_complete_vals("component")
    component_name = input('What is the component name? (<tab> for list)')
    AutoComplete.set_auto_complete_vals("branch")
    branch_name = input('What is the branch name? (<tab> for list)')
    # Send a request to get the url to the repo
    # then do a git clone if we are doing url, or otherwise copy from filepath

    # Pass in component and branch
    full_url = cli_configuration["server_url"] + 'component'
    send_payload = {"component": component_name,
                    "branch": branch_name,
                    "linux_username": cli_configuration["linux_uname"],
                    "github_username": cli_configuration["github_uname"] }
    payload_received = requests.post(full_url, send_payload)
    print(payload_received)
    