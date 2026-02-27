# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0.


from builder.core.host import current_os
from builder.core.project import Import
from builder.core.toolchain import Toolchain
from builder.core.util import UniqueList
from builder.actions.install import InstallPackages
from builder.actions.script import Script

import os
import re
import stat
import tempfile
import urllib.request

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
LLVM_VERSION=18
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
LLVM_VERSION_PATTERNS[10]="-10"
LLVM_VERSION_PATTERNS[11]="-11"
LLVM_VERSION_PATTERNS[12]="-12"
LLVM_VERSION_PATTERNS[13]="-13"
LLVM_VERSION_PATTERNS[14]="-14"
LLVM_VERSION_PATTERNS[15]="-15"
LLVM_VERSION_PATTERNS[16]="-16"
LLVM_VERSION_PATTERNS[17]="-17"
LLVM_VERSION_PATTERNS[18]="-18"

if [ ! ${LLVM_VERSION_PATTERNS[$LLVM_VERSION]+_} ]; then
    echo "This script does not support LLVM version $LLVM_VERSION"
    exit 3
fi

LLVM_VERSION_STRING=${LLVM_VERSION_PATTERNS[$LLVM_VERSION]}

# find the right repository name for the distro and version
case "$DIST_VERSION" in
    Debian_9* )       REPO_NAME="deb http://apt.llvm.org/stretch/  llvm-toolchain-stretch$LLVM_VERSION_STRING main" ;;
    Debian_10* )      REPO_NAME="deb http://apt.llvm.org/buster/   llvm-toolchain-buster$LLVM_VERSION_STRING  main" ;;
    Debian_11* )      REPO_NAME="deb http://apt.llvm.org/bullseye/ llvm-toolchain-bullseye$LLVM_VERSION_STRING  main" ;;
    Debian_12* )      REPO_NAME="deb http://apt.llvm.org/bookworm/ llvm-toolchain-bookworm$LLVM_VERSION_STRING  main" ;;
    Debian_unstable ) REPO_NAME="deb http://apt.llvm.org/unstable/ llvm-toolchain$LLVM_VERSION_STRING         main" ;;
    Debian_testing )  REPO_NAME="deb http://apt.llvm.org/unstable/ llvm-toolchain$LLVM_VERSION_STRING         main" ;;
    Ubuntu_16.04 )    REPO_NAME="deb http://apt.llvm.org/xenial/   llvm-toolchain-xenial$LLVM_VERSION_STRING  main" ;;
    Ubuntu_18.04 )    REPO_NAME="deb http://apt.llvm.org/bionic/   llvm-toolchain-bionic$LLVM_VERSION_STRING  main" ;;
    Ubuntu_18.10 )    REPO_NAME="deb http://apt.llvm.org/cosmic/   llvm-toolchain-cosmic$LLVM_VERSION_STRING  main" ;;
    Ubuntu_19.04 )    REPO_NAME="deb http://apt.llvm.org/disco/    llvm-toolchain-disco$LLVM_VERSION_STRING   main" ;;
    Ubuntu_19.10 )   REPO_NAME="deb http://apt.llvm.org/eoan/      llvm-toolchain-eoan$LLVM_VERSION_STRING    main" ;;
    Ubuntu_20.04 )   REPO_NAME="deb http://apt.llvm.org/focal/     llvm-toolchain-focal$LLVM_VERSION_STRING   main" ;;
    Ubuntu_20.10 )   REPO_NAME="deb http://apt.llvm.org/groovy/    llvm-toolchain-groovy$LLVM_VERSION_STRING  main" ;;
    Ubuntu_21.04 )   REPO_NAME="deb http://apt.llvm.org/hirsute/   llvm-toolchain-hirsute$LLVM_VERSION_STRING main" ;;
    Ubuntu_22.04 )   REPO_NAME="deb http://apt.llvm.org/jammy/     llvm-toolchain-jammy$LLVM_VERSION_STRING main"   ;;
    Ubuntu_24.04 )   REPO_NAME="deb http://apt.llvm.org/noble/     llvm-toolchain-noble$LLVM_VERSION_STRING main"   ;;
    * )
        echo "Distribution '$DISTRO' in version '$VERSION' is not supported by this script (${DIST_VERSION})."
        exit 2
