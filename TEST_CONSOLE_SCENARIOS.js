/**
 * 🧪 CHROME CONSOLE TEST SCENARIOS
 * TwinCAT SmartHome HMI - Vollständige Test-Suite
 *
 * Kopiere diese Tests in die Chrome DevTools Console (F12)
 * und führe sie nacheinander aus.
 */

console.log('🧪 TwinCAT SmartHome HMI - Test Suite geladen');
console.log('='.repeat(60));

// =============================================================================
// TEST 1: SYSTEM STATUS
// =============================================================================
async function test1_SystemStatus() {
    console.log('\n📊 TEST 1: System Status');
    console.log('-'.repeat(60));

    try {
        const response = await fetch('/api/system/status');
        const data = await response.json();

        console.log('✅ Response Status:', response.status);
        console.log('📦 Data:', data);

        // Validierung
        if (!data.status) {
            console.error('❌ FEHLER: "status" Property fehlt!');
        } else {
            console.log('✅ Status:', data.status);
        }

        if (!data.plc) {
            console.error('❌ FEHLER: "plc" Property fehlt!');
        } else {
            console.log('✅ PLC verbunden:', data.plc.connected);
        }

        return data;
    } catch (error) {
        console.error('❌ TEST FEHLGESCHLAGEN:', error);
        return null;
    }
}

// =============================================================================
// TEST 2: PLC VERBINDUNG
// =============================================================================
async function test2_PLCConnection() {
    console.log('\n🔌 TEST 2: PLC Verbindung');
    console.log('-'.repeat(60));

    try {
        // Hole PLC Communication Modul Status
        const plcModules = await fetch('/api/admin/plcs');
        const plcData = await plcModules.json();

        console.log('📦 PLC Config:', plcData);
        console.log('✅ Total PLCs:', plcData.statistics?.total_plcs || 0);
        console.log('✅ Active PLCs:', plcData.statistics?.active_plcs || 0);

        return plcData;
    } catch (error) {
        console.error('❌ TEST FEHLGESCHLAGEN:', error);
        return null;
    }
}

// =============================================================================
// TEST 3: SYMBOL-ABRUF (CACHE)
// =============================================================================
async function test3_SymbolCache() {
    console.log('\n💾 TEST 3: Symbol-Abruf aus Cache');
    console.log('-'.repeat(60));

    try {
        const response = await fetch('/api/plc/symbols');
        const data = await response.json();

        console.log('✅ Response Status:', response.status);
        console.log('📊 Symbol Count:', data.count);
        console.log('📦 First 5 Symbols:', data.symbols?.slice(0, 5));

        // Validierung
        if (data.count === 0) {
            console.warn('⚠️ WARNUNG: Keine Symbole im Cache!');
            console.log('💡 Tipp: TPY hochladen oder Live-Abruf verwenden');
        } else {
            console.log(`✅ ${data.count} Symbole im Cache`);
        }

        // Prüfe Struktur
        if (data.symbols && data.symbols.length > 0) {
            const firstSymbol = data.symbols[0];
            console.log('\n🔍 Symbol-Struktur Check:');
            console.log('  - name:', firstSymbol.name || '❌ FEHLT');
            console.log('  - type:', firstSymbol.type || '❌ FEHLT');
            console.log('  - index_group:', firstSymbol.index_group);
            console.log('  - index_offset:', firstSymbol.index_offset);
        }

        return data;
    } catch (error) {
        console.error('❌ TEST FEHLGESCHLAGEN:', error);
        return null;
    }
}

