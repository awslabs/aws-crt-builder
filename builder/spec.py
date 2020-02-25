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

from data import *
from host import current_host, current_platform, current_arch


def validate_spec(build_spec):

    assert build_spec.host in HOSTS, "Host name {} is invalid".format(
        build_spec.host)
    assert build_spec.target in TARGETS, "Target {} is invalid".format(
        build_spec.target)

    assert build_spec.arch in ARCHS, "Architecture {} is invalid".format(
        build_spec.target)

    assert build_spec.compiler in COMPILERS, "Compiler {} is invalid".format(
        build_spec.compiler)
    compiler = COMPILERS[build_spec.compiler]

    assert build_spec.compiler_version in compiler['versions'], "Compiler version {} is invalid for compiler {}".format(
        build_spec.compiler_version, build_spec.compiler)

    supported_hosts = compiler['hosts']
    assert build_spec.host in supported_hosts or current_platform() in supported_hosts, "Compiler {} does not support host {}".format(
        build_spec.compiler, build_spec.host)

    supported_targets = compiler['targets']
    assert build_spec.target in supported_targets, "Compiler {} does not support target {}".format(
        build_spec.compiler, build_spec.target)


class BuildSpec(object):
    """ Refers to a specific build permutation, gets converted into a toolchain """

    def __init__(self, **kwargs):
        for slot in ('host', 'target', 'arch', 'compiler', 'compiler_version'):
            setattr(self, slot, 'default')
        self.downstream = False

        spec = kwargs.get('spec', None)
        if spec:
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
        for slot in ('host', 'target', 'arch', 'compiler', 'compiler_version', 'downstream'):
            if slot in kwargs and kwargs[slot]:
                setattr(self, slot, kwargs[slot])

        # Convert defaults to be based on running environment
        if self.host == 'default':
            self.host = current_host()
        if self.target == 'default':
            self.target = current_platform()
        if self.arch == 'default':
            self.arch = current_arch()

        self.name = '-'.join([self.host, self.compiler,
                              self.compiler_version, self.target, self.arch])
        if self.downstream:
            self.name += "-downstream"

        validate_spec(self)

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name
