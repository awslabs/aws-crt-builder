FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

# libc++ and the clang that instruments it must be the same release.
# To bump: set both vars, rebuild, and point CRT jobs at clang-<LLVM_MAJOR>.
# LLVM_MAJOR = apt/binary suffix (clang-19); LLVM_RELEASE = git tag (llvmorg-<x.y.z>).
ARG LLVM_MAJOR=19
ARG LLVM_RELEASE=19.1.7

###############################################################################
# Install prereqs
###############################################################################
RUN apt-get update -qq \
    && apt-get -y install \
    git \
    curl \
    sudo \
    unzip \
    python3-dev \
    python3-pip \
    build-essential \
    ninja-build \
    # For PPAs
    software-properties-common \
    apt-transport-https \
    ca-certificates \
    golang-go \
    && apt-get clean

###############################################################################
# Python/AWS CLI
###############################################################################
WORKDIR /tmp

RUN python3 -m pip install setuptools \
    && curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o awscliv2.zip \
    && unzip awscliv2.zip \
    && sudo aws/install \
    && aws --version

###############################################################################
# Install clang from the LLVM apt repository
###############################################################################
RUN curl -sSL https://apt.llvm.org/llvm.sh -o llvm.sh \
    && chmod +x llvm.sh \
    && ./llvm.sh ${LLVM_MAJOR} \
    && apt-get clean \
    && rm -f llvm.sh

###############################################################################
# Build a MemorySanitizer-instrumented libc++/libc++abi at /opt/libcxx-msan.
#
# MSan needs the whole program instrumented, including the C++ runtime; a distro
# libc++ yields false positives. Consumers link this via LIBCXX_MSAN_ROOT.
#
# Modern CMake (not the old one other images pin) is needed for recent LLVM.
#
# CMake options:
#   LLVM_ENABLE_RUNTIMES            libunwind is deliberately excluded: MSan calls
#                                   the unwinder to print reports, so instrumenting
#                                   it recurses into MSan until the stack overflows.
#   LIBCXXABI_USE_LLVM_UNWINDER=OFF don't require/link the (unbuilt) LLVM unwinder;
#                                   the system unwinder is linked by consumers.
###############################################################################
RUN curl -sSL https://github.com/Kitware/CMake/releases/download/v3.29.6/cmake-3.29.6-linux-x86_64.tar.gz -o cmake.tar.gz \
    && tar xzf cmake.tar.gz -C /usr/local --strip-components=1 \
    && rm -f cmake.tar.gz \
    && cmake --version \
    && git clone --depth=1 --branch llvmorg-${LLVM_RELEASE} https://github.com/llvm/llvm-project /tmp/llvm-project \
    && cmake -G Ninja -S /tmp/llvm-project/runtimes -B /tmp/llvm-msan-build \
        -DCMAKE_BUILD_TYPE=Release \
        -DCMAKE_C_COMPILER=clang-${LLVM_MAJOR} \
        -DCMAKE_CXX_COMPILER=clang++-${LLVM_MAJOR} \
        -DLLVM_ENABLE_RUNTIMES="libcxx;libcxxabi" \
        -DLLVM_USE_SANITIZER=MemoryWithOrigins \
        -DLIBCXXABI_USE_LLVM_UNWINDER=OFF \
        -DLIBCXX_INCLUDE_TESTS=OFF \
        -DLIBCXXABI_INCLUDE_TESTS=OFF \
        -DCMAKE_INSTALL_PREFIX=/opt/libcxx-msan \
    && cmake --build /tmp/llvm-msan-build --target install-cxx install-cxxabi \
    && rm -rf /tmp/llvm-project /tmp/llvm-msan-build

ENV LIBCXX_MSAN_ROOT=/opt/libcxx-msan

###############################################################################
# MSan toolchain file (consumers pass -DCMAKE_TOOLCHAIN_FILE=/opt/msan-toolchain.cmake).
# Keeps the MSan flags next to the libc++ they target. *_INIT lets the project
# append its own flags.
###############################################################################
RUN printf '%s\n' \
    'set(CMAKE_C_FLAGS_INIT "-fsanitize=memory -fsanitize-memory-track-origins=2")' \
    'set(CMAKE_CXX_FLAGS_INIT "-fsanitize=memory -fsanitize-memory-track-origins=2 -nostdinc++ -isystem /opt/libcxx-msan/include/c++/v1")' \
    'set(CMAKE_EXE_LINKER_FLAGS_INIT "-fsanitize=memory -nostdlib++ -L/opt/libcxx-msan/lib -Wl,-rpath,/opt/libcxx-msan/lib -lc++ -lc++abi -lgcc_s")' \
    > /opt/msan-toolchain.cmake

###############################################################################
# Install entrypoint
###############################################################################
ADD entrypoint.sh /usr/local/bin/builder
RUN chmod a+x /usr/local/bin/builder
ENTRYPOINT ["/usr/local/bin/builder"]