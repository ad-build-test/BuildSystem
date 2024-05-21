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
    # TODO:
    # 1) I think we will make a build, deploy, and test workflow for
    # each of the template repos.
    # 2) Then we can skip calling gh workflow run, and instead
    # use gh api to call the build.yaml or deploy.yaml or test.yaml
