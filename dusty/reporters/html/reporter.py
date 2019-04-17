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
    Reporter: html
"""

from dusty.tools import log
from dusty.models.module import DependentModuleModel
from dusty.models.reporter import ReporterModel


class Reporter(DependentModuleModel, ReporterModel):
    """ Report results from scanners """

    def __init__(self, context):
        """ Initialize reporter instance """
        self.context = context
        self.config = \
            self.context.config["reporters"][__name__.split(".")[-2]]
        self.errors = list()
        self.meta = dict()

    def report(self):
        """ Report """
        log.debug(f"Config: {self.config}")
        log.info("Reporting")

    def get_errors(self):
        """ Get errors """
        return self.errors

    def get_meta(self, name, default=None):
        """ Get meta value """
        if name in self.meta:
            return self.meta[name]
        return default

    def on_start(self):
        """ Called when testing starts """

    def on_finish(self):
        """ Called when testing ends """

    def on_scanner_start(self, scanner):
        """ Called when scanner starts """

    def on_scanner_finish(self, scanner):
        """ Called when scanner ends """

    @staticmethod
    def fill_config(data_obj):
        """ Make sample config """
        data_obj.insert(len(data_obj), "file", "/path/to/report.html", comment="HTML report path")

    @staticmethod
    def validate_config(config):
        """ Validate config """
        log.debug(f"Config: {config}")

    @staticmethod
    def depends_on():
        """ Return required depencies """
        return []

    @staticmethod
    def run_before():
        """ Return optional depencies """
        return ["email"]

    @staticmethod
    def get_name():
        """ Reporter name """
        return "html"

    @staticmethod
    def get_description():
        """ Reporter description """
        return "HTML reporter"
