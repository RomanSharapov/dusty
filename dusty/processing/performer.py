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
    Processing performer
"""

import importlib
import pkgutil

from ruamel.yaml.comments import CommentedMap

from dusty.tools import log
from dusty.tools import dependency
from dusty.models.module import ModuleModel
from dusty.models.performer import PerformerModel


class ProcessingPerformer(ModuleModel, PerformerModel):
    """ Process results """

    def __init__(self, context):
        """ Initialize instance """
        self.context = context

    def prepare(self):
        """ Prepare for action """
        log.info("Preparing")
        general_config = dict()
        if "processing" in self.context.config["general"]:
            general_config = self.context.config["general"]["processing"]
        config = self.context.config["processing"]
        for processor_name in config:
            # Merge general config
            merged_config = general_config.copy()
            merged_config.update(config[processor_name])
            config[processor_name] = merged_config
            try:
                # Init processor instance
                processor = importlib.import_module(
                    f"dusty.processing.{processor_name}.processor"
                ).Processor
                # Validate config
                processor.validate_config(config[processor_name])
                # Add to context
                self.context.processing[processor.get_name()] = processor(self.context)
            except:
                log.exception("Failed to prepare processor %s", processor_name)
        # Resolve depencies
        dependency.resolve_depencies(self.context.processing)

    def perform(self):
        """ Perform action """
        log.info("Starting result processing")
        # Collect all scanner results and errors
        for scanner_module_name in self.context.scanners:
            scanner = self.context.scanners[scanner_module_name]
            self.context.results.extend(scanner.get_results())
            self.context.errors[scanner_module_name] = scanner.get_errors()
        # Run processors
        performed = set()
        perform_processing_iteration = True
        while perform_processing_iteration:
            perform_processing_iteration = False
            for processor_module_name in list(self.context.processing):
                if processor_module_name in performed:
                    continue
                performed.add(processor_module_name)
                perform_processing_iteration = True
                processor = self.context.processing[processor_module_name]
                try:
                    processor.execute()
                except:
                    log.exception("Processor %s failed", processor_module_name)

    def get_module_meta(self, module, name, default=None):
        """ Get submodule meta value """
        try:
            module_name = importlib.import_module(
                f"dusty.processing.{module}.processor"
            ).Processor.get_name()
            if module_name in self.context.processing:
                return self.context.processing[module_name].get_meta(name, default)
            return default
        except:
            return default

    def schedule_processor(self, processor_name, processor_config):
        """ Schedule processor run in current context after all already configured processors """
        try:
            # Init processor instance
            processor = importlib.import_module(
                f"dusty.processing.{processor_name}.processor"
            ).Processor
            if processor.get_name() in self.context.processing:
                log.debug("Processor %s already scheduled", processor_name)
                return
            # Prepare config
            config = self.context.config["processing"]
            if processor_name not in config or not isinstance(config[processor_name], dict):
                config[processor_name] = dict()
            if "processing" in self.context.config["general"]:
                general_config = self.context.config["general"]["processing"]
                merged_config = general_config.copy()
                merged_config.update(config[processor_name])
                config[processor_name] = merged_config
            config[processor_name].update(processor_config)
            # Validate config
            processor.validate_config(config[processor_name])
            # Add to context
            self.context.processing[processor.get_name()] = processor(self.context)
            # Resolve depencies
            dependency.resolve_depencies(self.context.processing)
            # Done
            log.info("Scheduled processor %s", processor_name)
        except:
            log.exception("Failed to schedule processor %s", processor_name)

    @staticmethod
    def fill_config(data_obj):
        """ Make sample config """
        general_obj = data_obj["general"]
        general_obj.insert(
            len(general_obj), "processing", CommentedMap(),
            comment="Settings common to all processors"
        )
        data_obj.insert(len(data_obj), "processing", CommentedMap(), comment="Processing config")
        processing_obj = data_obj["processing"]
        processing_module = importlib.import_module("dusty.processing")
        for _, name, pkg in pkgutil.iter_modules(processing_module.__path__):
            if not pkg:
                continue
            processor = importlib.import_module(
                "dusty.processing.{}.processor".format(name)
            )
            processing_obj.insert(
                len(processing_obj), name, CommentedMap(),
                comment=processor.Processor.get_description()
            )
            processor.Processor.fill_config(processing_obj[name])

    @staticmethod
    def validate_config(config):
        """ Validate config """
        if "processing" not in config:
            log.warning("No processing defined in config")

    @staticmethod
    def get_name():
        """ Module name """
        return "processing"

    @staticmethod
    def get_description():
        """ Module description or help message """
        raise "performs result processing"
