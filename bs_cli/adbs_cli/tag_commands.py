import click
import subprocess
import readline
import os
import tarfile
import subprocess
from adbs_cli.auto_complete import AutoComplete
from adbs_cli.cli_configuration import under_development

def get_user_input(prompt):
    return input(prompt)

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
    tag_bytes = subprocess.check_output(['gh', 'release', 'list', '--json', 'tagName', '--jq', '.[].tagName'])
    tag_list = tag_bytes.decode("utf-8").split()
    readline.set_completer(AutoComplete(tag_list).complete)

@tag.command()
@click.option("-c", "--component", required=False, help="Component Name")
@click.option("-b", "--branch", required=False, help="Branch Name")
@click.option("-t", "--tag", required=True, help="Tag (ex: R1.4.2)")
@click.option("-r", "--results", required=True, help="The build results folder (ex: oscilloscope-main-RHEL7-12345), can be grabbed from PR build comment")
def create(component: str, branch: str, tag: str, results: str): # TODO
    """Create a new tagged artifact and send to artifact storage. Then add a git tag"""
    # Get user input
    # Patrick move steps 1-4 to deployment controller 
    # leave step 5 here to create the git tag 
    # TODO: Add the automatic checking of comp/branch
    scratch_filepath = "/sdf/group/ad/eed/ad-build/scratch"
    results_dir_top = os.path.join(scratch_filepath, results, component)

    # 1) Change to the 'build_results' directory
    build_results_dir = os.path.join(results_dir_top, "build_results")
    build_results = f"{component}-{branch}"
    change_directory(build_results_dir)

    # 2) Rename the specified directory to the tag
    build_results_full_path = os.path.join(build_results_dir, build_results)
    rename_directory(build_results_full_path, os.path.join(build_results_dir, tag))

    # 3) Create a tarball of the renamed directory
    create_tarball(os.path.join(build_results_dir, tag), tag)

    # 4) Push to artifact storage

    # Step 5: Create a Git tag and push it
    # create_and_push_git_tag(tag)

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