// =============================================================================
// TEST 4: LIVE-SYMBOL-ABRUF (VON PLC)
// =============================================================================
async function test4_LiveSymbolLoad() {
    console.log('\n☁️ TEST 4: Live-Symbol-Abruf von PLC');
    console.log('-'.repeat(60));

    try {
        // Zuerst: PLC-Verbindungsstatus prüfen
        console.log('🔍 Prüfe PLC-Verbindungsstatus...');
        const statusResponse = await fetch('/api/system/status');
        const statusData = await statusResponse.json();

        console.log('📊 System Status:', statusData);
        console.log('   - PLC verbunden:', statusData.plc?.connected || false);
        console.log('   - Status:', statusData.status || 'unknown');

        if (!statusData.plc?.connected) {
            console.warn('⚠️ WARNUNG: PLC ist NICHT verbunden!');
            console.log('💡 Lösung: PLC-Verbindung zuerst herstellen:');
            console.log('   1. Gehe zu Setup-Page');
            console.log('   2. Überprüfe AMS NetId und Port');
            console.log('   3. Klicke "Verbinden"');
            console.log('   4. Warte auf Verbindungsbestätigung');
            console.log('\n🔧 ODER manuell verbinden:');
            console.log('   await fetch("/api/plc/connect", {method: "POST"})');
            return { error: 'PLC nicht verbunden', connected: false };
        }

        console.log('✅ PLC ist verbunden - starte Live-Symbol-Abruf...');

        // Nun: Live-Symbol-Abruf
        const response = await fetch('/api/plc/symbols/live', {
            method: 'POST'
        });

        console.log('✅ Response Status:', response.status);

        const data = await response.json();
        console.log('📦 Response:', data);

        if (response.ok) {
            console.log(`✅ SUCCESS: ${data.symbol_count} Symbole von PLC geladen`);
            console.log('💾 Symbole wurden im Cache gespeichert');
            console.log('🔄 TreeView sollte jetzt aktualisiert sein');
        } else {
            console.error('❌ FEHLER:', data.error);

            if (response.status === 400) {
                console.log('💡 HTTP 400 - Mögliche Ursachen:');
                console.log('   1. PLC-Verbindung wurde zwischenzeitlich getrennt');
                console.log('   2. PLC client ist None');
                console.log('   3. Connection-Status meldet false');
            } else if (response.status === 503) {
                console.log('💡 HTTP 503 - PLC-Modul nicht verfügbar');
                console.log('   Backend-Fehler beim Laden des Moduls');
            } else if (response.status === 500) {
                console.log('💡 HTTP 500 - pyads Fehler');
                console.log('   get_all_symbols() ist fehlgeschlagen');
                console.log('   Prüfe Server-Logs für Details');
            }
        }

        return data;
    } catch (error) {
        console.error('❌ TEST FEHLGESCHLAGEN:', error);
        return null;
    }
}

