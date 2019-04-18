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
        module_name_map[modules_ordered_dict[item].__class__.__module__.split(".")[-2]] = \
            modules_ordered_dict[item]
    log.debug("Modules: %s", str(list(module_name_map.keys())))
    # Check required depencies
    for module_name in module_name_map:
        for dependency in module_name_map[module_name].depends_on():
            if dependency not in module_name_map:
                log.error("Dependency %s not present (required by %s)", dependency, module_name)
                raise RuntimeError("Required dependency not present")
    # Walk modules
    module_order = list()
    visited_modules = set()
    for module_name in module_name_map:
        if module_name not in module_order:
            _walk_module_depencies(module_name, module_name_map, module_order, visited_modules)
    # Re-order modules
    log.debug("Order: %s", str(module_order))
    for module_name in module_order:
        modules_ordered_dict.move_to_end(module_name_map[module_name].get_name())


def _walk_module_depencies(module_name, module_name_map, module_order, visited_modules):
    # Collect depencies
    depencies = list()
    depencies.extend(module_name_map[module_name].depends_on())
    for optional_dependency in module_name_map[module_name].run_after():
        if optional_dependency in module_name_map:
            depencies.append(optional_dependency)
    # Resolve
    visited_modules.add(module_name)
    for dependency in depencies:
        if dependency not in module_order:
            if dependency in visited_modules:
                log.error("Circular dependency (%s <-> %s)", dependency, module_name)
                raise RuntimeError("Circular dependency present")
            _walk_module_depencies(dependency, module_name_map, module_order, visited_modules)
    # Add to resolved order
    module_order.append(module_name)
