# Heizungsdashboard: Eurocontrol K und M

Das Modul erweitert die bestehende SmartHome-Flask-Anwendung unter `/heizung`.
Der Menüpunkt ist auf Desktop und Mobilgerät erreichbar. Es gibt eine gemeinsame
Übersicht und getrennte EG-/OG-Ansichten; `?etage=eg` bzw. `?etage=og` öffnet die
entsprechende Ansicht direkt. CSS, JavaScript, Symbole und Diagramme werden lokal
ausgeliefert; für diese Ansicht werden keine CDN-Ressourcen benötigt.

## Einrichtung

`config/heating.example.json` nach `config/heating.json` kopieren und die lokalen
BSB-LAN-/ioBroker-Adressen eintragen. Diese Datei und die Verlaufsdatenbank sind
Git-ignoriert. Ohne Konfiguration bleibt der Collector deaktiviert.
`simple-websocket` wird von der bestehenden Flask-SocketIO-Installation verwendet.

Die Installation erwartet LPB, K an Adresse 0 (Familie 22, Variante 254) und M an
Adresse 1 (Familie 23, Variante 254). Andere Geräte werden nicht stillschweigend
mit diesen Definitionen ausgelesen. Das Modul nutzt ausschließlich die bestehende
Rohlese-API `/JY06,...`; daher funktionieren die Messwerte auch vor Installation
des neuen BSB-LAN-Parameterprofils. Es wird keine ESP32-Firmware verändert.

Die Antworten werden auf Prüfsumme, Absender, Ziel, Objekt und TYPE_ANS geprüft.
Der ausgehende Frame muss eine TYPE_QUR ohne Nutzdaten sein. Abgelehnte Objekte
und ungültige Sensorwerte bleiben unverfügbar; `01 00 00` wird nie als gemessene
0 oder 20 Grad angezeigt. Relaiszustände beschreiben Kontakte, keine gemessene
Förderleistung oder Ventilposition. Auf/Zu stammen aus dem Siemens-Profil für
OV200.6; bisher physisch abgeglichen ist der Zustand Pumpe an/Mischer aus.

Die Brenneranzeige verwendet die K-Ausgänge K4/K5 aus `05000488`, Byte 0/1.
Im passenden OV200.4-Profil `D0016682.apw` referenziert der Relaistest die
Herstellerliste `Txt_RelaisTest_RVA43223` (MessageSet133): Brennerstufe 1 ist K4,
Stufe 1+2 ist K4+K5. Angezeigt wird der Relaisstatus, keine Flammenmessung.
Das zusätzliche Anlagestatus-Objekt `05000926` heißt zwar Brennerkontakt, seine
genaue Beziehung zu Relaisanforderung und tatsächlicher Flamme ist aber offen;
es wird deshalb für diese Anzeige nicht verwendet.
Der gleiche Block liefert Q3 an Byte 3 als Warmwasserpumpenrelais. Der
Profil-SHA256 für diese K-Zuordnung lautet
`38d209d81ca2b2acf3fd99e1b9e57aae2d3f8b92f27778a1ba7a7ed43c7f4958`.

## Gemeinsamer Cache und Verlauf

Ein Hintergrundthread liest schnelle Werte alle 30 Sekunden, Einstellungen alle
fünf Minuten. Geteilte LPB-Objekte werden je Runde nur einmal abgefragt. Browser
lesen alle fünf Sekunden denselben Cache und erzeugen keine eigenen Busabfragen.
Ein manueller Refresh aktualisiert ebenfalls nur die Anzeige. Der Collector
startet erst beim ersten Seiten-/Statusaufruf und endet mit dem WebManager.

Jeder Wert hat `value`, `quality`, `updated_at` und `age_seconds`. Schnelle Werte
werden nach mindestens 90 Sekunden ohne Aktualisierung als veraltet markiert,
langsame Einstellungen nach 15 Minuten. Die VM speichert Temperatur- und
Brennerverläufe für 30 Tage in `config/heating_history.db`. Die API liefert maximal
360 Punkte pro Abfrage; Datenlücken bleiben im Diagramm unterbrochen.

## ioBroker und Tado

Die native ioBroker-WebSocket-Verbindung liest Tado-Temperaturen, Raumvorgaben und
Feuchte. Adapterverbindung und Messzeitpunkt werden ausgewertet. Raumzuordnungen
stehen in `room_floors`, mit der vollständigen Tado-Raum-ID als Schlüssel und
`eg`, `og` oder `kg` als Wert. Ohne bestätigte Zuordnung bleibt ein Raum separat.
Raumnamen werden aus ioBroker gelesen oder mit `room_names` überschrieben.

Die Heizungswerte werden ausschließlich unter `0_userdata.0.heizung.*` mit
`ack=true` veröffentlicht. Die Objekte sind nicht schreibbar; ungültige oder
veraltete Werte werden als `null`, Qualität `0x40`, übertragen. Existierende
Objekte fremder Integrationen werden nicht übernommen. Neue Objekte tragen
`native.managed_by=smarthome-heating`.

Es gibt keine Stellbefehle, Tado-Schreibzugriffe oder Raumfühlereinspeisung.
Der aktuelle Brennerstartzähler ist keine Energiemessung. Daten- und Status-API:
`GET /api/heating/state`, `GET /api/heating/history?hours=1|6|24`.

