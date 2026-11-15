# Changelog

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
