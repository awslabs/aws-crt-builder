# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0.

import os

from builder.core.data import *
from builder.core.host import current_host, current_os, current_arch, normalize_arch


def _parse_version(version_str):
    """Parse a version string into a list of integers for comparison.
    The version string can be in format X, X.Y, X.Y.Z, etc."""
    try:
        return [int(x) for x in version_str.split('.')]
    except (ValueError, AttributeError):
        return None


def _compiler_meets_minimum_version(compiler_version, compiler):
    """Check if the compiler version meets the minimum supported version requirement.
    Returns True if compiler_version >= minimum known version, False otherwise."""
    # If the compiler_version is a known version, it's always valid and should not be 
    # subject to numeric comparison.
    if compiler_version in compiler['versions']:
        return True

    # Sort compiler version keys and find the lowest (minimal) version
    versions = [v for v in compiler['versions'].keys() if (v != 'default' and v != 'latest')]

    # Filter out versions that cannot be parsed
    versions = [_parse_version(v) for v in versions if _parse_version(v) is not None]

    # Versions are not specified or none are parseable, return True
    if not versions:
        return True

    # Sort and find the minimum version
    versions.sort()
    minimal_version = versions[0]

    # Parse compiler_version
    parsed_compiler = _parse_version(compiler_version)
    if parsed_compiler is None:
        return False

    # Compare using Python's native list comparison
    return parsed_compiler >= minimal_version


def validate_spec(build_spec, allow_higher_version=False):
    """Validate the build spec against known hosts, targets, architectures, and compilers.

    Args:
        allow_higher_version: If True, skip validation for compiler versions higher than
            what's in the known versions list (e.g. when a newer compiler is detected on
            the system), but still assert that the version is not lower than the minimum
            supported version. If False, the compiler version must exactly match one of
            the known versions.
    """

    assert build_spec.host in HOSTS, "Host name {} is invalid".format(
        build_spec.host)
    assert build_spec.target in TARGETS, "Target {} is invalid".format(
        build_spec.target)

    assert build_spec.arch in ARCHS, "Architecture {} is invalid".format(
        build_spec.target)

    assert build_spec.compiler in COMPILERS, "Compiler {} is invalid".format(
        build_spec.compiler)
    compiler = COMPILERS[build_spec.compiler]

    if not allow_higher_version:
        assert build_spec.compiler_version in compiler['versions'], "Compiler version {} is invalid for compiler {}".format(
            build_spec.compiler_version, build_spec.compiler)
    else:
        assert _compiler_meets_minimum_version(
            build_spec.compiler_version, compiler), \
            "Compiler version {} is lower than the minimum supported " \
            "version for compiler {}".format(
                build_spec.compiler_version, build_spec.compiler)

    supported_hosts = compiler['hosts']
    assert build_spec.host in supported_hosts or current_os() in supported_hosts, "Compiler {} does not support host {}".format(
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

        # Convert a target tuple into its component parts
        if '-' in self.target:
            self.target, self.arch = self.target.split('-')

        # Convert defaults to be based on running environment
        if self.host == 'default':
            self.host = current_host()
        if self.target == 'default':
            self.target = current_os()
        if self.arch == 'default':
            self.arch = current_arch()
        else:
            self.arch = normalize_arch(self.arch)

        self.name = '-'.join([self.host, self.compiler,
                              self.compiler_version, self.target, self.arch])
        if self.downstream:
            self.name += "-downstream"

        # Strict validation at construction time: compiler version must exactly match
        # a known version in the data dictionary.
        validate_spec(self)

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name

    def update_compiler(self, compiler, compiler_version):
        """Update the spec's compiler and version after resolving the system toolchain.

        This is called after the Toolchain detects the actual compiler installed on the
        system, and validates the detected compiler version.
        The function allows the spec to be set to a higher version than what's in the
        known versions list, but still rejects versions below the minimum supported.
        """
        self.compiler = compiler
        self.compiler_version = compiler_version

        self.name = '-'.join([self.host, self.compiler,
                              self.compiler_version, self.target, self.arch])
        if self.downstream:
            self.name += "-downstream"

        # Validate with allow_higher_version=True to allow system-detected compiler
        # newer than what's in our known versions list. We still reject versions
        # below the minimum supported version.
        validate_spec(self, allow_higher_version=True)
