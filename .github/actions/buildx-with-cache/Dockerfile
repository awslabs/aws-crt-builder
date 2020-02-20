FROM docker:19.03.2

COPY entrypoint.sh /entrypoint.sh

RUN apk add --no-cache bash \
    && apk add --no-cache curl

ENTRYPOINT ["/entrypoint.sh"]