# Heizungsdashboard: Eurocontrol K und M

Das Modul erweitert die bestehende SmartHome-Flask-Anwendung unter `/heizung`.
Der Menüpunkt ist auf Desktop und Mobilgerät erreichbar. Es gibt eine gemeinsame
Übersicht und getrennte EG-/OG-Ansichten; `?etage=eg` bzw. `?etage=og` öffnet die
entsprechende Ansicht direkt. CSS, JavaScript, Symbole und Diagramme werden lokal
ausgeliefert; für diese Ansicht werden keine CDN-Ressourcen benötigt.

## Einrichtung

### Zusätzliche lesende Diagnosefelder (09.11.2026)

20 weitere Felder ergänzen die laufende Erfassung (insgesamt 133). Die
Warmwasser-Anforderungsart `anlage.dhw_request_source` (`0500071E`) und
die Brennerart `anlage.burner_type` (`05000930`) werden zuerst in den
Diagnosekarten angezeigt. Die alten COzwValB-Werte verwenden auf dem Bus
`00`/`FF`, nicht die Bedienfeldcodes 0/1. Nicht zugeordnete Werte bleiben
`Code n`; deaktivierte Skalare bleiben unverfügbar.

Weitere Felder: Warmwasser-Trennschaltung, OEM-Kesselminimum,
Stufe-2-Freigabe-/Rückstellintegral, Kesselbetriebsart, Schornsteinfegerfunktion
sowie pro Regler Schnellaufheizungszuschlag, ZAF1/ZAF2, Anlagentyp,
Zeitquelle und Außentemperaturlieferant. Integrale werden in K·min mit
Skalierung 1 gelesen; sie sind weder Temperaturen noch feste Wartezeiten.
Die Außentemperaturquelle `05000082` enthält zwei Blockfelder (Segment,
Gerät), ohne vorangestelltes skalares Gültigkeitsbyte.

Die Konfiguration "Zweistufig" beweist weder die tatsächliche Verdrahtung noch
eine gemessene Stufenleistung. Verbrauchs- und Lernmodelle werden daraus nicht
geändert. "Trennschaltung" ist eine Kaskadenfunktion, keine
Zirkulationsabschaltung oder Warmwasser-Zuordnung zu Heizkreisen.

Alle Felder erscheinen automatisch unter `0_userdata.0.heizung.<area>.<key>`
mit `common.read=true`, `common.write=false` und `ack=true`. Ein Fehler oder
ungültiger Wert erzeugt `null` mit Qualitätskennzeichen. Neue Einstellungen
werden im langsamen Fünf-Minuten-Zyklus gelesen; die Schornsteinfegerfunktion
wird als Zustand im schnellen Zyklus erfasst. Es gibt keine neue Schreibroute.

### Begrenzte Interpretation von LPB-Attributen

Die Brötje-Herstelleranleitung ISR MODBM, 7715040-06 vom 24.07.2019,
Seiten 34–35, beschreibt LPB-Objekte 500, 504 und 507. Diese spätere Unterlage
wird nur bei passenden Objekten und dem in den K/M-Profilen bestätigten
Feldaufbau herangezogen:

| Abgefragtes Objekt | Eingeordnete Bits | Grenze |
| --- | --- | --- |
| `210001F4`, Heizungsanforderung / 500 | Bit 0 gültig, Bit 1 Zubringerpumpe angefordert | Weitere Attribute nicht zugeordnet |
| `150001F8`, Reduktionssignal EM / 504 | Bit 0 gültig, Bit 1 zwingende Reduktion | Prozentwert allein beweist keinen Pumpenstopp |
| `150001FB`, Zwangssignal EM / 507 | Bit 0 gültig, Bit 1 Zwang an alle statt nur Nachlauf | Bei T=0 ist das Prozentfeld kein zwingender Prozentbefehl |

#### Zweiter Entschlüsselungsschritt

Die explizite LPB-500-Definition wird jetzt auch mit den passenden vier Byte
langen VG-BW- und VM-Anforderungen (`250001F4`, `190001F4`) abgeglichen.
Bits 0/1 stehen für Gültigkeit/Zubringerpumpe, Bits 2/3 für absoluten/gleitenden
Warmwasservorrang. Vorrangkennzeichen werden nur bei gesetztem Gültigkeitsbit
als solche eingeordnet. Andere Bits bleiben offen; insbesondere werden neuere
BW-/HK-/Legionellenmasken nicht pauschal auf die alten Regler übertragen.
Eine angeforderte Zubringerpumpe ist nicht automatisch der lokale Q1-Kontakt.

