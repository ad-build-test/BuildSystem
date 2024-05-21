import click
import subprocess
import requests

@click.group()
def checkout():
    """checkout an existing [ component ]"""
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
    cater_id = click.prompt('What is the cater ID?')
    # 1) Prompt user for args above
    # 2) checkout the curl request using those args
    # OR 
    # 1) just call the gh cli command, if you do this route, then gh cli must be authorized
    # This is optimal so authroize once, then we can use gh commands or gh api commands without
    # the need for authorizing each time