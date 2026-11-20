# Monitor64

Add-on für Home Assistant OS mit drei Teilen:

- **Monitor64-Agent** auf Port 6465 (lesend, für Monitor64 gedacht)
- **Docker-Proxy** über TLS auf Port 2376 (read-only Docker-API)
- **Home-Assistant-Checks**, die direkt im Add-on laufen und als eigene Dienste in
  Monitor64 erscheinen

## Voraussetzungen

- Home Assistant OS oder Supervised.
- **Schutzmodus aus** (Add-on-Einstellungen) — nötig für `full_access`, `host_pid` und
  `docker_api`.
- Der HA-Host ist über seine IP erreichbar; Monitor64 verbindet sich über diese Adresse.
- Berechtigungen `homeassistant_api` (HA-Checks) und `docker_api` (Docker-Proxy) sind in
  `config.yaml` gesetzt.

## Installation

1. Im Add-on-Store unter „Repositories“ eintragen:
   `https://github.com/Jibbonator/xkrcwd` — dann `Monitor64` installieren und den
   Schutzmodus ausschalten.
2. In Monitor64 einen Host vom Typ **Agent** anlegen: Adresse = IP-Adresse des HA-Hosts,
   Port 6465, automatische Agent-Updates aus. Die angezeigte Schlüsselzeile in die Option
   `keys` übernehmen, Add-on starten.
3. In Monitor64 „Verbindung testen“ und den SSH-Host-Key per Fingerabdruck bestätigen.
4. Für Docker das Add-on-Log öffnen. Dort stehen `fingerprint=<sha256>` und eine Zeile
   `credentials={"key":…,"cert":…,"ca":…}`. In Monitor64 einen Host vom Typ **Docker**
   anlegen: Adresse `https://<ip-adresse>:2376`, Fingerabdruck festpinnen. Unter
   „Zugangsdaten“ nur das JSON hinter `credentials=` eintragen — ab der öffnenden `{` bis
   zur schließenden `}`, ohne das Wort `credentials`. Testen und bestätigen.

## Wichtig: Dienste werden erkannt, aber nicht automatisch gemeldet

Monitor64 übernimmt nichts von allein. Das gilt besonders für die **Docker-Container**:
Nach dem Anlegen des Docker-Hosts erscheinen sie als neue Dienste, melden aber
standardmäßig nichts. Auf der Host-Seite in Monitor64 die gewünschten Container
übernehmen und „melden“ einschalten (bzw. dauerhaft stumm lassen, wenn nicht gewünscht).

Für Container und Proxmox-Gäste kommt der **Soll-Zustand** dazu: `soll laufen` wertet
einen Stopp als Problem (kritisch), `darf aus sein` lässt ihn zu, `automatisch` nimmt bei
Proxmox-Gästen „beim Booten starten“ als Soll. Das ist unabhängig von „melden“ / „nur
anzeigen“ — Übernehmen, Melden und Soll-Zustand sind drei getrennte Einstellungen.

Gleiches gilt für alle anderen Dienste, inklusive der hier mitgelieferten HA-Checks: erst
nach dem Übernehmen greifen Schwellen und Benachrichtigungen.

## Optionen

### Agent und Docker-Proxy

| Option | Standard | Bedeutung |
|---|---|---|
| `keys` | leer | Öffentliche Schlüssel der Node(s), authorized_keys-Format, eine Zeile je Node. Der Wert hinter `--key` aus dem Installationsbefehl. |
| `local_scripts` | `false` | Zusätzliche eigene Skripte aus `/config/monitor64-agent/local.d/` einbinden (ergänzt die mitgelieferten Checks). |
| `listen` | `:2376` | Adresse des Docker-Proxys, für Bindung an eine IP z. B. `192.168.0.10:2376`. |
| `docker_socket` | `/var/run/docker.sock` | Socket der read-only Docker-API. |
| `agent_port` | `6465` | Port des Agenten. |
| `agent_root` | leer | Wurzel für `/proc`, `/sys` und Mounts. Für den Host `/proc/1/root`, damit Dateisysteme und Platten des HA-Hosts gelesen werden. |

