#!/usr/bin/env python3
import datetime
import json
import os
import urllib.error
import urllib.request

BASE = os.environ.get("SUPERVISOR_URL", "http://supervisor")
TOKEN = os.environ.get("SUPERVISOR_TOKEN", "")
OPTS = "/data/options.json"
TOKEN_FILE = "/data/monitor64-agent/ha.env"

try:
    import websocket
except ImportError:
    websocket = None


def token():
    if TOKEN:
        return TOKEN
    try:
        with open(TOKEN_FILE) as f:
            for line in f:
                if line.startswith("SUPERVISOR_TOKEN="):
                    return line.split("=", 1)[1].strip()
    except Exception:
        return ""
    return ""


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


def grace_min():
    try:
        return float(opt("grace_min", 10))
    except Exception:
        return 10.0


def in_grace(st):
    # Solange eine Entitaet kuerzer als grace_min auf unavailable/unknown steht, noch kein Alarm.
    try:
        ts = datetime.datetime.fromisoformat(str(st.get("last_changed", "")).replace("Z", "+00:00"))
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=datetime.timezone.utc)
        now = datetime.datetime.now(datetime.timezone.utc)
        return (now - ts.astimezone(datetime.timezone.utc)).total_seconds() < grace_min() * 60.0
    except Exception:
        return False


def http(path, timeout=4):
    req = urllib.request.Request(BASE + path, headers={"Authorization": "Bearer " + token()})
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


def check_backup_last():
    warn = opt("backup_warn_h", 48)
    crit = opt("backup_crit_h", 96)
    st = entity(str(opt("entity_backup_last", "sensor.backup_letztes_erfolgreiches_automatisches_backup")))
    if st is None:
        return
    state = str(st.get("state", ""))
    if state in ("unavailable", "unknown"):
        if in_grace(st):
            emit(0, "Home Assistant Backup Alter", None)
        else:
            emit(3, "Home Assistant Backup Alter", ["age=0"])
        return
    age = None
    try:
        ts = datetime.datetime.fromisoformat(state.replace("Z", "+00:00"))
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
        return
    state = str(st.get("state", ""))
    if state in ("unavailable", "unknown"):
        if in_grace(st):
            emit(0, "Home Assistant Backup Zustand", None)
        else:
            emit(3, "Home Assistant Backup Zustand", ["busy=0"])
        return
    busy = 0 if state == "idle" else 1
    emit(0 if busy == 0 else 1, "Home Assistant Backup Zustand", ["busy=%d" % busy])


def check_db():
    warn = opt("db_warn_gb", 8)
    crit = opt("db_crit_gb", 12)
    st = entity(str(opt("entity_db_size", "sensor.db_size")))
    if st is None:
        return
    state = str(st.get("state", ""))
    if state in ("unavailable", "unknown"):
        if in_grace(st):
            emit(0, "Home Assistant DB Groesse GB", None)
        else:
            emit(3, "Home Assistant DB Groesse GB", ["gb=0"])
        return
    try:
        kb = float(state)
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
    if websocket is None or not token():
        return None
    url = BASE.replace("https://", "wss://").replace("http://", "ws://") + "/core/websocket"
    try:
        ws = websocket.create_connection(url, timeout=8)
        msg = json.loads(ws.recv())
        if msg.get("type") == "auth_required":
            ws.send(json.dumps({"type": "auth", "access_token": token()}))
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


def check_custom():
    for raw in (opt("custom_services", []) or []):
        raw = str(raw).strip()
        if not raw:
            continue
        parts = [p.strip() for p in raw.split("|")]
        name = parts[0] if parts else ""
        label = "Home Assistant Eigene " + (name if name else "Zeile")
        valid = len(parts) >= 3 and name != "" and parts[1] != ""
        if not valid:
            emit(3, label, None, "Format: Name | Ziel | Bedingung")
            continue
        target = parts[1]
        conds = parts[2:]
        if target.lower().startswith("url "):
            url = target[4:].strip()
            expect = 200
            for c in conds:
                low = c.lower()
                if low.startswith("expect "):
                    try:
                        expect = int(c.split(" ", 1)[1])
                    except Exception:
                        expect = -1
            code = 0
            try:
                with urllib.request.urlopen(url, timeout=4) as r:
                    code = r.status
            except urllib.error.HTTPError as e:
                code = e.code
            except Exception:
                code = 0
            emit(0 if code == expect else 2, label, ["code=%d" % code])
            continue
        st = entity(target)
        if st is None:
            continue
        state = str(st.get("state", ""))
        for c in conds:
            low = c.lower()
            if low.startswith("state "):
                want = c.split(" ", 1)[1].strip().lower()
                bad = state.lower() == want
                emit(0 if not bad else 2, label, ["ok=%d" % (0 if bad else 1)])
                break
            if low.startswith("above ") or low.startswith("below "):
                mode = low.split(" ")[0]
                vals = c.split(" ", 1)[1].replace("/", " ").split()
                try:
                    warn = float(vals[0])
                    crit = float(vals[1]) if len(vals) > 1 else warn
                except Exception:
                    emit(3, label, None, "Bedingung unlesbar")
                    break
                if state.lower() in ("unavailable", "unknown"):
                    if in_grace(st):
                        emit(0, label, None)
                    else:
                        emit(3, label, ["value=0"])
                    break
                try:
                    v = float(state)
                except Exception:
                    emit(3, label, ["value=0"])
                    break
                if mode == "above":
                    emit("P", label, ["value=%.2f;%s;%s" % (v, warn, crit)])
                else:
                    emit("P", label, ["value=%.2f;%s:;%s:" % (v, warn, crit)])
                break
        else:
            emit(3, label, None, "Bedingung fehlt")


def check_watch():
    for eid in (opt("watch_entities", []) or []):
        eid = str(eid)
        if not eid:
            continue
        st = entity(eid)
        name = "Home Assistant Entitaet " + eid
        if st is None:
            continue
        bad = str(st.get("state", "")) in ("unavailable", "unknown")
        if bad and in_grace(st):
            emit(0, name, None)
            continue
        emit(0 if not bad else 2, name, ["ok=%d" % (0 if bad else 1)])


def main():
    if not token():
        emit(3, "Home Assistant Token", None, "SUPERVISOR_TOKEN fehlt")
        return
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
    check_custom()
    check_watch()


if __name__ == "__main__":
    main()
