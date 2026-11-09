'use strict';
(() => {
  const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const read=(m,k)=>m?.[k]?.quality==='valid'?m[k].value:null;
  const number=v=>v.toLocaleString('de-DE',{maximumFractionDigits:2});
  const entry=(title,meaning,effect,check)=>({title,meaning,effect,check});
  const entries={
    dhw_request_source:entry('Warmwasser-Anforderungsart','Legt fest, ob die Speicherregelung einen Temperaturfühler oder einen Thermostatkontakt verwendet.','Bei Speicherfühler wird die gemessene Speichertemperatur zur Regelung verwendet. Ein Thermostat liefert stattdessen einen Schaltzustand.','Das ist eine Konfiguration, keine erkannte Wasserentnahme. Die Wilo-Zirkulationspumpe wird dadurch nicht überwacht. Unbekannte Codes bleiben ohne erfundene Zuordnung.'),
    dhw_dedicated:entry('Warmwasser-Trennschaltung','Sonderfunktion für eine getrennte Warmwasserladung in einer Kessel-Kaskade.','Die Funktion kann einen Kessel während der Speicherladung von der Versorgung anderer Verbraucher trennen.','Nicht mit der Warmwasser-Zuordnung zu Heizkreisen, einer Zirkulationsleitung oder einem geschlossenen Absperrhahn verwechseln. Aus bedeutet nur: diese Reglerfunktion ist ausgeschaltet.'),
    burner_type:entry('Brennerart · Konfiguration','Eingestellte ein- oder zweistufige Brenneransteuerung der Eurocontrol K.','Bei zweistufiger Konfiguration verwendet der Regler zusätzliche Freigabe- und Rückstellkriterien für Stufe 2.','Diese Einstellung beweist weder eine tatsächlich angeschlossene zweite Brennerstufe noch deren Leistung. Die Verbrauchsschätzung wird dadurch nicht automatisch geändert.'),
    stage2_release_integral:entry('Stufe 2 · Freigabeintegral','Temperatur-Zeit-Schwelle für die Freigabe der zweiten Brennerstufe.','Ein länger bestehender Temperaturbedarf kann sich bis zur eingestellten Schwelle aufsummieren.','Die Einheit K·min ist Temperaturdifferenz mal Zeit. Ein Wert 10 ist weder 10 °C noch eine feste Wartezeit von 10 Minuten. Die tatsächliche zweite Brennerstufe ist nicht unabhängig bestätigt.'),
    stage2_reset_integral:entry('Stufe 2 · Rückstellintegral','Temperatur-Zeit-Schwelle für das Zurücknehmen der zweiten Brennerstufe.','Ergänzt das Freigabeintegral bei der zweistufigen Regelung.','K·min beschreibt ein Integral, keinen laufenden Countdown. Eine Einstellung ist kein Nachweis einer gerade aktiven Brennerstufe.'),
    boiler_min_oem:entry('Kesselminimum · OEM-Grenze','Vom Hersteller vorgesehene untere Begrenzung der Kesselminimaltemperatur.','Ergänzt die normale Kessel-Minimaleinstellung.','Die vorhandene Grenze wird nur angezeigt. Daraus folgt keine Empfehlung, den alten Kessel kälter zu betreiben; Kesselanforderungen und Kondensationsschutz sind zu beachten.'),
    boiler_mode:entry('Kesselbetriebsart · Einstellung','Konfiguration der Kesselregelung als Dauerbetrieb oder Automatik.','Beeinflusst die Kesselbereitschaft bei fehlendem Wärmebedarf.','Dies ist eine andere Einstellung als die Betriebsart des Heizkreises. Automatik bedeutet nicht, dass der Brenner ständig eingeschaltet ist.'),
    chimney_sweep:entry('Schornsteinfegerfunktion','Gemeldeter Zustand der Prüffunktion für Abgasmessungen.','Eine aktive Prüffunktion kann das normale bedarfsgeführte Regelverhalten übersteuern.','Die Anzeige startet keinen Test. Für die Auswertung des normalen Heizbetriebs muss ein aktiver Sonderbetrieb berücksichtigt werden.'),
    startup_boost:entry('Raumsollwertüberhöhung · Schnellaufheizung','Gespeicherter Zuschlag zum Raumsollwert für die Schnellaufheizung.','Kann unter den Bedingungen dieser Funktion das Aufheizen beschleunigen.','5 K bedeutet eine zusätzliche Vorgabe, keine gemessene Raumtemperatur und keinen Nachweis einer gerade aktiven Schnellaufheizung.'),
    adaptation_zaf1:entry('Adaptionsempfindlichkeit · ZAF1','Gespeicherter Empfindlichkeitsfaktor der automatischen Heizkurvenanpassung.','Wirkt nur, wenn die Adaption und ihre Voraussetzungen tatsächlich erfüllt sind.','Ein gespeicherter Faktor ist kein Lernfortschritt der VM. Bei ausgeschalteter Adaption wird daraus keine aktive Anpassung abgeleitet.'),
    adaptation_zaf2:entry('Adaptionsempfindlichkeit · ZAF2','Zweiter gespeicherter Empfindlichkeitsfaktor der automatischen Heizkurvenanpassung.','Ergänzt ZAF1 in der internen Reglerfunktion.','Die Zahlen sind weder Temperaturen noch eine Aussage über die Qualität des Machine Learning auf der VM.'),
    plant_type:entry('Anlagentyp · Reglercode','Vom jeweiligen Regler gemeldete Kennung seines Anlagenschemas.','Kann mit dem passenden Schaltbild der Herstelleranleitung abgeglichen werden.','K und M besitzen eigene Codes. Ein Code allein bestätigt nicht die tatsächliche Verrohrung oder Verdrahtung; hier wird kein unbekanntes Schema erfunden.'),
    clock_source:entry('Uhrzeitquelle','Zeigt, ob die Regleruhr selbstständig arbeitet, die LPB-Zeit übernimmt oder Zeitmaster ist.','Eine gemeinsame Zeitquelle unterstützt übereinstimmende Wochenprogramme von K und M.','LPB-Zeit ist keine Internet-Zeitsynchronisation. Die angezeigte aktuelle Regleruhr zusätzlich prüfen.'),
    outside_source:entry('Außentemperaturquelle · LPB','Segment und Geräteadresse des Außentemperaturlieferanten im LPB-Verbund.','Erklärt, warum beide Regler einen Außentemperaturwert verwenden können, obwohl nur einer einen lokalen Außenfühler hat.','Die Quelle ist ein aus zwei Feldern gelesener Buswert. Sie bestätigt weder die Kalibrierung noch den Montageort des Außenfühlers.'),
    room_setpoint:entry('Aktueller Raumsollwert','Die momentan vom Heizungsregler verwendete Temperaturvorgabe für den Raum.','Das Zeitprogramm kann zwischen Komfort-, Reduzier- und Frostschutzvorgabe wechseln.','Ein Sollwert von 8 °C bedeutet nicht, dass der Raum 8 °C warm ist. Die tatsächlichen Tado-Messungen stehen in der Raumansicht.'),
    nominal:entry('Komfortsollwert','Raumtemperaturvorgabe für die Komfortphasen.','Sie dient dem Regler als Grundlage für die Berechnung des Wärmebedarfs.','Ein höherer Wert öffnet nicht automatisch alle Raumthermostate. Zeitprogramm, Heizkurve und Ventile wirken zusammen.'),
    reduced:entry('Reduziertsollwert','Raumtemperaturvorgabe für die Absenkphasen.','Die Heizung kann auch in der Absenkphase weiter Wärme anfordern. Nach einer Sollwertsenkung kann eine Schnellabsenkung folgen.','Den Wert mit dem aktuellen Raumsollwert und dem Zeitprogramm desselben Heizkreises vergleichen. Er ist keine Messung der Raumtemperatur.'),
    frost:entry('Frostschutzsollwert','Eine niedrige Raumtemperaturvorgabe für den Schutzbetrieb.','Frostschutzfunktionen können auch außerhalb einer Komfortphase Heizbetrieb auslösen.','Der Raum-Frostschutzsollwert und der Anlagenfrostschutz sind verschiedene Funktionen.'),
    curve:entry('Heizkurve','Die Kennlinie verbindet Außentemperatur und benötigte Heizwassertemperatur.','Eine steilere Kennlinie erhöht den berechneten Temperaturbedarf bei sinkender Außentemperatur stärker.','Hier gilt die alte Eurocontrol-Reglerskala. Einen angezeigten Wert wie 14 nicht ungeprüft in 1,4 oder 0,14 umrechnen. EG-Fußbodenheizung und OG-Heizkörper getrennt beurteilen.'),
    parallel:entry('Parallelverschiebung','Verschiebt die Heizkennlinie gegenüber ihrer Grundlage.','Beeinflusst das Temperaturniveau zusätzlich zur Steigung der Heizkurve.','Parallelverschiebung und Steigung getrennt betrachten; den Effekt im Verlauf über vergleichbare Wetterbedingungen beobachten.'),
    room_influence:entry('Raumeinfluss','Einstellung, ob der Regler einen Raumfühlerwert in die Regelung einbeziehen soll.','Ein nutzbarer Raumwert kann die witterungsabhängige Regelung korrigieren.','„Ein“ bestätigt nur die Einstellung. Prüfen, ob am zugehörigen Regler tatsächlich ein gültiger Raumwert vorliegt. Tado wird derzeit nur angezeigt und nicht als Fühler eingespeist.'),
    room_gain:entry('Gespeicherter Einflussfaktor','Gespeicherte Stärke des Raumeinflusses.','Der Faktor kann eine Raumabweichung gewichten, wenn der Raumeinfluss mit passender Raumwertquelle wirksam ist.','Ein gespeicherter Faktor beweist keinen aktiven Raumeinfluss. Aktivierung und Raumfühlerstatus zusätzlich prüfen.'),
    differential:entry('Raumschaltdifferenz','Schaltabstand der raumtemperaturabhängigen Begrenzung.','Verhindert unter den passenden Voraussetzungen zu häufiges Ein- und Ausschalten an einer einzigen Temperaturschwelle.','Ohne passenden Raumfühler ist daraus kein Pumpenschaltgrund ableitbar. Ein nicht verfügbarer Wert kann auch eine deaktivierte Funktion bedeuten.'),
    adaptation:entry('Heizkurvenadaption','Einstellung für die automatische Anpassung der Heizkennlinie.','Die Funktion kann die Kennlinie anhand geeigneter Rückmeldungen nachführen.','„Ein“ ist kein Nachweis einer erfolgreichen Anpassung. Raumgerät, Fühlerwert und Voraussetzungen des konkreten Reglers prüfen.'),
    summer:entry('Sommer-/Wintergrenze','Außentemperaturbezogene Grenze der automatischen Heizungsumschaltung.','Die Regelung berücksichtigt dabei verarbeitete Wetterwerte und eine Umschalthysterese.','Nicht allein die aktuelle Außentemperatur mit dieser Zahl vergleichen. Auch gedämpfte Temperatur, Betriebsart und zentrale Umschaltung beachten.'),
    quick_setback:entry('Schnellabsenkungsfaktor · KON','Ein Faktor für Schnellabsenkung und Optimierung ohne verwendeten Raumfühler.','Nach dem Wechsel auf einen niedrigeren Raumsollwert kann die Pumpe vorübergehend ausgeschaltet bleiben. Die Dauer hängt auch von Wetter und Sollwertsprung ab.','10 bedeutet weder 10 Minuten noch 10 °C. Die KON-Einstellung ist kein aktiver Schnellabsenkungsstatus.'),
    flow_actual:entry('Vorlauftemperatur','Gemessene Temperatur des Heizwassers im zugehörigen Vorlauf.','Der Wert zeigt das Ergebnis der Versorgung und Mischerregelung.','Eine Abweichung vom Sollwert allein beweist keinen Defekt. Pumpenkontakt, Mischerbefehle und zeitlichen Verlauf gemeinsam prüfen.'),
    flow_setpoint:entry('Vorlaufsollwert','Vom Regler berechnete Temperaturvorgabe für das Heizwasser.','Heizkurve, Betriebsniveau, Begrenzungen und weitere Regelfunktionen können darauf einwirken.','Ein angezeigter Sollwert allein beweist keine wirksame Wärmeanforderung oder eingeschaltete Pumpe.'),
    flow_min:entry('Vorlauf · Minimum','Eingestellte untere Begrenzung der Vorlauftemperaturvorgabe.','Sie kann einen berechneten Sollwert begrenzen, wenn die Regelbedingungen dafür gelten.','Eine Mindestvorgabe bedeutet nicht, dass die Pumpe immer läuft.'),
    flow_max:entry('Vorlauf · Maximum','Eingestellte obere Begrenzung der Vorlauftemperaturvorgabe.','Begrenzt die Temperaturvorgabe im Regelbetrieb.','Für die Fußbodenheizung die Auslegung der Anlage beachten. Dieser Softwarewert ersetzt keinen vorhandenen unabhängigen Temperaturbegrenzer.'),
    boost:entry('Mischerüberhöhung','Temperaturzuschlag für die Versorgung eines gemischten Heizkreises.','Der Wärmeerzeuger kann dadurch eine höhere Temperaturvorgabe erhalten als der gemischte Heizkreis.','Die Überhöhung ist keine gemessene Temperatur und nicht der Komfortsollwert eines Raumes.'),
    overrun:entry('Pumpennachlauf','Eingestellte Nachlaufzeit nach dem Wegfall einer entsprechenden Anforderung.','Die Pumpe kann weiter angefordert werden, obwohl die eigentliche Heizanforderung bereits beendet ist.','Dies ist die konfigurierte Dauer, kein laufender Countdown und kein Beweis für einen gerade aktiven Nachlauf.'),
    pump:entry('Heizkreispumpe · Q1','Der vom Regler gemeldete Schaltzustand des Pumpenkontakts.','„Ein“ bedeutet, dass der Kontakt Pumpenbetrieb anfordert.','Es werden weder Drehzahl noch Durchfluss gemessen. Den konkreten Schaltgrund gemeinsam mit Zeitprogramm und Pumpendiagnose prüfen.'),
    mode:entry('Betriebsart','Die vom Regler gemeldete Betriebsart des Heizkreises.','In Automatik wird das Zeitprogramm berücksichtigt. Im Handbetrieb gelten andere Regeln.','Automatik ist keine dauerhafte Heizanforderung. Auch eine Absenkphase kann Heizbedarf haben.'),
    room_actual:entry('Raumfühler am Regler','Der direkt vom Eurocontrol-Regler gemeldete Raumtemperaturwert.','Ein verwendbarer Raumfühlerwert kann für Raumbegrenzung, Raumeinfluss und Adaption wichtig sein.','Tado und dieser Reglerwert sind getrennte Datenquellen. Nicht verfügbar bedeutet nicht 0 °C und darf nicht durch einen erfundenen Standardwert ersetzt werden.'),
    outside:entry('Außentemperatur','Vom Regler verwendeter Außentemperaturwert; er kann über LPB kommen.','Wichtige Eingangsgröße für die witterungsabhängige Regelung.','Ein fehlender lokaler Außenfühler schließt einen gültigen über den Bus empfangenen Außentemperaturwert nicht aus.'),
    outside_local:entry('Lokaler Außenfühler','Wert des direkt an diesem Regler angeschlossenen Außenfühlers.','Beschreibt die lokale Quelle, nicht zwingend den über LPB verwendeten Wetterwert.','Bei der M kann der lokale Wert fehlen, während die Außentemperatur über den Bus vorhanden ist.'),
    outside_attenuated:entry('Gedämpfte Außentemperatur','Zeitlich verarbeiteter Wetterwert des Reglers.','Er reagiert langsamer als der aktuelle Messwert und spielt bei der Sommer-/Winterumschaltung eine Rolle.','Unterschiede zur aktuellen Außentemperatur sind grundsätzlich zu erwarten und nicht automatisch ein Sensorfehler.'),
    outside_composite:entry('Gemischte Außentemperatur','Aus aktuellem und gedämpftem Wetterwert gebildete Regelgröße.','Die Gebäudeeinstellung beeinflusst die Mischung; diese Größe fließt in die Regelung ein.','Mit dem aktuellen und gedämpften Wert vergleichen. „Gemischt“ bezeichnet hier eine Rechengröße, keinen zusätzlichen Außenfühler.'),
    building:entry('Gebäudebauweise','Modellannahme des Reglers zur thermischen Trägheit des Gebäudes.','Beeinflusst die Verarbeitung der Wettergrößen.','„Schwer“ bedeutet eine Reglereinstellung, keine automatisch gemessene Gebäudeeigenschaft.'),
    clock:entry('Regleruhr','Wochentag und Uhrzeit, die der jeweilige Regler meldet.','Die Wochenprogramme müssen im Kontext dieser Uhr gelesen werden.','Hier werden keine unbestätigten Kalenderdaten aus alten Telegrammfeldern angezeigt. K und M können eine gemeinsame Zeitquelle verwenden.'),
    error_code:entry('Fehlercode','Aktuell gelesene Fehlermeldung des Reglers.','0 bedeutet, dass in diesem Feld keine Fehlermeldung gemeldet wird.','Fehlercode 0 beweist nicht, dass alle Räume warm sind oder alle hydraulischen Komponenten funktionieren.'),
    error_priority:entry('Fehlerpriorität','Zusatzfeld des Fehlerblocks.','Ergänzt einen gemeldeten Fehlercode.','Ohne passenden Fehlercode und Herstellerzuordnung nicht als eigenständige Störung interpretieren.'),
    relay_test:entry('Relaistest · Einstellung','Vom Regler gemeldete Auswahl des Relaistests.','Ein Relaistest ist eine Prüffunktion und ersetzt den normalen Regelbetrieb nicht.','Die Anzeige ist nur lesend. Für die Pumpenbeobachtung ist der tatsächliche Q1-Kontakt maßgeblich.'),
    lpb_power:entry('LPB-Speisungsstatus','Gemeldeter Zustand der Busspeisung.','Hilft bei der Einordnung der Buskommunikation.','„Ein“ ist keine Spannungs- oder Qualitätsmessung des Buskabels.'),
    plant_frost:entry('Anlagenfrostschutz','Einstellung der Schutzfunktion für die Anlage.','Schutzfunktionen können außerhalb normaler Komfortzeiten eingreifen.','Die Einstellung allein zeigt nicht an, dass gerade Frostschutzbetrieb aktiv ist.'),
    changeover_source:entry('Sommer-/Winterumschaltung','Die zugeordnete Umschaltfunktion bzw. deren Quelle.','Eine zentrale Umschaltung kann auf mehrere Regler wirken.','K und M verwenden hier unterschiedliche Wertebedeutungen. Diese Einstellung ist nicht der aktive Sommer-/Winterstatus.'),
    pump_function:entry('Pumpenfunktion','Konfigurierte Zuordnung des Pumpenausgangs an der K.','Die Auswertung eines Kontakts hängt von der tatsächlichen Anlagenverdrahtung ab.','Die Funktion ist eine Konfiguration, der Q1-Kontakt ein Zustand. Beides ersetzt keine Prüfung, welche Pumpe tatsächlich angeschlossen ist.'),
    remote_switch:entry('Telefon-/Fernschaltkontakt','Gemeldeter Zustand eines externen Umschaltkontakts.','Kann je nach Reglereinstellung auf die Betriebsweise wirken.','„Ein“ allein legt die konkrete Wirkung nicht fest. Verdrahtung und zugehörige Reglerfunktion prüfen.'),
    boiler:entry('Kesseltemperatur','Vom K-Regler gemeldete Isttemperatur des Kessels.','Sie kann sich von den Temperaturen der einzelnen Heizkreise unterscheiden.','Ein warmer Kessel bedeutet nicht automatisch Heizbedarf oder eine laufende Heizkreispumpe.'),
    boiler_min:entry('Kessel · Minimum','Eingestellte untere Kesseltemperaturgrenze im Regelbetrieb.','Wirkt unter den Bedingungen der Kesselregelung.','Dies ist weder die Raumtemperatur noch eine Zusage, dass der Kessel ununterbrochen auf diesem Wert bleibt.'),
    boiler_max:entry('Kessel · Maximum','Eingestellte obere Kesseltemperaturgrenze im Regelbetrieb.','Begrenzt die Temperaturvorgabe der Kesselregelung.','Kesselgrenze und Vorlaufgrenze der Fußbodenheizung sind verschiedene Einstellungen.'),
    boiler_differential:entry('Kesselschaltdifferenz','Temperaturabstand der Kessel-Schaltregelung.','Beeinflusst die temperaturabhängigen Ein- und Ausschaltbedingungen.','Die Einheit K beschreibt eine Temperaturdifferenz: 10 K sind ein Abstand von 10 Grad, keine absolute Temperatur von 10 °C.'),
    burner_min_run:entry('Mindestbrennerlaufzeit','Eingestellte Mindestlaufzeit innerhalb der Brennerregelung.','Kann die normale Taktung beeinflussen.','Eine Einstellung ist keine gemessene Laufzeit und keine Garantie gegen eine Abschaltung durch andere maßgebliche Funktionen.'),
    burner_hours:entry('Brennerbetriebsstunden','Gesamtzähler aus dem verifizierten K-Erzeugerstatus.','Ergänzt den Startzähler und die zeitweise beobachtete Relaisstatistik.','Dies ist kein Energiezähler. Der Decoder gilt für die K; der ähnlich lange M-Statusblock hat hier kein bestätigtes Stundenfeld.'),
    starts:entry('Brennerstarts','Gesamtstartzähler des K-Reglers.','Änderungen im Zähler werden für die beobachteten Starts verwendet.','Der Gesamtzähler ist nicht die Anzahl der Starts im gewählten Statistikzeitraum.'),
    burner:entry('Brennerrelais','Gemeldete Kontakte der Brennerstufen K4/K5.','Zeigen die vom Regler angeforderten Relaiszustände.','Keine Flammenmessung. Die abgetastete Relaislaufzeit ist keine direkt gemessene Brenner- oder Energiemenge.'),
    dhw:entry('Warmwassertemperatur','Gemessene Temperatur des Trinkwarmwassers am Reglerfühler.','Die Laderegelung vergleicht sie mit ihren Vorgaben.','Eine Temperatur unter dem Nennsollwert beweist für sich allein keine Störung oder gerade aktive Ladung.'),
    dhw_setpoint:entry('Warmwassersollwert','Eingestellte normale Temperaturvorgabe der Warmwasserbereitung.','Wirkt zusammen mit Warmwasserprogramm, Betriebsart und Schaltdifferenz.','Dies ist keine Raum- oder Heizkreisvorgabe. Die Hilfen geben keine pauschale Änderung der Trinkwasser-Einstellungen vor.'),
    dhw_reduced:entry('Warmwasser · Reduziertsollwert','Abgesenkte Temperaturvorgabe für die Warmwasserbereitung.','Welche Vorgabe gilt, hängt von der Warmwasserregelung ab.','Nicht mit dem Reduziertsollwert eines Heizkreises verwechseln.'),
    dhw_max:entry('Warmwasser · maximaler Nennsollwert','Obere Einstellgrenze der normalen Warmwasservorgabe.','Begrenzt eine Vorgabe, nicht die aktuelle Temperatur auf diesen Wert.','70 °C als Grenze bedeutet nicht, dass der Speicher gerade auf 70 °C geladen wird.'),
    dhw_differential:entry('Warmwasserschaltdifferenz','Temperaturabstand für die Schaltregelung der Warmwasserladung.','Ein Abstand kann erklären, warum eine Ladung nicht bei jeder kleinen Temperaturabweichung startet.','K bedeutet Temperaturdifferenz. Programm, Freigabe und weitere Regelbedingungen zusätzlich beachten.'),
    dhw_boost:entry('Überhöhung zur Warmwasserladung','Temperaturzuschlag zur Versorgung der Warmwasserladung.','Betrifft die für die Ladung angeforderte Erzeugertemperatur.','Nicht zum Raumtemperaturwert addieren und nicht als gemessene Speichertemperatur lesen.'),
    dhw_enabled:entry('Warmwasser-Betriebsart','Einstellung, ob die Warmwasserbereitung grundsätzlich freigegeben ist.','Die tatsächliche Ladung hängt zusätzlich von Bedarf und Programm ab.','„Ein“ bedeutet nicht, dass die Ladepumpe Q3 ständig laufen muss.'),
    dhw_program:entry('Warmwasserprogramm','Zeitliche Zuordnung der Warmwasserbereitung.','Kann von einem lokalen oder systemweiten Heizprogramm mit Vorverlegung abhängen.','Dies ist nicht automatisch dasselbe Programm wie die Komfortphasen eines einzelnen Heizkreises.'),
    dhw_priority:entry('Warmwasserpriorität','Konfigurierte Abstimmung von Warmwasserbereitung und Raumheizung.','Eine Vorrangfunktion kann die Wärmeabnahme der Heizkreise einschränken.','Die Einstellung „Gleitend“ allein beweist keine aktive Heizkreissperre. Q3, Anforderungen und gültige Sperrsignale gemeinsam beobachten.'),
    dhw_charging:entry('Warmwasser-Ladeart','Konfiguration von Ladepumpe oder Umschaltventil.','Beschreibt die Art der vorgesehenen Warmwasseransteuerung.','Die Ladeart ist eine Einstellung, kein gerade aktiver Pumpen- oder Ventilzustand.'),
    schedule:entry('Heizzeiten der Woche','Komfortfenster je Tag und Heizkreis.','In Automatik gilt außerhalb der Fenster die Absenkung. Pumpen werden zusätzlich nach Regelbedingungen geschaltet.','Ein lokaler Entwurf verändert die Heizung erst nach Vorschau und bestätigter Übertragung. EG und OG haben eigene Programme.'),
    quality:entry('Datenqualität','Jeder Wert wird zusammen mit seinem Abfragestatus angezeigt.','Gültig, veraltet, nicht verfügbar und noch nicht gelesen sind unterschiedliche Zustände.','Ein fehlender Wert ist weder Null noch ein Beweis für einen abgesteckten Sensor. Ursache und Funktion getrennt prüfen.'),
    signals:entry('Anforderungs- und Sperrsignale','Telegramme enthalten neben Temperatur- oder Prozentfeldern zusätzliche Attribute.','Die Felder können zur Ursachenforschung mit Pumpenwechseln verglichen werden.','Ungeklärte Attributbits erlauben keine gesicherte Aussage über die Wirksamkeit. Ein Wertfeld von 50 % beweist keinen aktiven Zwang von 50 %.'),
  };
  const aliases={burner_on_threshold:'threshold',burner_off_threshold:'threshold',mixer_open:'mixer',mixer_close:'mixer',dhw_pump:'loading'};
  entries.threshold=entry('Berechnete Brennerschalttemperatur','Vom Regler gemeldete berechnete Ein- oder Ausschalttemperatur.','Hilft beim Einordnen der Kesselregelung.','Kein manuell zu schreibender Schaltbefehl und kein Messwert des Sicherheitstemperaturbegrenzers.');
  entries.mixer=entry('Mischerantrieb','Gemeldeter Auf- oder Zu-Kontakt des Mischerantriebs.','Ein aktiver Kontakt fordert eine Bewegung in die entsprechende Richtung an.','Kein gemessener Öffnungsgrad. Beide Kontakte Aus bedeutet nur keine gemeldete Ansteuerung, nicht „Ventil geschlossen“.');
  entries.loading=entry('Warmwasser-Ladekontakt · Q3','Der gemeldete Kontakt der Warmwasser-Ladeansteuerung.','Kann bei einer Pumpenbeobachtung zusammen mit der Warmwasserpriorität betrachtet werden.','Q3 Ein allein beweist weder Durchfluss noch eine Sperre der Heizkreise.');
  const qualityText={valid:'Gültig gelesen',stale:'Veraltet',unavailable:'Kein gültiger Wert geliefert',pending:'Noch nicht gelesen',error:'Antwort nicht auswertbar'};
  function format(item){
    if(item?.quality!=='valid')return qualityText[item?.quality]||'Nicht verfügbar';
    const v=item.value;
    return typeof v==='boolean'?(v?'Ein':'Aus'):typeof v==='number'?number(v)+(item.unit?' '+item.unit:''):String(v??'—');
  }
  function getHelp(key,area,snapshot){
    const metrics=area==='anlage'?snapshot?.plant:snapshot?.floors?.[area]?.metrics;
    const item=metrics?.[key];
    const data=entries[key]||entries[aliases[key]]||(key.endsWith('_raw')?entries.signals:entries.quality);
    const notes=[];
    const sensor=metrics?.room_actual;
    if(['room_influence','room_gain','adaptation','differential','adaptation_zaf1','adaptation_zaf2'].includes(key)){
      if(sensor?.quality==='unavailable')notes.push('Bei diesem Regler wird derzeit kein gültiger Raumfühlerwert geliefert. Die Einstellung allein belegt daher keine wirksame Raumregelung.');
      else if(sensor?.quality!=='valid')notes.push('Der Raumfühlerstatus ist noch nicht verlässlich bestätigt. Fehlende oder veraltete Daten erlauben keine Aussage über die Wirksamkeit.');
    }
    if(key==='room_gain'&&read(metrics,'room_influence')===false)notes.push('Der Raumeinfluss wird als Aus gemeldet; der angezeigte Faktor bleibt ein gespeicherter Wert.');
    if(['adaptation_zaf1','adaptation_zaf2'].includes(key)&&read(metrics,'adaptation')===false)notes.push('Die Heizkurvenadaption wird als Aus gemeldet; der Faktor bleibt ein gespeicherter Wert.');
    return {...data,title:item?.label||data.title,current:item?format(item):null,quality:item?qualityText[item.quality]||'Unbekannt':null,
      updated_at:item?.updated_at||null,notes,area};
  }
  function button(key,area,label){return `<button type="button" class="heating-help-trigger" data-heating-help="${esc(key)}" data-help-area="${esc(area)}" aria-label="Hilfe zu ${esc(label)}" aria-haspopup="dialog">?</button>`;}
  function guideChecks(snapshot,area){
    const m=snapshot?.floors?.[area]?.metrics||{};
    const sensor=m.room_actual, influence=read(m,'room_influence');
    const values=[{title:'Raumfühler am Regler',value:format(sensor),note:'Die Tado-Anzeige speist derzeit keinen Raumfühlerwert ein.'}];
    if(influence===true&&sensor?.quality==='unavailable')values.push({title:'Raumeinfluss prüfen',value:'Ein · Raumwert nicht verfügbar',note:'Aktivierung und fehlender Raumwert getrennt prüfen. Daraus folgt keine automatische Änderungsempfehlung.'});
    else values.push({title:'Raumeinfluss',value:format(m.room_influence),note:sensor?.quality==='valid'?'Ein gültiger Raumwert liegt vor; die Funktionsvoraussetzungen bleiben zusätzlich zu beachten.':'Ohne gültigen Raumwert ist eine wirksame Rückmeldung nicht bestätigt.'});
    const adaptation=read(m,'adaptation');
    values.push({title:'Heizkurvenadaption',value:format(m.adaptation),note:adaptation===true?'Die aktivierte Einstellung beweist noch keine wirksame Anpassung.':adaptation===false?'Die Adaption wird als Aus gemeldet.':'Der Adaptionsstatus ist nicht verlässlich bestätigt.'});
    return values;
  }
  class View{
    constructor(dialog,guide){
      this.dialog=dialog;this.guide=guide;this.step=0;
      document.addEventListener('click',event=>{
        const trigger=event.target.closest('[data-heating-help]');
        if(trigger){this.open(trigger.dataset.heatingHelp,trigger.dataset.helpArea,trigger);return;}
        const start=event.target.closest('[data-open-heating-guide]');if(start)this.openGuide(start);
      });
      dialog.querySelector('[data-help-close]').addEventListener('click',()=>dialog.close());
      guide.querySelector('[data-guide-close]').addEventListener('click',()=>guide.close());
      guide.querySelector('[data-guide-back]').addEventListener('click',()=>this.showStep(this.step-1));
      guide.querySelector('[data-guide-next]').addEventListener('click',()=>this.step===3?guide.close():this.showStep(this.step+1));
      guide.addEventListener('click',event=>{const b=event.target.closest('[data-guide-step]');if(b)this.showStep(Number(b.dataset.guideStep));});
      dialog.addEventListener('close',()=>this.restore());
      guide.addEventListener('close',()=>this.guideTrigger?.focus({preventScroll:true}));
    }
    update(snapshot,view){
      this.snapshot=snapshot;this.view=view;
      const trigger=document.querySelector('#pump-heading [data-heating-help]');
      if(trigger)trigger.dataset.helpArea=view==='og'?'og':'eg';
    }
    restore(){
      if(this.trigger?.isConnected)this.trigger.focus({preventScroll:true});
      else if(this.key&&this.area)document.querySelector(`[data-heating-help="${this.key}"][data-help-area="${this.area}"]`)?.focus({preventScroll:true});
    }
    open(key,area,trigger){
      if(!/^[a-z_]+$/.test(key)||!['eg','og','anlage'].includes(area))return;
      this.key=key;this.area=area;this.trigger=trigger;
      const data=getHelp(key,area,this.guide.open&&this.guide.contains(trigger)?this.guideSnapshot:this.snapshot);
      this.dialog.querySelector('#heating-help-title').textContent=data.title;
      const context=area==='anlage'?'Anlage · Eurocontrol K':area==='eg'?'EG · Eurocontrol M':'OG · Eurocontrol K';
      this.dialog.querySelector('[data-help-content]').innerHTML=`<p class="help-context">${context}${data.current!==null?' · '+esc(data.current):''}</p>${data.quality?`<p class="help-status">${esc(data.quality)}${data.updated_at?' · Abfrage '+new Date(data.updated_at*1000).toLocaleTimeString('de-DE',{timeZone:'Europe/Berlin'}):''} · Stand beim Öffnen</p>`:''}<h3>Was bedeutet das?</h3><p>${esc(data.meaning)}</p><h3>Wie wirkt es sich aus?</h3><p>${esc(data.effect)}</p><h3>So ordnest du den Wert ein</h3><p>${esc(data.check)}</p>${data.notes.map(n=>`<p class="help-callout">${esc(n)}</p>`).join('')}<p class="help-source">Grundlagen: passende Eurocontrol-/Siemens-Geräteprofile. Ergänzende Funktionsbeschreibungen: <a href="https://mhgheating.co.uk/wp-content/uploads/2012/04/RVA46-D.pdf" target="_blank" rel="noopener noreferrer">Siemens RVA46</a> und <a href="https://www.hansa-heiztechnik.de/UserFiles/file/Download/Altgeraete/Regler-RVA63.pdf" target="_blank" rel="noopener noreferrer">Siemens RVA63/53</a> (abweichende Bedienzeilen). Ungeklärte Telegrammkennzeichen bleiben offen.</p>`;
      this.dialog.showModal();
      this.dialog.scrollTop=0;
    }
    openGuide(trigger){
      this.guideTrigger=trigger;this.guideSnapshot=this.snapshot?JSON.parse(JSON.stringify(this.snapshot)):null;
      this.guideAreas=this.view==='eg'||this.view==='og'?[this.view]:['eg','og'];
      this.showStep(0);this.guide.showModal();
    }
    showStep(step){
      this.step=Math.min(3,Math.max(0,step));
      const titles=['Anlage verstehen','Messwerte prüfen','Einstellungen einordnen','Verhalten beobachten'];
      this.guide.querySelector('[data-guide-progress]').innerHTML=titles.map((t,i)=>`<button type="button" data-guide-step="${i}" ${i===this.step?'aria-current="step"':''}><span>${i+1}</span>${t}</button>`).join('');
      this.guide.querySelector('#heating-guide-title').textContent=titles[this.step];
      const s=this.guideSnapshot;
      let html='';
      if(this.step===0)html='<p>Die Eurocontrol M regelt die gemischte Fußbodenheizung im EG. Die Eurocontrol K versorgt den Heizkörperkreis im OG und den Kessel. Beide Kreise getrennt beurteilen.</p><div class="help-callout">Die einzelnen Raumthermostate verteilen bzw. begrenzen die Wärme im Raum. Ein hoher Thermostatwunsch allein beweist keine laufende Heizkreispumpe oder zentrale Wärmeanforderung.</div><h3>Tado richtig einordnen</h3><p>Die Raumwerte kommen über ioBroker. Sie werden in dieser Anbindung angezeigt und nicht als Raumfühler an K oder M geschickt.</p>';
      if(this.step===1)html='<p>Zuerst die Datenqualität prüfen: „nicht verfügbar“ ist kein gemessener Nullwert. „Veraltet“ ist kein aktueller Zustand.</p>'+this.guideAreas.map(a=>`<section class="guide-floor"><h3>${a.toUpperCase()} · ${a==='eg'?'Fußbodenheizung / M':'Heizkörper / K'}</h3>${guideChecks(s,a).map(c=>`<div class="guide-check"><strong>${esc(c.title)}</strong><span>${esc(c.value)}</span><p>${esc(c.note)}</p></div>`).join('')}</section>`).join('');
      if(this.step===2)html='<p>Keine allgemeingültige Zahlenkombination passt zu jedem Gebäude. Die Hilfen erklären die vorhandenen Einstellungen; sie übertragen keine neuen Werte.</p>'+this.guideAreas.map(a=>{const m=s?.floors?.[a]?.metrics||{};return `<section class="guide-floor"><h3>${a.toUpperCase()} · vorhandene Vorgaben</h3>${['nominal','reduced','curve','parallel','flow_max','quick_setback'].filter(k=>m[k]).map(k=>`<div class="guide-setting"><span>${esc(m[k].label)} ${button(k,a,m[k].label)}</span><strong>${esc(format(m[k]))}</strong></div>`).join('')}</section>`;}).join('')+'<p class="help-callout">Bei Fußbodenheizung die thermische Trägheit berücksichtigen. Heizkurve, Raumsollwerte und Thermostatventile gemeinsam betrachten; aus einem einzelnen kalten Raum keine pauschale Erhöhung aller Werte ableiten.</p>';
      if(this.step===3)html='<h3>Ein sinnvoller Beobachtungsablauf</h3><ol><li>Regleruhr, Automatik und Komfort-/Absenkphase vergleichen.</li><li>Raumsollwert und tatsächliche Tado-Temperatur unterscheiden.</li><li>Q1, Vorlauf und Mischerbefehle im zeitlichen Zusammenhang ansehen.</li><li>In der Pumpendiagnose Signalwerte und Mitschnitt vergleichen. Unbekannte Attribute bleiben ohne sichere Ursachenzuweisung.</li></ol><div class="help-callout">Mondsymbol bedeutet reduzierten Betrieb. Es beweist keinen bestimmten Pumpen-Abschaltgrund. KON beschreibt eine Einstellung und keinen laufenden Countdown.</div><h3>Was lässt sich hier ändern?</h3><p>Die allgemeinen Heizungsparameter werden nur gelesen. Beim Zeitprogramm gibt es einen getrennten Ablauf mit Entwurf, Vorschau und bestätigter Übertragung. Diese Einrichtungshilfe ändert nichts an der Anlage.</p>';
      this.guide.querySelector('[data-guide-content]').innerHTML=html;
      this.guide.querySelector('[data-guide-back]').disabled=this.step===0;
      this.guide.querySelector('[data-guide-next]').textContent=this.step===3?'Hilfe abschließen':'Weiter';
      this.guide.querySelector('[data-guide-content]').scrollTop=0;
      if(this.guide.open)this.guide.querySelector('#heating-guide-title').focus({preventScroll:true});
    }
  }
  const api={entries,getHelp,guideChecks,button,format,View};
  if(typeof module==='object'&&module.exports)module.exports=api;else window.HeatingHelp=api;
})();
