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
    Dependency tools
"""

from dusty.tools import log


def resolve_depencies(modules_ordered_dict):
    """ Resolve depencies """
    # Prepare module name map
    module_name_map = dict()
    for item in modules_ordered_dict:
        log.debug(modules_ordered_dict[item].__class__)
        log.debug(modules_ordered_dict[item].__class__.__name__)
        log.debug(modules_ordered_dict[item].__class__.__module__)
        module_name_map[modules_ordered_dict[item].__class__.__module__.split(".")[-2]] = item
    log.debug(module_name_map)


class DependentModule:
    """ Module with depencies """

    def __init__(self, name, depencies=None):
        self.name = name
        self.depencies = list()
        if isinstance(depencies, list):
            self.depencies.extend(depencies)
