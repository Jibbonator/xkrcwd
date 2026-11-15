# Monitor64

Ein Add-on für Home Assistant OS: Monitor64-Agent als SSH-Dienst auf Port 6465 und ein
read-only Docker-API-Proxy über TLS auf Port 2376.

## Voraussetzungen

- Home Assistant OS oder Supervised.
- **Schutzmodus aus** (Einstellungen des Add-ons): nötig für `full_access`, `host_pid` und
  `docker_api`.
- NetBird auf dem Host erreichbar; Monitor64 verbindet sich über die Mesh-Adresse.

## Optionen

| Option | Standard | Bedeutung |
|---|---|---|
| `keys` | leer | Öffentliche Schlüssel der Node(s) im authorized_keys-Format, eine Zeile je Node. Genau der Wert hinter `--key` aus dem Installationsbefehl von Monitor64. |
| `local_scripts` | `false` | Eigene Skripte aus `/config/monitor64-agent/local.d/` einbinden. |
| `listen` | `:2376` | Adresse des Docker-Proxys. Für Bindung an NetBird z. B. `100.96.x.y:2376`. |
| `docker_socket` | `/var/run/docker.sock` | Socket der read-only Docker-API. |
| `agent_port` | `6465` | Port des Agenten. |
| `agent_root` | leer | Wurzel für `/proc`, `/sys` und Mounts. Für den Host `/proc/1/root` — damit die Dateisysteme und Platten des HA-Hosts gelesen werden. |

## Einrichtung

1. Repository-URL im Add-on-Store eintragen, `Monitor64` installieren, Schutzmodus aus.
2. In Monitor64 einen Host vom Typ Agent anlegen: Adresse = NetBird-Adresse des
   HA-Hosts, Port 6465, automatische Agent-Updates aus. Die angezeigte Schlüsselzeile in
   `keys` übernehmen, Add-on starten.
3. In Monitor64 „Verbindung testen“ und den SSH-Host-Key per Fingerabdruck bestätigen.
4. Für Docker das Add-on-Log öffnen. Dort stehen `fingerprint=<sha256>` und
   `credentials={"key":…,"cert":…,"ca":…}`. In Monitor64 einen Host vom Typ Docker
   anlegen: Adresse `https://<netbird-adresse>:2376`, Fingerabdruck festpinnen, JSON unter
   „Zugangsdaten“, testen und bestätigen.

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

## Grenzen

- `updates` bleibt leer: Home Assistant OS hat keine Paketmanager-Updates.
- Ohne `agent_root` sieht der Agent die Mounts des Containers, nicht die des Hosts.
- Ohne gesetzten Fingerabdruck braucht die Docker-Verbindung eine vertraute CA und einen
  passenden Hostnamen; das Add-on erzeugt eine eigene CA, die Monitor64 nur mit
  hinterlegtem Pin akzeptiert.