esac


# install everything
if [[ $LLVM_VERSION -ne 3 ]]; then
    curl -sSL https://apt.llvm.org/llvm-snapshot.gpg.key | apt-key add -
    add-apt-repository "${REPO_NAME}"
    apt-get update
fi
apt-get install -y clang$LLVM_VERSION_STRING
"""


def _get_codename():
    """
    Get the distribution codename (e.g., 'noble', 'bookworm').
    Works with Ubuntu and Debian.
    We should probably only care about Ubuntu but may as well support both and older codename detection is possible.
    Returns None if codename cannot be determined.
    """
    import subprocess

    # Try lsb_release (works on Ubuntu, Debian)
    try:
        result = subprocess.run(['lsb_release', '-cs'], capture_output=True, text=True)
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except (FileNotFoundError, Exception):
        pass

    # Try /etc/os-release
    try:
        with open('/etc/os-release', 'r') as f:
            os_release = {}
            for line in f:
                if '=' in line:
                    key, value = line.strip().split('=', 1)
                    os_release[key] = value.strip('"')

            # VERSION_CODENAME is the standard field
            if 'VERSION_CODENAME' in os_release and os_release['VERSION_CODENAME']:
                return os_release['VERSION_CODENAME']

            # For Ubuntu, we can also check UBUNTU_CODENAME
            if 'UBUNTU_CODENAME' in os_release and os_release['UBUNTU_CODENAME']:
                return os_release['UBUNTU_CODENAME']
    except (FileNotFoundError, Exception):
        pass

    # Try /etc/lsb-release (older Ubuntu systems)
    try:
        with open('/etc/lsb-release', 'r') as f:
            for line in f:
                if line.startswith('DISTRIB_CODENAME='):
                    codename = line.strip().split('=', 1)[1].strip('"')
                    if codename:
                        return codename
    except (FileNotFoundError, Exception):
        pass

    return None


def _fetch_url_content(url):
    """
    Fetch content from a URL.
    We use curl as a subprocess for compression handling.
    Falls back to urllib if curl is not available.
    """
    import subprocess

    # Use curl with --compressed flag (handles all compression types)
    try:
        result = subprocess.run(
            ['curl', '-s', '--compressed', url],
            capture_output=True,
            text=True,
            timeout=60
        )
        if result.returncode == 0 and result.stdout:
            return result.stdout
    except (FileNotFoundError, subprocess.TimeoutExpired, Exception) as e:
        print('curl not available or failed, falling back to urllib: {}'.format(e))

    # Fall back to urllib with gzip decompression.
    # apt.llvm.org uses gzip encoding for the main page, no compression for llvm.sh
    import gzip
    try:
        req = urllib.request.Request(url, headers={
            'Accept-Encoding': 'gzip, identity',
            'User-Agent': 'aws-crt-builder'
        })
        with urllib.request.urlopen(req, timeout=30) as response:
            data = response.read()
            encoding = response.info().get('Content-Encoding', '')

            if encoding == 'gzip':
                return gzip.decompress(data).decode('utf-8')
            else:
                # No compression
                return data.decode('utf-8')

    except Exception as e:
        print('urllib fetch failed: {}'.format(e))

    return None


def get_latest_llvm_version():
    """
    Detect the latest available LLVM/Clang version from apt.llvm.org.
    Prefers the qualification/RC branch (stable + 1), falls back to stable if not available.

    Supported distributions:
    - Ubuntu: bionic (18.04), focal (20.04), jammy (22.04), noble (24.04), plucky (25.04), questing (25.10)
    - Debian: bullseye (11), bookworm (12), trixie (13)

    Returns the version number as a string, or None if detection fails.
    """
    try:
        # Download the llvm.sh script to get the stable version
        llvm_sh_content = _fetch_url_content('https://apt.llvm.org/llvm.sh')
        if not llvm_sh_content:
            print('Warning: Could not download llvm.sh')
            return None

        # Extract CURRENT_LLVM_STABLE from the script
        stable_match = re.search(r'CURRENT_LLVM_STABLE=(\d+)', llvm_sh_content)
        if not stable_match:
            print('Warning: Could not parse CURRENT_LLVM_STABLE from llvm.sh')
            return None

        stable_version = int(stable_match.group(1))
        qualification_version = stable_version + 1

        # Get the codename (works for Ubuntu and Debian)
        codename = _get_codename()

        if codename:
            print('Detected distribution codename: {}'.format(codename))

            # Parse the LLVM apt page to find available versions for this codename
            apt_page = _fetch_url_content('https://apt.llvm.org/')
            if apt_page:
                # Look for llvm-toolchain-<codename>-<version> patterns
                pattern = r'llvm-toolchain-{}-(\d+)'.format(re.escape(codename))
                available_versions = set(re.findall(pattern, apt_page))

                if available_versions:
                    print('Available LLVM versions for {}: {}'.format(
                        codename, ', '.join(sorted(available_versions, key=int))))

                    if str(qualification_version) in available_versions:
                        print('Latest LLVM: Using qualification/RC branch: clang-{}'.format(qualification_version))
                        return str(qualification_version)
                    elif str(stable_version) in available_versions:
                        print('Latest LLVM: Qualification branch {} not available for {}, using stable: clang-{}'.format(
                            qualification_version, codename, stable_version))
                        return str(stable_version)
                    else:
                        # Use the highest available version for this codename
                        highest = max(available_versions, key=int)
                        print('Latest LLVM: Neither qualification ({}) nor stable ({}) available for {}, using highest available: clang-{}'.format(
                            qualification_version, stable_version, codename, highest))
                        return highest
                else:
                    print('Warning: No LLVM versions found for codename {} on apt.llvm.org'.format(codename))
                    print('This distribution may not be supported by apt.llvm.org')
            else:
                print('Warning: Could not fetch apt.llvm.org page')
        else:
            print('Warning: Could not determine distribution codename')

        # Fall back to stable version if we couldn't check availability
        print('Latest LLVM: Falling back to stable version: clang-{}'.format(stable_version))
        return str(stable_version)

    except Exception as e:
        print('Warning: Could not detect latest LLVM version: {}'.format(e))
        return None


class LLVM(Import):
    # Cache for the resolved latest version
    _latest_version_cache = None

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

    @staticmethod
    def resolve_latest_version():
        """
        Resolve 'latest' to an actual version number. We cache the result to avoid repeating this step.
        """
        if LLVM._latest_version_cache is None:
            LLVM._latest_version_cache = get_latest_llvm_version()
        return LLVM._latest_version_cache

    def install(self, env):
        if self.installed:
            return

        sh = env.shell
        config = env.config

        # Ensure compiler packages are installed
        packages = UniqueList(config.get('compiler_packages', []))
        Script([InstallPackages(packages)],
               name='Install compiler prereqs').run(env)

        # Handle 'latest' version
        version = env.toolchain.compiler_version
        if version == 'latest':
            version = LLVM.resolve_latest_version()
            if version is None:
                raise Exception("Could not determine latest LLVM version")
            print('Resolved clang-latest to clang-{}'.format(version))
            env.toolchain.compiler_version = version
            env.spec.compiler_version = version

        installed_path, installed_version = Toolchain.find_compiler(
            env.spec.compiler, version)
        if installed_path:
            print('Compiler {} {} already exists at {}'.format(
                env.spec.compiler, installed_version, installed_path))
            self.installed = True
            return

        sudo = env.config.get('sudo', current_os() == 'linux')
        sudo = ['sudo'] if sudo else []

        # Strip minor version info
        version = version.replace(r'\..+', '')

        script = tempfile.NamedTemporaryFile(delete=False)
        script_path = script.name
        script.write(LLVM_SH.encode())
        script.close()

        # Make script executable
        os.chmod(script_path, stat.S_IRUSR | stat.S_IRGRP |
                 stat.S_IROTH | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        sh.exec(*sudo, [script_path, version], check=True)

        self.installed = True
