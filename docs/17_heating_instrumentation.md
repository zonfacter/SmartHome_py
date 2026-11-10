# Anlagenplan, externe Temperaturfühler und Verlustdiagnose

Die Seite `/heizung/anlagenplan` ergänzt die externe SmartHome-Anwendung. Sie verändert keine BSB-LAN-Firmware und sendet weder LPB- noch Thermostat- oder Pumpenbefehle.

## 2D-Anlagenplan

Die Zeichenfläche beginnt leer. Die Bibliothek enthält Kessel, Speicher, Heizungs-/Ladepumpe, Trinkwasser-Zirkulationspumpe, Absperrventil, Rückschlagventil, Mischer, Heizkörper, Fußbodenheizung, Verteiler, Abzweig, Temperaturfühler, Beschriftung, Ausdehnungsgefäß und Wärmetauscher.

Bauteile lassen sich verschieben, drehen, beschriften und mit Notizen versehen. Zum Verbinden den Leitungsmodus wählen und zwei Anschlusspunkte anklicken. Leitungen folgen verschobenen Bauteilen. Im Eigenschaftenbereich lassen sich Leitungstyp und zusätzliche Knicke festlegen; Knickpunkte sind verschiebbar. Für Abzweige ausdrücklich Knoten setzen. Eine bloße Kreuzung verbindet zwei Leitungen nicht. Farben sind manuell eingezeichnete Leitungsarten und keine gemessenen Temperaturen oder Strömungsrichtungen.

Rückgängig/Wiederholen, Zoom, Verschieben der Ansicht und „Alles anzeigen“ erleichtern die Bearbeitung. Die Pfeiltasten bewegen ein ausgewähltes Bauteil; Entf entfernt es samt angeschlossenen Leitungen. JSON-Export/-Import erlaubt eine lokale Sicherung und spätere Weiterbearbeitung; SVG-Export erstellt eine eigenständige Grafik. Im Browser wird ein ungespeicherter Entwurf gesichert und beim nächsten Laden zur Wiederherstellung angeboten. Der serverseitige Plan wird erst über **Plan speichern** geschrieben. Eine Versionsnummer verhindert das stille Überschreiben eines neueren Plans aus einem zweiten Browser.

Der Plan ist ein vom Betreiber dokumentiertes Schema. Die Diagnose leitet daraus keine automatisch als bestätigt geltende Anlagenhydraulik ab.

## Sieben neutrale Messkanäle

Sieben Kanäle `sensor_1` bis `sensor_7` sind vorbereitet. Sie beginnen neutral mit „Zuordnung offen“ und ohne ioBroker-ID. Die Kanalnummer ist keine bestätigte Rohrfunktion. Im Plan werden diese Kanäle als S1–S7 markiert. Eindeutige Hardwareadressen können zusätzlich hinterlegt werden, damit die Identität auch bei einer späteren Umbenennung nachvollziehbar bleibt.

Unter **Messstellen & Verlauf → ioBroker-IDs und Messstellen einrichten** können konkrete Temperatur-IDs, optional eine Messzeit-ID und eine Online-ID eingetragen werden. Datenpunkte werden ausschließlich über `getState` gelesen. Keine Objekte oder Zustände der Quelle werden geschrieben. Es werden keine MQTT-Kommandos versendet. Aufgabe und Beschriftung im ESP werden durch die Anwendung nicht automatisch geändert.

Die Funktion wird separat ausdrücklich zugeordnet: Speicherlade-Vorlauf, Speicherlade-Rücklauf, OG-Vorlauf, OG-Rücklauf, EG-Rücklauf, Trinkwasser-Zirkulationsrücklauf oder Heizungsraumluft. Jede bestätigte Funktion darf nur einmal vergeben sein. Ohne bestätigte Funktion bleibt ein Kanal im Verlauf, wird aber nicht als eine bestimmte Rohrleitung interpretiert. Beim Identifizieren mit einem kontrollierten Temperaturreiz eine **Fühleridentifikation** als Versuchsnotiz erfassen. Temperaturverläufe und bestehende Namen liefern Hinweise, ersetzen jedoch keine physische Zuordnung.

