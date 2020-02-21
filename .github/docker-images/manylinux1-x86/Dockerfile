FROM scratch
ADD base.tar /

###############################################################################
# Install builder package
###############################################################################
ADD builder /usr/local/bin/builder
COPY entrypoint.sh /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]