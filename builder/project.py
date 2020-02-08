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


class Project(object):
    """ Describes a given library and its dependencies/consumers """

    def __init__(self, **kwargs):
        self.upstream = self.dependencies = kwargs.get('upstream', [])
        self.downstream = self.consumers = kwargs.get('downstream', [])
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
        deps = [[p][target in p.get('targets', [])] for p in self.dependencies]
        return deps
    
    def get_consumers(self, spec):
        """ Gets consumers for a given BuildSpec, filters by target """
        target = spec.target
        consumers = [[p][target in p.get('targets', [])] for p in self.consumers]
        return consumers
