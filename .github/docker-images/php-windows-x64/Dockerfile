# escape=`

FROM mcr.microsoft.com/windows/servercore:ltsc2019

SHELL ["cmd", "/S", "/C"]

ARG VC_VER=vc14
ARG PHP_VER=7.2
ARG ARCH=x64
ARG PHP_SDK_VER=php-sdk-2.2.0

# Install chocolatey
ADD https://chocolatey.org/install.ps1 C:\TEMP\install_choco.ps1
RUN powershell.exe -NoProfile -InputFormat None -ExecutionPolicy Bypass -Command "C:\TEMP\install_choco.ps1" && SET "PATH=%PATH%;%ALLUSERSPROFILE%\chocolatey\bin" && `
    choco install -y --no-progress git 7zip && `
    # install cmake
    choco install -y --no-progress cmake --installargs 'ADD_CMAKE_TO_PATH=""System""' && `
    # install python
    choco install -y --no-progress python3 --install-arguments "/InstallDir:C:\\python3 /PrependPath=1" && `
    # update path and test
    refreshenv && `
    git --version && `
    cmake --version && `
    python --version


# Install Build Tools with the Microsoft.VisualStudio.Workload.VCTools workload and VC 14 (2015) build tools
# Download the Build Tools bootstrapper.
ADD https://aka.ms/vs/16/release/vs_buildtools.exe C:\TEMP\vs_buildtools.exe
RUN C:\TEMP\vs_buildtools.exe --quiet --wait --norestart --nocache `
    --installPath C:\BuildTools `
    --add Microsoft.VisualStudio.Workload.VCTools `
    --add Microsoft.VisualStudio.Component.VC.140 `
    --add Microsoft.VisualStudio.Component.Windows10SDK.16299 `
    --remove Microsoft.VisualStudio.Component.Windows81SDK `
    || IF "%ERRORLEVEL%"=="3010" EXIT 0

# Install PHP SDK from Microsoft
RUN git clone https://github.com/Microsoft/php-sdk-binary-tools C:\php-sdk && `
    cd C:\php-sdk && `
    git checkout %PHP_SDK_VER% && `
    phpsdk-%VC_VER%-%ARCH%.bat && `
    phpsdk_buildtree phpdev && `
    git clone https://github.com/php/php-src.git %VC_VER%\%ARCH%\php-src && cd %VC_VER%\%ARCH%\php-src && `
    phpsdk_deps --update --branch %PHP_VER% && `
    buildconf && configure --enable-cli && nmake

ENTRYPOINT ["powershell.exe", "-NoLogo", "-ExecutionPolicy", "Bypass"]