### Home-Assistant-Checks

Alle Checks laufen über die Supervisor-API (`SUPERVISOR_TOKEN`), sind einzeln schaltbar
und erscheinen als eigene Dienste in Monitor64.

| Option | Standard | Bedeutung |
|---|---|---|
| `enable_checks` | `true` | Alle mitgelieferten Checks ab (`false` = keine Dienste). |
| `enable_api` | `true` | Antwortet der HA-Core auf `/core/api/`? |
| `enable_backup_last` | `true` | Alter des letzten erfolgreichen automatischen Backups. |
| `enable_backup_state` | `true` | Zustand des Backup-Managers (Warnung, wenn nicht `idle`). |
| `enable_db` | `true` | Größe der Recorder-Datenbank. |
| `enable_updates` | `true` | Anzahl verfügbarer Updates aus den `update.*`-Entitäten (HA Core, HA OS, Supervisor, Add-ons, HACS/Proxmox). Nur Anzeige, kein Alarm. |
| `enable_integrations` | `true` | Integrationen in `setup_error`, `setup_retry`, `migration_error`, `failed_unload`. |
| `ignore_integrations` | `[]` | Domains oder Titel, die beim Integrations-Check nicht zählen (Groß-/Kleinschreibung egal). |
| `watch_entities` | `[]` | Einzelne Entitäten, die auf `unavailable`/`unknown` geprüft werden. Leer = aus. |
| `custom_services` | `[]` | Eigene Dienste, eine Zeile je Dienst (siehe unten). |
| `entity_backup_last` | `sensor.backup_letztes_erfolgreiches_automatisches_backup` | Entität mit dem Zeitstempel des letzten erfolgreichen Backups (englisch: `sensor.backup_last_successful_automatic_backup`). |
| `entity_backup_state` | `sensor.backup_backup_manager_zustand` | Zustand des Backup-Managers (englisch: `sensor.backup_backup_manager_state`). |
| `entity_db_size` | `sensor.db_size` | Entität mit der DB-Größe in kB (z. B. per Command-Line-Sensor). |
| `backup_warn_h` | `48` | Warnung ab diesem Alter des letzten Backups in Stunden. |
| `backup_crit_h` | `96` | Kritisch ab diesem Alter in Stunden. |
| `db_warn_gb` | `8` | Warnung ab dieser DB-Größe in GB. |
| `db_crit_gb` | `12` | Kritisch ab dieser DB-Größe in GB. |

Der Integrations-Check nutzt den Core-Websocket (`config_entries/get`), weil die REST-API
diesen Zustand nicht liefert; dafür ist `python3-websocket` im Image.

### Eigene Dienste (`custom_services`)

Eine Zeile pro Dienst, Felder durch `|` getrennt, Leerzeichen sind egal. Der Dienst heißt
in Monitor64 `Home Assistant Eigene <Name>`.

| Ziel | Bedingung | Beispielzeile |
|---|---|---|
| Entität | `above warn/crit` | `Kühlschrank \| sensor.fridge_temp \| above 6/8` |
| Entität | `below warn/crit` | `Batterie \| sensor.battery \| below 20/10` |
| Entität | `state wert` | `Leck \| binary_sensor.water_leak \| state on` |
| URL | `expect code` | `HA API \| url http://supervisor/core/api/ \| expect 200` |

Was geht:

- `above`/`below`: Zahlenvergleich mit `warn/crit`, oder nur ein Wert — der gilt dann für
  beide Stufen. `above` schlägt bei größer-gleich an, `below` bei kleiner-gleich.
- Nur Warnung: `above 6/100000` warnt ab 6 und wird praktisch nie kritisch. Bei `below`
  umgekehrt, dort das kritische Limit sehr tief setzen, z. B. `below 20/-100000`.
