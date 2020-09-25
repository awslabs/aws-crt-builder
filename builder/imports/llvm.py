# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0.


from host import current_os
from project import Import
from toolchain import Toolchain
from util import UniqueList
from actions.install import InstallPackages
from actions.script import Script

import os
import stat
import tempfile

# this is a copy of https://apt.llvm.org/llvm.sh modified to add support back in
# for older versions of clang < 8, and removed the need for clangd, lldb

LLVM_SH = """\
#!/bin/bash
################################################################################
# Part of the LLVM Project, under the Apache License v2.0 with LLVM Exceptions.
# See https://llvm.org/LICENSE.txt for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
################################################################################
#
# This script will install the llvm toolchain on the different 
# Debian and Ubuntu versions

set -eux

# read optional command line argument
LLVM_VERSION=9
if [ "$#" -eq 1 ]; then
    LLVM_VERSION=$1
fi

DISTRO=$(lsb_release -is)
VERSION=$(lsb_release -sr)
DIST_VERSION="${DISTRO}_${VERSION}"

if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root!" 
   exit 1
fi

declare -A LLVM_VERSION_PATTERNS
LLVM_VERSION_PATTERNS[3]="-3.9"
LLVM_VERSION_PATTERNS[6]="-6.0"
LLVM_VERSION_PATTERNS[7]="-7"
LLVM_VERSION_PATTERNS[8]="-8"
LLVM_VERSION_PATTERNS[9]="-9"
LLVM_VERSION_PATTERNS[10]=""

if [ ! ${LLVM_VERSION_PATTERNS[$LLVM_VERSION]+_} ]; then
    echo "This script does not support LLVM version $LLVM_VERSION"
    exit 3
fi

LLVM_VERSION_STRING=${LLVM_VERSION_PATTERNS[$LLVM_VERSION]}

# find the right repository name for the distro and version
case "$DIST_VERSION" in
    Debian_9* )       REPO_NAME="deb http://apt.llvm.org/stretch/  llvm-toolchain-stretch$LLVM_VERSION_STRING main" ;;
    Debian_10* )      REPO_NAME="deb http://apt.llvm.org/buster/   llvm-toolchain-buster$LLVM_VERSION_STRING  main" ;;
    Debian_unstable ) REPO_NAME="deb http://apt.llvm.org/unstable/ llvm-toolchain$LLVM_VERSION_STRING         main" ;;
    Debian_testing )  REPO_NAME="deb http://apt.llvm.org/unstable/ llvm-toolchain$LLVM_VERSION_STRING         main" ;;
    Ubuntu_16.04 )    REPO_NAME="deb http://apt.llvm.org/xenial/   llvm-toolchain-xenial$LLVM_VERSION_STRING  main" ;;
    Ubuntu_18.04 )    REPO_NAME="deb http://apt.llvm.org/bionic/   llvm-toolchain-bionic$LLVM_VERSION_STRING  main" ;;
    Ubuntu_18.10 )    REPO_NAME="deb http://apt.llvm.org/cosmic/   llvm-toolchain-cosmic$LLVM_VERSION_STRING  main" ;;
    Ubuntu_19.04 )    REPO_NAME="deb http://apt.llvm.org/disco/    llvm-toolchain-disco$LLVM_VERSION_STRING   main" ;;
    Ubuntu_19.10 )    REPO_NAME="deb http://apt.llvm.org/eoan/     llvm-toolchain-eoan$LLVM_VERSION_STRING    main" ;;
    * )
        echo "Distribution '$DISTRO' in version '$VERSION' is not supported by this script (${DIST_VERSION})."
        exit 2
esac


# install everything
curl -sSL https://apt.llvm.org/llvm-snapshot.gpg.key | apt-key add -
add-apt-repository "${REPO_NAME}"
apt-get update 
apt-get install -y clang$LLVM_VERSION_STRING
"""


class LLVM(Import):
    def __init__(self, **kwargs):
        super().__init__(
            compiler=True,
            config={
                'targets': ['linux'],
            },
            **kwargs)
        self.installed = False

    def resolved(self):
        return True

    def install(self, env):
        if self.installed:
            return

        sh = env.shell
        config = env.config

        # Ensure compiler packages are installed
        packages = UniqueList(config.get('compiler_packages', []))
        Script([InstallPackages(packages)], name='Install compiler prereqs').run(env)

        installed_path, installed_version = Toolchain.find_compiler(
            env.spec.compiler, env.spec.compiler_version)
        if installed_path:
            print('Compiler {} {} already exists at {}'.format(
                env.spec.compiler, installed_version, installed_path))
            self.installed = True
            return

        sudo = env.config.get('sudo', current_os() == 'linux')
        sudo = ['sudo'] if sudo else []

        # Strip minor version info
        version = env.toolchain.compiler_version.replace('\..+', '')

        script = tempfile.NamedTemporaryFile(delete=False)
        script_path = script.name
        script.write(LLVM_SH.encode())
        script.close()

        # Make script executable
        os.chmod(script_path, stat.S_IRUSR | stat.S_IRGRP |
                 stat.S_IROTH | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        sh.exec(*sudo, [script_path, version], check=True)

        self.installed = True
