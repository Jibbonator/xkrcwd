# Node64 als Home-Assistant-App.
#
# Das Upstream-Image ist "FROM scratch" mit ENTRYPOINT /node64 und User 65532 –
# darin laesst sich weder /data uebernehmen noch ein Startskript ergaenzen.
# Deshalb eine schlanke Huelle: feste Alpine-Basis, das Binary per COPY aus dem
# offiziellen Image, /data beim Start dem Benutzer 65532 uebergeben.
#
# Die Zeile mit ghcr.io und "version" in config.yaml gehoeren zusammen und werden
# beim Update gemeinsam gesetzt.

FROM alpine:3.22

ARG BUILD_ARCH=amd64
ARG BUILD_VERSION=0.0.0

RUN apk add --no-cache ca-certificates jq su-exec libcap

COPY --from=ghcr.io/ipv64net/node64:1.7.10 /node64 /usr/local/bin/node64
RUN setcap cap_net_bind_service,cap_net_raw=+p /usr/local/bin/node64

COPY run.sh /run.sh
RUN chmod 0755 /run.sh

ENV NODE64_DATA_DIR=/data \
    NODE64_HTTP_PORT=8080

LABEL io.hass.version="${BUILD_VERSION}" \
      io.hass.type="app" \
      io.hass.arch="${BUILD_ARCH}"

ENTRYPOINT ["/run.sh"]
