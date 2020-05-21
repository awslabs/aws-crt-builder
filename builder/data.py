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

from enum import Enum
from util import dict_alias

########################################################################################################################
# DATA DEFINITIONS
########################################################################################################################


class PKG_TOOLS(Enum):
    APT = 'apt'
    BREW = 'brew'
    YUM = 'yum'
    APK = 'apk'
    CHOCO = 'choco'
    PKG = 'freebsd_pkg'


KEYS = {
    # Build
    'python': "",  # where to find python on the machine
    'c': None,  # c compiler
    'cxx': None,  # c++ compiler
    'cmake_args': [],  # additional cmake arguments

    # where the cmake binaries should be stored, and dependencies installed
    'build_dir': 'build',
    'deps_dir': '{build_dir}/deps',
    'install_dir': '{build_dir}/install',
    'build_env': {},  # environment variables to set before starting build
    'pre_build_env': {},
    'pre_build_steps': [],  # steps to run before build
    'post_build_env': {},
    'post_build_steps': [],  # steps to run after build
    'run_tests': True,  # whether or not to run tests
    'build': None,  # deprecated, use build_steps
    # steps to run instead of the default cmake compile
    'build_steps': ['build'],
    'test': None,  # deprecated, use test_steps
    'test_env': {},
    'test_steps': ['test'],  # steps to run instead of the default ctest

    'setup_steps': [],  # Commands to run at env setup time
    'pkg_tool': None,  # apt, brew, yum, apk, etc
    'pkg_setup': [],  # commands required to configure the package system
    # command to install packages, should be of the form 'pkgmanager arg1 arg2 {packages will go here}'
    'pkg_install': '',
    'pkg_update': '',  # command to update the package manager's database
    'packages': [],  # packages to install
    'compiler_packages': [],  # packages to support compiler
    'needs_compiler': True,  # whether or not this build needs a compiler
    'cross_compile_platform': None,

    'imports': [],  # Additional targets this project needs from builder or scripts
    'upstream': [],
    'downstream': [],

    # Linux
    'sudo': False  # whether or not sudo is necessary for installs
}

# Add apt_setup, et al
for suffix, default in [('setup', []), ('install', ''), ('update', ''), ('packages', []), ('compiler_packages', [])]:
    for pkg in PKG_TOOLS:
        key = '{}_{}'.format(pkg.value, suffix)
        KEYS[key] = default

###############################################################################
# Supported architectures
# Be sure to use these monikers in this file for consistency, some aliases are
# applied after all tables are built
###############################################################################
ARCHS = {
    'x86': {
        'arch': 'x86',
        'aliases': ['i686', 'x86_32']
    },
    'x64': {
        'arch': 'x64',
        'aliases': ['amd64', 'x86_64']
    },
    'armv6': {
        'arch': 'armv6',
        'cross_compile_platform': 'linux-armv6',
        'imports': ['dockcross'],
    },
    'armv7': {
        'arch': 'armv7',
        'cross_compile_platform': 'linux-armv7',
        'imports': ['dockcross'],
        'aliases': ['armv7a']
    },
    'armv8': {
        'arch': 'armv8',
        'cross_compile_platform': 'linux-arm64',
        'imports': ['dockcross'],
        'aliases': ['arm64', 'arm64v8', 'arm64v8a', 'aarch64'],
    },
    'mips': {
        'arch': 'mips',
        'cross_compile_platform': 'linux-mips',
        'imports': ['dockcross'],
    },
}

# Apply arch aliases
for arch in list(ARCHS.keys()):
    for alias in ARCHS[arch].get('aliases', []):
        dict_alias(ARCHS, arch, alias)

