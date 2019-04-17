#!/usr/bin/python3
# coding=utf-8

#   Copyright 2019 getcarrier.io
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

"""
    Main entry point
"""

import pkgutil
import argparse
import importlib
from logging import DEBUG, INFO

import pkg_resources
import dusty.commands
from dusty.tools import log


def main():
    """ Main """
    # Initialize argument parser
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        "-d", "--debug", dest="log_level",
        help="enable debug output",
        action="store_const", const=DEBUG, default=INFO
    )
    parser.add_argument(
        "--call-from-legacy", dest="call_from_legacy",
        help=argparse.SUPPRESS,
        action="store_true", default=False
    )
    subparsers = parser.add_subparsers(
        dest="command", title="commands",
        help="command to execute, use <command> -h to get command help"
    )
    subparsers.required = True
    # Load commands
    commands = dict()
    for _, name, pkg in pkgutil.iter_modules(dusty.commands.__path__):
        if pkg:
            continue
        module = importlib.import_module("dusty.commands.{}".format(name))
        argparser = subparsers.add_parser(
            module.Command.get_name(),
            help=module.Command.get_description(),
            formatter_class=argparse.ArgumentDefaultsHelpFormatter
        )
        commands[module.Command.get_name()] = module.Command(argparser)
    # Parse arguments
    args = parser.parse_args()
    # Setup logging
    log.init(args.log_level)
    # Display welcome message
    log.info(f"Dusty {pkg_resources.require('dusty')[0].version} is starting")
    log.debug("Loaded commands: {}".format(", ".join(list(commands.keys()))))
    # Run selected command
    commands[args.command].execute(args)
    # Display bye-bye message
    log.info("All done. Have a nice day")
