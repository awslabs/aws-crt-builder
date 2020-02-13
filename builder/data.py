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

########################################################################################################################
# DATA DEFINITIONS
########################################################################################################################

KEYS = {
    # Build
    'python': "",  # where to find python on the machine
    'c': None,  # c compiler
    'cxx': None,  # c++ compiler
    'pre_build_steps': [],  # steps to run before build
    'post_build_steps': [],  # steps to run after build
    'build_env': {},  # environment variables to set before starting build
    'cmake_args': [],  # additional cmake arguments
    'run_tests': True,  # whether or not to run tests
    'build': [],  # deprecated, use build_steps
    'build_steps': [],  # steps to run instead of the default cmake compile
    'test': [],  # deprecated, use test_steps
    'test_steps': [],  # steps to run instead of the default ctest
    'pkg_setup': [],  # commands required to configure the package system
    # command to install packages, should be of the form 'pkgmanager arg1 arg2 {packages will go here}'
    'pkg_install': None,
    'pkg_update': None,  # command to update the package manager's database
    'packages': [],  # packages to install
    'compiler_packages': [],  # packages to support compiler
    'needs_compiler': True,  # whether or not this build needs a compiler

    # Linux
    'sudo': False  # whether or not sudo is necessary for installs
}

HOSTS = {
    'linux': {
        'variables': {
            'python': "python3",
        },

        'cmake_args': [
            "-DPERFORM_HEADER_CHECK=ON",
        ],
        'sudo': True
    },
    'ubuntu': {
        # need ld and make and such
        'compiler_packages': ['build-essential'],
        'pkg_setup': [
            'apt-key adv --fetch-keys http://apt.llvm.org/llvm-snapshot.gpg.key',
            'apt-add-repository ppa:ubuntu-toolchain-r/test',
            ['apt-add-repository',
                'deb http://apt.llvm.org/xenial/ llvm-toolchain-xenial-6.0 main'],
            ['apt-add-repository',
                'deb http://apt.llvm.org/xenial/ llvm-toolchain-xenial-7 main'],
            ['apt-add-repository',
                'deb http://apt.llvm.org/xenial/ llvm-toolchain-xenial-8 main'],
            ['apt-add-repository',
                'deb http://apt.llvm.org/xenial/ llvm-toolchain-xenial-9 main'],
        ],
        'pkg_update': 'apt-get -qq update -y',
        'pkg_install': 'apt-get -qq install -y',
    },
    'al2012': {
        'cmake_args': [
            "-DENABLE_SANITIZERS=OFF",
            "-DPERFORM_HEADER_CHECK=OFF",
        ],

        'pkg_update': 'yum update -y',
        'pkg_install': 'yum install -y',

        'variables': {
            'python': "python3",
        },
    },
    'al2': {
        'cmake_args': [
            "-DENABLE_SANITIZERS=OFF",
            "-DPERFORM_HEADER_CHECK=OFF",
        ],

        'pkg_update': 'yum update -y',
        'pkg_install': 'yum install -y',

        'variables': {
            'python': "python3",
        },
    },
    'manylinux': {
        'architectures': {
            'x86': {
                'image': "123124136734.dkr.ecr.us-east-1.amazonaws.com/aws-common-runtime/manylinux1:x86",
            },
            'x64': {
                'image': "123124136734.dkr.ecr.us-east-1.amazonaws.com/aws-common-runtime/manylinux1:x64",
            },
        },

        'pkg_update': 'yum update -y',
        'pkg_install': 'yum install -y',

        'variables': {
            'python': "/opt/python/cp37-cp37m/bin/python",
        },
    },
    'windows': {
        'variables': {
            'python': "python.exe",
        },

        'pkg_install': 'choco install --no-progress',

        'cmake_args': [
            "-DPERFORM_HEADER_CHECK=ON",
        ],
    },
    'macos': {
        'variables': {
            'python': "python3",
        },

        'pkg_install': 'brew install',
    }
}

TARGETS = {
    'linux': {
        'architectures': {
            'x86': {
                'cmake_args': [
                    '-DCMAKE_C_FLAGS=-m32',
                    '-DCMAKE_CXX_FLAGS=-m32',
                ],
            },
        },

        'cmake_args': [
            "-DENABLE_SANITIZERS=ON",
        ],
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
    },
    'android': {
        'cmake_args': [
            "-DTARGET_ARCH=ANDROID",
            "-DCMAKE_TOOLCHAIN_FILE=/opt/android-ndk/build/cmake/android.toolchain.cmake",
            "-DANDROID_NDK=/opt/android-ndk",
        ],
        'run_tests': False,

        'architectures': {
            'arm64v8a': {
                'cmake_args': [
                    "-DANDROID_ABI=arm64-v8a",
                ],
            },
        },
    },
    'windows': {
        "variables": {
            "exe": ".exe"
        }
    },
}

COMPILERS = {
    'default': {
        'hosts': ['macos', 'linux', 'windows'],
        'targets': ['macos', 'linux', 'windows'],

        'versions': {
            'default': {}
        }
    },
    'clang': {
        'hosts': ['linux', 'macos'],
        'targets': ['linux', 'macos'],

        'cmake_args': ['-DCMAKE_EXPORT_COMPILE_COMMANDS=ON', '-DENABLE_FUZZ_TESTS=ON'],

        'apt_keys': ["http://apt.llvm.org/llvm-snapshot.gpg.key"],

        'versions': {
            'default': {
                '!cmake_args': [],
            },
            '3': {
                'compiler_packages': ["clang-3.9"],
                'c': "clang-3.9",
                'cxx': "clang-3.9",
            },
            '6': {
                'compiler_packages': ["clang-6.0", "clang-tidy-6.0"],

                'c': "clang-6.0",
                'cxx': "clang-6.0",
            },
            '7': {
                'compiler_packages': ["clang-7", "clang-tidy-7"],

                'c': "clang-7",
                'cxx': "clang-7",
            },
            '8': {
                'compiler_packages': ["clang-8", "clang-tidy-8"],

                'c': "clang-8",
                'cxx': "clang-8",
            },
            '9': {
                'compiler_packages': ["clang-9", "clang-tidy-9"],

                'c': "clang-9",
                'cxx': "clang-9",
            },
            # 10 and 11 are XCode Apple clang/LLVM
            '10': {
                '!cmake_args': [],
            },
            '11': {
                '!cmake_args': [],
            },
        },
    },
    'gcc': {
        'hosts': ['linux', 'manylinux', 'al2012', 'al2'],
        'targets': ['linux'],

        'c': "gcc-{version}",
        'cxx': "g++-{version}",
        'compiler_packages': ["gcc-{version}", "g++-{version}"],

        'versions': {
            '4.8': {},
            '5': {},
            '6': {},
            '7': {},
            '8': {},
        },

        'architectures': {
            'x86': {
                'compiler_packages': ["gcc-{version}-multilib", "g++-{version}-multilib"],
            },
        },
    },
    'msvc': {
        'hosts': ['windows'],
        'targets': ['windows'],

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
            '19': {
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
