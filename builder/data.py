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
    'python': "",
    'c': None,
    'cxx': None,
    'pre_build_steps': [],
    'post_build_steps': [],
    'build_env': {},
    'cmake_args': [],
    'run_tests': True,
    'build': [],
    'test': [],

    # Linux
    'use_apt': False,
    'apt_keys': [],
    'apt_repos': [],
    'apt_packages': [],

    # macOS
    'use_brew': False,
    'brew_packages': [],

    # CodeBuild
    'enabled': True,
    'image': "",
    'image_type': "",
    'compute_type': "",
    'requires_privilege': False,
}

HOSTS = {
    'linux': {
        'variables': {
            'python': "python3",
        },

        'cmake_args': [
            "-DPERFORM_HEADER_CHECK=ON",
        ],

        'use_apt': True,
        'apt_repos': [
            "ppa:ubuntu-toolchain-r/test",
        ],
    },
    'al2012': {
        'cmake_args': [
            "-DENABLE_SANITIZERS=OFF",
            "-DPERFORM_HEADER_CHECK=OFF",
        ],

        'variables': {
            'python': "python3",
        },
    },
    'al2': {
        'cmake_args': [
            "-DENABLE_SANITIZERS=OFF",
            "-DPERFORM_HEADER_CHECK=OFF",
        ],

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

        'variables': {
            'python': "/opt/python/cp37-cp37m/bin/python",
        },
    },
    'windows': {
        'variables': {
            'python': "python.exe",
        },


        'cmake_args': [
            "-DPERFORM_HEADER_CHECK=ON",
        ],
    },
    'macos': {
        'variables': {
            'python': "python3",
        },

        'use_brew': True,
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
        'hosts': ['macos', 'al2012', 'al2', 'manylinux', 'linux', 'windows'],
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
                '!apt_repos': [],
                '!cmake_args': [],
            },
            '3': {
                '!post_build_steps': [],
                '!apt_repos': [],
                '!cmake_args': [],

                'apt_packages': ["clang-3.9"],
                'c': "clang-3.9",
                'cxx': "clang-3.9",
            },
            '6': {
                'apt_repos': [
                    "deb http://apt.llvm.org/xenial/ llvm-toolchain-xenial-6.0 main",
                ],
                'apt_packages': ["clang-6.0", "clang-tidy-6.0"],

                'c': "clang-6.0",
                'cxx': "clang-6.0",

                'requires_privilege': True,
            },
            '7': {
                'apt_repos': [
                    "deb http://apt.llvm.org/xenial/ llvm-toolchain-xenial-7 main",
                ],
                'apt_packages': ["clang-7", "clang-tidy-7"],

                'c': "clang-7",
                'cxx': "clang-7",

                'requires_privilege': True,
            },
            '8': {
                'apt_repos': [
                    "deb http://apt.llvm.org/xenial/ llvm-toolchain-xenial-8 main",
                ],
                'apt_packages': ["clang-8", "clang-tidy-8"],

                'c': "clang-8",
                'cxx': "clang-8",

                'requires_privilege': True,
            },
            '9': {
                'apt_repos': [
                    "deb http://apt.llvm.org/xenial/ llvm-toolchain-xenial-9 main",
                ],
                'apt_packages': ["clang-9", "clang-tidy-9"],

                'c': "clang-9",
                'cxx': "clang-9",

                'requires_privilege': True,
            },
            # 10 and 11 are XCode Apple clang/LLVM
            '10': {
                '!apt_repos': [],
                '!cmake_args': [],
            },
            '11': {
                '!apt_repos': [],
                '!cmake_args': [],
            },
        },
    },
    'gcc': {
        'hosts': ['linux', 'manylinux', 'al2012', 'al2'],
        'targets': ['linux'],

        'c': "gcc-{version}",
        'cxx': "g++-{version}",
        'apt_packages': ["gcc-{version}", "g++-{version}"],

        'versions': {
            '4.8': {},
            '5': {},
            '6': {},
            '7': {},
            '8': {},
        },

        'architectures': {
            'x86': {
                'apt_packages': ["gcc-{version}-multilib", "g++-{version}-multilib"],
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
