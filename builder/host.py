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
import sys


def current_platform():
    if sys.platform == 'win32':
        return 'windows'
    elif sys.platform == 'darwin':
        return 'macos'
    elif 'linux' in sys.platform or sys.platform in ('cygwin', 'msys'):
        return 'linux'


def current_arch():
    if current_platform() == 'linux':
        machine_id = os.uname()[4]
        m = re.match(r'^(aarch64|armv[6-8])', machine_id.strip())
        if m:
            arch = m.group(1)
            if arch == 'aarch64':
                arch = 'armv8'
            return arch
    return ('x64' if sys.maxsize > 2**32 else 'x86')


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
    try:
        return _current_host
    except:
        def _discover_host():
            platform = current_platform()
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
                if _file_contains('/etc/os-release', 'Alpine Linux'):
                    return 'alpine'
                return 'linux'
            else:
                return platform
        _current_host = _discover_host()
        return _current_host
