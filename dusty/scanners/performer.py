#!/usr/bin/python3
# coding=utf-8
# pylint: disable=I0011,R0903,W0702

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
    Scanning performer
"""

import importlib
import pkgutil

from ruamel.yaml.comments import CommentedMap

from dusty.tools import log
from dusty.models.module import ModuleModel
from dusty.models.performer import PerformerModel


class ScanningPerformer(ModuleModel, PerformerModel):
    """ Runs scanners """

    def __init__(self, context):
        """ Initialize instance """
        self.context = context

    def prepare(self):
        """ Prepare for action """
        log.info("Preparing")
        general_config = dict()
        if "scanners" in self.context.config["general"]:
            general_config = self.context.config["general"]["scanners"]
        config = self.context.config["scanners"]
        for scanner_type in config:
            for scanner_name in config[scanner_type]:
                if not isinstance(config[scanner_type][scanner_name], dict):
                    config[scanner_type][scanner_name] = dict()
                # Merge general config
                if scanner_type in general_config:
                    merged_config = general_config[scanner_type].copy()
                    merged_config.update(config[scanner_type][scanner_name])
                    config[scanner_type][scanner_name] = merged_config
                try:
                    # Init scanner instance
                    scanner = importlib.import_module(
                        f"dusty.scanners.{scanner_type}.{scanner_name}.scanner"
                    ).Scanner
                    # Validate config
                    scanner.validate_config(config[scanner_type][scanner_name])
                    # Add to context
                    self.context.scanners[scanner.get_name()] = scanner(self.context)
                except:
                    log.exception(
                        "Failed to prepare %s scanner %s",
                        scanner_type, scanner_name
                    )

    def perform(self):
        """ Perform action """
        log.info("Starting scanning")
        reporting = self.context.performers.get("reporting", None)
        if reporting:
            reporting.on_start()
        for scanner_module_name in self.context.scanners:
            scanner = self.context.scanners[scanner_module_name]
            log.info(f"Running {scanner_module_name} ({scanner.get_description()})")
            if reporting:
                reporting.on_scanner_start(scanner_module_name)
            try:
                scanner.execute()
            except:
                log.exception("Scanner %s failed", scanner_module_name)
            if reporting:
                reporting.on_scanner_finish(scanner_module_name)
        if reporting:
            reporting.on_finish()

    def get_module_meta(self, module, name, default=None):
        """ Get submodule meta value """
        try:
            module_name = importlib.import_module(
                f"dusty.scanners.{module}.scanner"
            ).Scanner.get_name()
            if module_name in self.context.scanners:
                return self.context.scanners[module_name].get_meta(name, default)
            return default
        except:
            return default

    @staticmethod
    def fill_config(data_obj):
        """ Make sample config """
        general_obj = data_obj["general"]
        general_obj.insert(
            len(general_obj), "scanners", CommentedMap(), comment="Settings common to all scanners"
        )
        general_scanner_obj = general_obj["scanners"]
        data_obj.insert(len(data_obj), "scanners", CommentedMap(), comment="Scanners config")
        scanner_obj = data_obj["scanners"]
        scanners_module = importlib.import_module("dusty.scanners")
        for _, name, pkg in pkgutil.iter_modules(scanners_module.__path__):
            if not pkg:
                continue
            general_scanner_obj.insert(len(general_scanner_obj), name, CommentedMap())
            scanner_type = importlib.import_module("dusty.scanners.{}".format(name))
            scanner_obj.insert(len(scanner_obj), name, CommentedMap())
            inner_obj = scanner_obj[name]
            for _, inner_name, inner_pkg in pkgutil.iter_modules(scanner_type.__path__):
                if not inner_pkg:
                    continue
                scanner = importlib.import_module(
                    "dusty.scanners.{}.{}.scanner".format(name, inner_name)
                )
                inner_obj.insert(
                    len(inner_obj), inner_name, CommentedMap(),
                    comment=scanner.Scanner.get_description()
                )
                scanner.Scanner.fill_config(inner_obj[inner_name])

    @staticmethod
    def validate_config(config):
        """ Validate config """
        if "scanners" not in config:
            log.error("No scanners defined in config")
            raise ValueError("No scanners configuration present")

    @staticmethod
    def get_name():
        """ Module name """
        return "scanning"

    @staticmethod
    def get_description():
        """ Module description or help message """
        raise "performs scanning"
