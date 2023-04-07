# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0.

from enum import Enum
from builder.core.util import dict_alias

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
    ZYPPER = 'zypper'
    DNF = 'dnf'
    OPKG = 'opkg'
    OBSD_PKG = 'openbsd_pkg'


KEYS = {
    # Build
    'python': "",  # where to find python on the machine
    'c': None,  # c compiler
    'cxx': None,  # c++ compiler
    'cmake_args': [],  # additional cmake arguments

    'CI_JSON_FILES': [],  # CI JSON files

    # where the cmake binaries should be stored, and dependencies installed
    'build_dir': 'build',
    'deps_dir': '{build_dir}/deps',
    'install_dir': '{build_dir}/install',
    'env': {},  # environment variables global for all steps
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

    'variants': {},  # additional build variants

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
    },
    'armv7': {
        'arch': 'armv7',
        'aliases': ['armv7a']
    },
    'armv8': {
        'arch': 'armv8',
        'aliases': ['arm64', 'arm64v8', 'arm64v8a', 'aarch64'],
    },
    'mips': {
        'arch': 'mips',
        'cross_compile_platform': 'linux-mips',
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
            'apt-add-repository -y ppa:ubuntu-toolchain-r/test',
        ],
        'pkg_update': 'apt-get -qq update -y',
        'pkg_install': 'apt-get -qq install -y',
        'variables': {
            'python': "python3.8",
        },
    },
    'debian': {
        'os': 'linux',
        'pkg_tool': PKG_TOOLS.APT,
        # need ld and make and such
        'packages': ['build-essential'],
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
    'openwrt': {
        'os': 'linux',
        'pkg_tool': PKG_TOOLS.OPKG,
        'pkg_setup': [],
        'pkg_update': 'opkg update',
        'pkg_install': 'opkg install',
    },
    'raspbian': {
        'os': 'linux',
        'pkg_tool': PKG_TOOLS.APT,
        # need ld and make and such
        'packages': ['build-essential'],
        'pkg_update': 'apt-get -qq update -y',
        'pkg_install': 'apt-get -qq install -y',
    },
    'fedora': {
        'os': 'linux',
        'pkg_tool': PKG_TOOLS.DNF,
        'pkg_update': 'dnf update -y',
        'pkg_install': 'dnf install -y',
    },
    'opensuse': {
        'os': 'linux',
        'pkg_tool': PKG_TOOLS.ZYPPER,
        'pkg_update': 'zypper refresh && zypper --non-interactive patch',
        'pkg_install': 'zypper install -y',
        'variables': {
            'python': "python3.9",
        },
    },
    'rhel': {
        'os': 'linux',
        'pkg_tool': PKG_TOOLS.DNF,
        'pkg_update': 'dnf update -y',
        'pkg_install': 'dnf install -y',
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
            'python': "/opt/python/cp39-cp39/bin/python",
        },
    },
    'centos': {
        'os': 'linux',
        'pkg_tool': PKG_TOOLS.YUM,
        'pkg_update': 'yum update -y',
        'pkg_install': 'yum install -y',
        'sudo': False,

        'variables': {
            'python': 'python3'
        }
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
    },
    'openbsd': {
        'os': 'openbsd',
        'variables': {
            'python': "python3",
        },
        'sudo': True,

        'pkg_tool': PKG_TOOLS.OBSD_PKG,
        'packages': [
            'cmake',
            'git',
        ],
        'pkg_install': 'pkg_add -I'
    }
}