// =============================================================================
// TEST 5: SYMBOL-SUCHE (ERWEITERT)
// =============================================================================
async function test5_SymbolSearch(searchQuery = 'MAIN') {
    console.log('\n🔍 TEST 5: Symbol-Suche (Erweitert)');
    console.log('-'.repeat(60));
    console.log('🔎 Suche nach:', searchQuery);

    try {
        // API-Suche
        const response = await fetch(`/api/plc/symbols?search=${encodeURIComponent(searchQuery)}`);
        const data = await response.json();

        console.log('✅ Response Status:', response.status);
        console.log('📊 Gefundene Symbole:', data.count);

        if (data.count === 0) {
            console.warn('⚠️ WARNUNG: Keine Treffer!');
            console.log('💡 Mögliche Ursachen:');
            console.log('   1. Suchbegriff existiert nicht');
            console.log('   2. Search-Parameter wird nicht korrekt verarbeitet');
            console.log('   3. Symbol-Cache ist leer');
            console.log('   4. Regex-Filter ist fehlerhaft');

            // Teste ob generell Symbole vorhanden sind
            const allSymbols = await fetch('/api/plc/symbols');
            const allData = await allSymbols.json();
            console.log(`\n🔍 Debug: Total Symbole im Cache: ${allData.count}`);

            if (allData.count > 0) {
                console.log('   ℹ️ Symbole vorhanden, aber Suche findet nichts');
                console.log('   💡 Backend-Filter ist wahrscheinlich defekt');

                // Zeige erste 5 Symbol-Namen zum Vergleich
                console.log('\n📋 Erste 5 Symbole im Cache:');
                allData.symbols?.slice(0, 5).forEach(s => {
                    console.log(`   - ${s.name}`);
                });
            } else {
                console.log('   ℹ️ Kein Symbol-Cache vorhanden');
            }
        } else {
            console.log(`✅ ${data.count} Symbole gefunden`);
            console.log('\n📋 Ergebnisse (erste 10):');
            data.symbols.slice(0, 10).forEach((s, i) => {
                console.log(`   ${i + 1}. ${s.name} (${s.type})`);
            });

            // Zeige weitere Statistiken
            if (data.count > 10) {
                console.log(`\n   ... und ${data.count - 10} weitere`);
            }
        }

        // Prüfe Frontend-Suche
        console.log('\n🔍 Frontend-Suche Check:');
        const searchInput = document.getElementById('symbol-search');
        if (searchInput) {
            console.log('   ✅ Search Input gefunden');
            console.log('   Aktueller Wert:', searchInput.value);

            // Simuliere Suche
            searchInput.value = searchQuery;
            console.log('   ℹ️ Wert gesetzt auf:', searchQuery);

            // Prüfe ob Event-Listener existieren
            const listeners = getEventListeners ? getEventListeners(searchInput) : null;
            if (listeners) {
                console.log('   Event Listeners:', Object.keys(listeners));
            } else {
                console.log('   ⚠️ getEventListeners nicht verfügbar (Chrome DevTools erforderlich)');
            }

            // Trigger Input Event
            searchInput.dispatchEvent(new Event('input', { bubbles: true }));
            console.log('   🔔 Input Event getriggert');

            // Warte kurz und prüfe TreeView
            await new Promise(r => setTimeout(r, 500));

            const treeView = document.getElementById('symbol-tree');
            if (treeView) {
                const visibleNodes = treeView.querySelectorAll('li:not([style*="display: none"]), .tree-node:not(.hidden)');
                console.log(`   🌲 Sichtbare TreeView Nodes: ${visibleNodes.length}`);

                if (visibleNodes.length === 0) {
                    console.error('   ❌ FEHLER: TreeView zeigt keine Ergebnisse');
                    console.log('   💡 Frontend-Filter funktioniert nicht');
                }
            }
        } else {
            console.warn('   ⚠️ Search Input #symbol-search nicht gefunden');
        }

        return data;
    } catch (error) {
        console.error('❌ TEST FEHLGESCHLAGEN:', error);
        return null;
    }
}

// =============================================================================
// TEST 6: WIDGET-ERSTELLUNG UND DISPLAY-CHECK
// =============================================================================
async function test6_WidgetCreate() {
    console.log('\n🎨 TEST 6: Widget-Erstellung und Display-Check');
    console.log('-'.repeat(60));

    const testWidget = {
        title: 'Test Widget Console',
        type: 'boolean',
        variable: 'MAIN.bTestVariable',
        page: 'dashboard',
        position: { x: 50, y: 50 }
    };

    console.log('📤 Erstelle Widget:', testWidget);

    try {
        const response = await fetch('/api/widgets', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(testWidget)
        });

        const data = await response.json();

        console.log('✅ Response Status:', response.status);
        console.log('📦 Response:', data);

        if (response.ok) {
            const widgetId = data.id || data.widget_id;
            console.log('✅ Widget erstellt!');
            console.log('   ID:', widgetId);

            // Warte kurz für DOM-Update
            await new Promise(r => setTimeout(r, 1000));

            // Prüfe ob Widget im DOM ist
            console.log('\n🔍 Prüfe DOM-Rendering...');
            const widgetElement = document.querySelector(`[data-widget-id="${widgetId}"]`);

            if (widgetElement) {
                console.log('✅ Widget im DOM gefunden!');
                console.log('   Element:', widgetElement);
                console.log('   Sichtbar:', widgetElement.offsetParent !== null);
                console.log('   Position:', {
                    left: widgetElement.style.left,
                    top: widgetElement.style.top
                });
            } else {
                console.error('❌ Widget NICHT im DOM gefunden!');
                console.log('💡 Mögliche Ursachen:');
                console.log('   1. Widget-Rendering-Funktion nicht aufgerufen');
                console.log('   2. Falsche Page (aktuell:', window.location.hash, ')');
                console.log('   3. WebSocket-Update nicht empfangen');
                console.log('   4. DOM-Selector falsch');

                // Prüfe alle Widgets im DOM
                const allWidgets = document.querySelectorAll('[data-widget-id]');
                console.log(`\n🔍 Gefundene Widgets im DOM: ${allWidgets.length}`);
                allWidgets.forEach((w, i) => {
                    console.log(`   ${i + 1}. ID: ${w.dataset.widgetId}`);
                });
            }

            // Prüfe Widget Manager
            if (typeof widgetManager !== 'undefined') {
                console.log('\n🔍 Widget Manager Check:');
                console.log('   widgetManager existiert:', true);
                console.log('   widgets Array:', widgetManager.widgets?.length || 0);

                const foundInManager = widgetManager.widgets?.find(w => w.id === widgetId);
                if (foundInManager) {
                    console.log('   ✅ Widget in widgetManager.widgets gefunden');
                } else {
                    console.error('   ❌ Widget NICHT in widgetManager.widgets');
                }
            } else {
                console.warn('   ⚠️ widgetManager nicht definiert');
            }

            return data;
        } else {
            console.error('❌ FEHLER:', data.error);
            return null;
        }
    } catch (error) {
        console.error('❌ TEST FEHLGESCHLAGEN:', error);
        return null;
    }
}

