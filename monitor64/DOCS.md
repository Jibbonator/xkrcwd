# Monitor64

Ein Add-on für Home Assistant OS: Monitor64-Agent als SSH-Dienst auf Port 6465, ein
read-only Docker-API-Proxy über TLS auf Port 2376 und fest eingebaute Checks für Home
Assistant selbst (Erreichbarkeit, Backups, Recorder-DB, Updates, Integrationen).

## Voraussetzungen

- Home Assistant OS oder Supervised.
- **Schutzmodus aus** (Einstellungen des Add-ons): nötig für `full_access`, `host_pid` und
  `docker_api`.
- Der HA-Host ist über IP erreichbar; Monitor64 verbindet sich über die IP-Adresse.
- Das Add-on nutzt die Berechtigungen `homeassistant_api` (HA-Checks) und `docker_api`
  (Docker-Proxy); beide stehen in `config.yaml`.

## Optionen

| Option | Standard | Bedeutung |
|---|---|---|
| `keys` | leer | Öffentliche Schlüssel der Node(s) im authorized_keys-Format, eine Zeile je Node. Genau der Wert hinter `--key` aus dem Installationsbefehl von Monitor64. |
| `local_scripts` | `false` | Zusätzliche eigene Skripte aus `/config/monitor64-agent/local.d/` einbinden (neben den mitgelieferten HA-Checks). |
| `listen` | `:2376` | Adresse des Docker-Proxys. Für Bindung an eine bestimmte IP z. B. `192.168.0.10:2376`. |
| `docker_socket` | `/var/run/docker.sock` | Socket der read-only Docker-API. |
| `agent_port` | `6465` | Port des Agenten. |
| `agent_root` | leer | Wurzel für `/proc`, `/sys` und Mounts. Für den Host `/proc/1/root` — damit die Dateisysteme und Platten des HA-Hosts gelesen werden. |

### Home-Assistant-Checks

Die mitgelieferten Checks laufen über die Supervisor-API (`SUPERVISOR_TOKEN`) und melden
als eigene Dienste in Monitor64. Jeder Check lässt sich einzeln abschalten.

| Option | Standard | Bedeutung |
|---|---|---|
| `enable_checks` | `true` | Alle mitgelieferten Checks aus (`false` = keine Dienste). |
| `enable_api` | `true` | Prüft, ob der HA-Core über `/core/api/` antwortet. |
| `enable_backup_last` | `true` | Alter des letzten erfolgreichen automatischen Backups. |
| `enable_backup_state` | `true` | Zustand des Backup-Managers (Warnung, wenn nicht `idle`). |
| `enable_db` | `true` | Größe der Recorder-Datenbank. |
| `enable_updates` | `true` | Anzahl verfügbarer Updates aus den `update.*`-Entitäten, also HA Core, HA OS, Supervisor und Add-ons (nur Anzeige). |
| `enable_integrations` | `true` | Config Entries in `setup_error`, `setup_retry`, `migration_error`, `failed_unload`. |
| `watch_entities` | `[]` | Liste einzelner Entitäten, die auf `unavailable`/`unknown` geprüft werden (leer = aus). |
| `custom_services` | `[]` | Eigene Dienste, eine Zeile je Dienst im Format `Name | Ziel | Bedingung` (siehe unten). |
| `ignore_integrations` | `[]` | Domain oder Titel von Integrationen, die beim Integrations-Check nicht zählen (Groß-/Kleinschreibung egal). |
| `entity_backup_last` | `sensor.backup_letztes_erfolgreiches_automatisches_backup` | Entität mit dem Zeitstempel des letzten erfolgreichen Backups (auf englischen Installationen `sensor.backup_last_successful_automatic_backup`). |
| `entity_backup_state` | `sensor.backup_backup_manager_zustand` | Zustand des Backup-Managers (`sensor.backup_backup_manager_state`). |
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

- `above`/`below`: Zahlenvergleich, `warn/crit` oder nur `warn` (dann gilt sie auch für kritisch).
  `above` schlägt bei größer-gleich an, `below` bei kleiner-gleich.
- Nur Warnung oder nur kritisch: `above 6/100000` warnt ab 6 und wird praktisch nie
  kritisch; bei `below` umgekehrt, dort das kritische Limit sehr tief setzen, z. B.
  `below 20/-100000`.