Zusätzlich wird `1500020A` / LPB 522 als Erzeugerstatus im Verbund ausgewertet.
Die exakten K/M-Profile bestätigen das zwei Byte lange Attributfeld am Anfang
des fünf Byte langen Blocks. Nur die dokumentierten Bits 0–5 und 8 werden
eingeordnet. Bit 0 bedeutet hier **Erzeuger vorhanden**, nicht ein skalares
Gültigkeitsbyte. Die übrigen zugeordneten Anzeigen betreffen ECO/Außengrenze,
Störung, Schornsteinfegerfunktion, manuelle Sperre, Nichtverfügbarkeit wegen
Warmwasserladung und Handbetrieb. Bei nicht bestätigter Erzeugerpräsenz werden
die anderen Bits nicht als aktive Zustände verwendet. Leistungsfelder und
`11000209` / LPB 521 erhalten daraus keine neue Interpretation.

`assessment` ergänzt die Pumpendiagnose um einen begrenzten Zusammenhang
(Heizanforderung, Nachlauf, Warmwasser-Reduktion, Erzeugerhinweis oder
Absenkphase ohne gültige lokale Anforderung). Alter, Qualität und Zeitversatz
werden für die jeweils tatsächlich verwendeten Signale geprüft. Mehr als
30 Sekunden Versatz, mehr als 90 Sekunden Alter oder Zukunftszeitstempel
führen zur Enthaltung. `cause_status` bleibt `unresolved`, da der eindeutige
physische Schaltgrund nicht bewiesen ist. Im EG wird eine mögliche Begrenzung
am Mischer von einem OG-Pumpenstopp unterschieden. Treffen Heizanforderung und
Nachlauf zusammen, werden beide genannt.

Die vorhandenen Busabfragen werden je Controller zusammenhängend gelesen;
der gemeinsame K/Q3-Kontakt liegt unmittelbar vor dem M-Kontext. Geteilte
Objekte werden weiterhin nur einmal je Runde gelesen. EM-Status 522 wird nun
im schnellen Zyklus erfasst. Zukünftige Änderungsaufzeichnungen enthalten
auch diesen Status, den bisherigen EE-Rohblock und EG-Mischerbefehle/Vorlauf.
Dadurch entstehen keine nachträglich erfundenen historischen Statuswerte.

Eine einzelne Leseprobe von M-Kandidat `0500065E` (Sperrsignalverstärkung,
erst in späteren Profilen vorhanden) wurde abgewiesen. Sie wird nicht in die
laufende Erfassung aufgenommen. Die übrigen Sperr-/Zwangsobjekte 503, 505,
506 und Betriebsniveau 523 bleiben ohne behauptete Bitbelegung. Der Vergleich
von Niveau 1/2 mit reduziertem/normalem Raumsollwert ergab einen Übergangsfall
mit abweichenden Feldern; dies genügt nicht für eine sichere Protokollzuordnung.