## Prüfung und Wiederherstellung

`python -m unittest test_heating_dashboard.py` prüft ohne Netzwerk die
Frameintegrität, Dekodierung, ungültige Sensoren, getrennte Relaisbits, den
gemeinsamen Cache, falsche Geräteidentität, veraltete Werte, ioBroker-Schreibgrenzen
und die nur lesenden HTTP-Routen. `make smoke` schließt diese Tests ein.

Vor einer Installation die geänderten Quelldateien sichern und auf dem Ziel mit
der dortigen virtuellen Umgebung prüfen. Ein Dienstneustart lädt die neuen
Routen. Zur Deaktivierung `enabled=false` setzen und den Webdienst neu starten;
die ursprüngliche SmartHome-Seite und andere Integrationen bleiben erhalten.

## Native Wochenprogramme

Die Wochenübersicht liest tatsächliche Reglerprogramme und plant keine eigenen
Stellbefehle auf der VM. Die passenden Profile besitzen sieben Tagesarrays mit
`COzwDpVhSwitchPointArray` / `COzwSwitchPointArray`; diese werden vom bisherigen
allgemeinen `COzwVal*`-Extraktor nicht erfasst. Die früher geprüften Einzeladressen
`05000A28/29` waren für diese Versionen ungeeignet.

Bestätigt sind Montag `05000A8C` bis Sonntag `05000A92`, jeweils M/EG an Ziel 1
und K/OG an Ziel 0. Alle 14 Abfragen lieferten TYPE_ANS mit gültiger Prüfsumme.
Die zwölf Rohbytes bilden drei Paare `Startstunde, Startminute, Endstunde,
Endminute`, ohne zusätzliches skalares Gültigkeitsbyte. Bit 7 kennzeichnet einen
deaktivierten Schaltpunkt; beobachtet wurden die ungenutzten Startwerte `80`
und `98` (hex). `24:00` ist als Ende zulässig. Beschädigte oder überlappende
Intervalle werden nicht als plausibles Zeitprogramm dargestellt.

Die Programme werden einmal je 15 Minuten gelesen und nach 31 Minuten ohne neue
Antwort als veraltet markiert. `schedules` im Status-JSON enthält beide Wochen.
ioBroker erhält pro Tag einen nur lesenden Textwert unter
`0_userdata.0.heizung.eg.schedule_monday` bis `schedule_sunday`, ebenso für OG.
Die Ansicht folgt der gewählten Etage und markiert den aktuellen Wochentag in
Europe/Berlin. Die Komfortzeiten gelten in Automatik und sind keine direkte
Dauerfreigabe für Pumpen oder Brenner. Die Schreibdarstellung dieser Tagesarrays
ist noch nicht praktisch bestätigt; es gibt daher keine Speichern-Befehle.

Quellen: K `D0016682.apw`, OV200.4 (SHA oben), Montag DP2082/Adresstail2698;
M `D0017684.apw`, OV200.6, SHA
`bffb18693acab2abff2fe5945f85ed05026d3c7fa85ca33a7c35401e6738e1ad`,
Montag DP1884/Adresstail2496. Die Tageslabels stammen aus Katalogzeilen298–304.


### Wochenraster und lokale Entwürfe

Die Ansicht bietet ein Wochenraster mit gemeinsamer 00–24-Uhr-Achse pro Heizkreis
und eine kompakte Zeitliste. Farbige Bereiche zeigen Komfortphasen, der übrige
Bereich die Absenkphase in Automatik. Dies sind keine Pumpen-Sperrzeiten.
Auf schmalen Bildschirmen lässt sich das Raster innerhalb seiner Karte verschieben.

Ein Tag oder „Zeiten entwerfen“ öffnet einen Editor für maximal drei Zeitfenster,
Viertelstunden, 24:00 als Tagesende und Kopieren auf Werktage, Wochenende oder
alle sieben Tage. Ungültige Zeiten und Überschneidungen werden zurückgewiesen.
Entwürfe verwenden getrennte Browser-Schlüssel `heating-schedule-draft-v1-eg` und
`heating-schedule-draft-v1-og`. Sie bleiben über Neuladen erhalten, werden weder
an die VM noch an ioBroker oder die Heizung gesendet. „Reglerstand anzeigen“
ermöglicht den Vergleich; Verwerfen lässt sich während der Sitzung rückgängig machen.
Ein geänderter Reglerstand gegenüber der Entwurfsbasis wird kenntlich gemacht.

Es gibt weiterhin keine schreibende Heizungsroute. Der vorhandene BSB-LAN-Code
enthält einen generischen `VT_TIMEPROG`-Encoder mit zwölf Bytes, bezeichnet ihn
aber selbst als `TODO test it`. Das bestätigt noch keine sicheren Schreibvorgänge
für diese beiden Eurocontrol-Varianten oder deren deaktivierte Schaltpunkte.
Daher ist die direkte Übertragung in dieser Version nicht implementiert.
Validierung: `node --test test_heating_schedule.cjs` ist Teil von `make smoke`
und `make test`; zusätzlich Browserprüfung von Editor, Kopieren, Vergleich,
Persistenz, Zeitliste und mobiler Darstellung.
