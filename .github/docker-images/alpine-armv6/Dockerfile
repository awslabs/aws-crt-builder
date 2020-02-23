FROM scratch
ADD base.tar /

###############################################################################
# Install builder package
###############################################################################
ADD builder /usr/local/bin/builder.pyz
COPY entrypoint.sh /usr/local/bin/builder
CMD ["/bin/sh", "-c"]