###############################################################################
# Host operating systems
###############################################################################
HOSTS = {
    'linux': {
        'os': 'linux',
        'variables': {
            'python': "python3",
        },

        'cmake_args': [
            "-DPERFORM_HEADER_CHECK=ON",
        ],
        'sudo': True
    },
    'ubuntu': {
        'os': 'linux',
        'pkg_tool': PKG_TOOLS.APT,
        # need ld and make and such
        'packages': ['build-essential'],
        'pkg_setup': [
            'apt-add-repository ppa:ubuntu-toolchain-r/test',
        ],
        'pkg_update': 'apt-get -qq update -y',
        'pkg_install': 'apt-get -qq install -y',
    },
    'alpine': {
        'os': 'linux',
        'pkg_tool': PKG_TOOLS.APK,
        'packages': ['build-base'],
        'pkg_setup': [],
        'pkg_update': '',
        'pkg_install': 'apk add --no-cache',
    },
    'raspbian': {
        'os': 'linux',
        'pkg_tool': PKG_TOOLS.APT,
        # need ld and make and such
        'packages': ['build-essential'],
        'pkg_update': 'apt-get -qq update -y',
        'pkg_install': 'apt-get -qq install -y',
    },
    'al2012': {
        'os': 'linux',
        'cmake_args': [
            "-DENABLE_SANITIZERS=OFF",
            "-DPERFORM_HEADER_CHECK=OFF",
        ],

        'pkg_tool': PKG_TOOLS.YUM,
        'pkg_update': 'yum update -y',
        'pkg_install': 'yum install -y',

        'variables': {
            'python': "python3",
        },
    },
    'al2': {
        'os': 'linux',
        'cmake_args': [
            "-DENABLE_SANITIZERS=OFF",
            "-DPERFORM_HEADER_CHECK=OFF",
        ],

        'pkg_tool': PKG_TOOLS.YUM,
        'pkg_update': 'yum update -y',
        'pkg_install': 'yum install -y',

        'variables': {
            'python': "python3",
        },
    },
    'manylinux': {
        'os': 'linux',
        'pkg_tool': PKG_TOOLS.YUM,
        'pkg_update': 'yum update -y',
        'pkg_install': 'yum install -y',
        'sudo': False,

        'variables': {
            'python': "/opt/python/cp37-cp37m/bin/python",
        },
    },
    'windows': {
        'os': 'windows',
        'variables': {
            'python': "python.exe",
        },

        'pkg_tool': PKG_TOOLS.CHOCO,
        'pkg_install': 'choco install --no-progress',

        'cmake_args': [
            "-DPERFORM_HEADER_CHECK=ON",
        ],
    },
    'macos': {
        'os': 'macos',
        'variables': {
            'python': "python3",
        },

        'pkg_tool': PKG_TOOLS.BREW,
        'pkg_install': 'brew install',
    },
    'freebsd': {
        'os': 'freebsd',
        'variables': {
            'python': "python3",
        },
        'sudo': True,

        'pkg_tool': PKG_TOOLS.PKG,
        'pkg_update': 'pkg update',
        'pkg_install': 'pkg install -y'
    }
}

HOSTS['darwin'] = HOSTS['macos']
HOSTS['debian'] = HOSTS['ubuntu']

for arch in ARCHS.keys():
    for alias in ARCHS[arch].get('aliases', []):
        dict_alias(HOSTS, arch, alias)

