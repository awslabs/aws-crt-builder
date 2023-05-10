FROM openwrt/rootfs

# for some reason this directory isn't created by this point and we need it
RUN mkdir -p /var/lock
RUN mkdir -p /usr/local/bin

RUN opkg update

# packages in openwrt
RUN opkg install git-http ca-bundle curl python3 python3-pip gcc make bash sudo

# packages we have to get from alpine

# first, pull apk directly
RUN wget http://dl-cdn.alpinelinux.org/alpine/v3.16/main/x86_64/apk-tools-static-2.12.9-r3.apk
RUN tar -xzf apk-tools-static-2.12.9-r3.apk

# next, install stuff that either
#  (1) isn't in openwrt and we don't want to build ourselves (cmake, maven)
#  (2) appears to be broken (python3-awscli)
#
# Under normal circumstances, we let the repository (via builder.json and custom actions) guide the language runtime installation, but since
#  (1) openwrt does not have many runtimes in its package manager (and tools like maven that depend on those runtimes)
#  (2) we are only doing openwrt CI checks for Java
# we install the desired JDK here as well.
#
RUN ./sbin/apk.static -X http://dl-cdn.alpinelinux.org/alpine/v3.16/main -X http://dl-cdn.alpinelinux.org/alpine/v3.16/community -U --allow-untrusted --initdb add cmake openjdk8 maven aws-cli

# stub libraries for stuff we unconditionally link; functionality is all actually in musl already
# long term we might want to make our recognition better, but this is a blocker for the s2n build 
RUN ar -rc /usr/lib/libpthread.a
RUN ar -rc /usr/lib/libdl.a
RUN ar -rc /usr/lib/librt.a
RUN ar -rc /usr/lib/libm.a

###############################################################################
# Install entrypoint
###############################################################################
ADD entrypoint.sh /usr/local/bin/builder
RUN chmod a+x /usr/local/bin/builder
ENTRYPOINT ["/usr/local/bin/builder"]