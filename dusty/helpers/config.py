#!/usr/bin/python3
# coding=utf-8
# pylint: disable=I0011,R0903

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
    Config helper
"""

import os
import re
import yaml

from ruamel.yaml.comments import CommentedMap

from dusty.tools import log
from dusty.data import constants


class ConfigHelper:
    """ Parses config """

    def __init__(self, context):
        """ Initialize context instance """
        self.context = context

    def load(self, config_variable, config_file, suite):
        """ Load and parse config """
        config_data = os.environ.get(config_variable, None)
        if not config_data:
            log.info("Loading %s config from %s", suite, config_file)
            with open(config_file, "rb") as file_:
                config_data = file_.read()
        else:
            log.info("Loading %s config from %s", suite, config_variable)
        self.context.suite = suite
        config = self._variable_substitution(
            yaml.load(
                os.path.expandvars(config_data),
                Loader=yaml.FullLoader
            )
        )
        if not self._validate_config_base(config):
            raise ValueError("Invalid config")
        self.context.config = config["suites"].get(suite)

    def _variable_substitution(self, obj):
        """ Allows to use raw environmental variables inside YAML/JSON config """
        if isinstance(obj, dict):
            for key in list(obj.keys()):
                obj[self._variable_substitution(key)] = \
                    self._variable_substitution(obj.pop(key))
        if isinstance(obj, list):
            for index, item in enumerate(obj):
                obj[index] = self._variable_substitution(item)
        if isinstance(obj, str) and re.match(r"^\@[a-zA-Z_][a-zA-Z0-9_]*$", obj) \
                and obj[1:] in os.environ:
            return os.environ[obj[1:]]
        return obj

    def _validate_config_base(self, config):
        if config.get(constants.CONFIG_VERSION_KEY, 0) != constants.CURRENT_CONFIG_VERSION:
            log.error("Invalid config version")
            return False
        if "suites" not in config:
            log.error("Suites are not defined")
            return False
        if not config["suites"].get(self.context.suite, None):
            log.error("Suite is not defined: %s", self.context.suite)
            return False
        return True

    @staticmethod
    def fill_config(data_obj):
        """ Make sample config """
        data_obj.insert(
            len(data_obj), constants.CONFIG_VERSION_KEY, constants.CURRENT_CONFIG_VERSION
        )
        data_obj.insert(len(data_obj), "suites", CommentedMap(), comment="Test suites")
