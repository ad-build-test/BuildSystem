import click
import subprocess
import os
import subprocess
from adbs_cli.request import Request
from adbs_cli.component import Component
from adbs_cli.auto_complete import AutoComplete
from adbs_cli.cli_configuration import under_development,  Api

@click.group(hidden=True)
def admin():
    """admin [ create | edit | delete ]"""
    pass

@admin.command()
@click.option("-c", "--component", required=False, help="Component Name")
@click.option("-b", "--branch", required=True, help="Branch Name")
@click.option("-t", "--tag", required=True, help="Tag (ex: R1.4.2)")
@click.option("-r", "--results", required=True, help="The build results folder (ex: oscilloscope-main-RHEL7-12345), can be grabbed from PR build comment")
@click.option("-v", "--verbose", is_flag=True, required=False, help="More detailed output")
def add(component: str, branch: str, tag: str, results: str, verbose: bool): # TODO
    """Add a component to the component database"""
    click.echo("== ADBS == Failure to add to database")
