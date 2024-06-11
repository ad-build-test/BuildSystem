import click
from request import Request
from auto_complete import AutoComplete
from component import Component
import logging
import inquirer


@click.group()
def create():
    """Create a new [ repo | branch | issue ]"""
    pass

@create.command()
@click.option("-c", "--component", required=False, help="Component Name")
@click.option("-b", "--branch", required=False, help="Branch Name")
@click.option("-u", "--url", required=False, help="Add existing component to build system")
def repo(component: str, branch: str, url: str):
    """Create a new repo"""
    request = Request(Component(component, branch))
    # args: (May make most of these prompted to user)
    # organization, template repo name, new repo owner (should be automatic),
    # name of repo, description, include_all_branches, private
    # TODO: May make the requests.post a function in request class as well since its repeating
    request.set_endpoint('component')
    request.set_component_fields()
    if (url): request.add_to_payload("url", url)
    # payload_received = request.post_request()

    logging.info(request.headers)
    logging.info(request.payload)
    logging.info(payload_received)
    

@create.command()
@click.option("-f", "--fix", type=int, required=False, help="Add fix branch based off issue number")
@click.option("-ft", "--feat", type=int, required=False, help="Add feature branch based off issue number")
@click.option("-d", "--dev", required=False, help="Add development branch")
@click.option("-b", "--branch", required=False, help="Specify which branch to branch from")
@click.option("-t", "--tag", required=False, help="Specify which tag to branch from")
@click.option("-ct", "--commit", required=False, help="Specify which commit to branch from")
@click.option("-a", "--add", is_flag=True, required=False, help="Add an EXISTING branch to database")
def branch(fix: int, feat: int, dev: str, branch: str, tag: str, commit: str, add: bool):
    """Create a new branch"""
    component_obj = Component()
    request = Request(component_obj)

    # 1) First check that user is in repo
    if (not component_obj.set_cur_dir_component()):
        click.echo('fatal: not a git repository (or any of the parent directories)')
        return
    # 1.1) if adding existing branch, then use current repo/branch
    if (add):
        full_branch_name = component_obj.branch_name
    else:
        # 2) See if branch, tag, committ option filled out, or prompt user
        branches = component_obj.git_get_branches()
        tags = component_obj.git_get_tags()
        # commits = component_obj.git_get_commits() # TODO: query branch for commit OR get the list of commits from every branch
        if (branch): 
            if (branch in branches):
                branch_point_type = 'branch'
                branch_point_value = branch
            else:
                click.echo('fatal: invalid branch name!')
                return
        elif (tag): 
            if (tag in tags):
                branch_point_type = 'tag'
                branch_point_value = tag
            else:
                click.echo('fatal: invalid tag name!')
                return
        elif (commit): 
            branch_point_type = 'commit'
            branch_point_value = commit
            # if (commit in commits):
            #     branch_point_type = 'commit'
            #     branch_point_value = commit
            # else:
            #     click.echo('fatal: invalid commit name!')
            #     return
        else:
            question = [inquirer.List(
                        "branch_point",
                        message="Specify what to branch from",
                        choices=["branch", "tag", "commit"])]
            branch_point_type = inquirer.prompt(question)['branch_point']
            if (branch_point_type == 'branch'): AutoComplete.set_auto_complete_vals('branch', branches)
            elif (branch_point_type == 'tag'): AutoComplete.set_auto_complete_vals('tag', tags)
            
            branch_point_value = input("Specify name of " + branch_point_type + ": ")

        # 3) See if fix, feat, or dev option filled out, or prompt user
        if (fix): 
            branch_type = 'fix'
            branch_type_value = fix
        elif (feat):
            branch_type = 'feat'
            branch_type_value = feat
        elif (dev):
            branch_type = 'dev'
            branch_type_value = dev
        else:
            question = [inquirer.List(
                        "branch_type",
                        message="Specify type of branch to create",
                        choices=["fix", "feat", "dev"])]
            branch_type = inquirer.prompt(question)['branch_type']
            branch_type_value = input("Specify name of issue number (or dev name): ")

        full_branch_name = branch_type + '-' + branch_type_value

    # 4) Write to database
    endpoint = 'component/' + component_obj.name + '/branch'
    request.set_endpoint(endpoint)
    request.set_component_name()
    request.add_to_payload("branch", full_branch_name)
    payload_received = request.post_request()

    logging.info(request.headers)
    logging.info(request.payload)
    logging.info(payload_received)

    # 5) Create the branch using git and push
    if (not add): # Dont create branch if user just wants to add to database
        component_obj.git_create_branch(branch_point_type, branch_point_value, full_branch_name)
        component_obj.git_commit(full_branch_name)
        if (component_obj.git_push(full_branch_name)):
            click.echo('Successfully created branch: ' + full_branch_name)



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

    