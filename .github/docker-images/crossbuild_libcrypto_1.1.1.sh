#!/usr/bin/env bash

# This builds libcrypto in the specified container, and uploads the result to S3 for use in building future containers
# Usage: $0 (linux|android) (x86|x64|arm64|armv6|armv7) (openssl config)
set -ex

[ $# -eq 3 ]
os=$1
arch=$2
# See ./Configure LIST in openssl
config_platform=$3

libcrypto_version=1.1.1
android_ndk_version=16b
android_api_version=19

# Note that commands going into dockcross need to be quoted based on which shell you want the expansion done by. If the
# expansion should be done in the container, make sure the command is single quoted

# AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY must be in env vars to pass to container
[ ! -z "$AWS_ACCESS_KEY_ID" ] && [ ! -z "$AWS_SECRET_ACCESS_KEY" ]

mkdir -p /tmp/openssl-${os}-${arch}
pushd /tmp/openssl-${os}-${arch}
if [ ! -d openssl ]; then
    git clone --single-branch --branch OpenSSL_1_1_1-stable https://github.com/openssl/openssl.git
fi

docker run --rm dockcross/${os}-${arch} > dockcross-${os}-${arch} && chmod a+x dockcross-${os}-${arch}
cd openssl

# prep for android build if necessary
if [ $os == 'android' ]; then
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
    # download setenv-android.sh script, edit it to use our versions
    # No interpolation, expand in the dockcross shell
    (cat <<- "BOOT"
#!/usr/bin/env bash
set -ex
export CC=
export CXX=
export CPP=
export AR=
BOOT
    )> .dockcross
    # now with interpolation
    (cat <<- BOOT
export ANDROID_NDK_HOME=/work/android-ndk-r${android_ndk_version}
export PACKAGE_NAME=libcrypto-${libcrypto_version}-${os}-${arch}.tar.gz
curl -sSL -o setenv-android.sh https://wiki.openssl.org/images/7/70/Setenv-android.sh
sed -E --in-place "s/^_ANDROID_NDK=.*$/_ANDROID_NDK=android-ndk-r${android_ndk_version}/" setenv-android.sh
sed -E --in-place "s/^_ANDROID_API=.*$/_ANDROID_API=android-${android_api_version}/" setenv-android.sh
sed -E --in-place "s/^(_ANDROID_EABI=.+)-4.8/\1-4.9/" setenv-android.sh
sed -E --in-place 's/\r//g' setenv-android.sh
chmod a+x setenv-android.sh
. setenv-android.sh
env
./config -fPIC no-md2 no-rc5 no-rfc3779 no-sctp no-ssl-trace no-zlib no-hw no-mdc2 no-seed no-idea no-camellia no-bf no-dsa no-ssl3 no-capieng no-unit-test no-tests -DSSL_FORBID_ENULL -DOPENSSL_NO_DTLS1 -DOPENSSL_NO_HEARTBEATS --prefix=/work/opt/openssl --openssldir=/work/opt/openssl
BOOT
    )>> .dockcross
    # No interpolation, eval in dockcross shell
    (cat <<- "BOOT"
export PATH=$ANDROID_NDK_HOME/toolchains/llvm/prebuilt/linux-x86_64/bin:$PATH
make -j
make install_sw
rm -rf /work/opt/openssl/man || true
tar cvzf /work/${PACKAGE_NAME} -C /work/opt/openssl .
BOOT
    )>> .dockcross
    chmod a+x .dockcross
    ../dockcross-${os}-${arch} bash -c "echo DONE"
###############################################################################
else ########################### NOT ANDROID ##################################
###############################################################################
    # No interpolation, expand in the dockcross shell
    (cat <<- "BOOT"
#!/usr/bin/env bash
set -ex
export PATH=$PATH:$(dirname $CC)
export CC=`echo $CC | sed -e 's/clang/gcc/'`
export CXX=`echo $CXX | sed -e 's/clang\+*/g++/'`
export AR=`find $(dirname $CC) -name '*-gnu-ar' | head -1`
if [ ! -x $(dirname $CC)/*-ranlib ]; then
    mkdir ~/bin
    ln -s $(which ranlib) ~/bin/$(echo $(basename $CC) | sed -e s/-gcc$/-ranlib/)
    PATH=$PATH:~/bin
fi
BOOT
    )> .dockcross

    # now with interpolation
    (cat <<- BOOT
export PACKAGE_NAME=libcrypto-${libcrypto_version}-${os}-${arch}.tar.gz
./Configure ${config_platform} -fPIC no-md2 no-rc5 no-rfc3779 no-sctp no-ssl-trace no-zlib no-hw no-mdc2 no-seed no-idea no-camellia no-bf no-dsa no-ssl3 no-capieng no-unit-test no-tests -DSSL_FORBID_ENULL -DOPENSSL_NO_DTLS1 -DOPENSSL_NO_HEARTBEATS --prefix=/work/opt/openssl --openssldir=/work/opt/openssl
BOOT
    )>> .dockcross
    # No interpolation, expand in the dockcross shell
    # PATH, AR, and CC have to be carefully managed because openssl's configure/make is a little fragile during cross compiles
    (cat <<- "BOOT"
PATH=$PATH:`dirname $CC` make  CC=`basename $CC` AR=`basename $AR` -j
make install_sw
rm -rf /work/opt/openssl/man || true
tar cvzf /work/${PACKAGE_NAME} -C /work/opt/openssl .
BOOT
    )>> .dockcross

    chmod a+x .dockcross
    ../dockcross-${os}-${arch} --args '--privileged' bash -c "echo DONE"
fi

# Upload to S3
aws s3 cp libcrypto-${libcrypto_version}-${os}-${arch}.tar.gz s3://aws-crt-builder/_binaries/libcrypto/libcrypto-${libcrypto_version}-${os}-${arch}.tar.gz
popd
