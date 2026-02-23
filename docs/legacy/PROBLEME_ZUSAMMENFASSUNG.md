# Probleme-Zusammenfassung & Status

## ✅ GELÖST

### 1. Dashboard Schnellzugriff
**Problem**: Buttons hatten keine Event-Listener
**Lösung**: `setupDashboardQuickActions()` Funktion hinzugefügt in `app.js:563-601`
**Status**: ✅ BEHOBEN

### 2. Log-System Zugriff
**Problem**: Admin-Page hatte keinen Log-Viewer
**Lösung**:
- HTML hinzugefügt (index.html:527-597) mit Log-Tabelle + Service-Management
- JavaScript-Funktionen (`loadLogs()`, `loadServiceInfo()`, `clearLogs()`, `restartService()`)
**Status**: ✅ BEHOBEN

### 3. Auto-Connect für konfigurierte PLCs
**Problem**: PLCs verbinden nicht automatisch beim Start
**Lösung**: Auto-Connect-Logik in `plc_communication.py:71-85` hinzugefügt
**Status**: ✅ BEHOBEN (lädt aus config_manager)

---

## ⚠️ VERBLEIBENDE PROBLEME

### 4. PLC Reconnect funktioniert nicht
**Problem**: Nach Disconnect kann nicht neu verbunden werden
**Root Cause**: `connectPLC()` speichert nur in LocalStorage, NICHT in config_manager
**Wo**: `web/static/js/app.js:418-421`

```javascript
// AKTUELL (FALSCH):
localStorage.setItem('plc_ams_id', amsId);

// SOLLTE SEIN:
// Backend-API aufrufen um in config_manager zu speichern
await fetch('/api/plc/configure', {
    method: 'POST',
    body: JSON.stringify({ ams_id, ams_port, ip_address })
});
```

**Lösung**:
1. Backend-API erstellen: `POST /api/plc/configure` (speichert in config_manager)
2. Frontend `connectPLC()` anpassen um API zu nutzen

---

### 5. UNKNOWN-Variablen Problem
**Problem**: Symbol-Auslese zeigt weiterhin UNKNOWN für Variablen
**Root Cause**: Mehrere mögliche Ursachen:

#### A) TPY-Datei nicht geladen
- Prüfen: Ist TPY-Datei hochgeladen?
- Log: `plc_data/` Verzeichnis prüfen

#### B) Widget-Sync läuft zu früh
- `data_gateway.sync_widget_subscriptions()` wird in `initialize()` aufgerufen
- ABER: PLC ist zu diesem Zeitpunkt noch NICHT verbunden!
- Lösung: Widget-Sync NACH PLC-Connect ausführen

#### C) Symbol-Parser liefert keine Typen
- `plc_symbol_parser.py` parsed TPY korrekt?
- Typen werden korrekt extrahiert?

**Debugging-Schritte**:
1. Console-Log prüfen für Widget-Sync:
   ```
   🔄 Synchronisiere X Widgets mit PLC...
   ✅ Widget-Sync abgeschlossen: X Variablen registriert
   ```

2. PLC-Status prüfen:
   ```python
   # Ist PLC verbunden wenn Widget-Sync läuft?
   if self.plc.connected:  # WICHTIG!
       self.plc.read_by_name(variable, plc_type)
   ```

3. Symbols-API testen:
   ```
   GET /api/plc/symbols?search=MAIN
   ```
   Liefert die API Typen korrekt?

---

## 🔧 FIXES NEEDED

### Fix 4: PLC Config Persistence

**Backend** (`modules/gateway/web_manager.py`):
```python
@self.app.route('/api/plc/configure', methods=['POST'])
def configure_plc():
    """Speichert PLC-Konfiguration in config_manager"""
    data = request.json

    config_mgr = self.app_context.module_manager.get_module('config_manager')
    config_mgr.set_config_value('plc_ams_net_id', data['ams_id'])
    config_mgr.set_config_value('plc_ams_port', data.get('ams_port', 851))
    config_mgr.set_config_value('plc_ip_address', data.get('ip_address', ''))
    config_mgr.save_config()

    return jsonify({'success': True})
```

**Frontend** (`web/static/js/app.js`):
```javascript
async connectPLC() {
    // ... validation ...

    // 1. Speichere Config im Backend (NICHT LocalStorage!)
    await fetch('/api/plc/configure', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            ams_id: amsId,
            ams_port: amsPort,
            ip_address: ipAddress
        })
    });

    // 2. Dann verbinden
    const response = await fetch('/api/plc/connect', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            ams_id: amsId,
            ams_port: amsPort,
            ip_address: ipAddress
        })
    });
}
```

### Fix 5: Widget-Sync Timing

**Problem**: Widget-Sync läuft BEVOR PLC verbunden ist

**Lösung 1** (Quick-Fix):
```python
# in data_gateway.py sync_widget_subscriptions()
if not self.plc:
    print("  ⚠️  Widget-Sync: PLC-Modul nicht verfügbar")
    return

if not self.plc.connected:  # NEU!
    print("  ⚠️  Widget-Sync: PLC nicht verbunden - überspringe")
    return

# ... rest of sync ...
```

**Lösung 2** (Proper):
```python
# in plc_communication.py connect()
def connect(self) -> bool:
    # ... verbindung herstellen ...

    if self.connected:
        # Trigger Widget-Sync NACH erfolgreicher Verbindung
        data_gateway = self.app_context.module_manager.get_module('data_gateway')
        if data_gateway:
            data_gateway.sync_widget_subscriptions()

    return self.connected
```

---

## 📋 Testing-Checkliste

### Nach Fix 4 (PLC Reconnect):
- [ ] PLC verbinden via Setup-Page
- [ ] Server neu starten
- [ ] PLC sollte automatisch verbinden
- [ ] PLC disconnecten
- [ ] PLC erneut verbinden (sollte funktionieren)

### Nach Fix 5 (UNKNOWN-Variablen):
- [ ] Widget mit PLC-Variable erstellen
- [ ] Server neu starten
- [ ] Widget sollte korrekten Wert zeigen (NICHT "UNKNOWN")
- [ ] Console-Log prüfen für Widget-Sync-Meldungen

---

## 🎯 Priorität

1. **Fix 4 (PLC Reconnect)** - HOCH
   - Betrifft Grundfunktionalität
   - Einfach zu beheben

2. **Fix 5 (UNKNOWN-Variablen)** - MITTEL
   - Debugging erforderlich
   - Mehrere mögliche Ursachen
