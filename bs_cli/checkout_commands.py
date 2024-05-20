import click
import subprocess

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
    # 1) Prompt user for args above
    # 2) checkout the curl request using those args
    # OR 
    # 1) just call the gh cli command, if you do this route, then gh cli must be authorized
    # This is optimal so authroize once, then we can use gh commands or gh api commands without
    # the need for authorizing each time