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
