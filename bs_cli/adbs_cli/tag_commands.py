import click
import subprocess
import readline
from adbs_cli.auto_complete import AutoComplete
from adbs_cli.cli_configuration import under_development

@click.group()
def tag():
    """Tag [ create | edit | delete ]"""
    # Register our completer function for tags
    tag_bytes = subprocess.check_output(['gh', 'release', 'list', '--json', 'tagName', '--jq', '.[].tagName'])
    tag_list = tag_bytes.decode("utf-8").split()
    readline.set_completer(AutoComplete(tag_list).complete)

@tag.command()
# @click.option("--count", type=int, required=False, default=1, help="Number of greetings.")
# @click.option("--name", required=False, prompt="Your name", help="The person to greet.")
def create(): # TODO
    """Create a new tag"""
    under_development() # TODO
    # args: (May make most of these prompted to user)
    # organization, template repo name, new repo owner (should be automatic),
    # name of repo, description, include_all_branches, private
    subprocess.run(['gh', 'release', 'create'])
    # 1) Prompt user for args above
    # 2) tag the curl request using those args
    # OR 
    # 1) just call the gh cli command, if you do this route, then gh cli must be authorized
    # This is optimal so authroize once, then we can use gh commands or gh api commands without
    # the need for authorizing each time
@tag.command()
def edit():
    """Edit an existing tag"""
    under_development() # TODO
    click.echo('edit tag')
    tag_name = input('What is the tag name? (<tab> for list): ')
    subprocess.run(['gh', 'release', 'edit', tag_name])
    # TODO: Figure out which flags for tag editing we want:
        # List of flags 
        # 1) tag name
        # 2) tag title
        # 3) ...

@tag.command()
def delete(): 
    """Delete an existing tag"""
    under_development() # TODO
    click.echo('delete tag')
    tag_name = input('What is the tag name? (<tab> for list): ')
    subprocess.run(['gh', 'release', 'delete', tag_name])

""" gh pr list --json author --jq '.[].author.login'
tag gh commands
release
create
delete-asset
delete
download
edit
list
upload
view
"""