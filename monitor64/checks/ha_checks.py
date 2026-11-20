#!/usr/bin/env python3
import datetime
import json
import os
import urllib.error
import urllib.request

BASE = os.environ.get("SUPERVISOR_URL", "http://supervisor")
TOKEN = os.environ.get("SUPERVISOR_TOKEN", "")
OPTS = "/data/options.json"

try:
    import websocket
except ImportError:
    websocket = None


def options():
    try:
        with open(OPTS) as f:
            return json.load(f)
    except Exception:
        return {}


OPT = options()


def opt(name, default):
    v = OPT.get(name, default)
    if v is None:
        return default
    if isinstance(v, str) and v == "":
        return default
    return v


def http(path, timeout=4):
    req = urllib.request.Request(BASE + path, headers={"Authorization": "Bearer " + TOKEN})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception:
        return 0, ""


def entity(eid):
    code, body = http("/core/api/states/" + eid)
    if code != 200:
        return None
    try:
        return json.loads(body)
    except Exception:
        return None


def emit(status, name, metrics=None, text=None):
    line = '%s "%s" %s' % (status, name, "|".join(metrics) if metrics else "-")
    if text:
        line = line + " " + text
    print(line)


def check_api():
    code, body = http("/core/api/")
    ok = code == 200 and "API running" in body
    emit(0 if ok else 2, "Home Assistant API", ["ok=%d" % (1 if ok else 0)])


def check_backup_last():
    warn = opt("backup_warn_h", 48)
    crit = opt("backup_crit_h", 96)
    st = entity(str(opt("entity_backup_last", "sensor.backup_letztes_erfolgreiches_automatisches_backup")))
    age = None
    if st is not None:
        try:
            ts = datetime.datetime.fromisoformat(str(st.get("state", "")).replace("Z", "+00:00"))
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=datetime.timezone.utc)
            now = datetime.datetime.now(datetime.timezone.utc)
            age = (now - ts.astimezone(datetime.timezone.utc)).total_seconds() / 3600.0
        except Exception:
            age = None
    if age is None:
        emit(3, "Home Assistant Backup Alter", ["age=0"])
    else:
        emit("P", "Home Assistant Backup Alter", ["age=%.1f;%s;%s" % (age, warn, crit)])


def check_backup_state():
    st = entity(str(opt("entity_backup_state", "sensor.backup_backup_manager_zustand")))
    if st is None:
        emit(3, "Home Assistant Backup Zustand", ["busy=0"])
    else:
        busy = 0 if str(st.get("state", "")) == "idle" else 1
        emit(0 if busy == 0 else 1, "Home Assistant Backup Zustand", ["busy=%d" % busy])


def check_db():
    warn = opt("db_warn_gb", 8)
    crit = opt("db_crit_gb", 12)
    st = entity(str(opt("entity_db_size", "sensor.db_size")))
    if st is None:
        emit(3, "Home Assistant DB Groesse GB", ["gb=0"])
        return
    try:
        kb = float(st.get("state"))
    except Exception:
        emit(3, "Home Assistant DB Groesse GB", ["gb=0"])
        return
    emit("P", "Home Assistant DB Groesse GB", ["gb=%.2f;%s;%s" % (kb / 1048576.0, warn, crit)])


def check_updates():
    code, body = http("/core/api/states")
    pending = 0
    if code == 200:
        try:
            for st in json.loads(body):
                if str(st.get("entity_id", "")).startswith("update.") and str(st.get("state", "")) == "on":
                    pending += 1
        except Exception:
            pending = 0
    emit(0, "Home Assistant Updates", ["pending=%d" % pending])


def ws_entries():
    if websocket is None or not TOKEN:
        return None
    url = BASE.replace("https://", "wss://").replace("http://", "ws://") + "/core/websocket"
    try:
        ws = websocket.create_connection(url, timeout=8)
        msg = json.loads(ws.recv())
        if msg.get("type") == "auth_required":
            ws.send(json.dumps({"type": "auth", "access_token": TOKEN}))
            msg = json.loads(ws.recv())
        if msg.get("type") != "auth_ok":
            ws.close()
            return None
        ws.send(json.dumps({"id": 1, "type": "config_entries/get"}))
        res = json.loads(ws.recv())
        ws.close()
        if res.get("success") is not True:
            return None
        return res.get("result")
    except Exception:
        return None


def check_integrations():
    entries = ws_entries()
    if entries is None:
        emit(3, "Home Assistant Integrationen", ["failed=0"])
        return
    ignore = set(str(x).lower() for x in (opt("ignore_integrations", []) or []))
    failed = []
    for e in entries:
        if e.get("disabled_by"):
            continue
        if str(e.get("source", "")) == "ignore":
            continue
        if str(e.get("state", "")) in ("setup_error", "migration_error", "setup_retry", "failed_unload"):
            if str(e.get("domain", "")).lower() in ignore or str(e.get("title", "")).lower() in ignore:
                continue
            failed.append(e)
    emit(0 if not failed else 2, "Home Assistant Integrationen", ["failed=%d" % len(failed)])


def check_watch():
    for eid in (opt("watch_entities", []) or []):
        eid = str(eid)
        if not eid:
            continue
        st = entity(eid)
        name = "Home Assistant Entitaet " + eid
        if st is None:
            emit(3, name, ["ok=0"])
            continue
        bad = str(st.get("state", "")) in ("unavailable", "unknown")
        emit(0 if not bad else 2, name, ["ok=%d" % (0 if bad else 1)])


def main():
    if not TOKEN:
        emit(3, "Home Assistant Token", None, "SUPERVISOR_TOKEN fehlt")
        return
    if opt("enable_api", True):
        check_api()
    if opt("enable_backup_last", True):
        check_backup_last()
    if opt("enable_backup_state", True):
        check_backup_state()
    if opt("enable_db", True):
        check_db()
    if opt("enable_updates", True):
        check_updates()
    if opt("enable_integrations", True):
        check_integrations()
    check_watch()


if __name__ == "__main__":
    main()