// =============================================================================
// TEST 7: WIDGET-LISTE LADEN
// =============================================================================
async function test7_WidgetList() {
    console.log('\n📋 TEST 7: Widget-Liste');
    console.log('-'.repeat(60));

    try {
        const response = await fetch('/api/widgets');
        const data = await response.json();

        console.log('✅ Response Status:', response.status);
        console.log('📊 Anzahl Widgets:', data.length || 0);
        console.log('📦 Widgets:', data);

        if (Array.isArray(data) && data.length > 0) {
            console.log('\n🎨 Widget-Details:');
            data.forEach((widget, index) => {
                console.log(`\n  Widget ${index + 1}:`);
                console.log('    ID:', widget.id);
                console.log('    Title:', widget.title);
                console.log('    Type:', widget.type);
                console.log('    Variable:', widget.variable);
                console.log('    Page:', widget.page);
            });
        } else {
            console.warn('⚠️ Keine Widgets gefunden');
        }

        return data;
    } catch (error) {
        console.error('❌ TEST FEHLGESCHLAGEN:', error);
        return null;
    }
}

// =============================================================================
// TEST 8: TPY-UPLOAD SIMULATION
// =============================================================================
function test8_TPYUploadInfo() {
    console.log('\n📤 TEST 8: TPY-Upload Info');
    console.log('-'.repeat(60));

    console.log('💡 TPY-Upload muss über UI getestet werden:');
    console.log('   1. Gehe zu Setup-Page');
    console.log('   2. Klicke ".tpy Datei hochladen"');
    console.log('   3. Wähle TwinCAT_Project.tpy');
    console.log('   4. Beobachte Console für:');
    console.log('      - "TPY-Parsing: X Symbole gefunden"');
    console.log('      - "Symbol-Cache aktualisiert: X Symbole"');
    console.log('      - "✅ ERFOLG: X Symbole geladen"');

    console.log('\n🔍 Nach Upload erwartete Logs:');
    console.log('   📂 Root-Element: PlcProjectInfo');
    console.log('   🔍 Gefunden: 952 <Symbol> Elemente');
    console.log('   ✅ 700+ eindeutige Symbole extrahiert');
    console.log('   💾 700+ Symbole konvertiert');
    console.log('   ✅ ERFOLG: 700+ Symbole geladen');
}