HOSTS['darwin'] = HOSTS['macos']

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
            'x64': {
                'cmake_args': [
                    '-DCMAKE_OSX_ARCHITECTURES=x86_64',
                ],
            },
            'armv8': {
                'cmake_args': [
                    '-DCMAKE_OSX_ARCHITECTURES=arm64',
                ],
            },
        },
        '!cmake_args': ['-DENABLE_SANITIZERS=ON'],
        'variables': {
            'exe': '',
        },
    },
    'ios': {
        'cmake_args': [
            '-GXcode',
            '-DCMAKE_SYSTEM_NAME=iOS',
            '-DCMAKE_OSX_ARCHITECTURES="{osx_architectures}"',
            '-DCMAKE_OSX_DEPLOYMENT_TARGET={osx_deployment_target}'
        ],
        'run_tests': False,
        'architectures': {
            'armv8': {
                'variables': {
                    'osx_architectures': 'arm64'
                }
            }
        },
        'variables': {
            'exe': '',
            'osx_deployment_target': '13.0',
            'osx_architectures': 'arm64'
        },
    },
    'tvos': {
        'cmake_args': [
            '-GXcode',
            '-DCMAKE_SYSTEM_NAME=tvOS',
            '-DCMAKE_OSX_ARCHITECTURES="{osx_architectures}"',
            '-DCMAKE_OSX_DEPLOYMENT_TARGET={osx_deployment_target}'
        ],
        'run_tests': False,
        'architectures': {
            'armv8': {
                'variables': {
                    'osx_architectures': 'arm64'
                }
            }
        },
        'variables': {
            'exe': '',
            'osx_deployment_target': '13.0',
            'osx_architectures': 'arm64'
        },
    },
    'watchos': {
        'cmake_args': [
            '-GXcode',
            '-DCMAKE_SYSTEM_NAME=watchOS',
            '-DCMAKE_OSX_ARCHITECTURES="{osx_architectures}"',
            '-DCMAKE_OSX_DEPLOYMENT_TARGET={osx_deployment_target}'
        ],
        'run_tests': False,
        'architectures': {
            'armv8': {
                'variables': {
                    'osx_architectures': 'arm64'
                }
            }
        },
        'variables': {
            'exe': '',
            'osx_deployment_target': '5.0',
            'osx_architectures': 'arm64'
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
    },
    'openbsd': {
        'cmake_args': [
            "-DENABLE_SANITIZERS=OFF",
        ],
        'variables': {
            'exe': ''
        },
    }
}

TARGETS['darwin'] = TARGETS['macos']
TARGETS['osx'] = TARGETS['macos']

for arch in ARCHS.keys():
    for alias in ARCHS[arch].get('aliases', []):
        dict_alias(TARGETS, arch, alias)

