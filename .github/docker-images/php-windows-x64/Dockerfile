# escape=`

FROM 123124136734.dkr.ecr.us-east-1.amazonaws.com/aws-crt/vc16-windows-x64:latest

SHELL ["cmd", "/S", "/C"]

ARG VC_MONIKER=vc15
ARG PHP_VER=7.2
ARG PHP_ARCH=x64
ARG PHP_SDK_VER=php-sdk-2.2.0

# Install chocolatey deps
RUN choco install -y --no-progress composer && `
    refreshenv && `
    composer --version

# Install PHP SDK from Microsoft and build PHP to C:\php
RUN git clone https://github.com/Microsoft/php-sdk-binary-tools C:\php-sdk && `
    cd C:\php-sdk && `
    git checkout %PHP_SDK_VER% && `
    "C:\\BuildTools\\Common7\\Tools\\VsDevCmd.bat" && `
    phpsdk-%VC_MONIKER%-%PHP_ARCH%.bat && `
    call phpsdk_buildtree php-%PHP_VER% && `
    git clone https://github.com/php/php-src.git %VC_MONIKER%\%PHP_ARCH%\php-src && cd %VC_MONIKER%\%PHP_ARCH%\php-src && `
    git checkout %PHP_VER% && `
    call phpsdk_deps --update --branch %PHP_VER% && `
    call buildconf && `
    call configure --enable-cli --with-openssl && `
    nmake && `
    nmake install