Das Beispiel `config/heating_instrumentation.example.json` zeigt die Datenstruktur für die Konfigurations-API; diese Datei wird nicht automatisch eingelesen. Die tatsächliche Zuordnung liegt privat in der SQLite-Datenbank. Reale IDs und Hardwareadressen gehören nicht in öffentliche Beispiele.

## Messzeit, Qualität und Aufzeichnung

Der separate Hintergrundleser fragt eingerichtete Kanäle ungefähr alle zehn Sekunden ab, unabhängig vom LPB-Polling und ohne offenen Browser. Lange Netzwerkantworten können das Raster verlängern. Ohne eingerichtete IDs gibt es keine Quellenabfragen und keine künstlich erzeugte Sensorhistorie.

Temperaturen müssen endliche Zahlen in °C sein. Zeichenketten, boolesche Werte, Fehlerqualität, unbestätigte Zustände, ungültige Zeiten und veraltete Daten werden nicht als gültige Messungen gespeichert. Das Standardgültigkeitsalter beträgt 60 Sekunden und ist zwischen 20 und 3600 Sekunden einstellbar. Messzeit-IDs akzeptieren Unix-Sekunden, Unix-Millisekunden oder ISO-Zeit mit ausdrücklicher Zeitzone. Ohne zusätzliche Zeit-ID gilt der ioBroker-Zustandszeitpunkt; die Datenquelle muss diesen mit tatsächlichen Messungen aktualisieren. Ein erneut zugestellter alter MQTT-Retain-Wert darf nicht dadurch als aktuelle physische Messung gelten.

Eine Online-ID darf boolesch oder textuell sein; der erwartete Wert wird ausdrücklich konfiguriert, beispielsweise `Connected`. MQTT-LWT ist ein gespeicherter Sitzungszustand und benötigt keinen periodisch erneuerten Zeitstempel. Die Temperaturmessung benötigt dennoch einen frischen Messzeitpunkt. Ein abweichender LWT-Zustand sperrt die Messung.

Die Sensorhistorie bleibt bis zu 90 Tage lokal erhalten. Darstellung: 1/6/24 Stunden sowie 7/30/90 Tage. Für längere Verläufe aggregiert SQLite auf höchstens etwa 720 Zeitraster; Minima und Maxima bleiben enthalten, unvollständige Raster werden nicht mit einer erfundenen Mittelwertkurve überbrückt. Die hochauflösende Rohaufzeichnung kann bei durchgängigem Betrieb erheblichen Datenbankplatz benötigen; eine Verkleinerung der Grafik löscht keine Rohmessungen.

Speicher- und Kesseltemperatur sowie Pumpenrelais werden als bereits vorhandener LPB-Kontext mit ihrem ursprünglichen Zeitstempel mitgeführt. Das erzeugt keine zusätzlichen Busabfragen. Ein zehn Sekunden alter Sensorpunkt macht den langsameren LPB-Kontext nicht zu einer neuen unabhängigen Messung. Kontext älter als 90 Sekunden oder mit unterbrochener Busverbindung wird ungültig.

Die reguläre Minuten-Beobachtung enthält außerdem den aktuellen Stand der externen Fühler. Die bestehende thermische Regression wird dadurch nicht automatisch um ungeprüfte Koeffizienten erweitert und darf weiter nicht steuern.

## Verlustdiagnose und Versuchsnotizen

Die separate Diagnose gruppiert etwa zehnminütige, nicht überlappende Beobachtungsfenster nach EG-/OG-Relaisstatus, gemeldeter Zirkulationshahnstellung, Entnahmeangabe und 5-K-Band der Speichertemperatur. Sie benötigt gültigen Speicherfühler, Pumpenkontext und ausdrücklich zugeordnete, gültige Fühler für Lade-Vorlauf und Lade-Rücklauf. Pumpenwechsel, Speicherladungen, Lücken, gemeldete Entnahmen und manuelle Pumpen-/Fühlertests werden ausgespart. Eine geänderte Quell- oder Funktionszuordnung verbindet nicht stillschweigend unterschiedliche Messstellen.

