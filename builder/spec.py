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

import os
import sys


def current_platform():
    if sys.platform == 'win32':
        return 'windows'
    elif sys.platform == 'darwin':
        return 'macos'
    elif 'linux' in sys.platform or sys.platform in ('cygwin', 'msys'):
        return 'linux'


def current_arch():
    if os.uname()[4][:3].startswith('arm'):
        arch = ('armv8' if sys.maxsize > 2**32 else 'armv7')
    return ('x64' if sys.maxsize > 2**32 else 'x86')


class BuildSpec(object):
    """ Refers to a specific build permutation, gets converted into a toolchain """

    def __init__(self, **kwargs):
        for slot in ('host', 'target', 'arch', 'compiler', 'compiler_version'):
            setattr(self, slot, 'default')
        self.downstream = False

        if 'spec' in kwargs:
            spec = kwargs['spec']
            if spec.startswith('default'):  # default or default(-{variant})
                _, *rest = spec.split('-')
            elif not '-' in spec:  # just a variant
                rest = [spec]
            else:  # Parse the spec from a single string
                self.host, self.compiler, self.compiler_version, self.target, self.arch, * \
                    rest = spec.split('-')

            for variant in ('downstream',):
                if variant in rest:
                    setattr(self, variant, True)
                else:
                    setattr(self, variant, False)

        # Pull out individual fields. Note this is not in an else to support overriding at construction time
        for slot in ('host', 'target', 'arch', 'compiler', 'compiler_version'):
            if slot in kwargs:
                setattr(self, slot, kwargs[slot])

        # Convert defaults to be based on running environment
        if self.host == 'default':
            self.host = current_platform()
        if self.target == 'default':
            self.target = current_platform()
        if self.arch == 'default':
            self.arch = current_arch()

        self.name = '-'.join([self.host, self.compiler,
                              self.compiler_version, self.target, self.arch])
        if self.downstream:
            self.name += "-downstream"

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name