- Die Reihenfolge zählt: `above 99/6` heißt kritisch ab 6, die 99 ist dann wirkungslos.
- `state`: Alarm, wenn der Zustand genau dem Wert entspricht (Groß-/Kleinschreibung egal).
- `url`: vollständige URL; `expect` ist optional, Standard `200`.
- Der Name ist frei; er wird Teil des Dienstnamens und darf Umlaute enthalten.

Was nicht geht:

- Mehrere Bedingungen pro Zeile oder Logik wie AND/OR/Regex.
- Vergleiche zwischen zwei Entitäten.
- Formatierungen, Suche in Attributen, Authentifizierung mit eigenen Tokens.
- Zustände mit `|` im Wert.

Fehlerverhalten: fehlt die Entität oder ist die Zeile unlesbar, meldet der Dienst Status 3
mit dem Hinweis `Format: Name | Ziel | Bedingung`. Änderungen greifen nach einem Neustart
des Add-ons.

## Einrichtung

1. Im Add-on-Store unter „Repositories“ diese URL eintragen:
   `https://github.com/Jibbonator/xkrcwd` — danach `Monitor64` installieren und den
   Schutzmodus ausschalten.
2. In Monitor64 einen Host vom Typ Agent anlegen: Adresse = IP-Adresse des
   HA-Hosts, Port 6465, automatische Agent-Updates aus. Die angezeigte Schlüsselzeile in
   `keys` übernehmen, Add-on starten.
3. In Monitor64 „Verbindung testen“ und den SSH-Host-Key per Fingerabdruck bestätigen.
4. Für Docker das Add-on-Log öffnen. Dort stehen `fingerprint=<sha256>` und eine Zeile
   `credentials={"key":…,"cert":…,"ca":…}`. In Monitor64 einen Host vom Typ Docker
   anlegen: Adresse `https://<ip-adresse>:2376`, Fingerabdruck festpinnen. Unter
   „Zugangsdaten“ nur das JSON hinter `credentials=` eintragen — also ab der öffnenden
   `{` bis zur schließenden `}`, ohne das Wort `credentials`. Dann testen und bestätigen.

Der Fingerabdruck bleibt über Neustarts gleich, weil die Zertifikate in `/data/proxy`
liegen. Sie werden nur erzeugt, wenn sie fehlen.

## Was das Add-on sieht

- Agent: lesend CPU, Load, RAM/Swap, Dateisysteme, Platten-I/O, Netz je Port, Bonding,
  Temperaturen, ZFS/mdraid, SMART, systemd-Dienste und eigene Skripte. Nur die vier
  Anfragen `info`, `collect`, `update`, `keys`, keine Shell.
- Docker-Proxy: lesend Container, Status, Health, Neustarts, CPU und RAM. Erlaubt sind
  ausschließlich `GET`/`HEAD` auf `/_ping`, `/version`, `/info`, `/containers/json`,
  `/containers/<id>/json` und `/containers/<id>/stats`. Alles andere wird mit 403
  abgewiesen.
- Home-Assistant-Checks: lesend über `SUPERVISOR_TOKEN` — `GET /core/api/` und
  `GET /core/api/states/<entity>` für Erreichbarkeit, Backups, DB-Größe und Updates,
  dazu ein Websocket-Aufruf `config_entries/get` für den Integrationszustand. Keine
  Schreibzugriffe, kein Zugriff auf die Datenbankdatei. Abschaltbar über die Optionen
  im Abschnitt „Home-Assistant-Checks“.

## Grenzen

- Der Agent-Dienst `updates` bleibt leer, weil Home Assistant OS keinen Paketmanager hat. HA Core, HA OS, Supervisor und Add-ons deckt stattdessen der Check `Home Assistant Updates` ab.
- Ohne `agent_root` sieht der Agent die Mounts des Containers, nicht die des Hosts.
- Ohne gesetzten Fingerabdruck braucht die Docker-Verbindung eine vertraute CA und einen
  passenden Hostnamen; das Add-on erzeugt eine eigene CA, die Monitor64 nur mit
  hinterlegtem Pin akzeptiert.
