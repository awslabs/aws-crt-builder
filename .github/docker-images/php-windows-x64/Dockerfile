# escape=`

FROM mcr.microsoft.com/windows/servercore:ltsc2019

SHELL ["cmd", "/S", "/C"]

# Download the Build Tools bootstrapper.
ADD https://aka.ms/vs/16/release/vs_buildtools.exe C:\TEMP\vs_buildtools.exe

# Install chocolatey
RUN "%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -InputFormat None -ExecutionPolicy Bypass -Command "iex ((New-Object System.Net.WebClient).DownloadString('https://chocolatey.org/install.ps1'))" && SET "PATH=%PATH%;%ALLUSERSPROFILE%\chocolatey\bin" && `
    choco install -y git 7zip && `
    # install cmake
    choco install cmake --installargs 'ADD_CMAKE_TO_PATH=""System""' -y && `
    # install python
    choco install -y python3 --install-arguments "/InstallDir:C:\\python3 /PrependPath=1" && `
    # update path and test
    refreshenv && `
    git --version && `
    cmake --version && `
    python --version


# Install Build Tools with the Microsoft.VisualStudio.Workload.VCTools workload and VC 15 (2015) build tools
RUN C:\TEMP\vs_buildtools.exe --quiet --wait --norestart --nocache `
    --installPath C:\BuildTools `
    --add Microsoft.VisualStudio.Workload.VCTools `
    --add Microsoft.VisualStudio.Component.VC.140 `
    --add Microsoft.VisualStudio.Component.Windows10SDK.16299 `
    --remove Microsoft.VisualStudio.Component.Windows81SDK `
    || IF "%ERRORLEVEL%"=="3010" EXIT 0

# Install chocolatey
RUN "%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -InputFormat None -ExecutionPolicy Bypass -Command "iex ((New-Object System.Net.WebClient).DownloadString('https://chocolatey.org/install.ps1'))" && SET "PATH=%PATH%;%ALLUSERSPROFILE%\chocolatey\bin" && `
    choco install -y git 7zip && `
    # install cmake
    choco install cmake --installargs 'ADD_CMAKE_TO_PATH=""System""' -y && `
    # install python
    choco install -y python3 --install-arguments "/InstallDir:C:\\python3 /PrependPath=1" && `
    # update path and test
    refreshenv && `
    git --version && `
    cmake --version && `
    python --version

ENTRYPOINT ["powershell.exe", "-NoLogo", "-ExecutionPolicy", "Bypass"]
