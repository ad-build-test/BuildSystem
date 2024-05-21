import click
import subprocess

@click.group()
def tag():
    """Tag [ create | edit | delete ]"""
    pass

@tag.command()
# @click.option("--count", type=int, required=False, default=1, help="Number of greetings.")
# @click.option("--name", required=False, prompt="Your name", help="The person to greet.")
def create(): # TODO
    """Create a new tag"""
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
def edit(): # TODO
    """edit an existing tag"""
    click.echo('edit tag')
    subprocess.run(['gh', 'release', 'edit'])

@tag.command()
def delete(): 
    # BLOCKED: CATER does not have an API, but will have it once the NEW CATER 
    # Claudio is working on is finished
    # TODO: 
    # 1) get link to CATER, or see if CATER has API
    # 2) Then use that to generate the issue.
    # 3) May use gh api instead of gh issue so we can avoid prompting user each field
    """tag a new issue"""
    click.echo('delete tag')
    cater_id = click.prompt('What is the cater ID?')
    type = click.prompt('Which system do you want your issue in? [Github | Jira]').lower()
    print(type)
    if (type == 'github'):
        subprocess.run(['gh', 'issue', 'tag'])
        pass
    elif (type == 'jira'):
        pass
    else:
        click.echo('Invalid system choice')

"""
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