#!/bin/sh
set -eu

OPTS=/data/options.json
DATA=/data/monitor64-agent
PROXYDATA=/data/proxy

opt() {
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

tmp="$DATA/keys.tmp"
: >"$tmp"
if [ -r "$OPTS" ]; then
	jq -r '.keys[]? | select(length > 0)' "$OPTS" >>"$tmp"
fi
chmod 0600 "$tmp"
mv "$tmp" "$DATA/keys"

CHECKS=true
if [ -r "$OPTS" ]; then
	CHECKS=$(jq -r 'if has("enable_checks") then (.enable_checks | tostring) else "true" end' "$OPTS" 2>/dev/null || echo true)
fi

rm -rf "$DATA/local.d"
mkdir -p "$DATA/local.d"
if [ "$CHECKS" = "true" ]; then
	cp /usr/local/share/monitor64/checks/* "$DATA/local.d"/ 2>/dev/null || true
fi
if [ "$LOCAL" = "true" ] && [ -d /config/monitor64-agent/local.d ]; then
	cp /config/monitor64-agent/local.d/* "$DATA/local.d"/ 2>/dev/null || true
fi
chmod 0755 "$DATA/local.d"/* 2>/dev/null || true

mkdir -p /run/systemd/system

monitor64-proxy -listen "$LISTEN" -socket "$SOCKET" -data "$PROXYDATA" &
proxy_pid=$!

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

while kill -0 "$proxy_pid" 2>/dev/null && kill -0 "$agent_pid" 2>/dev/null; do
	sleep 2
done
wait 2>/dev/null || true
echo "monitor64: proxy or agent exited, restarting container" >&2
exit 1
