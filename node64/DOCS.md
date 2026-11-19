# Node64

Node64 als Home-Assistant-App: Healthchecks und Statusseiten, DNS64 (Filter-DNS
mit DHCP), PROXY64/CDN64 (Reverse Proxy), DynDNS, Monitor64, IPAM64, Zertifikate
und Honeypot64. Ein Go-Binary, SQLite, eingebettete Weboberfläche – alles unter
`/data`.

## Netzerk

Die App läuft im Host-Netz (`host_network`), weil die Module feste Ports binden:

| Port | Modul |
| --- | --- |
| 8080/tcp | Weboberfläche |
| 53/udp, 53/tcp | DNS64 |
| 80/tcp, 443/tcp | PROXY64, DNS64 (DoH) |
| 853/tcp, 853/udp | DNS64 (DoT, DoQ) |
| 6465/tcp | Monitor64-Agent (nur wenn genutzt) |
| 162/udp | Monitor64 SNMP-Traps (nur wenn genutzt) |

Alle Ports müssen auf dem HAOS-Host frei sein. Nach dem Start die Oberfläche
unter `http://<haos-host>:8080` öffnen; der Assistent legt das Admin-Konto an.

## Updates

Node64 bringt ein Selbst-Update mit; im Container ist es **aus** (Standard).
Bitte aus lassen – das Image gehört dem Supervisor, die Version kommt über das
Add-on-Update. Ein Selbst-Update im Container würde die Version im Image
überschreiben und beim nächsten Neustart verworfen.

## Daten und Sicherung

Alles liegt unter `/data` (Datenbank, Schlüssel, Zertifikate, Backups). Das
Verzeichnis ist in HA-Snapshots enthalten. Zum Umzug von einer bestehenden Node:
unter *Einstellungen → Daten & Sicherung* ein `.n64backup` ziehen und in der App
über dieselbe Seite wieder einspielen.

## Rechte

`NET_RAW` wird für ICMP-Checks gebraucht. Weitere Rechte werden nicht verlangt;
das Docker-Modul (Docker-Socket) ist in der App nicht verfügbar.
