import click
import requests
from component import Component
from payload import Payload

@click.group()
@click.option("-c", "--component", required=False, help="Component Name")
@click.option("-b", "--branch", required=False, help="Branch Name")
@click.pass_context
def run(ctx, component, branch):
    """Run a [ build | deployment | test ]"""
    component_obj = Component(component, branch)
    ctx.obj = Payload(component_obj)
    pass

@run.command()
@click.pass_obj # Grab 'component' object from run group
def build(payload):
    """Trigger a build"""
    payload.set_component_fields()
    print(payload.send_payload)
    payload_received = requests.post(payload.url + 'build', payload.send_payload)
    print(payload_received)

@run.command()
@click.pass_obj
def test(payload):
    """Trigger a test"""
    payload.set_component_fields()
    print(payload.send_payload)
    payload_received = requests.post(payload.url + 'test', payload.send_payload)
    print(payload_received)
