import click
import subprocess

CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])

@click.group(context_settings=CONTEXT_SETTINGS)
def run():
    """Run a [ build | deployment | test ]"""
    pass

@run.command()
def workflow():
    """Command to trigger a workflow"""
    click.echo('Run a workflow with the repo')
    subprocess.run(['gh', 'workflow', 'run'])