Starke Abkühlungen bleiben hier sichtbar; sie werden nicht automatisch als Zapfung verworfen. Nicht dokumentierte Entnahmen bleiben **unbekannt**, auch wenn kein Ereignis eingetragen wurde. „Keine Entnahme“ gilt nur für einen ausdrücklich gemeldeten, das gesamte Fenster abdeckenden Zeitraum. Eine zugleich gemeldete Entnahme hat Vorrang. Hahnstellungen gelten ab ihrem gemeldeten Zeitpunkt bis zur nächsten Meldung. Ein Hahnwechsel innerhalb des Fensters wird nicht einem konstanten Zustand zugeordnet. Die Zeiten werden ausdrücklich als Europe/Berlin behandelt; mehrdeutige bzw. fehlende Zeiten während einer Zeitumstellung werden abgelehnt.

Die Tabelle zeigt Median des Abkühltrends am Speicherfühler, Ladeleitungs-Temperaturdifferenz, Kessel-minus-Speicher und die weiteren zugeordneten Fühlermittel. Positive Abkühltrends bedeuten sinkende Fühlertemperatur; negative bedeuten Erwärmung. Die Gruppen sind keine unabhängigen kontrollierten Versuche. Unterschiedliche Kesseltemperaturen, Ladehistorie, Wärmebedarf, Umgebung und unbekannte Entnahmen können das Ergebnis beeinflussen.

Aus Pumpenrelais und Rohrtemperaturen folgen **keine gemessene Durchflussmenge, keine bestätigte Strömungsrichtung, keine Wärmeleistung und keine Gasersparnis**. Eine vermutete ungewollte Durchströmung bleibt ein Diagnosehinweis. Der Verrohrungsplan und zusätzliche Messungen erleichtern die Prüfung durch eine sachkundige Person.

## Schnittstellen und Speicherung

- `GET /api/heating/instrumentation`: aktuelle Messqualität, Originalmesszeiten, konfigurierte und identifizierte Kanäle.
- `GET|PUT /api/heating/instrumentation/config`: sieben Messstellen; PUT mit `{revision,data:{channels:[...]}}`.
- `GET /api/heating/instrumentation/history?hours=24`: Historie (1, 6, 24, 168, 720, 2160 Stunden).
- `GET /api/heating/instrumentation/diagnosis?hours=24`: beschreibende Verlustdiagnose, maximal sieben Tage.
- `GET|POST /api/heating/instrumentation/notes`: Betreiberangaben; keine Stellbefehle.
- `GET|PUT /api/heating/piping-plan`: versioniertes, validiertes Schema mit Knoten und Leitungen.

Lokale Änderungen benötigen JSON und `X-Heating-Setup: 1`; ein fremder Browser-Origin wird abgelehnt. Größenlimits, Schema-Prüfung und Versionskonflikte schützen vor beschädigten oder überschriebenen Plänen. Texte werden als Texte behandelt und im SVG/HTML maskiert; importiertes SVG/HTML oder beliebige ausführbare URLs werden nicht übernommen.

Zusätzliche Tabellen in der bestehenden privaten `config/heating_history.db`: `heating_setup`, `heating_sensor_samples` und `heating_experiment_notes`. Die vorhandenen Reglerkonfigurationen und Wochenprogramme werden nicht verändert. Vor Installation erfolgt eine Sicherung der bestehenden Datenbank und der geänderten Quelldateien.

Die Erweiterung gehört zur externen SmartHome-Anwendung, nicht zur BSB-LAN-Firmware. Umsetzung durch @zonfacter mit KI-Unterstützung; keine automatische Veröffentlichung beim Originalprojekt.
