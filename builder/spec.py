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


class BuildSpec(object):
    """ Refers to a specific build permutation, gets converted into a toolchain """

    def __init__(self, **kwargs):
        for slot in ('host', 'target', 'arch', 'compiler', 'compiler_version'):
            setattr(self, slot, 'default')
        self.downstream = False

        if 'spec' in kwargs:
            # Parse the spec from a single string
            self.host, self.compiler, self.compiler_version, self.target, self.arch, * \
                rest = kwargs['spec'].split('-')

            for variant in ('downstream',):
                if variant in rest:
                    setattr(self, variant, True)
                else:
                    setattr(self, variant, False)

        # Pull out individual fields. Note this is not in an else to support overriding at construction time
        for slot in ('host', 'target', 'arch', 'compiler', 'compiler_version'):
            if slot in kwargs:
                setattr(self, slot, kwargs[slot])

        self.name = '-'.join([self.host, self.compiler,
                              self.compiler_version, self.target, self.arch])
        if self.downstream:
            self.name += "-downstream"

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name