Die Herstellerquelle ist auch direkt verfügbar:
[Brötje ISR MODBM, Seiten 34–35](https://polo.broetje.de/pdf/7715040%3D6%3Dpdf_%28bdr_a4_manual%29%3Dde-de_ma_modbm.pdf).
Die Unterscheidung zwischen Pumpen- und Mischerbegrenzung ist ergänzend in
[Siemens RVA46 CE1P2372E, S. 66 und 97](https://mhgheating.co.uk/wp-content/uploads/2012/04/RVA46-D.pdf)
beschrieben; modellabhängige BMU-Funktionen und Schaltschwellen daraus werden
nicht als bestätigte Wirkung dieser Installation ausgegeben.

Die Auswertung enthält Quelle, Anwendungsgrenze, `protocol_valid`,
`unknown_attribute_bits` und gegebenenfalls `mandatory`. Sie erscheint in
"Signalwerte & Attribute" und im bereits vorhandenen lesbaren ioBroker-JSON
`<eg|og>.pump_diagnosis`. `effective` bleibt bewusst `null` und
`cause_status=unresolved`: Die Dokumentation und ein zeitlicher Zusammenhang
beweisen nicht jede Wirkung der alten Eurocontrol oder den einzigen Schaltgrund.
Die Zuordnung wird nicht auf Erzeugergruppen-Sperre 503, VM-Sperre 505,
Erzeugerzwang 506, EM-Anforderung 501 oder Betriebsniveau 523 übertragen.

Ein lokaler Snapshot mit 1371 Änderungsaufzeichnungen enthält 305 OG-Einträge
mit Reduktion `64 01`; in allen war Q3 Ein und die OG-Pumpe Aus. Im EG waren
bei demselben Signal sowohl laufende als auch stehende Pumpenkontakte zu sehen.
Diese Häufigkeiten sind Ereigniszahlen, keine Zeitanteile, unabhängigen Versuche
oder Kausalitätsbelege. Es wurden für den Vergleich keine Reglerwerte verstellt.

Quellen: passendes Siemens-Profil K `D0016682.apw` (OV200.4),
M `D0017684.apw` (OV200.6), lesender Geräteabgleich und
[Brötje ISR MODBM, S. 34–35](https://forum.iobroker.net/assets/uploads/files/1676708238143-7715040-06-24072019-montageanleitung-modbus-busmodul-isr-modbm.pdf).
SHA256 der Herstelleranleitung:
`84bc5e6043d481b06ca5872ff83aeec8d6e9a174e1c64da89c0ac4c9a41414be`.
Ergänzende Funktionsbeschreibungen in
[Siemens RVA63/53, S. 124 und 131](https://www.hansa-heiztechnik.de/UserFiles/file/Download/Altgeraete/Regler-RVA63.pdf)
haben andere Bedienzeilennummern; die Objektzuordnung stammt aus dem K/M-Profil.

Die Gasabschätzung kann aus manuellen Zählerständen empirisch kalibriert werden.
Zeitlich getrennte Messblöcke dauern mindestens eine Stunde, enthalten mindestens
zehn beobachtete Relaisminuten und benötigen mindestens 95 Prozent Messabdeckung.
Häufigere Ablesungen werden zu nicht überlappenden Blöcken zusammengefasst.
Mindestens zwei Blöcke und insgesamt 60 Relaisminuten sind erforderlich; bei
mehr als 25 Prozent Streuung der Faktoren wird keine gemeinsame Schätzung genutzt.
Der Faktor ist Gesamt-Zähler-m³ geteilt durch die erfassten Relaisstunden und bleibt
vorläufig. Der letzte lange Block wird außerdem mit dem zuvor bestimmten Faktor
gegengeprüft. Das Ergebnis bleibt in `heating_gas_calibration` dauerhaft gespeichert.
Fehlen später die Rohdaten, wird es als historisch angezeigt und nicht automatisch
für neue Schätzungen verwendet. Flammenlaufzeit und kWh-Nennleistungsrichtwerte
werden durch diesen Zählerabgleich nicht kalibriert. Heizungsparameter bleiben unberührt.

Live-Aktualisierungen verwenden `heating_live.js`: Text und Attribute werden
in bestehenden DOM-Knoten geändert. Kacheln, offene Details, Fokus, Auswahl und
Scrollposition werden bei Hintergrundabfragen nicht neu erzeugt. Der kleine
Browser-Regressionstest `tests/heating_live.html` prüft das einschließlich SVG.

Eine fehlerhafte LPB-Antwort betrifft nur die abgefragte Objektgruppe oder den
betroffenen Wochenprogrammtag. Andere checksum-geprüfte Werte desselben Zyklus
bleiben gültig. Teilfehler werden als `connection.degraded` und mit Objektkennung
protokolliert. Nach drei aufeinanderfolgenden Abfragefehlern endet der Durchlauf,
damit ein Ausfall nicht einen Timeout für jedes Objekt auslöst. Eine falsche
Geräte-/Busidentität beendet weiterhin sämtliche Datenabfragen. Historische
Lücken werden nicht nachträglich gefüllt und Frischegrenzen nicht erhöht.

`config/heating.example.json` nach `config/heating.json` kopieren und die lokalen
BSB-LAN-/ioBroker-Adressen eintragen. Diese Datei und die Verlaufsdatenbank sind
Git-ignoriert. Ohne Konfiguration bleibt der Collector deaktiviert.
`simple-websocket` wird von der bestehenden Flask-SocketIO-Installation verwendet.

Die Installation erwartet LPB, K an Adresse 0 (Familie 22, Variante 254) und M an
Adresse 1 (Familie 23, Variante 254). Andere Geräte werden nicht stillschweigend
mit diesen Definitionen ausgelesen. Die Messwerte nutzen die bestehende
Rohlese-API `/JY06,...`; daher funktionieren sie auch vor Installation
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

Die ioBroker-Anbindung sendet keine Stellbefehle, Tado-Schreibzugriffe oder Raumfühlereinspeisung.
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
Dauerfreigabe für Pumpen oder Brenner. Das native Schreiben dieser Tagesarrays wurde inzwischen durch einen gezielten
Mittwochs-Test mit ACK, Rücklesen und Wiederherstellung bestätigt (siehe unten).

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
Zehn-Minuten-Schritte, 24:00 als Tagesende und Kopieren auf Werktage, Wochenende oder
alle sieben Tage. Ungültige Zeiten und Überschneidungen werden zurückgewiesen.
Entwürfe verwenden getrennte Browser-Schlüssel `heating-schedule-draft-v1-eg` und
`heating-schedule-draft-v1-og`. Sie bleiben über Neuladen erhalten. Erst die gesonderte Vorschau sendet den
Entwurf zur VM; an ioBroker werden keine Schreibaufträge geschickt. „Reglerstand anzeigen“
ermöglicht den Vergleich; Verwerfen lässt sich während der Sitzung rückgängig machen.
Ein geänderter Reglerstand gegenüber der Entwurfsbasis wird kenntlich gemacht.

Die gezielte Liveprüfung am
2026-11-08 hat inzwischen das Schreiben des Mittwochsprogramms `05000A8E` für
beide Regler bestätigt: unverändertes SET mit ACK, kontrollierte Änderung,
unabhängiges Rücklesen, Wiederherstellung und Vergleich aller 14 Tagesprogramme.
Die ursprünglichen Komfortphasen blieben anschließend vollständig erhalten.
Inaktive Schaltblöcke können beim SET von `80 00 00 00` nach `98 00 18 00`
normalisiert werden. Das sind keine zusätzlichen Komfortphasen.
Die K rundete Minute 15 auf Minute 10 ab, die M Minute 45 auf Minute 40.
Der Editor verwendet daher gemeinsame
Zehn-Minuten-Schritte; ein ACK allein genügt nicht als Übernahmeprüfung.
Die darauf aufbauende Übertragung wird im folgenden Abschnitt beschrieben.
Die Live-Tests beweisen keine beliebigen SETs für alle RVA-Varianten und
prüften keine Löschung sämtlicher Phasen oder einen dritten aktiven Zeitblock.
Validierung: `node --test test_heating_schedule.cjs` ist Teil von `make smoke`
und `make test`; zusätzlich Browserprüfung von Editor, Kopieren, Vergleich,
Persistenz, Zeitliste und mobiler Darstellung.


## Gezieltes Übertragen von Wochenentwürfen

Standardmäßig ist die Funktion ausgeschaltet. Für die geprüfte Anlage werden
`schedule_writes_enabled: true` und die tatsächliche `bsb_mac` in der privaten
`config/heating.json` gesetzt. Vor jeder Vorschau und Übernahme werden Adapter-MAC,
LPB, Eigenadresse66, Standardziel0, globaler Leseschutz und beide getesteten
Familien/Varianten/OV-Kennungen geprüft. Der globale ESP32-Schreibschutz bleibt
aktiv. Ein eigener Handler erlaubt ausschließlich TYPE_SET03 mit zwölf Bytes
an `05000A8C` bis `05000A92` und ausschließlich das vom Nutzer gewählte K/M-Ziel.
Andere Heizungsparameter sind über diese Funktion nicht schreibbar.

Ablauf: lokal planen, „Übertragung prüfen“, Tagesänderungen ansehen, dann
„An Heizung übertragen“. Die VM liest die Woche frisch und vergleicht sie mit
der Entwurfsbasis. Eine weitere Prüfung direkt vor der Übernahme verhindert,
dass zwischenzeitliche Regleränderungen unbemerkt überschrieben werden.
Unveränderte Tage werden ausgelassen. Pro Tag sind null bis drei aufsteigende,
nicht überlappende Phasen mit Zehn-Minuten-Schritten möglich; 24:00 ist nur als
Ende zulässig. Jede SET-Antwort wird vollständig auf Prüfsumme, Ziel, Objekt,
Nutzdaten und ACK geprüft. Anschließend werden die wirklichen Schaltpunkte
unabhängig ausgelesen und abschließend alle sieben Tage verglichen.

Vorschau und Übernahme nutzen die bestehende Control-Authentifizierung sowie
Origin-Prüfung, JSON und `X-Heating-Schedule: 1`. Die Vorschau gilt drei Minuten
und gehört nur zur anfragenden Client-Adresse. Doppelte Bestätigungen eines
erfolgreichen Vorgangs liefern das frühere Ergebnis ohne weitere SETs.
Collector und Übernahme teilen eine Bus-Sperre; diese Anwendung wird als ein
Serviceprozess betrieben.

Vor jedem SET schreibt die VM Sicherung und Absicht mit fsync in
`config/heating_schedule_transactions/<id>.json` (Git-ignoriert). Bei Fehlern
werden die versuchten Tage rückwärts wiederhergestellt und ausgelesen. Eine
währenddessen fremd geänderte Tageskonfiguration wird nicht blind überschrieben.
Unbestätigte Rücksetzungen werden deutlich gemeldet und sperren neue Übernahmen.
Nach einem Prozessabbruch werden offene Journale beim nächsten Collectorlauf bzw.
vor einer neuen Vorschau geprüft und, soweit eindeutig, wiederhergestellt.
Wiederherstellung ist bei dauerhaft unterbrochener Kommunikation nicht garantiert;
der Fehlerstatus benennt die betroffenen Tage. Historische Journale bleiben lokal
als Nachweis erhalten und enthalten private Heizzeiten.

Tests simulieren echte LPB-Frames und prüfen gezielte Ziel-/Tagesauswahl,
Vorschau ohne SET, Konflikte, abgelaufene/fremde Tokens, Replay, verlorene Antworten,
ACK ohne passenden Rücklesewert, Rücksetzen mehrerer Tage, fehlgeschlagenes
Rücksetzen, Wiederanlauf und fremde Bedieneränderungen. Die ursprünglichen
Liveversuche betrafen ein-/zweiphasige Mittwochsprogramme; Randfälle wie ein
leerer Tag, dritte Phase und 24:00 werden durch Codec-/Transaktionstests geprüft
und bei einer echten Übernahme ebenfalls unabhängig ausgelesen.


## Erweiterte lesende Diagnose und Brennerstatistik

Die zweite Auswertung der passenden Profile D0016682 (K/OV200.4) und D0017684
(M/OV200.6) wurde mit 58 skalaren und 21 Blockabfragen an beiden realen Reglern
abgeglichen. Die Erweiterung liest ausschließlich TYPE_QUR06 ohne Nutzdaten.
Sie ergänzt 67 Felder, insgesamt 108 POINTS. Der bestehende, eng begrenzte
Zeitprogramm-Schreibweg wird davon nicht erweitert.

- Kessel: Minimum/Maximum, Schaltdifferenz, Mindestbrennerlaufzeit und die vom
  Regler gemeldeten berechneten Brenner-Ein-/Ausschalttemperaturen.
- Warmwasser: Betriebsart, Reduziert-/Maximalsollwert, Schaltdifferenz,
  Temperaturüberhöhung, Ladeart, Programm und Priorität.
- Je Regler: Fehlercode und Priorität, Regleruhr, Relaistest-Einstellung,
  LPB-Speisungsstatus, Anlagenfrostschutz-Einstellung, Bauweise, Quelle der
  Sommer-/Winterumschaltung und lokale/gedämpfte/gemischte Außentemperatur.
- OG: zusätzlich die bisher nur am EG angezeigten Absenk-/Frost- und
  Vorlaufgrenzen, Regler-Raumfühler, Vorlaufvorgabe, Pumpennachlauf und -funktion.
- 21 LPB-Blöcke werden in einer geschlossenen Rohdiagnose einschließlich ihrer
  Zusatzkennzeichen angezeigt. Ungeklärte Attribute werden weder als aktive
  Sperre noch als Ursache für einen Pumpenstopp interpretiert.

Der zweibytegroße Fehlerblock `0500006B` enthält Code an Offset 0 und Priorität
an Offset 1, ohne skalaren Gültigkeitspräfix. Die Regleruhr `0500000B` zeigt nur
Wochentag und Uhrzeit; die übrigen Felder werden nicht als Kalenderdatum benutzt.
Der K-Erzeugerstatus `11000209` ist 9 Bytes lang; Bytes 5–8 enthalten einen
vorzeichenbehafteten Sekunden-Zähler, in Stunden umgerechnet. Negative Werte
bleiben unverfügbar. Der reale Wert passte zum zuvor vom Betreiber notierten
Betriebsstundenzähler. Die M definiert an dieser Stelle kein Stundenfeld und
verwendet ausschließlich die vollständige Rohdarstellung.

Nicht vorhandene Sensoren bleiben `null`. Ein ungültiger lokaler M-Außenfühler
schließt eine über LPB übernommene Außentemperatur nicht aus. Der Speisungsstatus
ist keine Busspannungsmessung. Nicht bekannte Enumwerte erscheinen als Code;
Programm/Priorität folgen den begrenzten Legacy-Wertebereichen, nicht beliebigen
modernen BSB-Zuordnungen. Grunddaten und Profil-SHA256 sind oben dokumentiert.
Private Vollmitschnitte und Herstellerkataloge bleiben außerhalb des Repositorys.

`GET /api/heating/statistics?hours=1|6|24` berechnet aus unverdichteten lokalen
Messpunkten gemeinsam gültige Intervalle für Startzähler und K4/K5. Abstände über
120 Sekunden bzw. drei Pollintervalle werden ausgelassen. Bei Relaiswechseln
wird der vorherige beobachtete Zustand bis zum nächsten Messpunkt gehalten;
die Zeitauflösung entspricht der Abtastung. K4 oder K5 an bedeutet Relaislauf;
beide müssen explizit aus sein, um einen Auszustand zu bestätigen. Historische
fehlende K5-Werte werden nicht als aus ergänzt. Eine Rate ohne Daten bleibt
`null`, nicht 0. Die Abdeckung bezieht sich auf das ganze gewählte Zeitfenster.

Der Startzähler hat 16 Bit. Übergänge nahe 65535 nach 0 werden als Überlauf behandelt;
andere Rückgänge werden als Rücksetzung ausgelassen. Die Statistik liefert
Relaisminuten je beobachtetem Start, keine ausgemessenen vollständigen Brennerzyklen.
Weder Relaiskontakte noch die Statistik beweisen eine Flamme oder Gasmenge.
Der native Betriebsstundenzähler ist zusätzlich als separater Gesamtwert sichtbar.

Der Verlauf speichert jetzt auch Betriebsstunden, zweite Brennerstufe und alle
Wettergrößen. Gemischte alte/neue Zeilen werden über eine gemeinsame Schlüsselmenge
zusammengeführt; fehlende ältere Felder bleiben `null`, Zähler werden nicht gemittelt.
Der Temperaturverlauf kann auf aktuelle/gedämpfte/gemischte Außentemperatur des
gewählten Heizkreises umgeschaltet werden. Kein Verlauf wird rückwirkend erfunden.

Alle neuen POINTS werden über die bestehende ioBroker-Integration als bestätigte,
nicht schreibbare Zustände exportiert. TEXT_KINDS und Rohblöcke sind Strings,
Fehlercodes Zahlen, echte boolesche Felder Booleans. Zusätzlich stehen unter
`0_userdata.0.heizung.statistik.*_24h` beobachtete Starts, Relaisminuten,
Starts/Stunde, Relaisminuten/Start und Abdeckung. Die Statistik wird nach dem
Speichern des neuen Messpunkts veröffentlicht. Fehler-/Wetterwerte teilen die
vorhandenen Abfragen; Einstellungen und Rohblöcke werden nur langsam gelesen.
Kein Browser erzeugt zusätzliche LPB-Abfragen.

`test_heating_diagnostics.py` prüft Blockgrenzen, Nullwerte, K/M-Trennung,
Uhrzeit-Platzhalter, Überlauf/Rücksetzung, Datenlücken, zweite Brennerstufe,
Fenstergrenzen und die Weiterverarbeitung historischer Daten.
## Pump context and bounded signal research

The pump cards intentionally keep `cause_status:unresolved`. They distinguish
the actual Q1 contact, the controller's own weekly clock/program phase, current
setpoints and possible influences. A reduced phase, DHW contact or positive
percentage alone must never become a confirmed stop/start reason. Sensor gaps,
stale contacts and undecoded attributes remain unknown.

The exact RVA43/RVA46 APW profiles identify these block fields (zero-based):

| Blocks | Field layout | Remaining limitation |
| --- | --- | --- |
| `210001F4`, `250001F4`, `190001F4` | signed I16 temperature at 0, 1/64 °C; U16 attributes at 2 | Attribute bit semantics and effective demand are unresolved |
| `150001F5` | Same, plus priority byte at 4 | Priority semantics unresolved |
| `110001F7`, `150001F8`, `190001F9`, `110001FA`, `150001FB` | signed I8 percentage field at 0; U8 attributes at 1 | Neither `00 00` nor a positive field proves validity or active intervention |
| `2D00020B` | U8 level at 0; U8 attributes at 1 | Level/validity mapping needs contrasting observations |

In these LPB names, EG means an **Erzeugergruppe**, not the ground floor;
EM/VM denote the producer/consumer mixer context. Identical block shapes do
not establish that every functional object is active in the actual plant.
The structured fields retain exact raw bytes, attribute hex and numbered set
bits, and always report `effective:null`. No guessed bit masks are applied.

Additional payload-free reads: KON `050005FB` (two-byte scalar with a
validity prefix, factor 0–20) and telephone/remote contact `050004B8`. Relevant
request/lock/forced blocks now share the fast collector cycle with Q1; the
diagnosis reports read-time skew. No extra bus reads are triggered by UI/API.

[Siemens CE1P2372E](https://mhgheating.co.uk/wp-content/uploads/2012/04/RVA46-D.pdf),
sections 5.4.1 and 6.6, documents pump shutdown during quick setback without a
room sensor and explains that valid demand, overrun and protection functions
affect pump operation. KON is a setting, not an active-status signal. This
general behavior supports a possible influence, not automatic causal proof.

Changed Q1/mode/setpoint/signal/quality combinations are retained locally in
`heating_pump_events` for seven days, including their original observation
timestamps. Clock ticks alone do not generate events. Samples are sequential,
not an atomic bus snapshot; no pre-installation history is fabricated. The
`GET /api/heating/pumps?hours=1|6|24` endpoint returns at most 40 events per
floor. The UI shows the latest eight and labels inference limits explicitly.
The same current structured diagnosis is exported as a read-only JSON string
under `0_userdata.0.heizung.<eg|og>.pump_diagnosis`. No heating SET was added.

## Kontexthilfe und Einrichtung

Fragezeichen an den Heizkreis-Einstellungen und Diagnosezeilen öffnen einen
zentralen, per Tastatur bedienbaren Dialog. Er zeigt Bedeutung, Wirkung,
Interpretationsgrenzen und den beim Öffnen gelesenen Wert samt Datenqualität.
Die Bereiche EG/M, OG/K und Anlage bleiben getrennt. Der Dialog wird vom
laufenden Fünf-Sekunden-Refresh nicht neu aufgebaut; nach dem Schließen wird
der Fokus an den zugehörigen Auslöser zurückgegeben.

„Einrichtung & Werte verstehen“ führt durch vier Schritte mit einer beim
Öffnen aufgenommenen Momentaufnahme: Anlagenaufteilung, Fühler-/Datenqualität,
vorhandene Vorgaben, Beobachtungsablauf. Die Hilfe unterscheidet insbesondere
Raumsollwert und Messwert, Tado-Anzeige und Reglerfühler, gespeicherten Faktor
und wirksame Funktion sowie KON und eine tatsächlich aktive Schnellabsenkung.
Sie schlägt keine pauschalen Zahlenwerte vor, speichert keine Konfiguration
und führt keine Schreibbefehle aus. Unbekannte Signalattribute bleiben offen.
Alle Hilfetexte werden als lokale statische Datei ausgeliefert. Nur der
bewusst anklickbare Herstellerlink öffnet eine externe Dokumentation.

## Lernende Beobachtung ohne Stellzugriff

Die optionale, ignorierte `config/heating_observer.json` aktiviert ausschließlich
`mode: observe`. Andere Modi werden abgelehnt. Ein Beispiel liegt unter
`config/heating_observer.example.json`. Das Beobachtungsmodul bekommt nur
Snapshots und einen lokalen SQLite-Pfad; es besitzt weder Bus-/HTTP-Transport
noch einen Writer. Es ändert keine Reglerparameter, Tado-Vorgaben oder
Zeitprogramme. Die bisherigen manuellen Zeitprogramm-Routen bleiben separat.

Bei aktiviertem Beobachter startet der vorhandene Collector bereits beim
Dienststart, auch ohne Browser. Nach dem ioBroker-Abgleich wird höchstens einmal
pro Minute ein kompakter Datensatz in `heating_observations` gespeichert,
90 Tage aufbewahrt und nicht rückwirkend aus unvollständigen Altdaten erzeugt.
Raum-ID, Etage, Gerätetyp, Temperatur, Sollwert, Feuchte, Heizbedarf und
Quellenzeitpunkte bleiben getrennt. Tado-Felder werden einzeln nach q, Alter,
Numerik und Wertebereich geprüft. 0 % Heizbedarf ist gültig; fehlende Werte sind
keine Null. Verbindungsabbrüche werden nicht als frische Trainingsdaten genutzt.

Das stündliche Lernen läuft in einem eigenen Thread mit einer standardisierten
Ridge-Regression ohne zusätzliche ML-Paketabhängigkeiten. EG und OG erhalten
je Heizungsraum ein eigenes thermisches Antwortmodell, der Speicher ein eigenes
Lade-/Abkühlmodell. Klimageräte und unbestätigte Gerätetypen werden aufgezeichnet,
aber nicht als Gas-Heizungsraum trainiert. Keller-Räume werden aufgezeichnet,
gehören jedoch nicht zum EG-/OG-Modell. Keine widersprüchlichen Raumwerte werden
gemittelt oder durch einen vorgegebenen Referenzraum ersetzt.

Das Modellfenster umfasst 28 Tage, auf fünf Minuten ausgedünnt. Nicht überlappende
15–30-Minuten-Intervalle müssen vollständig gültig sein; Lücken über sieben
Minuten schließen ein Intervall aus. Raum-Modelle verwenden Wetterdifferenz
und eine mit Q1 und gültigem Tado-Heizbedarf gewichtete Versorgungsgröße:
EG-Vorlauf bzw. OG-Kesseltemperatur als Proxy. Das ist kein gemessener Wärmestrom.
Das Speichermodell nutzt Q3, Kessel- und Speichertemperatur; die Umgebung ist
explizit mit 20 °C angenommen. Größere Temperaturstürze ohne Ladung werden als
mögliche Entnahmen aus der Abkühlmodellierung ausgeschlossen. Es gibt keinen
Zapfmengen- oder Hygienemodell-Nachweis.

Mindestens 48 Intervalle, drei Beobachtungstage und 48 Stunden Spanne sowie
Heiz-/Abkühlphasen und veränderliche Eingänge sind nötig. Die letzten 20 Prozent
bleiben zeitlich nachgelagerte Prüfdaten. Erst wenn Vorzeichen plausibel sind
und der Temperaturfehler kleiner als bei unveränderter Temperatur ist, wird
`validated` gemeldet. Danach wird auf allen geeigneten Daten neu angepasst.
Eine geprüfte Temperaturreaktion garantiert weder kausale Identifikation noch
Energieeinsparung; es werden keine Steuerempfehlungen automatisch ausgeführt.
Lernstand und Zeitpunkt stehen dauerhaft in `heating_learning`.

### Relaiszeit und Nennleistungsreferenz

Die zusätzliche Rechnung verwendet Roh-Historienintervalle mit gültigen K4/K5
an beiden Enden, höchstens drei Minuten Abstand. Sie benötigt keinen gültigen
Startzähler. Gezählt wird die Vereinigung der Kontakte, keine doppelte Laufzeit
bei zwei aktiven Stufen; Stufenzeiten sind separat enthalten. Messlücken werden
nicht hochgerechnet. Dies bleibt eine abgetastete Relaiszeit, keine Flammenmessung.

Die Typenschild-Nennwärmebelastung (Hi/Heizwertbasis) und Nennwärmeleistung sind
getrennte Konfigurationsfelder. Referenzenergie = Nennbelastung mal beobachtete
Relaisstunden, unter der ausdrücklich unbestätigten Annahme voller Belastung
während jeder Relaisminute. Gasäquivalent = Referenzenergie / angenommener
Heizwert (standardmäßig nur als Beispiel 10 kWh/Nm³). Es handelt sich um
Normvolumen, nicht Zähler-Betriebsvolumen. Für reale Gasabrechnung sind unter
anderem Brennwert und Zustandszahl erforderlich; Hi und Hs sind nicht austauschbar.
Der Abgasverlust wird nicht als Anlagen-/Jahresnutzungsgrad verwendet. Eine
Umrüstsatznummer und ein einzelner Messzettel bestätigen keine Stufenleistung.

Die Oberfläche unter `#beobachtung` zeigt Aufzeichnungsstand, Modelle,
Raum-/Speicherverläufe und ausdrücklich unkalibrierte Richtwerte.
`GET /api/heating/observer` und `/api/heating/observer/history` sind rein lesend,
mit `hours=1|6|24`. Historien liefern maximal 360 Punkte; ungültige Werte in einem
Verdichtungsabschnitt bleiben Lücken. Alle Daten bleiben lokal auf der VM.

### Warmwasser-Langzeitverlauf

Die eigene Karte `#warmwasser-verlauf` zeigt den gemessenen Speicherfühler für
denselben Zeitraum wie drei zusätzliche Relais-Schaltspuren (EG Q1, OG Q1 und
Warmwasser-Ladekontakt Q3). Gespeicherte Beobachtungen liefern die Kontakte;
es gibt keine rückwirkend erfundenen Pumpenzustände und keine Wilo-Rückmeldung.
Die Schaltliste nennt für jeden Wechsel das Intervall zwischen zwei Ablesungen
(maximal 180 Sekunden Abstand), keinen vermeintlich exakten Schaltzeitpunkt.
Ungültige Werte, Messlücken und das eigentliche Wechselintervall bleiben
unbekannt. Die Spuren enthalten höchstens 720 Zeitabschnitte je Kontakt,
mit Ein-/Aus-/unbekannten Sekunden und Wechselzähler; die letzten 20 Wechsel
pro Kontakt werden zusätzlich aufgelistet. Diese Ergänzung ist rein lesend.

Der Temperaturverlauf ist wählbar für
24 Stunden, 7, 30 oder 90 Tage. `GET /api/heating/observer/dhw-history?days=1|7|30|90`
liefert höchstens 720 Zeitabschnitte mit Mittelwert, Minimum, Maximum und Anzahl.
Ältere tatsächlich gemessene Anlagenhistorie (bis 30 Tage) wird bis zum Beginn
der Beobachtungsaufzeichnung genutzt; danach gilt das 90-Tage-Beobachtungsarchiv.
Es werden keine Daten rückwirkend erzeugt. Fehlende/ungültige Temperaturen und
Abstände über drei Minuten unterbrechen die Verbindungslinie; Extrema bleiben
bei der Verdichtung erhalten. Die Anzeige verändert keine Warmwasserregelung.

### Eigene Lernübersicht und Gasstützwerte

Der Menüpunkt „Machine Learning“ öffnet `/heizung/lernen`. Navigation und Beobachtungs-
details werden als gemeinsame Jinja-Teile eingebunden. Drei Karten zeigen getrennt
EG, OG und Speicher, geprüfte Modellanzahl und die Datengrundlage. Der Balken ergibt
sich aus den Mindestanforderungen an gültige Zeitfenster, Tage, Zeitspanne und Heiz-/
Abkühlfenster; er ist weder Trainingsrestzeit noch ein Nachweis für Einsparungen.
Die Detailansicht erklärt fehlende Voraussetzungen je Heizungsraum. Klimageräte
bleiben reine Aufzeichnung; die bestehende Heizungsübersicht bleibt erreichbar.

Gelegentliche manuelle Ablesungen stehen dauerhaft in `heating_gas_readings` derselben
SQLite-Datenbank, unabhängig von der 90-Tage-Aufbewahrung des Messarchivs. Gespeichert
werden UTC-Ablesezeit, ganzzahlige Tausendstel m³ und Erfassungszeit. Eingaben ohne
Zeitzone gelten als Europe/Berlin. Doppelte Eingaben erzeugen keine doppelten Daten;
Gegenrichtung des Zählers oder Konflikte mit Nachbarständen werden abgelehnt. Ein
Zählerwechsel braucht eine gesonderte Behandlung. Das Formular schreibt ausschließlich
diese lokale Tabelle und hat keinen Zugriff auf Bus, Tado oder Heizprogramme.

Erst zwei Stützwerte ergeben einen gemessenen Gesamtverbrauch. Für das letzte Intervall
wird die verfügbare Relaiszeit aus der Anlagenhistorie mit Abdeckung angezeigt, zusammen
mit der bisherigen Nennleistungsreferenz. Das Gaszähler-Betriebsvolumen ist nicht direkt
das berechnete Normvolumen. Fehlende Ablesungen werden nicht interpoliert, Modelle
werden damit nicht ungeprüft umskaliert, und ein Gesamtgaszähler liefert keine gemessene
Zuordnung auf EG, OG oder Warmwasser. Die Werte dienen vorerst als unabhängiger Abgleich.