// =============================================================================
// TEST 9: TREEVIEW-DATEN PRÜFEN (ERWEITERT)
// =============================================================================
async function test9_TreeViewData() {
    console.log('\n🌲 TEST 9: TreeView-Daten Prüfung (Erweitert)');
    console.log('-'.repeat(60));

    try {
        const response = await fetch('/api/plc/symbols');
        const data = await response.json();

        console.log('📊 Total Symbols im Cache:', data.count);

        // KRITISCH: Symbol-Count-Diskrepanz analysieren
        console.log('\n⚠️ SYMBOL-COUNT-ANALYSE:');
        console.log('   - Erwartet (aus TPY): 952 Symbole');
        console.log('   - Im Cache gespeichert:', data.count);
        console.log('   - Differenz:', 952 - data.count);

        if (data.count < 952) {
            console.error(`❌ FEHLER: ${952 - data.count} Symbole fehlen!`);
            console.log('💡 Mögliche Ursachen:');
            console.log('   1. Duplikat-Filter zu aggressiv');
            console.log('   2. Ungültige Symbole werden gefiltert');
            console.log('   3. Parsing-Fehler beim TPY-Import');
            console.log('   4. Cache-Speicherung unvollständig');
        } else if (data.count === 952) {
            console.log('✅ Perfekt: Alle 952 Symbole vorhanden');
        }

        // Analysiere Symbol-Namen für Hierarchie
        const nameParts = {};
        const symbolsByType = {};
        const symbolsByDepth = { depth1: 0, depth2: 0, depth3: 0, depth4plus: 0 };

        if (data.symbols) {
            data.symbols.forEach(symbol => {
                // Hierarchie
                const parts = symbol.name.split('.');
                const root = parts[0];
                nameParts[root] = (nameParts[root] || 0) + 1;

                // Tiefe
                const depth = parts.length;
                if (depth === 1) symbolsByDepth.depth1++;
                else if (depth === 2) symbolsByDepth.depth2++;
                else if (depth === 3) symbolsByDepth.depth3++;
                else symbolsByDepth.depth4plus++;

                // Typ
                const type = symbol.type || 'UNKNOWN';
                symbolsByType[type] = (symbolsByType[type] || 0) + 1;
            });
        }

        console.log('\n🏗️ Symbol-Hierarchie (Top 10):');
        Object.entries(nameParts)
            .sort((a, b) => b[1] - a[1])
            .slice(0, 10)
            .forEach(([root, count]) => {
                console.log(`   ${root}: ${count} Symbole`);
            });

        console.log('\n📏 Symbol-Tiefe:');
        console.log('   Level 1 (z.B. MAIN):', symbolsByDepth.depth1);
        console.log('   Level 2 (z.B. MAIN.var):', symbolsByDepth.depth2);
        console.log('   Level 3 (z.B. MAIN.fb.var):', symbolsByDepth.depth3);
        console.log('   Level 4+ (tief verschachtelt):', symbolsByDepth.depth4plus);

        console.log('\n🏷️ Symbol-Typen (Top 10):');
        Object.entries(symbolsByType)
            .sort((a, b) => b[1] - a[1])
            .slice(0, 10)
            .forEach(([type, count]) => {
                console.log(`   ${type}: ${count} Symbole`);
            });

        // Prüfe auf Duplikate
        const names = data.symbols?.map(s => s.name) || [];
        const uniqueNames = new Set(names);
        const duplicateCount = names.length - uniqueNames.size;

        console.log('\n🔍 Duplikat-Prüfung:');
        if (duplicateCount > 0) {
            console.warn(`⚠️ WARNUNG: ${duplicateCount} Duplikate gefunden!`);

            // Zeige alle Duplikate
            const seen = new Set();
            const duplicates = [];
            names.forEach(name => {
                if (seen.has(name)) {
                    duplicates.push(name);
                }
                seen.add(name);
            });
            console.log('   Duplikate:', duplicates);
        } else {
            console.log('   ✅ Keine Duplikate gefunden');
        }

        // Prüfe TreeView-DOM
        console.log('\n🌲 TreeView DOM-Prüfung:');
        const treeViewElement = document.getElementById('symbol-tree');
        if (treeViewElement) {
            const treeNodes = treeViewElement.querySelectorAll('li, .tree-node, [data-symbol]');
            console.log('   TreeView Element gefunden:', true);
            console.log('   Tree Nodes im DOM:', treeNodes.length);
            console.log('   HTML Länge:', treeViewElement.innerHTML.length, 'chars');

            if (treeNodes.length === 0) {
                console.error('   ❌ TreeView ist LEER!');
                console.log('   💡 TreeView wurde nicht gerendert');
            } else if (treeNodes.length < data.count) {
                console.warn(`   ⚠️ Nur ${treeNodes.length} von ${data.count} Symbolen gerendert`);
            }
        } else {
            console.warn('   ⚠️ TreeView Element #symbol-tree nicht gefunden');
            console.log('   💡 Prüfe ob Element-ID korrekt ist');
        }

        return {
            totalSymbols: data.count,
            expectedSymbols: 952,
            missing: 952 - data.count,
            nameParts,
            symbolsByDepth,
            symbolsByType,
            duplicateCount
        };
    } catch (error) {
        console.error('❌ TEST FEHLGESCHLAGEN:', error);
        return null;
    }
}

