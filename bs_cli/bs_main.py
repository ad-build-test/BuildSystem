#!/usr/bin/python3
""" 
Offical CLI application for the accelerator directorate build system 
File: main.py

For more documentation refer to: 
https://confluence.slac.stanford.edu/display/LCLSControls/CLI+Tool
https://click.palletsprojects.com/en/8.1.x/
"""

# Plan:
# 1) Find an established library for CLI applications
    # Potential candidates: 
    # 1) argparse
    # 2) click
    # 3) pyCLI
    # 4) Typer
    # Lets use click for now since its minimal

# 2) Either use 'gh cli' as a pass through, or use the github REST API
    # 2.1) REST API may be favorable here to avoid reliance on installing gh cli
    # all we need is 'curl', and may be easier to update
    # Figure out how we can autheticate users just once, and store it in a safe file
    # or environment variable so any API request is straight forward
    # 2.2) gh cli has an advantage for having some of the commands we need already in 
    # place, with the right prompts and such.

# 3) Make the CLI look like standardized CLIs

# 4) Then we can start making the commands

# 5) We should add color - not priority

import click
import subprocess
import create_commands as create_group
import run_commands as run_group
import checkout_commands as checkout_group
import tag_commands as tag_group
# bs - build system
CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])

@click.group(context_settings=CONTEXT_SETTINGS)
def entry_point():
    """ Build System CLI\n
        For first-time usage, please 'bs login'
    """
@entry_point.command()
def login():
    """Login to authorize commands"""
    # May not need this function, we can just refer to an environment var
    click.echo('set token for authorizing github actions')
    subprocess.run(['gh', 'auth', 'login'])

if __name__ == '__main__':
    entry_point.add_command(create_group.create)
    entry_point.add_command(run_group.run)
    entry_point.add_command(checkout_group.checkout)
    entry_point.add_command(tag_group.tag)
    entry_point(prog_name='bs')

# TODO: If you want it as an exe that you can call from anywhere like "$ bs",
#  you can do the following:
    # 1. chmod +x bs_main.py
    # 2. ln -s bs_main.py bs
    # 3. sudo su
    # TODO: Copy folder instead, and check if 'run' command works in another repo
    # 4. cp -r bs_cli/ /usr/bin/
    # 5. ln -s bs_cli/bs_main.py bs
    # 6. mv bs /usr/bin/bs
    # done now you can call bs from anywhere
    
