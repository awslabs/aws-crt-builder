# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0.

from builder.core.data import ARCHS, HOSTS, PKG_TOOLS

import os
import re
import sys

from functools import lru_cache


def current_os():
    if sys.platform == 'win32':
        return 'windows'
    elif sys.platform == 'darwin':
        return 'macos'
    elif 'linux' in sys.platform or sys.platform in ('cygwin', 'msys'):
        return 'linux'
    elif sys.platform.startswith('freebsd'):
        return 'freebsd'
    elif sys.platform.startswith('openbsd'):
        return 'openbsd'
    return 'UNKNOWN'


def current_arch():
    if current_os() == 'linux' or current_os() == 'macos':
        machine_id = os.uname()[4]
        m = re.match(r'^(aarch64|armv[6-8]|arm64)', machine_id.strip())
        if m:
            arch = m.group(1)
            if arch == 'aarch64':
                arch = 'armv8'
            return arch
    return 'x64' if sys.maxsize > 2**32 else 'x86'


def current_platform():
    return '{}-{}'.format(current_os(), current_arch())


def normalize_arch(arch):
    return ARCHS[arch]['arch']


def normalize_target(target):
    """ convert target into canonical os and arch """
    assert '-' in target
    os, arch = target.split('-')
    arch = normalize_arch(arch)
    return '{}-{}'.format(os, arch)


def _file_contains(path, search):
    if os.path.isfile(path):
        with open(path) as f:
            line = f.readline()
            while line:
                if search in line:
                    return True
                line = f.readline()
    return False


@lru_cache(1)
def current_host():
    """ Between sys.platform or linux distro identifiers, determine the specific os """

    def _discover_host():
        platform = current_os()
        if platform == 'linux':
            # Note: that AL2 and AL2023 have the same substring. Check for AL2023 explicitly.
            # And also check that AL2 has "2 (", which is common to all base distributions of AL2
            if _file_contains('/etc/system-release', 'Amazon Linux release 2023'):
                return 'al2023'
            if _file_contains('/etc/system-release', 'Amazon Linux release 2 ('):
                return 'al2'
            if _file_contains('/etc/system-release', 'Bare Metal') or _file_contains('/etc/system-release', 'Amazon Linux AMI'):
                return 'al2012'
            if _file_contains('/etc/redhat-release', 'CentOS release 5.'):
                if os.path.exists('/opt/python/cp27-cp27m'):
                    return 'manylinux'
                return 'centos'
            if _file_contains('/etc/redhat-release', 'CentOS Linux release 7.'):
                if os.path.exists('/opt/python/cp39-cp39'):
                    return 'manylinux'
                return 'centos'
            if _file_contains('/etc/lsb-release', 'Ubuntu'):
                return 'ubuntu'
            if _file_contains('/etc/os-release', 'Debian'):
                return 'debian'
            if _file_contains('/etc/os-release', 'Alpine Linux'):
                if os.path.exists('/opt/python/cp39-cp39'):
                    return 'musllinux'
                return 'alpine'
            if _file_contains('/etc/os-release', 'Raspbian'):
                return 'raspbian'
            if _file_contains('/etc/system-release', 'Fedora'):
                return 'fedora'
            if _file_contains('/etc/os-release', 'openSUSE'):
                return 'opensuse'
            if _file_contains('/etc/os-release', 'Red Hat Enterprise Linux'):
                return 'rhel'
            if _file_contains('/etc/os-release', 'OpenWrt'):
                return 'openwrt'
            return 'linux'
        else:
            return platform
    return _discover_host()


def package_tool(host=current_host()):
    host_info = HOSTS.get(host, {})
    return host_info['pkg_tool']
