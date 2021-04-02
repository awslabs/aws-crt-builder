#!/usr/bin/env bash

# This builds libcrypto in the specified container, and uploads the result to S3 for use in building future containers
# Usage: $0 (linux|android) (x86|x64|arm64|armv6|armv7)
set -ex

# AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY must be in env vars to pass to container
[ ! -z "$AWS_ACCESS_KEY_ID" ] && [ ! -z "$AWS_SECRET_ACCESS_KEY" ]

if [ $# -eq 0 ]; then
    $0 linux x86
    $0 linux x64
    $0 linux armv6
    $0 linux armv7
    $0 linux arm64
    #$0 android x86
    #$0 android x64
    $0 android armeabi
    $0 android arm64
    exit 0
fi

[ $# -eq 2 ]
os=$1
arch=$2

openssl_target=${os}-${arch}
dockcross_target=${os}-${arch}

# openssl targets: (linux-x86|linux-x86_64|linux-aarch64|linux-armv4|android-x86|android-x86_64|android-armeabi|android-arm64)

case $os-$arch in
    manylinux1-x64)
        openssl_target=linux-x86_64
        ;;
    manylinux1-x86)
        openssl_target=linux-x86
        ;;
    manylinux2014-x64)
        openssl_target=linux-x86_64
        dockcross_target=manylinux2014-x64
        ;;
    manylinux2014-x86)
        openssl_target=linux-x86
        dockcross_target=manylinux2014-i686
        ;;
    manylinux2014-aarch64)
        openssl_target=linux-aarch64
        dockcross_target=manylinux2014-aarch64
        ;;
    *-x64)
        openssl_target=${os}-x86_64
        ;;
    linux-armv6|linux-armv7)
        openssl_target=linux-armv4
        dockcross_target=linux-${arch}
        ;;
    linux-arm64|linux-aarch64|linux-armv8)
        openssl_target=linux-aarch64
        dockcross_target=linux-arm64
        ;;
    android-arm|android-armeabi)
        openssl_target=android-armeabi
        dockcross_target=android-arm
        ;;
    android-arm64|android-aarch64|android-armv8)
        openssl_target=android-arm64
        dockcross_target=android-arm64
        ;;
esac

# Globals
compile_flags="-fPIC -g"
libcrypto_version=1.1.1
android_ndk_version=16b
android_api_version=19

# Create a .dockcross bootstrap file for the dockcross container, which is its init script
# Note that commands going into dockcross need to be quoted based on which shell you want the expansion done by. If the
# expansion should be done in the container, make sure the command is single quoted or quote heredoc'ed

###############################################################################
# ANDROID
###############################################################################
function build_android {
    if [ ! -d /tmp/openssl-${os}-${arch}/android-ndk-r${android_ndk_version} ]; then
        pushd /tmp/openssl-${os}-${arch}
        curl -sSL -o android-ndk.zip https://dl.google.com/android/repository/android-ndk-r${android_ndk_version}-linux-x86_64.zip
        yes | unzip android-ndk.zip
        popd
    fi
    if [ ! -e android-ndk-r${android_ndk_version} ]; then
        cp -r /tmp/openssl-${os}-${arch}/android-ndk-r${android_ndk_version} android-ndk-r${android_ndk_version}
    fi
    # configure the android SDK via .dockcross config
    # No interpolation, expand in the dockcross shell
    (cat <<- BOOT
#!/usr/bin/env bash
set -ex

export ANDROID_NDK_HOME=/work/android-ndk-r${android_ndk_version}
export CMAKE_TOOLCHAIN_FILE=$ANDROID_NDK_HOME/build/cmake/android.toolchain.cmake
export PACKAGE_NAME=libcrypto-${libcrypto_version}-${os}-${arch}.tar.gz
export LIBCRYPTO_PLATFORM=${openssl_target}
export COMPILE_FLAGS=${compile_flags}
BOOT
    )>> .dockcross
    # No interpolation, eval in dockcross shell
    (cat <<- "BOOT"
export PATH=$ANDROID_NDK_HOME/toolchains/llvm/prebuilt/linux-x86_64/bin:$PATH
./Configure ${LIBCRYPTO_PLATFORM} ${COMPILE_FLAGS} no-md2 no-rc5 no-rfc3779 no-sctp no-ssl-trace no-zlib no-hw no-mdc2 no-seed no-idea no-camellia no-bf no-dsa no-ssl3 no-capieng no-unit-test no-tests -DSSL_FORBID_ENULL -DOPENSSL_NO_DTLS1 -DOPENSSL_NO_HEARTBEATS --prefix=/work/opt/openssl --openssldir=/work/opt/openssl
make -j
make install_sw
rm -rf /work/opt/openssl/man || true
tar cvzf /work/${PACKAGE_NAME} -C /work/opt/openssl .
BOOT
    )>> .dockcross
    chmod a+x .dockcross
    ../dockcross-${dockcross_target} bash -c "echo DONE" 2>&1
}

