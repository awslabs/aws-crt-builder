FROM opensuse/leap:15.2

SHELL ["/bin/bash", "-c"]

RUN zypper refresh && zypper --non-interactive patch
RUN zypper install -y git gcc cmake curl python3 wget
