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
    Dict tools
"""

from collections import OrderedDict


# Taken from https://docs.python.org/3/library/collections.html#ordereddict-examples-and-recipes
class LastUpdatedOrderedDict(OrderedDict):
    """ Store items in the order the keys were last added """

    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        super().move_to_end(key)