// =============================================================================
// TEST 10: WEBSOCKET VERBINDUNG
// =============================================================================
function test10_WebSocketInfo() {
    console.log('\n🔌 TEST 10: WebSocket-Verbindung');
    console.log('-'.repeat(60));

    // Prüfe ob SocketHandler existiert
    if (typeof socketHandler !== 'undefined') {
        console.log('✅ socketHandler gefunden');
        console.log('   Socket:', socketHandler.socket);
        console.log('   Connected:', socketHandler.socket?.connected);
    } else {
        console.warn('⚠️ socketHandler nicht gefunden');
    }

    // Prüfe Socket.IO global
    if (typeof io !== 'undefined') {
        console.log('✅ Socket.IO library geladen');
    } else {
        console.error('❌ Socket.IO library NICHT geladen!');
    }
}

// =============================================================================
// VOLLSTÄNDIGE TEST-SUITE AUSFÜHREN
// =============================================================================
async function runAllTests() {
    console.clear();
    console.log('🚀 STARTE VOLLSTÄNDIGE TEST-SUITE');
    console.log('='.repeat(60));
    console.log('⏰ Start:', new Date().toLocaleTimeString());
    console.log('');

    const results = {};

    // Tests sequenziell ausführen
    results.test1 = await test1_SystemStatus();
    await new Promise(r => setTimeout(r, 500));

    results.test2 = await test2_PLCConnection();
    await new Promise(r => setTimeout(r, 500));

    results.test3 = await test3_SymbolCache();
    await new Promise(r => setTimeout(r, 500));

    results.test4 = await test4_LiveSymbolLoad();
    await new Promise(r => setTimeout(r, 500));

    results.test5 = await test5_SymbolSearch('MAIN');
    await new Promise(r => setTimeout(r, 500));

    results.test6 = await test6_WidgetCreate();
    await new Promise(r => setTimeout(r, 500));

    results.test7 = await test7_WidgetList();
    await new Promise(r => setTimeout(r, 500));

    test8_TPYUploadInfo();
    await new Promise(r => setTimeout(r, 500));

    results.test9 = await test9_TreeViewData();
    await new Promise(r => setTimeout(r, 500));

    test10_WebSocketInfo();

    console.log('\n' + '='.repeat(60));
    console.log('✅ ALLE TESTS ABGESCHLOSSEN');
    console.log('⏰ Ende:', new Date().toLocaleTimeString());
    console.log('');
    console.log('📊 ZUSAMMENFASSUNG:');
    console.log('   Test 1 (System Status):', results.test1 ? '✅' : '❌');
    console.log('   Test 2 (PLC Connection):', results.test2 ? '✅' : '❌');
    console.log('   Test 3 (Symbol Cache):', results.test3?.count > 0 ? '✅' : '⚠️');
    console.log('   Test 4 (Live Load):', results.test4?.success ? '✅' : '❌');
    console.log('   Test 5 (Search):', results.test5?.count > 0 ? '✅' : '⚠️');
    console.log('   Test 6 (Widget Create):', results.test6 ? '✅' : '❌');
    console.log('   Test 7 (Widget List):', results.test7 ? '✅' : '❌');
    console.log('   Test 9 (TreeView):', results.test9 ? '✅' : '❌');

    return results;
}

// =============================================================================
// HILFSFUNKTIONEN
// =============================================================================

/**
 * Verbindet mit der PLC
 */
