import click
import subprocess

import readline

class SimpleCompleter(object):
    
    def __init__(self, options):
        self.options = sorted(options)
        return

    def complete(self, text, state):
        response = None
        if state == 0:
            # This is the first time for this text, so build a match list.
            if text:
                self.matches = [s 
                                for s in self.options
                                if s and s.startswith(text)]
            else:
                self.matches = self.options[:]
        
        # Return the state'th item from the match list,
        # if we have that many.
        try:
            response = self.matches[state]
        except IndexError:
            response = None
        return response


@click.group()
def tag():
    """Tag [ create | edit | delete ]"""
    # Use the tab key for completion
    readline.parse_and_bind('tab: complete')
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
    """Edit an existing tag"""
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
    """Delete an existing tag"""

    click.echo('delete tag')
    out = subprocess.check_output(['gh', 'release', 'list', '--json', 'tagName', '--jq', '.[].tagName'])
    out = out.decode("utf-8")
    out_list = out.split()
    print(out_list)
        # Register our completer function
    readline.set_completer(SimpleCompleter(out_list).complete)
    tag_name = click.prompt('What is the tag name? (<tab> for list)')
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