###############################################################################
# UNIX
###############################################################################
function build_unix {
    # No interpolation, expand in the dockcross shell
    (cat <<- "BOOT"
#!/usr/bin/env bash
set -ex
# This setup would not normally be necessary within dockcross, but the OpenSSL
# Configure script is not very forgiving, and expects specific tools to have
# specific names, and exist at specific relative paths
# Put the cross compile toolchain dir on PATH
export PATH=$PATH:$(dirname $CC)
# Always use gcc, since it's always the cross compile toolchain
export CC=`echo $CC | sed -E 's/clang/gcc/'`
export CXX=`echo $CXX | sed -E 's/clang\+*/g++/'`
# Look for a cross-compile ar, if not found, use system ar
export AR=`find $(dirname $CC) -name '*-ar' | grep gnu | head -1`
if [ -z $AR ]; then
    AR=$(which ar)
fi
[ ! -z $AR ]
# Make sure a ranlib with the same prefix as gcc exists
gnu_ranlib=$(dirname $CC)/$(echo $(basename $CC) | sed -E s/gcc$/ranlib/)
if [ ! -x $gnu_ranlib ]; then
    mkdir ~/bin
    ln -s $(which ranlib) ~/bin/$(echo $(basename $CC) | sed -E s/gcc$/ranlib/)
    PATH=$PATH:~/bin
fi
BOOT
    )> .dockcross

    # now with interpolation
    (cat <<- BOOT
export PACKAGE_NAME=libcrypto-${libcrypto_version}-${os}-${arch}.tar.gz
./Configure ${openssl_target} ${compile_flags} no-md2 no-rc5 no-rfc3779 no-sctp no-ssl-trace no-zlib no-hw no-mdc2 no-seed no-idea no-camellia no-bf no-dsa no-ssl3 no-capieng no-unit-test no-tests -DSSL_FORBID_ENULL -DOPENSSL_NO_DTLS1 -DOPENSSL_NO_HEARTBEATS --prefix=/work/opt/openssl --openssldir=/work/opt/openssl
BOOT
    )>> .dockcross
    # No interpolation, expand in the dockcross shell
    # PATH, AR, and CC have to be carefully managed because openssl's configure/make is a little fragile during cross compiles
    (cat <<- "BOOT"
PATH=$PATH:`dirname $CC` make  CC=`basename $CC` AR=`basename $AR` -j
make install_sw
make clean
rm -rf /work/opt/openssl/man || true
tar cvzf /work/${PACKAGE_NAME} -C /work/opt/openssl .
BOOT
    )>> .dockcross

    chmod a+x .dockcross
    ../dockcross-${dockcross_target} --args '--privileged' bash -c "echo DONE" 2>&1
}

function build_libcrypto {
    if [ $os == 'android' ]; then
        build_android
    else
        build_unix
    fi
}

###############################################################################
# MAIN
###############################################################################
# clone openssl
mkdir -p /tmp/openssl-${os}-${arch}
pushd /tmp/openssl-${os}-${arch}
if [ ! -d openssl ]; then
    git clone --single-branch --branch OpenSSL_1_1_1-stable https://github.com/openssl/openssl.git
fi

# prepare dockcross
docker run --rm dockcross/${dockcross_target} > dockcross-${dockcross_target} && chmod a+x dockcross-${dockcross_target}
cd openssl

# execute the build
build_libcrypto

# Upload to S3
aws s3 cp libcrypto-${libcrypto_version}-${os}-${arch}.tar.gz s3://aws-crt-builder/_binaries/libcrypto/libcrypto-${libcrypto_version}-${os}-${arch}.tar.gz


popd
