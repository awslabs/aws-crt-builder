# This image starts with raspbian/jessie and upgrades it to buster, since there
# are no trustworthy curated buster images. This is then used as a base for our
# downstream images after export via docker save -o
FROM raspbian/jessie as base

SHELL ["/bin/bash", "-c"]
ENV DEBIAN_FRONTEND=noninteractive

###############################################################################
# # Upgrade to buster
###############################################################################
RUN sed -i 's/jessie/buster/' /etc/apt/sources.list \
    && apt-get update -y \
    && apt-get upgrade -y \
    && apt-get dist-upgrade -y \
    && apt-get autoremove -y \
    && apt-get -y purge $(dpkg -l | awk '/^rc/ { print $2 }')

ENTRYPOINT ["/bin/bash"]
