# Copyright 2010-2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License").
# You may not use this file except in compliance with the License.
# A copy of the License is located at
#
#  http://aws.amazon.com/apache2.0
#
# or in the "license" file accompanying this file. This file is distributed
# on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either
# express or implied. See the License for the specific language governing
# permissions and limitations under the License.

from collections import namedtuple


class Project(object):
    """ Describes a given library and its dependencies/consumers """

    def __init__(self, **kwargs):
        self.upstream = self.dependencies = [namedtuple('ProjectReference', u.keys())(
            *u.values()) for u in kwargs.get('upstream', [])]
        self.downstream = self.consumers = [namedtuple('ProjectReference', d.keys())(
            *d.values()) for d in kwargs.get('downstream', [])]
        self.account = kwargs.get('account', 'awslabs')
        self.name = kwargs['name']
        self.url = "https://github.com/{}/{}.git".format(
            self.account, self.name)
        self.path = kwargs.get('path', None)

    def __repr__(self):
        return "{}: {}".format(self.name, self.url)

    def get_dependencies(self, spec):
        """ Gets dependencies for a given BuildSpec, filters by target """
        target = spec.target
        deps = []
        for p in self.dependencies:
            if target in getattr(p, 'targets', []):
                deps.append(p)
        return deps

    def get_consumers(self, spec):
        """ Gets consumers for a given BuildSpec, filters by target """
        target = spec.target
        consumers = []
        for c in self.consumers:
            if target in getattr(c, 'targets', []):
                consumers.append(c)
        return consumers
