#!/bin/sh
# Startet Node64. Der Supervisor legt /data als root an, Node64 laeuft als 65532 –
# deshalb uebergibt dieses Skript das Verzeichnis und wechselt dann den Benutzer.
set -eu

OPTS=/data/options.json

opt() { # opt <jq-ausdruck> <standard>
	if [ -r "$OPTS" ]; then
		v=$(jq -r "$1 // empty" "$OPTS" 2>/dev/null || true)
		[ -n "$v" ] && { printf '%s' "$v"; return; }
	fi
	printf '%s' "$2"
}

LOG_LEVEL=$(opt '.log_level' 'info')
ADMIN_USER=$(opt '.admin_user' '')
ADMIN_PASSWORD=$(opt '.admin_password' '')

export NODE64_LOG_LEVEL="$LOG_LEVEL"
[ -n "$ADMIN_USER" ] && export NODE64_ADMIN_USER="$ADMIN_USER"
[ -n "$ADMIN_PASSWORD" ] && export NODE64_ADMIN_PASSWORD="$ADMIN_PASSWORD"

mkdir -p "$NODE64_DATA_DIR"
chown 65532:65532 "$NODE64_DATA_DIR"

# Selbst-Update bleibt aus (Standard von Node64): das Image gehoert dem Supervisor.
exec su-exec 65532:65532 /usr/local/bin/node64