- Die Reihenfolge zählt: `above 99/6` heißt kritisch ab 6, die 99 ist wirkungslos.
- `state`: Alarm, wenn der Zustand genau dem Wert entspricht (Groß-/Kleinschreibung egal).
- `url`: vollständige URL; `expect` optional, Standard `200`.
- Der Name ist frei, wird Teil des Dienstnamens und darf Umlaute enthalten.

Was nicht geht:

- Mehrere Bedingungen pro Zeile, AND/OR, Regex.
- Vergleiche zwischen zwei Entitäten.
- Attribute, Formatierungen, eigene Tokens für die URL.
- Zustände mit `|` im Wert.

Fehlerverhalten: fehlt die Entität oder ist die Zeile unlesbar, meldet der Dienst Status 3
mit dem Hinweis `Format: Name | Ziel | Bedingung`. Änderungen greifen nach einem Neustart
des Add-ons. Im Add-on-Panel gibt es keinen Hilfetext; Beispiele stehen nur hier.

Zertifikate des Docker-Proxys liegen in `/data/proxy`. Der Fingerabdruck bleibt über
Neustarts gleich, weil sie nur beim ersten Start erzeugt werden.

## Was das Add-on sieht

- **Agent:** lesend CPU, Load, RAM/Swap, Dateisysteme, Platten-I/O, Netz je Port, Bonding,
  Temperaturen, ZFS/mdraid, SMART, systemd-Dienste und eigene Skripte. Nur die Anfragen
  `info`, `collect`, `update`, `keys` — keine Shell.
- **Docker-Proxy:** lesend Container, Status, Health, Neustarts, CPU und RAM. Erlaubt sind
  ausschließlich `GET`/`HEAD` auf `/_ping`, `/version`, `/info`, `/containers/json`,
  `/containers/<id>/json` und `/containers/<id>/stats`; alles andere wird mit 403
  abgewiesen.
- **Home-Assistant-Checks:** lesend über `SUPERVISOR_TOKEN` — `GET /core/api/` und
  `GET /core/api/states/<entity>` für Erreichbarkeit, Backups, DB-Größe und Updates, dazu
  der Websocket-Aufruf `config_entries/get` für Integrationszustände. Keine
  Schreibzugriffe, kein Zugriff auf die Datenbankdatei.

## Grenzen

- Der Agent-Dienst `updates` bleibt leer, weil Home Assistant OS keinen Paketmanager hat.
  HA Core, HA OS, Supervisor und Add-ons deckt der Check `Home Assistant Updates` ab (nur
  Anzeige).
- Ohne `agent_root` sieht der Agent die Mounts des Containers, nicht die des Hosts.
- Ohne gesetzten Fingerabdruck braucht die Docker-Verbindung eine vertraute CA und einen
  passenden Hostnamen; das Add-on erzeugt eine eigene CA, die Monitor64 nur mit
  hinterlegtem Pin akzeptiert.
- Docker-Container und alle anderen Dienste müssen in Monitor64 übernommen und auf
  „melden“ gestellt werden — sonst nur Anzeige, kein Alarm.

## Fehlersuche

| Symptom | Ursache |
|---|---|
| HA-Checks melden Status 3 „Token fehlt“ | `homeassistant_api` fehlt in `config.yaml` oder die Datei `/data/monitor64-agent/ha.env` wurde nicht geschrieben (Add-on neu starten). |
| HA-Checks antworten mit 401 | Berechtigung `homeassistant_api` fehlt im laufenden Container (Add-on aktualisieren). |
| Keine Dienste „Eigene Skripte“ in Monitor64 | `enable_checks` ist `false`, oder die Dienste wurden noch nicht übernommen. |
| Docker-Proxy verbindet nicht | Fingerabdruck nicht gepinnt bzw. Zugangsdaten ohne das JSON hinter `credentials=` eingetragen. |
