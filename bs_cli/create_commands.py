import click
import subprocess

@click.group()
def create():
    """Create a new [ repo | branch | issue ]"""
    pass

@create.command()
# @click.option("--count", type=int, required=False, default=1, help="Number of greetings.")
# @click.option("--name", required=False, prompt="Your name", help="The person to greet.")
def repo(): # TODO
    """Create a new repo from a template repository"""
    # args: (May make most of these prompted to user)
    # organization, template repo name, new repo owner (should be automatic),
    # name of repo, description, include_all_branches, private
    click.echo('Create new repo from template')
    subprocess.run(['gh', 'repo', 'create'])
    # 1) Prompt user for args above
    # 2) Create the gh api request using those args
    # OR 
    # 1) just call the gh cli command, if you do this route, then gh cli must be authorized
    # This is optimal so authroize once, then we can use gh commands or gh api commands without
    # the need for authorizing each time
@create.command()
def branch(): # TODO
    """Create a new branch"""
    click.echo('Create new branch')

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
    if (type == 'github'):
        subprocess.run(['gh', 'issue', 'create'])
        pass
    elif (type == 'jira'):
        pass
    else:
        click.echo('Invalid system choice')