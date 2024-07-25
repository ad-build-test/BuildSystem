import click
import wget
import yaml
import os
import ansible_runner # TODO: Move to its own module once done testing
from component import Component
from request import Request

# TODO: May make logic a single function since its the same for all 3
# make the endpoint an argument
@click.group()
def run():
    """Run a [ build | deployment | test ]"""
    pass

@run.command()
@click.option("-c", "--component", required=False, help="Component Name")
@click.option("-b", "--branch", required=False, help="Branch Name")
def build(component: str, branch: str):
    """Trigger a build"""
    # 1) Set fields
    request = Request(Component(component, branch))
    request.set_component_fields()

    # 2) Write to database
    endpoint = 'build/component/' + request.component.name + '/branch/' + request.component.branch_name
    request.set_endpoint(endpoint)
    request.post_request(log=True)

@run.command()
@click.option("-c", "--component", required=False, help="Component Name")
@click.option("-b", "--branch", required=False, help="Branch Name")
def test(component: str, branch: str):
    """Trigger a test"""
    # 1) Set fields
    request = Request(Component(component, branch))
    request.set_component_fields()

    # 2) Write to database
    endpoint = 'test/component/' + request.component.name + '/branch/' + request.component.branch_name
    request.set_endpoint(endpoint)
    request.post_request(log=True)

@run.command()
@click.option("-c", "--component", required=False, help="Component Name")
@click.option("-b", "--branch", required=False, help="Branch Name")
def deployment(component: str, branch: str):
    """Run a deployment"""
    # 1) Set fields
    request = Request(Component(component, branch))    
    request.set_component_fields()

    """ASK ABOUT THIS: This may not make sense to clone manifest, since we 
    can assume that the repo the user is in, is the one they want to deploy
    answer: have both options, ideally they'd be in the repo they want to deploy,
    but user can specify another compononent (useful like if someone made a script
    to deploy a bunch of components). In that case, then you'd have to clone the repo
    to get the manifest and possibly a user-defined deployment script"""
    # 2) If user is not in repo, ask user where to clone repo, to get the manifest
    #   and the custom playbook (if specified)
        # Get URL from database
    if (not request.component.git_repo):
        clone_filepath = input("Specify filepath to clone repo temporarily: ")
        os.chdir(clone_filepath)
        component_info = request.get_component_from_db()
        # url = component_info['url'] + '/raw/' + request.component.branch_name + '/configure/CONFIG.yaml'
        # print(url)
        # wget.download(url)
        request.component.git_clone(component_info['url'])

    # Parse yaml
    yaml_filepath = 'configure/CONFIG.yaml'
    with open(yaml_filepath, 'r') as file:
        yaml_data = yaml.safe_load(file)
        # Print the parsed YAML data
    print("Parsed YAML data:")
    print(yaml_data)
    print(yaml_data["deploy"])

    # 3) Run the playbook
    r = ansible_runner.run(private_data_dir='/tmp', host_pattern='localhost', module='shell', module_args='whoami')
    print("{}: {}".format(r.status, r.rc))
    # successful: 0
    for each_host_event in r.events:
        print(each_host_event['event'])
    print("Final status:")
    print(r.stats)
    print(r.stdout)

    # 3) if not, check the database
        # 3.1) if not, ask user to add to database
    # 4) Run the playbook
    # hold off, work on steps to deploy build system entirely
    # 1) call the appropiate playbook - I believe we can store the component type in db,
    # then that can determine the type of deployment playbook to use
    # TODO: Where should we store these playbooks, same repo as CLI? 
        # If so, is that best practice? What if we make frequent playbook updates?
        # Do we roll out updates to /usr/bin frequent too?
        # Or do we want an API to take these requests like the rest of the commands here
        # If so, then the playbook would run on our cluster rather then on user space. Is that
        # what we want?
    # for the moment,
    # ? Upload the playbook and custom module to a collection then to the galaxy so its accessible
    # Specify the playbook in the test-ioc/configure/CONFIG.yaml manifest
    # And we can parse it locally here, eventually we will move this logic to backend
    #    grab the manifest from the component url, dont clone the whole thing
    #     just grab the manifest, (use wget/curl?)
    # Then if its not there, then we can check the deployment database if its spelled out
    # A user may make their own playbook if they want to, and then specify it in the manifest

    # TEMP - for now just use the test playbook
    # 2) 