###############################################################################
# Supported targets to compile for
###############################################################################
TARGETS = {
    'linux': {
        'architectures': {
            'x86': {
                'cmake_args': [
                    '-DCMAKE_C_FLAGS=-m32',
                    '-DCMAKE_CXX_FLAGS=-m32',
                ],
            },
            'armv6': {
                'run_tests': False
            },
            'armv7': {
                'run_tests': False
            },
            'armv8': {
                'run_tests': False
            },
            'mips': {
                'run_tests': False
            },
        },

        'cmake_args': [
            "-DENABLE_SANITIZERS=ON",
        ],

        'variables': {
            'exe': ''
        },
    },
    'macos': {
        'architectures': {
            'x86': {
                'cmake_args': [
                    '-DCMAKE_C_FLAGS=-m32',
                    '-DCMAKE_CXX_FLAGS=-m32',
                ],
            },
        },
        '!cmake_args': [],
        'variables': {
            'exe': ''
        },
    },
    'android': {
        'cmake_args': [
            "-DTARGET_ARCH=ANDROID",
            "-DANDROID_NATIVE_API_LEVEL=19"
        ],
        'run_tests': False,

        'architectures': {
            'armv7': {
                'cmake_args': [
                    "-DANDROID_ABI=armeabi-v7a",
                ]
            },
            'arm64v8a': {
                'cmake_args': [
                    "-DANDROID_ABI=arm64-v8a",
                ],
            },
        },
        'variables': {
            'exe': ''
        },
    },
    'windows': {
        "variables": {
            "exe": ".exe"
        }
    },
    'freebsd': {
        'cmake_args': [
            "-DENABLE_SANITIZERS=OFF",
        ],
        'variables': {
            'exe': ''
        },
    }
}

TARGETS['darwin'] = TARGETS['macos']

for arch in ARCHS.keys():
    for alias in ARCHS[arch].get('aliases', []):
        dict_alias(TARGETS, arch, alias)

###############################################################################
# Known compilers/versions
###############################################################################
COMPILERS = {
    'default': {
        'hosts': ['macos', 'linux', 'windows', 'freebsd'],
        'targets': ['macos', 'linux', 'windows', 'freebsd', 'android'],

        'versions': {
            'default': {}
        }
    },
    'clang': {
        'hosts': ['linux', 'macos'],
        'targets': ['linux', 'macos'],

        'imports': ['llvm'],

        'versions': {
            'default': {
                '!cmake_args': [],
            },
            '3': {
                'c': "clang-3.9",
                'cxx': "clang++-3.9",
            },
            '6': {
                'c': "clang-6.0",
                'cxx': "clang++-6.0",
                'cmake_args': ['-DENABLE_FUZZ_TESTS=ON'],
            },
            '7': {
                'c': "clang-7",
                'cxx': "clang++-7",
            },
            '8': {
                'c': "clang-8",
                'cxx': "clang++-8",
                'cmake_args': ['-DENABLE_FUZZ_TESTS=ON'],
            },
            '9': {
                'c': "clang-9",
                'cxx': "clang++-9",
                'cmake_args': ['-DENABLE_FUZZ_TESTS=ON'],
            },
            # 10 and 11 are XCode Apple clang/LLVM
            '10': {
                '!cmake_args': [],
            },
            '11': {
                '!cmake_args': [],
            },
        },
        'architectures': {
            # No fuzz tests on ARM
            'armv6': {
                '!cmake_args': []
            },
            'armv7': {
                '!cmake_args': []
            },
            'armv8': {
                '!cmake_args': []
            }
        }
    },
    'gcc': {
        'hosts': ['linux', 'manylinux', 'al2012', 'al2', 'freebsd'],
        'targets': ['linux', 'freebsd'],

        'imports': ['gcc'],

        'c': "gcc-{version}",
        'cxx': "g++-{version}",
        'compiler_packages': ['gcc', 'g++'],

        'apt_compiler_packages': ['gcc-{version}', 'g++-{version}'],

        'yum_compiler_packages': ['gcc', 'gcc-c++'],

        'versions': {
            '4.8': {},
            '5': {},
            '6': {},
            '7': {},
            '8': {},
        },

        'architectures': {
            'x86': {
                'apt_compiler_packages': ["gcc-{version}-multilib", "g++-{version}-multilib"],
                'yum_compiler_packages': ["gcc-multilib", "g++-multilib"],
            },
        },
    },
    'msvc': {
        'hosts': ['windows'],
        'targets': ['windows'],

        'imports': ['msvc'],

        'cmake_args': ["-G", "Visual Studio {generator_version}{generator_postfix}"],

        'versions': {
            '2015': {
                'variables': {
                    'generator_version': "14 2015",
                },
            },
            '2017': {
                'variables': {
                    'generator_version': "15 2017",
                },
            },
            '2019': {
                '!cmake_args': ["-G", "Visual Studio 16 2019", '-A', 'x64'],
            }
        },

        'architectures': {
            'x64': {
                'variables': {
                    'generator_postfix': " Win64",
                },
            },
        },
    },
    'ndk': {
        'hosts': ['linux'],
        'targets': ['android'],

        'versions': {
            'default': {
                'cmake_args': [
                    "-DANDROID_NATIVE_API_LEVEL=19",
                ],
            }
        }
    }
}

