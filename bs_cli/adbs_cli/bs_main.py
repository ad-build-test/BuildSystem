#!/usr/bin/python3
""" 
Offical CLI application for the accelerator directorate build system 
File: main.py

For more documentation refer to: 
https://confluence.slac.stanford.edu/display/LCLSControls/CLI+Tool
https://click.palletsprojects.com/en/8.1.x/
"""

import click
import os
import readline
import logging
from adbs_cli.cli_configuration import cli_configuration

import adbs_cli.create_commands as create_group
import adbs_cli.checkout_commands as checkout_group
import adbs_cli.tag_commands as tag_group
from adbs_cli.entry_point_commands import configure, build, test, deploy

# TODO: When done, add exception handling to all possible break points
# like [requests, environment vars, ]

# bs - build system
CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])

class OrderedGroup(click.Group):
    def list_commands(self, ctx):
        return self.commands.keys()  # Maintain the order of commands


@click.group(context_settings=CONTEXT_SETTINGS, cls=OrderedGroup)
def entry_point():
    """ Build System CLI\n
        For first-time usage, please 'bs configure'
    """
    linux_uname = os.environ.get('USER')
    github_uname = os.environ.get('AD_BUILD_GH_USER')
    # Set cli_configuration with linux_uname and gh_uname
    cli_configuration["linux_uname"] = linux_uname
    cli_configuration["github_uname"] = github_uname
         
def main():
    # Note - Order of adding in commands reflects on the frontend
    entry_point.add_command(configure)
    entry_point.add_command(checkout_group.checkout)
    entry_point.add_command(create_group.create)
    entry_point.add_command(build)
    entry_point.add_command(deploy)
    entry_point.add_command(test)
    entry_point.add_command(tag_group.tag)
    # Use the tab key for completion
    readline.parse_and_bind('tab: complete')
    logging.basicConfig(
        level=logging.INFO, # TODO: Change this to NOTSET when use in production
        format="%(levelname)s-%(name)s:[%(filename)s:%(lineno)s - %(funcName)s() ] %(message)s")
    entry_point(prog_name='bs')

if __name__ == '__main__':
    main()
