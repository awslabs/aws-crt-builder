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

from data import ARCHS, HOSTS, PKG_TOOLS

import os
import re
import sys


def current_os():
    if sys.platform == 'win32':
        return 'windows'
    elif sys.platform == 'darwin':
        return 'macos'
    elif 'linux' in sys.platform or sys.platform in ('cygwin', 'msys'):
        return 'linux'
    elif sys.platform.startswith('freebsd'):
        return 'freebsd'
    return 'UNKNOWN'


def current_arch():
    if current_os() == 'linux':
        machine_id = os.uname()[4]
        m = re.match(r'^(aarch64|armv[6-8])', machine_id.strip())
        if m:
            arch = m.group(1)
            if arch == 'aarch64':
                arch = 'armv8'
            return arch
    return ('x64' if sys.maxsize > 2**32 else 'x86')


def current_platform():
    return '{}-{}'.format(current_os(), current_arch())


def normalize_target(target):
    """ convert target into canonical os and arch """
    assert '-' in target
    os, arch = target.split('-')
    arch = ARCHS[arch]['arch']
    return '{}-{}'.format(os, arch)


def _file_contains(path, search):
    if os.path.isfile(path):
        #print('Probing {}'.format(path))
        with open(path) as f:
            line = f.readline()
            while line:
                #print('  {}'.format(line), end='')
                if search in line:
                    return True
                line = f.readline()
    return False


# cache the result of this, since it involves a bunch of file I/O
_current_host = None


def current_host():
    """ Between sys.platform or linux distro identifiers, determine the specific os """
    global _current_host
    if _current_host:
        return _current_host

    def _discover_host():
        platform = current_os()
        if platform == 'linux':
            if _file_contains('/etc/system-release', 'Amazon Linux release 2'):
                return 'al2'
            if _file_contains('/etc/system-release', 'Bare Metal'):
                return 'al2012'
            if _file_contains('/etc/redhat-release', 'CentOS release 5.11 (Final)'):
                return 'manylinux'
            if _file_contains('/etc/redhat-release', 'CentOS Linux release 7.7.1908'):
                return 'manylinux'
            if _file_contains('/etc/lsb-release', 'Ubuntu'):
                return 'ubuntu'
            if _file_contains('/etc/os-release', 'Debian'):
                return 'debian'
            if _file_contains('/etc/os-release', 'Alpine Linux'):
                return 'alpine'
            if _file_contains('/etc/os-release', 'Raspbian'):
                return 'raspbian'
            return 'linux'
        else:
            return platform
    _current_host = _discover_host()
    return _current_host


def package_tool(host=current_host()):
    host_info = HOSTS.get(host, {})
    return host_info['pkg_tool']