async function connectPLC() {
    console.log('🔌 Verbinde mit PLC...');
    try {
        const response = await fetch('/api/plc/connect', { method: 'POST' });
        const data = await response.json();
        console.log('Response:', data);
        if (response.ok) {
            console.log('✅ PLC verbunden');
        } else {
            console.error('❌ Verbindung fehlgeschlagen:', data.error);
        }
        return data;
    } catch (error) {
        console.error('❌ Fehler:', error);
        return null;
    }
}

/**
 * Trennt die PLC-Verbindung
 */
async function disconnectPLC() {
    console.log('🔌 Trenne PLC...');
    try {
        const response = await fetch('/api/plc/disconnect', { method: 'POST' });
        const data = await response.json();
        console.log('Response:', data);
        if (response.ok) {
            console.log('✅ PLC getrennt');
        }
        return data;
    } catch (error) {
        console.error('❌ Fehler:', error);
        return null;
    }
}

/**
 * Analysiert fehlende Symbole durch Vergleich mit TPY-Datei
 */
async function analyzeSymbolLoss() {
    console.log('\n🔬 SYMBOL-VERLUST ANALYSE');
    console.log('='.repeat(60));

    const cacheResponse = await fetch('/api/plc/symbols');
    const cacheData = await cacheResponse.json();

    console.log('📊 Statistik:');
    console.log('   - TPY hatte: 952 Symbole');
    console.log('   - Cache hat: ' + cacheData.count + ' Symbole');
    console.log('   - Verloren:', 952 - cacheData.count);
    console.log('   - Verlustrate:', ((952 - cacheData.count) / 952 * 100).toFixed(1) + '%');

    console.log('\n💡 Analyse:');
    if (952 - cacheData.count === 0) {
        console.log('✅ Kein Symbol-Verlust!');
    } else if (952 - cacheData.count === 201) {
        console.log('⚠️ Genau 201 Symbole fehlen');
        console.log('   Dies entspricht den Duplikaten im TPY-Filter');
        console.log('   Mögliche Ursachen:');
        console.log('   1. TPY enthält tatsächlich 201 Duplikate (NORMAL)');
        console.log('   2. Duplikat-Filter ist zu aggressiv (BUG)');
        console.log('   3. Verschiedene Symbol-Typen mit gleichem Namen');
    } else {
        console.log('⚠️ Unerwarteter Symbol-Verlust');
        console.log('   Weitere Untersuchung erforderlich');
    }

    return {
        expected: 952,
        actual: cacheData.count,
        lost: 952 - cacheData.count,
        lossRate: ((952 - cacheData.count) / 952 * 100).toFixed(1) + '%'
    };
}

// =============================================================================
// EINZELNE TESTS VERFÜGBAR MACHEN
// =============================================================================
console.log('\n📚 VERFÜGBARE TEST-FUNKTIONEN:');
console.log('   test1_SystemStatus()      - System Status prüfen');
console.log('   test2_PLCConnection()     - PLC Verbindung testen');
console.log('   test3_SymbolCache()       - Symbol-Cache laden');
console.log('   test4_LiveSymbolLoad()    - Live von PLC laden');
console.log('   test5_SymbolSearch(query) - Symbol-Suche testen');
console.log('   test6_WidgetCreate()      - Test-Widget erstellen');
console.log('   test7_WidgetList()        - Alle Widgets anzeigen');
console.log('   test8_TPYUploadInfo()     - TPY-Upload Anleitung');
console.log('   test9_TreeViewData()      - TreeView Daten prüfen');
console.log('   test10_WebSocketInfo()    - WebSocket Status');
console.log('');
console.log('🔧 HILFSFUNKTIONEN:');
console.log('   connectPLC()              - Mit PLC verbinden');
console.log('   disconnectPLC()           - PLC trennen');
console.log('   analyzeSymbolLoss()       - Symbol-Verlust analysieren');
console.log('');
console.log('🚀 VOLLSTÄNDIGE SUITE:');
console.log('   runAllTests()             - Alle Tests ausführen');
console.log('');
console.log('💡 BEISPIEL:');
console.log('   await connectPLC()');
console.log('   await test3_SymbolCache()');
console.log('   await test5_SymbolSearch("MAIN")');
console.log('   await analyzeSymbolLoss()');
console.log('   await runAllTests()');
console.log('='.repeat(60));