COMPILERS['msvc']['versions']['14'] = COMPILERS['msvc']['versions']['2015']
COMPILERS['msvc']['versions']['15'] = COMPILERS['msvc']['versions']['2017']
COMPILERS['msvc']['versions']['16'] = COMPILERS['msvc']['versions']['2019']

for arch in ARCHS.keys():
    for alias in ARCHS[arch].get('aliases', []):
        dict_alias(COMPILERS, arch, alias)

###############################################################################
# Supported os/arch couplets
###############################################################################
PLATFORMS = {
    'windows-x86': {},
    'windows-x64': {},
    'macos-x64': {},
    'freebsd-x64': {},
    'android-armv6': {},
    'android-armv7': {},
    'android-armv8': {},
    # Linux is done procedurally, below
}

# Windows
for arch in ['x86', 'x64']:
    canonical_windows = 'windows-{}'.format(arch)
    for alias in ARCHS[arch].get('aliases', []):
        alias_windows = 'windows-{}'.format(alias)
        PLATFORMS[alias_windows] = PLATFORMS[canonical_windows]

# MacOS
for mac in ['macos', 'darwin']:
    canonical_mac = 'macos-x64'
    for alias in ARCHS['x64'].get('aliases', []):
        alias_mac = '{}-{}'.format(mac, alias)
        if alias_mac != canonical_mac:
            PLATFORMS[alias_mac] = PLATFORMS[canonical_mac]

# FreeBSD
for alias in ARCHS['x64'].get('aliases', []):
    canonical_freebsd = 'freebsd-x64'
    for alias in ARCHS['x64'].get('aliases', []):
        alias_freebsd = 'freebsd-{}'.format(alias)
        if alias_freebsd != canonical_freebsd:
            PLATFORMS[alias_freebsd] = PLATFORMS[canonical_freebsd]

# Linux works on every arch we support
for arch in ARCHS.keys():
    canonical_linux = 'linux-{}'.format(arch)
    PLATFORMS[canonical_linux] = {}
    for alias in ARCHS[arch].get('aliases', []):
        alias_linux = 'linux-{}'.format(alias)
        PLATFORMS[alias_linux] = PLATFORMS[canonical_linux]

# Cross compile platforms
PLATFORMS['linux-armv6']['cross_compile_platform'] = 'linux-armv6'
PLATFORMS['linux-armv7']['cross_compile_platform'] = 'linux-armv7'
PLATFORMS['linux-armv8']['cross_compile_platform'] = 'linux-arm64'
PLATFORMS['android-armv6']['cross_compile_platform'] = 'android-arm'
PLATFORMS['android-armv7']['cross_compile_platform'] = 'android-arm'
PLATFORMS['android-armv8']['cross_compile_platform'] = 'android-arm64'
for cc_arch in ['armv6', 'armv7', 'armv8']:
    for cc_os in ['linux', 'android']:
        canonical_platform = '{}-{}'.format(cc_os, cc_arch)
        for alias in ARCHS[cc_arch].get('aliases', []):
            alias_platform = '{}-{}'.format(cc_os, alias)
            PLATFORMS[alias_platform] = PLATFORMS[canonical_platform]
