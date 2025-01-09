import click
import subprocess
import readline
import os
import tarfile
import subprocess
from adbs_cli.request import Request
from adbs_cli.component import Component
from adbs_cli.auto_complete import AutoComplete
from adbs_cli.cli_configuration import under_development,  Api

def change_directory(path):
    try:
        os.chdir(path)
        # print(f"Changed directory to {os.getcwd()}")
    except FileNotFoundError:
        print(f"Directory {path} not found.")
        exit(1)

def rename_directory(src_dir, dest_dir):
    try:
        if os.path.isdir(src_dir):
            os.rename(src_dir, dest_dir)
            print(f"Renamed directory {src_dir} to {dest_dir}")
        else:
            print(f"Directory {src_dir} not found.")
            exit(1)
    except Exception as e:
        print(f"Error renaming directory: {e}")
        exit(1)

def create_tarball(directory, tag):
    tarball_name = f"{tag}.tar.gz"
    try:
        with tarfile.open(tarball_name, "w:gz") as tar:
            tar.add(directory, arcname=os.path.basename(directory))
        print(f"Created tarball: {tarball_name}")
    except Exception as e:
        print(f"Error creating tarball: {e}")
        exit(1)

def create_and_push_git_tag(tag):
    try:
        # Create a Git tag
        subprocess.run(["git", "tag", tag], check=True)
        print(f"Created Git tag: {tag}")

        # Push the Git tag to the remote repository
        subprocess.run(["git", "push", "origin", tag], check=True)
        print(f"Pushed Git tag: {tag}")
    except subprocess.CalledProcessError as e:
        print(f"Error with Git command: {e}")
        exit(1)

@click.group()
def tag():
    """Tag [ create | edit | delete ]"""
    # Register our completer function for tags
    pass

@tag.command()
@click.option("-c", "--component", required=False, help="Component Name")
@click.option("-b", "--branch", required=True, help="Branch Name")
@click.option("-t", "--tag", required=True, help="Tag (ex: R1.4.2)")
@click.option("-r", "--results", required=True, help="The build results folder (ex: oscilloscope-main-RHEL7-12345), can be grabbed from PR build comment")
@click.option("-v", "--verbose", is_flag=True, required=False, help="More detailed output")
def create(component: str, branch: str, tag: str, results: str, verbose: bool): # TODO
    """Create a new tagged artifact and send to artifact storage. Then add a git tag"""
    # 1) Create tarball, send to deployment controller
    request = Request(Component(component), api=Api.DEPLOYMENT)
    request.set_component_name()
    payload = {"component_name": request.component.name,
               "branch": branch,
               "tag": tag,
               "results": results
               }
    request.add_dict_to_payload(payload)
    request.set_endpoint('/tag')

    response = request.post_request(log=verbose)
    # 2) Create git tag and push
    if (response.ok):
        click.echo("== ADBS == Tagged build results sent to artifact storage. Creating git tag...")
        create_and_push_git_tag(tag)

@tag.command()
def edit():
    """Edit an existing tag"""
    under_development() # TODO
    click.echo('edit tag')
    tag_name = input('What is the tag name? (<tab> for list): ')
    subprocess.run(['gh', 'release', 'edit', tag_name])
    # TODO: Figure out which flags for tag editing we want:
        # List of flags 
        # 1) tag name
        # 2) tag title
        # 3) ...

@tag.command()
def delete(): 
    """Delete an existing tag"""
    under_development() # TODO
    click.echo('delete tag')
    tag_name = input('What is the tag name? (<tab> for list): ')
    subprocess.run(['gh', 'release', 'delete', tag_name])