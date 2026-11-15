# Monitor64-Add-on: Agent aus dem gepatchten Quellbaum, Proxy aus dem Quellcode.
# Bewusst kein BUILD_FROM und kein S6-Overlay: das Add-on braucht host_pid, und S6
# vertraegt sich damit nicht. Debian statt Alpine, weil systemctl fuer den systemd-Status
# des Hosts gebraucht wird (Alpine hat kein systemd).

FROM golang:1.27-alpine AS agentbuild
WORKDIR /src
COPY agent-src/go.mod agent-src/go.sum ./
RUN go mod download
COPY agent-src/ ./
ARG AGENT_VERSION=0.1.6+addon
RUN CGO_ENABLED=0 go build -trimpath -ldflags "-s -w -X main.Version=${AGENT_VERSION}" \
      -o /out/monitor64-agent ./cmd/monitor64-agent

FROM golang:1.27-alpine AS proxybuild
WORKDIR /src
COPY proxy/go.mod proxy/main.go ./
RUN CGO_ENABLED=0 go build -trimpath -ldflags "-s -w" -o /out/monitor64-proxy .

FROM debian:bookworm-slim

ARG BUILD_ARCH=amd64
ARG BUILD_VERSION=0.0.0

LABEL io.hass.version="${BUILD_VERSION}" \
      io.hass.type="app" \
      io.hass.arch="${BUILD_ARCH}"

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      ca-certificates jq smartmontools systemd \
 && rm -rf /var/lib/apt/lists/*

COPY --from=agentbuild /out/monitor64-agent /usr/local/bin/monitor64-agent
COPY --from=proxybuild /out/monitor64-proxy /usr/local/bin/monitor64-proxy
COPY run.sh /run.sh
RUN chmod 0755 /run.sh

ENTRYPOINT ["/run.sh"]

