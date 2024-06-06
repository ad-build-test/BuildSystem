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
    endpoint = 'component/' + request.component.name + '/build'
    request.set_endpoint(endpoint)
    payload_received = request.post_request()

    logging.info(request.headers)
    logging.info(request.payload)
    logging.info(payload_received)

@run.command()
@click.option("-c", "--component", required=False, help="Component Name")
@click.option("-b", "--branch", required=False, help="Branch Name")
def test(component: str, branch: str):
    """Trigger a test"""
    # 1) Set fields
    request = Request(Component(component, branch))
    request.set_component_fields()

    # 2) Write to database
    endpoint = 'component/' + request.component.name + '/test'
    request.set_endpoint(endpoint)
    payload_received = request.post_request()

    logging.info(request.headers)
    logging.info(request.payload)
    logging.info(payload_received)
