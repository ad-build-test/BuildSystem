import click
import logging
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
    response = request.post_request()

    logging.info(response.status_code)
    logging.info(response.json())
    logging.info(response.request.url)
    logging.info(response.request.body)
    logging.info(response.request.headers)

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
    response = request.post_request()

    logging.info(response.status_code)
    logging.info(response.json())
    logging.info(response.request.url)
    logging.info(response.request.body)
    logging.info(response.request.headers)

@run.command()
@click.option("-c", "--component", required=False, help="Component Name")
@click.option("-b", "--branch", required=False, help="Branch Name")
def deployment(component: str, branch: str):
    """Run a deployment"""
    # 1) call the appropiate playbook - I believe we can store the component type in db,
    # then that can determine the type of deployment playbook to use
    # TODO: Where should we store these playbooks, same repo as CLI? 
        # If so, is that best practice? What if we make frequent playbook updates?
        # Do we roll out updates to /usr/bin frequent too?
        # Or do we want an API to take these requests like the rest of the commands here
        # If so, then the playbook would run on our cluster rather then on user space. Is that
        # what we want?
    for the moment,
    # ? Upload the playbook and custom module to a collection then to the galaxy so its accessible
    # Specify the playbook in the test-ioc/configure/CONFIG.yaml manifest
    # And we can parse it locally here, eventually we will move this logic to backend
    #    grab the manifest from the component url, dont clone the whole thing
    #     just grab the manifest, (use wget/curl?)
    # Then if its not there, then we can check the deployment database if its spelled out
    # A user may make their own playbook if they want to, and then specify it in the manifest

    # TEMP - for now just use the test playbook
    # 2) 
