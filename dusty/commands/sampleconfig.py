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
    Command: sampleconfig
"""

import ruamel.yaml

from ruamel.yaml.comments import CommentedMap

from dusty.tools import log
from dusty.models.module import ModuleModel
from dusty.models.command import CommandModel
from dusty.helpers.config import ConfigHelper
from dusty.scanners.performer import ScanningPerformer
from dusty.processing.performer import ProcessingPerformer
from dusty.reporters.performer import ReportingPerformer


class Command(ModuleModel, CommandModel):
    """ Generate sample config """

    def __init__(self, argparser):
        """ Initialize command instance, add arguments """
        argparser.add_argument(
            "-o", "--output", dest="output_file",
            help="path to output file",
            type=str, required=True
        )

    def execute(self, args):
        """ Run the command """
        log.info("Starting")
        # Make instances
        config = ConfigHelper
        scanning = ScanningPerformer
        processing = ProcessingPerformer
        reporting = ReportingPerformer
        # Make config
        data = CommentedMap()
        # Fill config
        config.fill_config(data)
        data_obj = data["suites"]
        data_obj.insert(len(data_obj), "example", CommentedMap(), comment="Example test suite")
        data_obj["example"].insert(0, "general", CommentedMap(), comment="General config")
        scanning.fill_config(data_obj["example"])
        processing.fill_config(data_obj["example"])
        reporting.fill_config(data_obj["example"])
        # Save to file
        yaml = ruamel.yaml.YAML()
        with open(args.output_file, "wb") as output:
            yaml.dump(data, output)
        # Done
        log.info("Done")

    @staticmethod
    def fill_config(data_obj):
        """ Make sample config """
        raise NotImplementedError()

    @staticmethod
    def validate_config(config):
        """ Validate config """
        raise NotImplementedError()

    @staticmethod
    def get_name():
        """ Command name """
        return "sampleconfig"

    @staticmethod
    def get_description():
        """ Command help message (description) """
        return "generate sample config"
