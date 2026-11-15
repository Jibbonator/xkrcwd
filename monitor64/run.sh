#!/bin/sh
# Startet den Monitor64-Agenten im Vordergrund und den Docker-Proxy daneben.
# Kein S6, kein systemd: der Container ist PID 1, beide Prozesse laufen als root.
set -eu

OPTS=/data/options.json
DATA=/data/monitor64-agent
PROXYDATA=/data/proxy

opt() { # opt <jq-ausdruck> <standard>
	if [ -r "$OPTS" ]; then
		v=$(jq -r "$1 // empty" "$OPTS" 2>/dev/null || true)
		[ -n "$v" ] && { printf '%s' "$v"; return; }
	fi
	printf '%s' "$2"
}

LISTEN=$(opt '.listen' ':2376')
SOCKET=$(opt '.docker_socket' '/var/run/docker.sock')
PORT=$(opt '.agent_port' '6465')
ROOT=$(opt '.agent_root' '')
LOCAL=$(opt '.local_scripts' 'false')

mkdir -p "$DATA" "$PROXYDATA"
chmod 0700 "$DATA" "$PROXYDATA"

# Schluessel aus den Add-on-Optionen (authorized_keys-Format, eine Zeile je Node).
tmp="$DATA/keys.tmp"
: >"$tmp"
if [ -r "$OPTS" ]; then
	jq -r '.keys[]? | select(length > 0)' "$OPTS" >>"$tmp"
fi
chmod 0600 "$tmp"
mv "$tmp" "$DATA/keys"

# Eigene Skripte: nur wenn ausdruecklich eingeschaltet, aus dem HA-Konfigurationsordner.
if [ "$LOCAL" = "true" ] && [ -d /config ]; then
	rm -rf "$DATA/local.d"
	ln -s /config/monitor64-agent/local.d "$DATA/local.d"
fi

# systemd-Status: der Agent prueft /run/systemd/system und ruft systemctl auf. Im Container
# fehlt der Ordner; systemctl redet ueber /run/dbus mit dem Host-systemd (host_dbus).
mkdir -p /run/systemd/system

# Docker-Proxy: TLS-Ende vor der read-only Docker-API, dauerhaft im Hintergrund.
monitor64-proxy -listen "$LISTEN" -socket "$SOCKET" -data "$PROXYDATA" &
proxy_pid=$!

# Agent: laeuft im Vordergrund, --root nur wenn gesetzt (Agent >= 0.1.3).
if [ -n "$ROOT" ]; then
	monitor64-agent run --dir "$DATA" --port "$PORT" --root "$ROOT" &
else
	monitor64-agent run --dir "$DATA" --port "$PORT" &
fi
agent_pid=$!

stop() {
	kill "$proxy_pid" "$agent_pid" 2>/dev/null || true
	wait 2>/dev/null || true
	exit 0
}
trap stop TERM INT

# Stirbt einer der beiden, beendet sich der Container und der Supervisor startet ihn neu.
while kill -0 "$proxy_pid" 2>/dev/null && kill -0 "$agent_pid" 2>/dev/null; do
	sleep 2
done
wait 2>/dev/null || true
echo "monitor64: proxy or agent exited, restarting container" >&2
exit 1
