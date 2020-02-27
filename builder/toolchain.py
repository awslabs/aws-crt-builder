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
from host import current_os, current_arch

# helpful list of XCode clang output: https://gist.github.com/yamaya/2924292


def _compiler_version(env, cc):
    if current_os() in ('linux', 'macos'):
        result = env.shell.exec(cc, '--version', quiet=True, stderr=False)
        text = result.output
        # Apple clang
        m = re.match('Apple (LLVM|clang) version (\d+)', text)
        if m:
            return 'clang', m.group(2)
        # LLVM clang
        m = re.match('clang version (\d+)', text)
        if m:
            return 'clang', m.group(1)
        # GCC 4.x
        m = re.match('gcc .+ (4\.\d+)', text)
        if m:
            return 'gcc', m.group(1)
        # GCC 5+
        m = re.match('gcc .+ (\d+)\.', text)
        if m:
            return 'gcc', m.group(1)
    return None, None


def _find_compiler_tool(env, name, versions):
    # look for the default tool, and see if the version is in the search set
    path = env.shell.where(name)
    if path:
        version = _compiler_version(env, path)[1]
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


def _is_cross_compile(os, arch):
    return os != current_os() or arch != current_arch()


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

        # detect cross-compile
        self.cross_compile = _is_cross_compile(self.target, self.arch)
        self.platform = '{}-{}'.format(self.target, self.arch)
        self.shell_env = []

        if self.cross_compile:
            self.compiler = 'gcc'
            # it's really 4.9, but don't need a separate entry for that
            self.compiler_version = '4.8'
        else:
            # resolve default compiler and/or version
            if self.compiler == 'default':
                c, v = Toolchain.default_compiler(env)
                if c and v:
                    self.compiler, self.compiler_version = c, v
            elif self.compiler_version == 'default':
                self.compiler_version = _compiler_version(
                    env, self.compiler_path(env))[1]
                if not self.compiler_version:
                    self.compiler_version = 'default'

        self.name = '-'.join([self.host, self.compiler,
                              self.compiler_version, self.target, self.arch])

    def compiler_path(self, env):
        assert not self.cross_compile
        if self.compiler == 'default':
            return Toolchain.default_compiler(env)[0]
        return Toolchain.find_compiler(env, self.compiler, self.compiler_version if self.compiler_version != 'default' else None)[0]

    def cxx_compiler_path(self, env):
        assert not self.cross_compile
        compiler = self.compiler
        if self.compiler == 'default':
            compiler = Toolchain.default_compiler(env)[0]
        if compiler == 'clang':
            return Toolchain.find_compiler_tool(env, compiler, 'clang++')[0]
        elif compiler == 'gcc':
            return Toolchain.find_compiler_tool(env, compiler, 'g++')[0]
        # msvc can compile with cl.exe regardless of language
        return self.compiler_path(env)

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name

    @staticmethod
    def find_gcc_tool(env, name, version=None):
        """ Finds gcc, gcc-ld, gcc-ranlib, etc at a specific version, or the latest one available """
        versions = [version] if version else _gcc_versions()
        return _find_compiler_tool(env, name, versions)

    @staticmethod
    def find_llvm_tool(env, name, version=None):
        """ Finds clang, clang-tidy, lld, etc at a specific version, or the latest one available """
        versions = [version] if version else _clang_versions()
        return _find_compiler_tool(env, name, versions)

    @staticmethod
    def find_msvc(env, version=None):
        """ Finds MSVC at a specific version, or the latest one available """
        def _find_msvc(env, version, install_vswhere=True):
            vswhere = env.shell.where('vswhere')
            # if that fails, install vswhere and try again
            if not vswhere and install_vswhere:
                result = env.shell.exec(
                    'choco', 'install', '--no-progress', 'vswhere')
                if result.returncode == 0:
                    return _find_msvc(env, version, False)
                return None, None

            compiler = None
            vc_version = None

            # Grab installed version
            result = env.shell.exec('vswhere', '-legacy', '-version', version,
                                    '-property', 'installationVersion', quiet=True)
            text = result.output
            m = re.match('(\d+)\.?', text)
            if m:
                vc_version = m.group(1)

            if not vc_version or vc_version != version:
                return None, None

            # Grab installation path
            result = env.shell.exec('vswhere', '-legacy', '-version', version,
                                    '-property', 'installationPath', quiet=True)
            text = result.output
            compiler = text.strip()

            return compiler, vc_version

        versions = [version] if version else _msvc_versions()
        for version in versions:
            path, version = _find_msvc(env, version)
            if path:
                return path, version
        return None, None

    @staticmethod
    def find_compiler(env, compiler, version=None):
        """ Returns path, found_version for the requested compiler if it is installed """
        if compiler == 'clang':
            return Toolchain.find_llvm_tool(env, compiler, version)
        elif compiler == 'gcc':
            return Toolchain.find_gcc_tool(env, compiler, version)
        elif compiler == 'msvc':
            return Toolchain.find_msvc(env, version)
        return None, None

    @staticmethod
    def find_compiler_tool(env, compiler, tool, version=None):
        """ Returns path, found_version for the requested tool if it is installed """
        if compiler == 'clang':
            return Toolchain.find_llvm_tool(env, tool, version)
        elif compiler == 'gcc':
            return Toolchain.find_gcc_tool(env, tool, version)

        return None, None

    @staticmethod
    def compiler_packages(compiler, version):
        """ Returns a list of packages required to use the requested compiler """
        compiler_config = COMPILERS.get(compiler, {}).get(
            'versions', {}).get(version, None)
        if compiler_config:
            return compiler_config.get('packages', [])
        return []

    @staticmethod
    def all_compilers(env):
        """ Returns a list of tuples of all available (compiler, version) """
        compilers = []
        for version in _gcc_versions():
            path, _version = Toolchain.find_gcc_tool(env, 'gcc', version)
            if path:
                compilers.append(('gcc', version))
        for version in _clang_versions():
            path, _version = Toolchain.find_llvm_tool(env, 'clang', version)
            if path:
                compilers.append(('clang', version))
        if current_os() == 'windows':
            for version in _msvc_versions():
                path, _version = Toolchain.find_msvc(env, version)
                if path:
                    compilers.append(('msvc', version))
        return compilers

    _default_compiler = None
    _default_version = None

    @staticmethod
    def default_compiler(env, target=None, arch=None):
        """ Finds the system default compiler and returns (compiler, version) """
        if Toolchain._default_compiler and Toolchain._default_version:
            return Toolchain._default_compiler, Toolchain._default_version

        if target and arch and _is_cross_compile(target, arch):
            return 'gcc', '4.8'

        def _find_compiler():
            compiler = None
            version = None
            platform = current_os()
            if platform in ('linux', 'macos'):
                # resolve CC and /usr/bin/cc
                for env_cc in (env.shell.where(os.environ.get('CC', None)), env.shell.where('cc')):
                    if env_cc:
                        cc, ccver = _compiler_version(env, env_cc)
                        if cc and ccver:
                            return cc, ccver

                # Try to find clang or gcc
                clang_path, clang_version = Toolchain.find_llvm_tool(
                    env, 'clang')
                gcc_path, gcc_version = Toolchain.find_gcc_tool(env, 'gcc')
                if clang_path:
                    compiler = 'clang'
                    version = clang_version
                elif gcc_path:
                    compiler = 'gcc'
                    version = gcc_version
                else:
                    print(
                        'Neither GCC or Clang could be found on this system, perhaps not installed yet?')

            else:
                compiler = 'msvc'
                version = Toolchain.find_msvc(env)[1]
            if not compiler or not version:
                print('WARNING: Default compiler could not be found')

            print('Default Compiler: {} {}'.format(compiler, version))
            return compiler, version

        Toolchain._default_compiler, Toolchain._default_version = _find_compiler()
        return Toolchain._default_compiler, Toolchain._default_version
