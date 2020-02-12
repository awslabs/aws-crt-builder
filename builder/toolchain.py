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
import re
from data import COMPILERS
from host import current_platform

# helpful list of XCode clang output: https://gist.github.com/yamaya/2924292


def _compiler_version(env, cc):
    if current_platform() in ('linux', 'macos'):
        result = env.shell.exec(cc, '--version', quiet=True, stderr=False)
        text = result.stdout.decode(encoding='UTF-8')
        m = re.match('Apple (LLVM|clang) version (\d+)', text)
        if m:
            return m.group(2)
        m = re.match('clang version (\d+)', text)
        if m:
            return m.group(1)
        m = re.match('gcc .+ (\d+)\..+$', text)
        if m:
            return m.group(1)
    return 'unknown'


def _find_compiler_tool(env, name, versions):
    # look for the default tool, and see if the version is in the search set
    path = env.shell.where(name)
    if path:
        version = _compiler_version(env, path)
        if version in versions:
            return path, version
    for version in versions:
        for pattern in ('{name}-{version}', '{name}-{version}.0'):
            exe = pattern.format(name=name, version=version)
            path = env.shell.where(exe)
            if path:
                return path, version
    return None, None


def _clang_versions():
    versions = [v for v in COMPILERS['clang']
                ['versions'].keys() if v != 'default']
    versions.sort()
    versions.reverse()
    return versions


def _gcc_versions():
    versions = [v for v in COMPILERS['gcc']
                ['versions'].keys() if v != 'default']
    versions.sort()
    versions.reverse()
    return versions


def _msvc_versions():
    versions = [v for v in COMPILERS['msvc']
                ['versions'].keys() if v != 'default']
    versions.sort()
    versions.reverse()
    return versions


def find_gcc_tool(env, name, version=None):
    """ Finds gcc, gcc-ld, gcc-ranlib, etc at a specific version, or the latest one available """
    versions = [version] if version else _gcc_versions()
    return _find_compiler_tool(env, name, versions)


def find_llvm_tool(env, name, version=None):
    """ Finds clang, clang-tidy, lld, etc at a specific version, or the latest one available """
    versions = [version] if version else _clang_versions()
    return _find_compiler_tool(env, name, versions)


def find_msvc(env, version=None):
    """ Finds MSVC at a specific version, or the latest one available """
    def _find_msvc(env, version, install_vswhere=True):
        vswhere = env.shell.where('vswhere')
        # if that fails, install vswhere and try again
        if not vswhere and install_vswhere:
            result = env.shell.exec(
                'choco', 'install', '--no-progress', 'vswhere')
            if result:
                return _find_msvc(env, versions, False)
            return None, None

        compiler = None
        vc_version = None

        # Grab installed version
        result = env.shell.exec('vswhere', '-legacy', '-version', version,
                                '-property', 'installationVersion', quiet=True)
        text = result.stdout.decode(encoding='UTF-8')
        m = re.match('(\d+)\.?', text)
        if m:
            vc_version = m.group(1)

        if not vc_version or vc_version != version:
            return None, None

        # Grab installation path
        result = env.shell.exec('vswhere', '-legacy', '-version', version,
                                '-property', 'installationPath', quiet=True)
        text = result.stdout.decode(encoding='UTF-8')
        compiler = text.strip()

        return compiler, vc_version

    versions = [version] if version else _msvc_versions()
    for version in versions:
        path, version = _find_msvc(env, version)
        if path:
            return path, version
    return None, None


def all_compilers(env):
    compilers = []
    for version in _gcc_versions():
        path, _version = find_gcc_tool(env, 'gcc', version)
        if path:
            compilers.append(('gcc', version))
    for version in _clang_versions():
        path, _version = find_llvm_tool(env, 'clang', version)
        if path:
            compilers.append(('clang', version))
    if current_platform() == 'windows':
        for version in _msvc_versions():
            path, _version = find_msvc(env, version)
            if path:
                compilers.append(('msvc', version))
    return compilers


_default_compiler = None
_default_version = None


def default_compiler(env):
    try:
        return _default_compiler, _default_version
    except UnboundLocalError:
        def _find_compiler():
            compiler = None
            version = None
            platform = current_platform()
            if platform in ('linux', 'macos'):
                clang_path, clang_version = find_llvm_tool(env, 'clang')
                gcc_path, gcc_version = find_gcc_tool(env, 'gcc')
                if clang_path:
                    print('Found clang {} as default compiler'.format(clang_version))
                    compiler = 'clang'
                    version = clang_version
                elif gcc_path:
                    print('Found gcc {} as default compiler'.format(gcc_version))
                    compiler = 'gcc'
                    version = gcc_version
                else:
                    print(
                        'Neither GCC or Clang could be found on this system, perhaps not installed yet?')

            else:
                compiler, version = find_msvc(env)
            return compiler, version
        _default_compiler, _default_version = _find_compiler()
        return _default_compiler, _default_version


class Toolchain(object):
    """ Represents a compiler toolchain """

    def __init__(self, env, **kwargs):
        if 'default' in kwargs or len(kwargs) == 0:
            for slot in ('host', 'target', 'arch', 'compiler', 'compiler_version'):
                setattr(self, slot, 'default')

        if 'spec' in kwargs:
            spec = kwargs['spec']
            self.host = spec.host
            self.compiler = spec.compiler
            self.compiler_version = spec.compiler_version
            self.target = spec.target
            self.arch = spec.arch

        # Pull out individual fields. Note this is not in an else to support overriding at construction time
        for slot in ('host', 'target', 'arch', 'compiler', 'compiler_version'):
            if slot in kwargs:
                setattr(self, slot, kwargs[slot])

        if self.compiler_version == 'default':
            self.compiler_version = _compiler_version(
                env, self.compiler_path(env))

        self.name = '-'.join([self.host, self.compiler,
                              self.compiler_version, self.target, self.arch])

    def compiler_path(self, env):
        if self.compiler == 'default':
            env_cc = os.environ.get('CC', None)
            if env_cc:
                return env.shell.where(env_cc)
            return env.shell.where('cc')
        elif self.compiler == 'clang':
            return find_llvm_tool(env, 'clang', self.compiler_version if self.compiler_version != 'default' else None)[0]
        elif self.compiler == 'gcc':
            return find_gcc_tool(env, 'gcc', self.compiler_version if self.compiler_version != 'default' else None)[0]
        elif self.compiler == 'msvc':
            return find_msvc(env)[0]
        return None

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name
