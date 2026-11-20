# Changelog

## 0.1.11-5

- Neue Option `custom_services`: eigene Dienste als Zeilen `Name | Ziel | Bedingung`
  (Entität mit `above`/`below`/`state`, oder URL mit `expect`).

## 0.1.11-4

- Token-Weitergabe korrigiert: Der Agent startet eigene Skripte mit gefilterter
  Umgebung, `SUPERVISOR_TOKEN` kam dort nie an. `run.sh` schreibt ihn jetzt nach
  `/data/monitor64-agent/ha.env`, das Skript liest ihn von dort.

## 0.1.11-3

- `homeassistant_api: true`: ohne diese Berechtigung antwortet der Supervisor auf
  `/core/api/` mit 401, alle HA-Checks liefen ins Leere.

## 0.1.11-2

- Mitgelieferte Home-Assistant-Checks: Erreichbarkeit des Core (`/core/api/`), Alter und
  Zustand des letzten automatischen Backups, Größe der Recorder-DB, verfügbare Updates
  (`update.*`-Entitäten) und Integrationen in Fehlerzuständen (Core-Websocket
  `config_entries/get`).
- Optionen `enable_checks`, `enable_api`, `enable_backup_last`, `enable_backup_state`,
  `enable_db`, `enable_updates`, `enable_integrations`; Entitäten
  `entity_backup_last`, `entity_backup_state`, `entity_db_size`; Schwellen
  `backup_warn_h`, `backup_crit_h`, `db_warn_gb`, `db_crit_gb`; Ausnahmen über
  `ignore_integrations` und `watch_entities`.
- `local_scripts` ergänzt die mitgelieferten Checks, statt sie zu ersetzen; `run.sh`
  kopiert beide in den Ordner des Agenten.
- Image: `python3` und `python3-websocket` für den Websocket-Aufruf.

## 0.1.11-1

- Agent auf 0.1.11 (Upstream 1.7.10): eingebetteten Quellbaum auf den Tag-Stand
  gezogen, Patch für den Agent-Root gegen 0.1.11 neu erzeugt.
- Versionierung umgestellt: führende Zahl ist die Agent-Version, was hinter dem
  Bindestrich steht, zählt nur die Add-on-Änderungen.

## 0.1.2-9

- Eingebetteten Agenten auf Upstream-Stand 1.7.0 gezogen (Agent 0.1.6), Patch für den
  Agent-Root gegen 0.1.6 neu erzeugt. Proxy und Optionen unverändert.

## 0.1.2-8

- Erste Veröffentlichung unter der neuen Repository-Adresse; inhaltlich unverändert
  gegenüber 0.1.2-7.

## 0.1.2-7

- Image auf Debian bookworm-slim umgestellt, `systemd` (systemctl) mit installiert;
  `run.sh` legt `/run/systemd/system` an. Damit kann der Agent den systemd-Status des
  HAOS-Hosts über das gemappte D-Bus (`host_dbus`) abfragen. Größe: 44 MB statt 13 MB.

## 0.1.2-6

- Capability `SYS_ADMIN` ergänzt: Bei NVMe-Platten scheitert das Auslesen der
  SMART/Health-Daten mit `NVME_IOCTL_ADMIN_CMD: Permission denied`, weil die
  NVMe-Admin-Kommandos `CAP_SYS_ADMIN` brauchen (`SYS_RAWIO` genügt nur bei SATA/SAT).

## 0.1.2-5

- Capability `SYS_RAWIO` ergänzt: Ohne sie scheitert `smartctl` an SAT-Geräten mit
  „Operation not permitted“ (SG_IO), auch als root im Container. Auf Jibbonator geprüft: mit der
  Capability ändert sich der Fehler von „Operation not permitted“ zu „No such device“
  (QEMU-Platte ohne SAT), die Capability greift also.

## 0.1.2-4

- `SYS_PTRACE` wieder entfernt: Auf HAOS bleibt `/proc/1/root` auch mit der Capability
  gesperrt (geprüft mit SYS_PTRACE, SYS_ADMIN, DAC_READ_SEARCH und SYS_RAWIO; nur ein
  wirklich privilegierter Container kommt durch, `full_access` macht das hier nicht).
- `agent_root` bleibt daher auf dem HAOS-Host leer. Daten wie bei Beszel: alles außer der
  Mount-Liste des Hosts; `fs` zeigt `/data` (die Datenpartition des Hosts).

## 0.1.2-3

- Capability `SYS_PTRACE` ergänzt. `full_access` allein machte den Container nicht
  privilegiert; ohne die Capability scheitert der Zugriff auf `/proc/1/root` mit
  „permission denied“, und mit `agent_root` fehlten CPU, RAM, Load, fs und disk.

## 0.1.2-2

- Agent wird aus dem gepatchten Quellbaum gebaut (`agent-src`, Version `0.1.2+addon`), kein
  Download des Upstream-Releases mehr nötig.
- Neues Startargument `--root` im Agenten; Option `agent_root` gibt die Wurzel für `/proc`,
  `/sys` und Mounts an. Im Container `/proc/1/root` setzen, damit die Dateisysteme und
  Platten des HA-Hosts gelesen werden.

## 0.1.2-1

- Erstes Add-on: Monitor64-Agent (6465) und read-only Docker-Proxy (2376) in einem
  Container.
- Agent-Binary aus dem signierten Release 0.1.2, SHA-256 je Architektur gepinnt.
- Proxy erzeugt CA, Server- und Client-Zertifikat beim ersten Start, gibt JSON und
  SHA-256-Fingerabdruck bei jedem Start im Log aus.
- Nur `GET`/`HEAD` auf `/_ping`, `/version`, `/info`, `/containers/json`,
  `/containers/<id>/json`, `/containers/<id>/stats`.
