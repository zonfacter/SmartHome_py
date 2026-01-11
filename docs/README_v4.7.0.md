# 🏠 TwinCAT SmartHome Web-HMI v4.7.0
## Professional SCADA/HMI System für TwinCAT PLC

---

## 🎯 **Über dieses Projekt:**

Ein **vollständiges Web-basiertes HMI-System** für Beckhoff TwinCAT PLCs mit:
- 🌐 Modern Responsive Web-UI (Dark Mode)
- ⚡ Echtzeit-Kommunikation (WebSocket + ADS)
- 📊 Variable Explorer mit TreeView
- 🔧 Widget-basiertes Dashboard-System
- 📈 Live-Monitoring & Analytics
- 🔄 Hot-Restart ohne Reboot
- 📝 SQLite-basiertes Logging

---

## ✨ **v4.7.0 Features:**

### **Variable Explorer** ✅
- Hierarchischer TreeView für PLC-Symbole
- Live-Suche & Filterung
- Copy-to-Clipboard
- Widget-Erstellung per Klick
- Drag & Drop Support

### **Widget-Management** ✅
- CRUD-APIs für Widgets
- Persistente Speicherung
- Lösch-Funktion (temporär)
- Auto-Type-Detection

### **Monitor-Dashboard** ✅
- Gateway-Status (Platform, GPU, Mode)
- Hardware-Monitoring (CPU/RAM via psutil)
- Latenz-Messung (PLC & WebSocket)
- Datenfluss-Visualisierung

### **System-Features** ✅
- Service Hot-Restart (Windows/Linux)
- SQLite Error-Logging
- Admin-Panel mit Logs
- Auto-Config-Creation

---

## 📦 **Installation:**

### **1. Voraussetzungen:**
```bash
Python 3.8+
pip install flask flask-socketio pyads psutil
```

### **2. Projekt-Setup:**
```bash
git clone <your-repo>
cd TwinCAT_Smarthome_Visu
python -X utf8 start_web_hmi.py --port 5001
```

### **3. Manuelle Integration (siehe `QUICK_START_INTEGRATION.md`):**
- Scripts in `index.html` einbinden
- HTML für Variable Explorer hinzufügen
- Variable Explorer initialisieren

**⏱️ Geschätzte Zeit: 10 Minuten**

---

## 🚀 **Schnellstart:**

### **1. PLC verbinden:**
```
http://localhost:5001
→ Setup → PLC Configuration
→ AMS NetID: 192.168.2.162.1.1
→ Port: 851
→ Connect
```

### **2. Symbole laden:**
```
Admin → PLC-Konfiguration
→ Upload .tpy
→ TwinCAT_Project.tpy auswählen
```

### **3. Variable Explorer nutzen:**
```
Admin → Variable Explorer
→ PLC-Symbole durchsuchen
→ Klick auf Variable → Widget erstellen
```

---

## 📖 **Dokumentation:**

| Datei | Beschreibung |
|-------|--------------|
| `QUICK_START_INTEGRATION.md` | ⚡ 10-Minuten Integrations-Guide |
| `INSTALLATION_v4.7.0.md` | 📖 Vollständige Installations- & Nutzungsanleitung |
| `FEATURE_ROADMAP.md` | 🗺️ Roadmap bis v5.0 |
| `IMPLEMENTATION_SUMMARY_v4.7.0.md` | 📝 Technische Implementierungs-Details |

---

## 🏗️ **Architektur:**

```
├── modules/
│   ├── core/
│   │   ├── config_manager.py ✅ (Widget CRUD)
│   │   ├── service_manager.py ✅ (Hot-Restart)
│   │   ├── database_logger.py ✅ (SQLite Logging)
│   │   └── plc_communication.py ✅
│   ├── gateway/
│   │   ├── data_gateway.py ✅ (Widget-Sync)
│   │   ├── web_manager.py ✅ (Hardware Monitor)
│   │   └── plc_symbol_parser.py ✅
│   └── integrations/
│       └── mqtt_module.py
├── web/
│   ├── static/js/
│   │   ├── app.js
│   │   └── components/
│   │       ├── tree_view.js ✅ (NEW)
│   │       └── variable_explorer.js ✅ (NEW)
│   └── templates/
│       └── index.html
└── config/ (Auto-Created)
    ├── twincat_config.json
    └── system_logs.db
```