###############################################################################
# Known compilers/versions
###############################################################################
COMPILERS = {
    'default': {
        'hosts': ['macos', 'linux', 'windows', 'freebsd', 'openbsd'],
        'targets': ['macos', 'linux', 'windows', 'freebsd', 'openbsd', 'android', 'ios', 'tvos', 'watchos'],

        'versions': {
            'default': {}
        }
    },
    'appleclang': {
        'hosts': ['macos'],
        'targets': ['macos', 'ios', 'tvos', 'watchos'],

        'versions': {
            'default': {},

            '11': {},
            '12': {},
            '13': {},
            '14': {},
        },
    },
    'clang': {
        'hosts': ['linux', 'openbsd'],
        'targets': ['linux', 'openbsd'],

        'imports': ['llvm'],

        'versions': {
            'default': {},
            '3': {
                'c': "clang-3.9",
                'cxx': "clang++-3.9",
            },
            '6': {
                'c': "clang-6.0",
                'cxx': "clang++-6.0",
                'cmake_args': ['-DENABLE_FUZZ_TESTS=ON'],
                # clang-6 support C++17, but headers requires at least libstdc++-7
                'apt_compiler_packages': ['libstdc++-7-dev'],
            },
            '7': {
                'c': "clang-7",
                'cxx': "clang++-7",
                'apt_compiler_packages': ['libstdc++-7-dev'],
            },
            '8': {
                'c': "clang-8",
                'cxx': "clang++-8",
                'cmake_args': ['-DENABLE_FUZZ_TESTS=ON'],
                'apt_compiler_packages': ['libstdc++-8-dev'],
            },
            '9': {
                'c': "clang-9",
                'cxx': "clang++-9",
                'cmake_args': ['-DENABLE_FUZZ_TESTS=ON'],
                'apt_compiler_packages': ['libstdc++-9-dev'],
            },
            '10': {},
            '11': {},
            '12': {},
            '13': {},
            '14': {},
            '15': {},
            '16': {}
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

        'apt_compiler_packages': ['gcc-{version}', 'g++-{version}', 'libstdc++-{version}-dev'],

        'yum_compiler_packages': ['gcc', 'gcc-c++'],

        'versions': {
            '4.8': {
                # ASan has been broken on 4.8 GCC version distributed on Ubuntu
                # and will unlikely to get fixed upstream. so turn it off.
                'cmake_args': ['-DENABLE_SANITIZERS=OFF'],
            },
            '5': {},
            '6': {},
            '7': {},
            '8': {},
            '9': {},
            '10': {},
            '11': {},
            '12': {}
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

        'versions': {
            # 2015
            '14': {
                'cmake_args': [
                    '-Tv140',
                ],
            },
            # 2017
            '15': {
                'cmake_args': [
                    '-Tv141',
                ],
            },
            # 2019
            '16': {
                'cmake_args': [
                    '-Tv142',
                ],
            }
        },

        'architectures': {
            'x86': {
                'cmake_args': [
                    '-AWin32',
                ],
            },
            'x64': {
                'cmake_args': [
                    '-Ax64',
                ],
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
    'macos-armv8': {},
    'freebsd-x64': {},
    'openbsd-x64': {},
    'android-armv6': {},
    'android-armv7': {},
    'android-armv8': {},
    'ios-armv8': {
        'cross_compile_platform': None
    },
    'tvos-armv8': {
        'cross_compile_platform': None
    },
    'watchos-armv8': {
        'cross_compile_platform': None
    }
    # Linux is done procedurally, below
}

# Windows
for arch in ['x86', 'x64']:
    canonical_windows = 'windows-{}'.format(arch)
    for alias in ARCHS[arch].get('aliases', []):
        alias_windows = 'windows-{}'.format(alias)
        PLATFORMS[alias_windows] = PLATFORMS[canonical_windows]

# MacOS
for arch in ['x64', 'armv8']:
    canonical_mac = 'macos-{}'.format(arch)
    for mac in ['macos', 'darwin', 'osx']:
        for alias in ARCHS[arch].get('aliases', []):
            alias_mac = '{}-{}'.format(mac, alias)
            if alias_mac != canonical_mac:
                PLATFORMS[alias_mac] = PLATFORMS[canonical_mac]

# iOS
for alias in ARCHS['armv8'].get('aliases', []):
    alias_ios = 'ios-{}'.format(alias)
    PLATFORMS[alias_ios] = PLATFORMS['ios-armv8']

# FreeBSD
for alias in ARCHS['x64'].get('aliases', []):
    canonical_freebsd = 'freebsd-x64'
    for alias in ARCHS['x64'].get('aliases', []):
        alias_freebsd = 'freebsd-{}'.format(alias)
        if alias_freebsd != canonical_freebsd:
            PLATFORMS[alias_freebsd] = PLATFORMS[canonical_freebsd]

# OpenBSD
for alias in ARCHS['x64'].get('aliases', []):
    canonical_openbsd = 'openbsd-x64'
    for alias in ARCHS['x64'].get('aliases', []):
        alias_openbsd = 'openbsd-{}'.format(alias)
        if alias_openbsd != canonical_openbsd:
            PLATFORMS[alias_openbsd] = PLATFORMS[canonical_openbsd]

# Linux works on every arch we support
for arch in ARCHS.keys():
    canonical_linux = 'linux-{}'.format(arch)
    PLATFORMS[canonical_linux] = PLATFORMS.get(canonical_linux, {})
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
        # link aliases to canonical config
        for alias in ARCHS[cc_arch].get('aliases', []):
            alias_platform = '{}-{}'.format(cc_os, alias)
            PLATFORMS[alias_platform] = PLATFORMS[canonical_platform]
