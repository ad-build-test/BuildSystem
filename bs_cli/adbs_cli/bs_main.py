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

import adbs_cli.create_commands as create_group
import adbs_cli.tag_commands as tag_group
import adbs_cli.admin_commands as admin_group
from adbs_cli.entry_point_commands import configure_user, generate_config, clone, build, test, deploy, mark

# TODO: When done, add exception handling to all possible break points
# like [requests, environment vars, ]

# bs - build system
CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])

class OrderedGroup(click.Group):
    def list_commands(self, ctx):
        return self.commands.keys()  # Maintain the order of commands


@click.group(context_settings=CONTEXT_SETTINGS, cls=OrderedGroup)
def entry_point():
    """ Build System (Software Factory) CLI\n
    Docs: https://confluence.slac.stanford.edu/x/RoOTGg
    """
         
def main():
    # Note - Order of adding in commands reflects on the frontend
    entry_point.add_command(configure_user)
    entry_point.add_command(generate_config)
    entry_point.add_command(clone)
    entry_point.add_command(create_group.create)
    entry_point.add_command(build)
    entry_point.add_command(deploy)
    entry_point.add_command(test)
    entry_point.add_command(mark)
    entry_point.add_command(tag_group.tag)
    entry_point.add_command(admin_group.admin)
    # Use the tab key for completion
    readline.parse_and_bind('tab: complete')
    logging.basicConfig(
        level=logging.INFO, # TODO: Change this to NOTSET when use in production
        format="%(levelname)s-%(name)s:[ %(filename)s:%(lineno)s ] %(message)s")
    entry_point(prog_name='bs')

if __name__ == '__main__':
    main()