---

## 🔧 **API-Endpunkte:**

### **Widgets:**
```bash
GET    /api/widgets              # Liste aller Widgets
POST   /api/widgets              # Neues Widget erstellen
PUT    /api/widgets/<id>         # Widget aktualisieren
DELETE /api/widgets/<id>         # Widget löschen
```

### **PLC:**
```bash
GET    /api/plc/symbols/tree     # Symbol-Hierarchie
POST   /api/plc/connect          # PLC verbinden
POST   /api/plc/write            # Variable schreiben
```

### **Admin:**
```bash
GET    /api/admin/logs           # System-Logs
POST   /api/admin/service/restart # Service neu starten
GET    /api/admin/service/info   # Service-Info
```

### **Monitor:**
```bash
GET    /api/monitor/dataflow     # Echtzeit-Statistiken (inkl. Hardware)
GET    /api/monitor/latency      # Latenz-Messung
```

---

## 🧪 **Testing:**

### **Unit-Tests:**
```bash
# TODO: pytest Suite hinzufügen
```

### **Manuelle Tests:**
1. ✅ PLC-Verbindung
2. ✅ Widget-Erstellung
3. ✅ Variable Explorer
4. ✅ Monitor-Dashboard
5. ✅ Service-Restart

---

## 🎨 **Screenshots:**

*(TODO: Screenshots hinzufügen)*

- Dashboard mit Widgets
- Variable Explorer TreeView
- Monitor-Dashboard
- Admin-Panel

---

## 🛣️ **Roadmap:**

### **v4.8 (geplant):**
- ✨ Widget-Editor Dialog (WYSIWYG)
- 🖱️ Drag & Drop (Variablen → Widgets)
- 🌐 MQTT Topic-Browser
- 💾 Persistentes Widget-Löschen

### **v4.9 (geplant):**
- 🔗 Connection Manager (Multi-PLC/MQTT)
- 📊 Time-Series Data (InfluxDB Integration)
- 👥 User-Management
- 📱 Mobile-Responsive Optimierungen

### **v5.0 (Vision):**
- 🤖 Auto-Widget-Generator (KI)
- 📱 Native Mobile App
- 🎨 Theme-Editor
- 📈 Advanced Analytics

Siehe `FEATURE_ROADMAP.md` für Details.

---

## 🐛 **Bekannte Issues:**

1. **Widget-Löschen nicht persistent** - Fix in v4.8
2. **MQTT Topic-Browser Backend fehlt** - Implementierung in v4.8
3. **psutil Windows-Warnung** - Optional, kann ignoriert werden

---

## 🤝 **Contributing:**

Contributions welcome! Bitte:
1. Fork das Repo
2. Feature-Branch erstellen
3. Commit mit aussagekräftiger Message
4. Pull Request erstellen

---

## 📝 **Changelog:**

### **v4.7.0 (2026-01-04):**
- ✅ Variable Explorer mit TreeView
- ✅ Widget CRUD APIs
- ✅ Hardware-Monitor Integration (psutil)
- ✅ Service Hot-Restart
- ✅ SQLite Logging
- ✅ Monitor-Dashboard Fixes

### **v4.5.3 (2025-12-20):**
- PLC-Kommunikation verbessert
- Widget-System Grundlage
- Dark Mode

---

## 📜 **Lizenz:**

MIT License - Siehe LICENSE Datei

---

## 👨‍💻 **Autor:**

TwinCAT Team
- 📧 Email: (TODO)
- 🌐 Website: (TODO)
- 💬 Discord: (TODO)

---

## 🙏 **Credits:**

- **Flask** - Web-Framework
- **Socket.IO** - WebSocket-Kommunikation
- **Pyads** - TwinCAT ADS-Protokoll
- **Lucide Icons** - Icon-System
- **Tailwind CSS** - UI-Framework
- **psutil** - Hardware-Monitoring

---

## 🆘 **Support:**

Bei Problemen:
1. 📖 Lesen Sie `QUICK_START_INTEGRATION.md`
2. 🔍 Prüfen Sie Browser-Konsole (F12)
3. 📝 Prüfen Sie Server-Logs
4. 🐛 Erstellen Sie ein GitHub Issue

---

**Made with ❤️ for Industrial Automation**

*Professional SCADA/HMI for the Modern Era*
