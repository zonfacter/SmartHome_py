/**
 * SmartHome OS Web-HMI - Haupt-Anwendung
 * Verwaltet Navigation, Widgets, Theme und Echtzeit-Updates
 */

class SmartHomeApp {
    constructor() {
        // Aktueller State
        this.currentPage = 'dashboard';
        this.theme = localStorage.getItem('theme') || 'dark';
        this.plcConnected = false;

        // Widget-Daten
        this.widgets = {
            lights: {},
            sensors: {},
            energy: {},
            cameras: []
        };

        // Socket-Handler
        this.socket = null;

        // Symbol-Browser State
        this.currentSymbols = [];
        this.searchDebounceTimer = null;

        // Initialisierung
        this.init();
    }

    init() {
        console.log('🚀 SmartHome App startet...');

        // Theme anwenden
        this.applyTheme(this.theme);

        // Event-Listener registrieren (nach kurzem Delay für DOM)
        setTimeout(() => {
            this.setupEventListeners();
            console.log('📋 Event-Listener registriert');
        }, 100);

        // Socket.IO initialisieren
        this.initializeSocket();

        // Initiale Seite anzeigen
        this.showPage('dashboard');

        // System-Status laden
        this.loadSystemStatus();

        console.log('✅ SmartHome App bereit');
    }

    // ========================================================================
    // NAVIGATION
    // ========================================================================

    setupEventListeners() {
        // Sidebar-Navigation (Desktop/Tablet)
        const navButtons = document.querySelectorAll('[data-page]');
        console.log(`🔍 Gefundene Navigation-Buttons: ${navButtons.length}`);

        navButtons.forEach(btn => {
            const page = btn.getAttribute('data-page');
            console.log(`  ➜ Button für Seite: ${page}`);

            btn.addEventListener('click', (e) => {
                e.preventDefault();
                console.log(`🖱️ Click auf: ${page}`);
                this.showPage(page);

                // Mobile-Menü schließen
                this.closeMobileMenu();
            });
        });

        // Mobile-Hamburger-Menü
        const hamburger = document.getElementById('hamburger-btn');
        if (hamburger) {
            console.log('🍔 Hamburger-Button gefunden');
            hamburger.addEventListener('click', () => {
                console.log('🍔 Hamburger geklickt');
                this.toggleMobileMenu();
            });
        } else {
            console.warn('⚠️ Hamburger-Button NICHT gefunden');
        }

        // Theme-Toggle-Buttons
        const themeButtons = document.querySelectorAll('.theme-toggle');
        console.log(`🎨 Theme-Toggle-Buttons: ${themeButtons.length}`);

        themeButtons.forEach(btn => {
            btn.addEventListener('click', () => {
                console.log('🎨 Theme-Toggle geklickt');
                this.toggleTheme();
            });
        });

        // PLC-Connection
        const connectBtn = document.getElementById('plc-connect-btn');
        if (connectBtn) {
            console.log('🔌 PLC-Connect-Button gefunden');
            connectBtn.addEventListener('click', () => {
                this.connectPLC();
            });
        } else {
            console.warn('⚠️ PLC-Connect-Button NICHT gefunden');
        }

        const disconnectBtn = document.getElementById('plc-disconnect-btn');
        if (disconnectBtn) {
            console.log('🔌 PLC-Disconnect-Button gefunden');
            disconnectBtn.addEventListener('click', () => {
                this.disconnectPLC();
            });
        } else {
            console.warn('⚠️ PLC-Disconnect-Button NICHT gefunden');
        }
    }

    showPage(pageName) {
        console.log(`🔄 Zeige Seite: ${pageName}`);

        // Alle Seiten ausblenden (entferne 'active' Klasse)
        document.querySelectorAll('.page').forEach(page => {
            page.classList.remove('active');
        });

        // Gewünschte Seite einblenden (füge 'active' Klasse hinzu)
        const targetPage = document.getElementById(`${pageName}-page`);
        if (targetPage) {
            targetPage.classList.add('active');
            this.currentPage = pageName;
            console.log(`✅ Seite '${pageName}' ist jetzt aktiv`);

            // Navigation-Buttons aktualisieren
            document.querySelectorAll('[data-page]').forEach(btn => {
                const btnPage = btn.getAttribute('data-page');
                if (btnPage === pageName) {
                    btn.classList.add('bg-blue-600', 'text-white');
                    btn.classList.remove('text-gray-600', 'dark:text-gray-300', 'hover:bg-gray-100', 'dark:hover:bg-gray-700');
                } else {
                    btn.classList.remove('bg-blue-600', 'text-white');
                    btn.classList.add('text-gray-600', 'dark:text-gray-300', 'hover:bg-gray-100', 'dark:hover:bg-gray-700');
                }
            });

            // Seiten-spezifische Ladung
            this.onPageChange(pageName);
        } else {
            console.error(`❌ Seite '${pageName}-page' nicht gefunden!`);
        }
    }

    onPageChange(pageName) {
        console.log(`📄 Wechsel zu: ${pageName}`);

        switch(pageName) {
            case 'dashboard':
                this.loadDashboard();
                break;
            case 'lighting':
                this.loadLightingPage();
                break;
            case 'climate':
                this.loadClimatePage();
                break;
            case 'energy':
                this.loadEnergyPage();
                break;
            case 'cameras':
                this.loadCamerasPage();
                break;
            case 'setup':
                this.loadSetupPage();
                break;
            case 'admin':
                this.loadAdminPage();
                break;
            case 'widgets':
                this.loadWidgetsPage();
                break;
            case 'monitor':
                this.loadMonitorPage();
                break;
        }
    }

    toggleMobileMenu() {
        const sidebar = document.getElementById('sidebar');
        if (sidebar) {
            sidebar.classList.toggle('-translate-x-full');
        }
    }

    closeMobileMenu() {
        const sidebar = document.getElementById('sidebar');
        if (sidebar && window.innerWidth < 768) {
            sidebar.classList.add('-translate-x-full');
        }
    }

    // ========================================================================
    // THEME MANAGEMENT
    // ========================================================================

    toggleTheme() {
        this.theme = this.theme === 'dark' ? 'light' : 'dark';
        this.applyTheme(this.theme);
        localStorage.setItem('theme', this.theme);
    }

    applyTheme(theme) {
        const html = document.documentElement;

        if (theme === 'light') {
            html.classList.remove('dark');
        } else {
            html.classList.add('dark');
        }

        console.log(`🎨 Theme gewechselt zu: ${theme}`);

        // Theme-Icons aktualisieren
        document.querySelectorAll('.theme-toggle').forEach(btn => {
            const icon = btn.querySelector('i');
            if (icon) {
                if (theme === 'light') {
                    icon.classList.remove('fa-sun');
                    icon.classList.add('fa-moon');
                } else {
                    icon.classList.remove('fa-moon');
                    icon.classList.add('fa-sun');
                }
            }
        });
    }

    // ========================================================================
    // SOCKET.IO
    // ========================================================================

    initializeSocket() {
        this.socket = new SocketHandler();

        // ⭐ v5.1.0: Initialize Variable Manager
        this.variableManager = new VariableManager(this.socket.socket);
        console.log('✅ Variable Manager initialisiert');

        // System-Capabilities
        this.socket.registerCallback('system_capabilities', (data) => {
            console.log('📊 System-Capabilities:', data);
            this.updateSystemInfo(data);
        });

        // Initial-Telemetrie
        this.socket.registerCallback('initial_telemetry', (data) => {
            console.log('📡 Initial-Telemetrie erhalten:', Object.keys(data).length, 'Einträge');
            this.updateAllWidgets(data);
        });

        // Telemetrie-Updates
        this.socket.registerCallback('telemetry_update', (data) => {
            this.updateWidget(data.key, data.value);
        });

        // Blob-Updates
        this.socket.registerCallback('blob_update', (data) => {
            console.log('🖼️ Blob-Update:', data.key);
            this.updateBlob(data.key);
        });

        // PLC-Schreib-Ergebnis
        this.socket.registerCallback('plc_write_result', (data) => {
            if (data.success) {
                console.log(`✅ PLC-Write OK: ${data.symbol} = ${data.value}`);
            } else {
                console.error(`❌ PLC-Write Fehler: ${data.error}`);
            }
        });
    }

    // ========================================================================
    // SYSTEM
    // ========================================================================

    async loadSystemStatus() {
        try {
            const response = await fetch('/api/system/status');
            const data = await response.json();

            console.log('🖥️ System-Status:', data);

            if (data.capabilities) {
                this.updateSystemInfo(data.capabilities);
            }

            // Lade auch Abhängigkeiten
            this.checkDependencies();

        } catch (error) {
            console.error('Fehler beim Laden des System-Status:', error);
        }
    }

    async checkDependencies() {
        console.log('🔍 Prüfe Abhängigkeiten...');

        try {
            const response = await fetch('/api/system/dependencies');
            const deps = await response.json();

            console.log('📦 Abhängigkeiten:', deps);

            // Update UI
            this.updateDependencyStatus('pyads', deps['pyads'] || {});
            this.updateDependencyStatus('paho-mqtt', deps['paho.mqtt'] || {});
            this.updateDependencyStatus('ffmpeg', deps['ffmpeg'] || {});

        } catch (error) {
            console.error('❌ Fehler beim Prüfen der Abhängigkeiten:', error);
        }
    }

    updateDependencyStatus(name, dep) {
        const elemId = `dep-${name}`;
        const elem = document.getElementById(elemId);
        if (!elem) return;

        const badge = elem.querySelector('span:last-child');
        if (!badge) return;

        if (dep.available) {
            badge.className = 'px-2 py-1 text-xs rounded bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300';
            badge.textContent = '✓ Verfügbar';

            // Zeige Version falls vorhanden
            if (dep.version) {
                badge.title = dep.version;
            }
        } else {
            badge.className = 'px-2 py-1 text-xs rounded bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300';
            badge.textContent = '✗ Nicht installiert';

            // Zeige Install-Befehl
            if (dep.install) {
                badge.title = `Installation: ${dep.install}`;
            }
        }
    }

    updateSystemInfo(caps) {
        // Plattform
        const platformElem = document.getElementById('sys-platform');
        if (platformElem && caps.platform) {
            const platformMap = {
                'windows': 'Windows',
                'linux': 'Linux',
                'darwin': 'macOS'
            };
            platformElem.textContent = platformMap[caps.platform] || caps.platform;
        }

        // GPU-Info im Setup aktualisieren
        const gpuInfo = document.getElementById('gpu-info');
        if (gpuInfo) {
            if (caps.gpu_available) {
                const gpuList = caps.gpu_list || [];
                const primary = caps.primary_gpu || caps.gpu_vendor || 'Unbekannt';

                let html = `<div class="font-medium text-green-400">✅ GPU verfügbar</div>`;
                html += `<div class="text-sm mt-1">Primär: ${primary}</div>`;

                if (gpuList.length > 1) {
                    html += `<div class="text-xs mt-2">Alle GPUs:</div>`;
                    html += `<ul class="text-xs ml-4 mt-1">`;
                    gpuList.forEach((gpu, i) => {
                        const isPrimary = gpu === primary;
                        html += `<li class="${isPrimary ? 'font-bold text-blue-400' : 'text-gray-400'}">${gpu}${isPrimary ? ' ⭐' : ''}</li>`;
                    });
                    html += `</ul>`;
                }

                // Features
                const features = [];
                if (caps.has_quicksync) features.push('QuickSync');
                if (caps.has_nvenc) features.push('NVENC');
                if (caps.has_vaapi) features.push('VAAPI');

                if (features.length > 0) {
                    html += `<div class="text-xs mt-2">Features: ${features.join(', ')}</div>`;
                }

                gpuInfo.innerHTML = html;
            } else {
                gpuInfo.innerHTML = '<div class="text-gray-400">❌ Keine GPU erkannt</div>';
            }
        }

        // Deployment-Mode
        const modeInfo = document.getElementById('deployment-mode');
        if (modeInfo) {
            modeInfo.textContent = caps.mode || 'Unbekannt';
        }
    }

    // ========================================================================
    // PLC CONNECTION
    // ========================================================================

    async connectPLC() {
        const amsId = document.getElementById('plc-ams-id')?.value;
        const amsPort = parseInt(document.getElementById('plc-ams-port')?.value || '851');
        const ipAddress = document.getElementById('plc-ip-address')?.value;

        if (!amsId) {
            alert('Bitte AMS Net ID eingeben!');
            return;
        }

        console.log('🔌 Verbinde PLC:', amsId);

        // Speichere Konfiguration in LocalStorage
        localStorage.setItem('plc_ams_id', amsId);
        localStorage.setItem('plc_ams_port', amsPort.toString());
        localStorage.setItem('plc_ip_address', ipAddress);

        try {
            const response = await fetch('/api/plc/connect', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    ams_id: amsId,
                    ams_port: amsPort,
                    ip_address: ipAddress
                })
            });

            const data = await response.json();

            if (data.success) {
                this.plcConnected = true;
                this.updatePLCStatus(true);
                console.log('✅ PLC verbunden');
            } else {
                alert('PLC-Verbindung fehlgeschlagen: ' + (data.error || 'Unbekannter Fehler'));
            }
        } catch (error) {
            console.error('Fehler bei PLC-Verbindung:', error);
            alert('Fehler bei PLC-Verbindung: ' + error.message);
        }
    }

    async disconnectPLC() {
        console.log('🔌 Trenne PLC...');

        try {
            const response = await fetch('/api/plc/disconnect', {
                method: 'POST'
            });

            const data = await response.json();

            if (data.success) {
                this.plcConnected = false;
                this.updatePLCStatus(false);
                console.log('✅ PLC getrennt');
            }
        } catch (error) {
            console.error('Fehler beim Trennen der PLC:', error);
        }
    }

    updatePLCStatus(connected) {
        const statusBadge = document.getElementById('plc-status-badge');
        const connectBtn = document.getElementById('plc-connect-btn');
        const disconnectBtn = document.getElementById('plc-disconnect-btn');

        if (statusBadge) {
            if (connected) {
                statusBadge.textContent = '🟢 Verbunden';
                statusBadge.className = 'px-3 py-1 rounded-full text-sm bg-green-500 text-white';
            } else {
                statusBadge.textContent = '🔴 Getrennt';
                statusBadge.className = 'px-3 py-1 rounded-full text-sm bg-red-500 text-white';
            }
        }

        if (connectBtn) connectBtn.disabled = connected;
        if (disconnectBtn) disconnectBtn.disabled = !connected;
    }

    // ========================================================================
    // WIDGET UPDATES
    // ========================================================================

    updateAllWidgets(telemetryData) {
        // Aktualisiert alle Widgets mit initialen Daten
        for (const [key, value] of Object.entries(telemetryData)) {
            this.updateWidget(key, value);
        }
    }

    updateWidget(key, value) {
        // Dashboard-Stats
        if (key === 'PLC.MAIN.temperature' || key.includes('temperature')) {
            this.updateDashboardStat('temp-value', value, '°C');
        }

        if (key.includes('pv_power') || key.includes('PV.power')) {
            this.updateDashboardStat('pv-value', (value / 1000).toFixed(1), 'kW');
        }

        if (key.includes('battery') && key.includes('soc')) {
            this.updateDashboardStat('battery-value', value, '%');
        }

        // Speichere für spätere Verwendung
        this.widgets[key] = value;
    }

    updateDashboardStat(elementId, value, unit = '') {
        const element = document.getElementById(elementId);
        if (element) {
            element.textContent = value + (unit ? ' ' + unit : '');
        }
    }

    updateBlob(key) {
        // Aktualisiere Blob-referenzierende Elemente (z.B. Bilder)
        const img = document.querySelector(`img[data-blob="${key}"]`);
        if (img) {
            img.src = `/api/blob/${key}?t=${Date.now()}`;
        }
    }

    // ========================================================================
    // PAGE LOADERS
    // ========================================================================

    async loadDashboard() {
        console.log('📊 Lade Dashboard...');

        // Setup Schnellzugriff-Buttons (FIX)
        this.setupDashboardQuickActions();

        // Lade Widgets für Dashboard-Page
        await this.loadAndRenderWidgets('dashboard');

        // Telemetrie-Daten abrufen
        try {
            const response = await fetch('/api/telemetry');
            const data = await response.json();

            this.updateAllWidgets(data);

            // Aktive-Lichter-Zähler
            let activeLights = 0;
            for (const [key, value] of Object.entries(data)) {
                if (key.includes('light') && value === true) {
                    activeLights++;
                }
            }
            this.updateDashboardStat('active-lights', activeLights, 'an');

        } catch (error) {
            console.error('Fehler beim Laden der Dashboard-Daten:', error);
        }
    }

    setupDashboardQuickActions() {
        // Schnellzugriff-Buttons im Dashboard
        const quickActions = document.querySelectorAll('#dashboard-page .grid button');
        if (!quickActions || quickActions.length === 0) return;

        quickActions.forEach((btn, index) => {
            const span = btn.querySelector('span');
            if (!span) return;

            const actionName = span.textContent.trim();

            // Entferne alte Event-Listener
            btn.replaceWith(btn.cloneNode(true));
            const newBtn = document.querySelectorAll('#dashboard-page .grid button')[index];

            newBtn.addEventListener('click', () => {
                console.log(`🎯 Schnellzugriff: ${actionName}`);

                switch(actionName) {
                    case 'Alle Lichter':
                        this.showPage('lighting');
                        break;
                    case 'Heizung':
                        this.showPage('climate');
                        break;
                    case 'Alarm':
                        alert('🚨 Alarm-System: Noch nicht implementiert');
                        break;
                    case 'Kameras':
                        this.showPage('cameras');
                        break;
                    default:
                        console.warn(`Unbekannte Aktion: ${actionName}`);
                }
            });
        });

        console.log(`✅ ${quickActions.length} Schnellzugriff-Buttons verbunden`);
    }

    async loadLightingPage() {
        console.log('💡 Lade Beleuchtung...');

        // ⭐ v5.1.1: Lade Widgets für diese Page
        await this.loadAndRenderWidgets('lighting');

        const container = document.getElementById('lighting-grid');
        if (!container) return;

        // Beispiel-Lichter (später dynamisch aus PLC)
        const lights = [
            { id: 'light_wz', name: 'Wohnzimmer', symbol: 'MAIN.VbAusgang6', state: false },
            { id: 'light_kz', name: 'Küche', symbol: 'MAIN.lights.kitchen', state: false },
            { id: 'light_sz', name: 'Schlafzimmer', symbol: 'MAIN.lights.bedroom', state: false },
            { id: 'light_bz', name: 'Bad', symbol: 'MAIN.lights.bathroom', state: false },
            { id: 'light_fl', name: 'Flur', symbol: 'MAIN.lights.hallway', state: false },
            { id: 'light_au', name: 'Außen', symbol: 'MAIN.lights.outdoor', state: false }
        ];

        container.innerHTML = '';

        lights.forEach(light => {
            const card = this.createLightCard(light);
            container.appendChild(card);
        });

        // Icons aktualisieren
        if (typeof lucide !== 'undefined') {
            lucide.createIcons();
        }
    }

    createLightCard(light) {
        const div = document.createElement('div');
        div.className = 'bg-white dark:bg-gray-800 rounded-lg shadow p-6 hover:bg-gray-50 dark:hover:bg-gray-750 transition-colors relative group';
        div.setAttribute('data-light-id', light.id);

        const state = this.widgets[`PLC.${light.symbol}`] || light.state;
        const stateClass = state ? 'bg-yellow-500' : 'bg-gray-400 dark:bg-gray-600';

        div.innerHTML = `
            <!-- Delete Button (nur bei Hover sichtbar) -->
            <button class="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity p-1 bg-red-500 hover:bg-red-600 text-white rounded delete-widget-btn" title="Löschen">
                <i data-lucide="trash-2" class="w-4 h-4"></i>
            </button>

            <div class="flex items-center justify-between mb-4">
                <div class="flex items-center space-x-3">
                    <i data-lucide="lightbulb" class="w-10 h-10 ${state ? 'text-yellow-500' : 'text-gray-400 dark:text-gray-500'}"></i>
                </div>
                <div class="w-12 h-6 ${stateClass} rounded-full relative cursor-pointer toggle-switch" data-symbol="${light.symbol}">
                    <div class="absolute w-4 h-4 bg-white rounded-full top-1 transition-all ${state ? 'right-1' : 'left-1'}"></div>
                </div>
            </div>
            <div class="text-lg font-semibold text-gray-900 dark:text-white">${light.name}</div>
            <div class="text-sm text-gray-600 dark:text-gray-400">${state ? 'Eingeschaltet' : 'Ausgeschaltet'}</div>
        `;

        // Toggle-Handler
        const toggle = div.querySelector('.toggle-switch');
        toggle.addEventListener('click', () => {
            this.toggleLight(light.symbol, !state);
        });

        // Delete-Handler
        const deleteBtn = div.querySelector('.delete-widget-btn');
        deleteBtn.addEventListener('click', (e) => {
            e.stopPropagation(); // Verhindert Toggle
            this.deleteLightWidget(light.id, light.name, div);
        });

        return div;
    }

    deleteLightWidget(lightId, lightName, element) {
        if (!confirm(`Widget "${lightName}" wirklich löschen?\n\n⚠️ Änderung ist nur temporär!`)) return;

        // Entferne aus DOM
        element.remove();

        console.log(`✅ Widget ${lightId} gelöscht (temporär - wird beim Neuladen zurückgesetzt)`);
    }

    async toggleLight(symbol, newState) {
        console.log(`💡 Schalte Licht: ${symbol} -> ${newState}`);

        // Via Socket.IO (mit SocketHandler API)
        this.socket.writePLC(symbol, newState, (result) => {
            if (result.success) {
                console.log(`✅ Licht ${symbol} geschaltet: ${newState}`);
            } else {
                console.error(`❌ Fehler beim Schalten: ${result.error}`);
            }
        });

        // Optimistic Update
        this.widgets[`PLC.${symbol}`] = newState;
        this.loadLightingPage();
    }

    async loadClimatePage() {
        console.log('🌡️ Lade Klima...');

        // ⭐ v5.1.1: Lade Widgets für diese Page
        await this.loadAndRenderWidgets('climate');

        const container = document.getElementById('climate-grid');
        if (!container) return;

        // Beispiel-Sensoren
        const sensors = [
            { name: 'Wohnzimmer', symbol: 'MAIN.temp.livingroom', temp: 22.5, humidity: 45 },
            { name: 'Schlafzimmer', symbol: 'MAIN.temp.bedroom', temp: 20.1, humidity: 50 },
            { name: 'Küche', symbol: 'MAIN.temp.kitchen', temp: 23.8, humidity: 55 },
            { name: 'Bad', symbol: 'MAIN.temp.bathroom', temp: 24.2, humidity: 60 }
        ];

        container.innerHTML = '';

        sensors.forEach(sensor => {
            const temp = this.widgets[`PLC.${sensor.symbol}`] || sensor.temp;

            const card = document.createElement('div');
            card.className = 'bg-white dark:bg-gray-800 rounded-lg shadow p-6';
            card.innerHTML = `
                <div class="flex items-center justify-between mb-3">
                    <i data-lucide="thermometer" class="w-10 h-10 text-blue-500"></i>
                    <div class="text-right">
                        <div class="text-xs text-gray-500 dark:text-gray-400">Luftfeuchtigkeit</div>
                        <div class="text-sm font-semibold text-gray-900 dark:text-white">${sensor.humidity}%</div>
                    </div>
                </div>
                <div class="text-lg font-semibold text-gray-900 dark:text-white mb-2">${sensor.name}</div>
                <div class="text-4xl font-bold text-gray-900 dark:text-white">${temp}°C</div>
            `;
            container.appendChild(card);
        });

        // Icons aktualisieren
        if (typeof lucide !== 'undefined') {
            lucide.createIcons();
        }
    }

    async loadEnergyPage() {
        console.log('⚡ Lade Energie...');

        // ⭐ v5.1.1: Lade Widgets für diese Page
        await this.loadAndRenderWidgets('energy');

        // Energie-Widgets werden über Telemetrie aktualisiert
        // Hier könnten Charts/Graphen initialisiert werden
    }

    async loadCamerasPage() {
        console.log('📹 Lade Kameras...');

        // ⭐ v5.1.1: Lade Widgets für diese Page
        await this.loadAndRenderWidgets('cameras');

        // Registriere Add-Camera-Button
        const addCameraBtn = document.getElementById('add-camera-btn');
        if (addCameraBtn && !addCameraBtn.hasAttribute('data-listener-attached')) {
            addCameraBtn.addEventListener('click', () => {
                this.addCamera();
            });
            addCameraBtn.setAttribute('data-listener-attached', 'true');
        }

        // Lade gespeicherte Kameras aus LocalStorage
        this.loadSavedCameras();
    }

    addCamera() {
        const nameInput = document.getElementById('camera-name');
        const urlInput = document.getElementById('camera-rtsp-url');

        const name = nameInput?.value?.trim();
        const streamUrl = urlInput?.value?.trim();

        if (!name || !streamUrl) {
            alert('Bitte Name und Stream-URL eingeben!');
            return;
        }

        // Validiere Stream-URL (RTSP oder MJPEG/HTTP)
        const isRTSP = streamUrl.startsWith('rtsp://');
        const isMJPEG = streamUrl.startsWith('http://') || streamUrl.startsWith('https://');

        if (!isRTSP && !isMJPEG) {
            alert('Ungültige Stream-URL! Format: rtsp://... oder http(s)://...');
            return;
        }

        // Lade bestehende Kameras
        let cameras = JSON.parse(localStorage.getItem('cameras') || '[]');

        // Ermittle Stream-Typ
        const streamType = isRTSP ? 'RTSP' : 'MJPEG';

        // Füge neue Kamera hinzu
        cameras.push({
            id: Date.now(),
            name: name,
            streamUrl: streamUrl,
            streamType: streamType
        });

        // Speichere
        localStorage.setItem('cameras', JSON.stringify(cameras));

        // Leere Inputs
        if (nameInput) nameInput.value = '';
        if (urlInput) urlInput.value = '';

        console.log(`✅ Kamera hinzugefügt: ${name}`);

        // Lade Liste neu
        this.loadSavedCameras();
    }

    loadSavedCameras() {
        const cameraListContainer = document.getElementById('camera-list');
        const camerasGridContainer = document.getElementById('cameras-grid');

        if (!cameraListContainer || !camerasGridContainer) return;

        // Lade Kameras aus LocalStorage
        const cameras = JSON.parse(localStorage.getItem('cameras') || '[]');

        if (cameras.length === 0) {
            cameraListContainer.innerHTML = '<p class="text-sm text-gray-500">Keine Kameras konfiguriert</p>';
            camerasGridContainer.innerHTML = '<p class="text-gray-500">Kameras werden nach Konfiguration hier angezeigt...</p>';
            return;
        }

        // Rendere Kamera-Liste
        let listHtml = '<div class="space-y-2">';
        cameras.forEach(camera => {
            const streamUrl = camera.streamUrl || camera.rtspUrl; // Backward compatibility
            const streamType = camera.streamType || 'RTSP';

            listHtml += `
                <div class="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-700 rounded-lg">
                    <div class="flex items-center space-x-3">
                        <i data-lucide="video" class="w-5 h-5 text-blue-500"></i>
                        <div>
                            <p class="font-medium text-gray-900 dark:text-white">${camera.name}</p>
                            <p class="text-xs text-gray-500 font-mono">${streamUrl}</p>
                            <span class="text-xs px-2 py-0.5 rounded ${streamType === 'MJPEG' ? 'bg-green-100 text-green-800' : 'bg-blue-100 text-blue-800'}">${streamType}</span>
                        </div>
                    </div>
                    <button class="px-3 py-1 bg-red-500 text-white text-sm rounded hover:bg-red-600 remove-camera-btn"
                            data-camera-id="${camera.id}">
                        <i data-lucide="trash-2" class="w-4 h-4 inline"></i>
                    </button>
                </div>
            `;
        });
        listHtml += '</div>';
        cameraListContainer.innerHTML = listHtml;

        // Rendere Live-Streams
        let gridHtml = '';
        cameras.forEach(camera => {
            const streamUrl = camera.streamUrl || camera.rtspUrl;
            const streamType = camera.streamType || 'RTSP';

            // MJPEG kann direkt im <img> angezeigt werden
            if (streamType === 'MJPEG') {
                gridHtml += `
                    <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
                        <h3 class="font-semibold text-gray-900 dark:text-white mb-2">${camera.name}</h3>
                        <div class="aspect-video bg-gray-900 rounded overflow-hidden">
                            <img src="${streamUrl}" alt="${camera.name}" class="w-full h-full object-cover"
                                 onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';">
                            <div class="w-full h-full flex items-center justify-center text-white bg-gray-900" style="display:none;">
                                <div class="text-center">
                                    <i data-lucide="alert-circle" class="w-12 h-12 mx-auto mb-2 text-red-500"></i>
                                    <p class="text-sm">Stream nicht erreichbar</p>
                                </div>
                            </div>
                        </div>
                        <p class="text-xs text-gray-500 dark:text-gray-400 mt-2 font-mono truncate">${streamUrl}</p>
                        <span class="text-xs px-2 py-0.5 rounded bg-green-100 text-green-800 inline-block mt-1">MJPEG (Live)</span>
                    </div>
                `;
            } else {
                // RTSP benötigt Transkodierung
                gridHtml += `
                    <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
                        <h3 class="font-semibold text-gray-900 dark:text-white mb-2">${camera.name}</h3>
                        <div class="aspect-video bg-gray-900 rounded flex items-center justify-center text-white">
                            <div class="text-center">
                                <i data-lucide="play-circle" class="w-12 h-12 mx-auto mb-2"></i>
                                <p class="text-sm">Stream wird transkodiert...</p>
                                <p class="text-xs text-gray-400 mt-1">RTSP → HLS</p>
                            </div>
                        </div>
                        <p class="text-xs text-gray-500 dark:text-gray-400 mt-2 font-mono truncate">${streamUrl}</p>
                        <span class="text-xs px-2 py-0.5 rounded bg-blue-100 text-blue-800 inline-block mt-1">RTSP (Transkodierung erforderlich)</span>
                    </div>
                `;
            }
        });
        camerasGridContainer.innerHTML = gridHtml;

        // Icons aktualisieren
        if (typeof lucide !== 'undefined') {
            lucide.createIcons();
        }

        // Event-Listener für Löschen-Buttons
        document.querySelectorAll('.remove-camera-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const cameraId = parseInt(btn.getAttribute('data-camera-id'));
                this.removeCamera(cameraId);
            });
        });
    }

    removeCamera(cameraId) {
        let cameras = JSON.parse(localStorage.getItem('cameras') || '[]');
        cameras = cameras.filter(cam => cam.id !== cameraId);
        localStorage.setItem('cameras', JSON.stringify(cameras));

        console.log(`🗑️ Kamera entfernt: ID ${cameraId}`);
        this.loadSavedCameras();
    }

    __OLD_loadCamerasPage_BACKUP() {
        const container = document.getElementById('cameras-grid');
        if (!container) return;

        // Beispiel-Kameras
        const cameras = [
            { name: 'Eingang', url: 'rtsp://192.168.1.100:554/stream1' },
            { name: 'Garten', url: 'rtsp://192.168.1.101:554/stream1' },
            { name: 'Garage', url: 'rtsp://192.168.1.102:554/stream1' }
        ];

        container.innerHTML = '';

        cameras.forEach(camera => {
            const card = document.createElement('div');
            card.className = 'bg-gray-800 rounded-lg overflow-hidden';
            card.innerHTML = `
                <div class="aspect-video bg-gray-900 flex items-center justify-center">
                    <i class="fas fa-video text-6xl text-gray-600"></i>
                </div>
                <div class="p-4">
                    <div class="font-medium">${camera.name}</div>
                    <div class="text-sm text-gray-400 mt-1">${camera.url}</div>
                </div>
            `;
            container.appendChild(card);
        });
    }

    async loadSetupPage() {
        console.log('⚙️ Lade Setup...');

        // ⭐ v5.1.1: Lade Widgets für diese Page
        await this.loadAndRenderWidgets('setup');

        // Lade gespeicherte PLC-Konfiguration aus LocalStorage
        const savedAmsId = localStorage.getItem('plc_ams_id');
        const savedAmsPort = localStorage.getItem('plc_ams_port');
        const savedIpAddress = localStorage.getItem('plc_ip_address');

        if (savedAmsId) {
            const amsIdInput = document.getElementById('plc-ams-id');
            if (amsIdInput) amsIdInput.value = savedAmsId;
        }

        if (savedAmsPort) {
            const amsPortInput = document.getElementById('plc-ams-port');
            if (amsPortInput) amsPortInput.value = savedAmsPort;
        }

        if (savedIpAddress) {
            const ipAddressInput = document.getElementById('plc-ip-address');
            if (ipAddressInput) ipAddressInput.value = savedIpAddress;
        }

        // Setup PLC-Button Event-Listener (falls noch nicht registriert)
        const connectBtn = document.getElementById('plc-connect-btn');
        if (connectBtn && !connectBtn.hasAttribute('data-listener-attached')) {
            console.log('🔌 Registriere PLC-Connect-Button');
            connectBtn.addEventListener('click', () => {
                this.connectPLC();
            });
            connectBtn.setAttribute('data-listener-attached', 'true');
        }

        const disconnectBtn = document.getElementById('plc-disconnect-btn');
        if (disconnectBtn && !disconnectBtn.hasAttribute('data-listener-attached')) {
            console.log('🔌 Registriere PLC-Disconnect-Button');
            disconnectBtn.addEventListener('click', () => {
                this.disconnectPLC();
            });
            disconnectBtn.setAttribute('data-listener-attached', 'true');
        }

        // Setup Symbol-Browser (falls noch nicht registriert)
        const symbolSearchBtn = document.getElementById('symbol-search-btn');
        if (symbolSearchBtn && !symbolSearchBtn.hasAttribute('data-listener-attached')) {
            console.log('🔍 Registriere Symbol-Search-Button');
            symbolSearchBtn.addEventListener('click', () => {
                this.searchPLCSymbols();
            });
            symbolSearchBtn.setAttribute('data-listener-attached', 'true');

            // Enter-Taste im Suchfeld
            const symbolSearch = document.getElementById('symbol-search');
            if (symbolSearch) {
                symbolSearch.addEventListener('keypress', (e) => {
                    if (e.key === 'Enter') {
                        this.searchPLCSymbols();
                    }
                });
            }
        }

        // Setup Live-Symbol-Abruf
        const loadLiveSymbolsBtn = document.getElementById('load-live-symbols-btn');
        if (loadLiveSymbolsBtn && !loadLiveSymbolsBtn.hasAttribute('data-listener-attached')) {
            console.log('☁️ Registriere Live-Symbol-Abruf-Button');
            loadLiveSymbolsBtn.addEventListener('click', () => {
                this.loadLiveSymbols();
            });
            loadLiveSymbolsBtn.setAttribute('data-listener-attached', 'true');
        }

        // Setup TPY-Upload
        const tpyUploadBtn = document.getElementById('tpy-upload-btn');
        const tpyUploadInput = document.getElementById('tpy-upload');
        if (tpyUploadBtn && tpyUploadInput && !tpyUploadBtn.hasAttribute('data-listener-attached')) {
            console.log('📤 Registriere TPY-Upload-Button');
            tpyUploadBtn.addEventListener('click', () => {
                tpyUploadInput.click();
            });
            tpyUploadInput.addEventListener('change', (e) => {
                this.uploadTPY(e.target.files[0]);
            });
            tpyUploadBtn.setAttribute('data-listener-attached', 'true');
        }

        // Setup MQTT-Handler (falls noch nicht registriert)
        const mqttConnectBtn = document.getElementById('mqtt-connect-btn');
        if (mqttConnectBtn && !mqttConnectBtn.hasAttribute('data-listener-attached')) {
            this.registerMQTTHandlers();
            mqttConnectBtn.setAttribute('data-listener-attached', 'true');
        }

        // Setup Symbol-Suche Event-Listener
        const symbolSearchInput = document.getElementById('symbol-search');
        if (symbolSearchInput) {
            // Input Event für Live-Suche
            symbolSearchInput.addEventListener('input', () => {
                // Debounce: Warte 300ms nach letzter Eingabe
                clearTimeout(this.searchDebounceTimer);
                this.searchDebounceTimer = setTimeout(() => {
                    this.searchPLCSymbols();
                }, 300);
            });

            // Enter-Key für sofortige Suche
            symbolSearchInput.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') {
                    clearTimeout(this.searchDebounceTimer);
                    this.searchPLCSymbols();
                }
            });
        }

        // Setup Type-Filter Event-Listener
        const typeFilterSelect = document.getElementById('symbol-type-filter');
        if (typeFilterSelect) {
            typeFilterSelect.addEventListener('change', () => {
                this.searchPLCSymbols();
            });
        }

        // Setup View-Mode-Umschaltung
        document.querySelectorAll('input[name="symbol-view"]').forEach(radio => {
            radio.addEventListener('change', () => {
                if (this.currentSymbols && this.currentSymbols.length > 0) {
                    const viewMode = radio.value;
                    const symbolTree = document.getElementById('symbol-tree');

                    if (viewMode === 'tree') {
                        this.renderSymbolTree(this.currentSymbols, symbolTree);
                    } else {
                        this.renderSymbolList(this.currentSymbols, symbolTree);
                    }
                }
            });
        });

        // Lade System-Status (mit Delay für DOM)
        setTimeout(() => {
            this.loadSystemStatus();
        }, 200);

        // Lade Symbole automatisch beim Seitenwechsel
        setTimeout(() => {
            this.searchPLCSymbols();
        }, 300);
    }

    // ========================================================================
    // PLC SYMBOL BROWSER
    // ========================================================================

    async searchPLCSymbols() {
        console.log('🔍 Suche PLC-Symbole...');

        const searchInput = document.getElementById('symbol-search');
        const typeFilter = document.getElementById('symbol-type-filter');
        const symbolTree = document.getElementById('symbol-tree');
        const counterElem = document.getElementById('symbol-counter');
        const filterInfo = document.getElementById('symbol-filter-info');

        if (!symbolTree) return;

        const searchQuery = searchInput?.value || '';
        const typeValue = typeFilter?.value || '';

        // Zeige Ladeanzeige
        symbolTree.innerHTML = '<p class="text-sm text-gray-500"><i data-lucide="loader-2" class="w-4 h-4 inline animate-spin"></i> Lade Symbole...</p>';
        lucide.createIcons();

        try {
            // API-Call mit Query-Parametern
            const params = new URLSearchParams();
            if (searchQuery) params.append('search', searchQuery);
            if (typeValue) params.append('type', typeValue);

            const response = await fetch(`/api/plc/symbols?${params.toString()}`);
            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'API-Fehler');
            }

            console.log(`✓ ${data.count} Symbole geladen`);

            // Update Counter
            if (counterElem) {
                counterElem.textContent = `${data.count} Symbole geladen`;
            }

            // Update Filter-Info
            if (filterInfo && (searchQuery || typeValue)) {
                let info = '';
                if (searchQuery) info += `Filter: "${searchQuery}"`;
                if (typeValue) info += ` Typ: ${typeValue}`;
                filterInfo.textContent = info;
            } else if (filterInfo) {
                filterInfo.textContent = '';
            }

            // Speichere Symbole für TreeView
            this.currentSymbols = data.symbols;

            // Prüfe View-Modus
            const viewMode = document.querySelector('input[name="symbol-view"]:checked')?.value || 'tree';

            if (viewMode === 'tree') {
                this.renderSymbolTree(data.symbols, symbolTree);
            } else {
                this.renderSymbolList(data.symbols, symbolTree);
            }

        } catch (error) {
            console.error('❌ Fehler beim Laden der Symbole:', error);
            symbolTree.innerHTML = `<p class="text-sm text-red-500"><i data-lucide="alert-circle" class="w-4 h-4 inline"></i> Fehler: ${error.message}</p>`;
            lucide.createIcons();
        }
    }

    renderSymbolTree(symbols, container) {
        if (!symbols || symbols.length === 0) {
            container.innerHTML = '<p class="text-sm text-gray-500">Keine Symbole gefunden</p>';
            return;
        }

        // Baue hierarchische Struktur
        const tree = {};
        symbols.forEach(symbol => {
            const parts = symbol.name.split('.');
            let current = tree;

            parts.forEach((part, index) => {
                const isLastPart = index === parts.length - 1;

                if (!current[part]) {
                    // Neuer Node
                    current[part] = {
                        _isLeaf: isLastPart,
                        _symbol: isLastPart ? symbol : null,
                        _children: {}
                    };
                } else {
                    // Node existiert bereits
                    if (isLastPart && !current[part]._symbol) {
                        // War bisher Ordner, jetzt auch Symbol
                        current[part]._symbol = symbol;
                    }
                }

                // Navigiere zu Kindern (immer, auch wenn Leaf - kann ja trotzdem Kinder haben!)
                current = current[part]._children;
            });
        });

        // Rendere Tree
        container.innerHTML = this.buildTreeHTML(tree, 0);
        this.attachTreeHandlers();
        lucide.createIcons();
    }

    buildTreeHTML(node, level) {
        let html = '';
        const indent = level * 16; // 16px per level

        // Sortiere Einträge: Ordner zuerst (A-Z), dann Variablen (A-Z)
        const entries = Object.entries(node).filter(([key]) => !key.startsWith('_'));

        entries.sort(([keyA, valueA], [keyB, valueB]) => {
            const hasChildrenA = Object.keys(valueA._children).length > 0;
            const hasChildrenB = Object.keys(valueB._children).length > 0;

            // Ordner vor Variablen
            if (hasChildrenA && !hasChildrenB) return -1;
            if (!hasChildrenA && hasChildrenB) return 1;

            // Innerhalb der Gruppe alphabetisch (case-insensitive)
            return keyA.toLowerCase().localeCompare(keyB.toLowerCase());
        });

        for (const [key, value] of entries) {
            const hasChildren = Object.keys(value._children).length > 0;

            if (hasChildren) {
                // Ordner-Knoten (kann auch ein Symbol sein!)
                const folderId = `folder-${Math.random().toString(36).substr(2, 9)}`;
                const symbol = value._symbol;

                html += `
                    <div class="folder-node" style="padding-left: ${indent}px">
                        <div class="folder-header flex items-center space-x-2 px-2 py-1 hover:bg-gray-100 dark:hover:bg-gray-800 rounded cursor-pointer text-sm"
                             data-folder-id="${folderId}"
                             ${symbol ? `data-symbol='${JSON.stringify(symbol)}'` : ''}>
                            <i data-lucide="chevron-right" class="w-4 h-4 chevron-icon transition-transform"></i>
                            <i data-lucide="folder" class="w-4 h-4 text-yellow-500"></i>
                            <span class="font-semibold text-gray-900 dark:text-white">${key}</span>
                            ${symbol ? `<span class="text-xs text-gray-500">: ${symbol.type}</span>` : ''}
                            <span class="text-xs text-gray-500">(${Object.keys(value._children).length})</span>
                        </div>
                        <div class="folder-content hidden" id="${folderId}">
                            ${this.buildTreeHTML(value._children, level + 1)}
                        </div>
                    </div>
                `;
            } else {
                // Blatt-Knoten (nur Variable, keine Kinder)
                const symbol = value._symbol;
                if (!symbol) continue; // Sollte nicht passieren

                const icon = this.getSymbolIcon(symbol.type);
                html += `
                    <div class="symbol-item flex items-center space-x-2 px-2 py-1 hover:bg-gray-100 dark:hover:bg-gray-800 rounded cursor-pointer text-sm"
                         style="padding-left: ${indent + 8}px"
                         data-symbol='${JSON.stringify(symbol)}'>
                        <i data-lucide="${icon}" class="w-4 h-4 text-blue-500"></i>
                        <span class="font-mono text-gray-900 dark:text-white">${key}</span>
                        <span class="text-xs text-gray-500">: ${symbol.type}</span>
                    </div>
                `;
            }
        }

        return html;
    }

    attachTreeHandlers() {
        // Folder-Click-Handler
        document.querySelectorAll('.folder-header').forEach(header => {
            header.addEventListener('click', (e) => {
                const folderId = header.dataset.folderId;
                const content = document.getElementById(folderId);
                const chevron = header.querySelector('.chevron-icon');

                if (content.classList.contains('hidden')) {
                    content.classList.remove('hidden');
                    chevron.style.transform = 'rotate(90deg)';
                } else {
                    content.classList.add('hidden');
                    chevron.style.transform = 'rotate(0deg)';
                }
            });
        });

        // Symbol-Click-Handler
        document.querySelectorAll('.symbol-item').forEach(item => {
            item.addEventListener('click', (e) => {
                const symbol = JSON.parse(item.dataset.symbol);
                console.log('📌 Symbol ausgewählt:', symbol);
                // TODO: Zeige Symbol-Details oder verwende für Widget-Config
                alert(`Symbol: ${symbol.name}\nTyp: ${symbol.type}\nKategorie: ${symbol.category}`);
            });
        });

        // Expand/Collapse All Buttons
        const expandBtn = document.getElementById('expand-all-btn');
        const collapseBtn = document.getElementById('collapse-all-btn');

        if (expandBtn) {
            expandBtn.onclick = () => {
                document.querySelectorAll('.folder-content').forEach(folder => {
                    folder.classList.remove('hidden');
                });
                document.querySelectorAll('.chevron-icon').forEach(chevron => {
                    chevron.style.transform = 'rotate(90deg)';
                });
                lucide.createIcons();
            };
        }

        if (collapseBtn) {
            collapseBtn.onclick = () => {
                document.querySelectorAll('.folder-content').forEach(folder => {
                    folder.classList.add('hidden');
                });
                document.querySelectorAll('.chevron-icon').forEach(chevron => {
                    chevron.style.transform = 'rotate(0deg)';
                });
                lucide.createIcons();
            };
        }
    }

    getSymbolIcon(type) {
        if (!type) return 'help-circle';
        const typeUpper = type.toUpperCase();
        if (typeUpper.includes('BOOL')) return 'toggle-left';
        if (typeUpper.includes('INT') || typeUpper.includes('DINT') || typeUpper.includes('UINT')) return 'hash';
        if (typeUpper.includes('REAL') || typeUpper.includes('LREAL')) return 'trending-up';
        if (typeUpper.includes('STRING')) return 'type';
        if (typeUpper.includes('TIME') || typeUpper.includes('DATE')) return 'clock';
        return 'circle';
    }

    renderSymbolList(symbols, container) {
        if (!symbols || symbols.length === 0) {
            container.innerHTML = '<p class="text-sm text-gray-500">Keine Symbole gefunden</p>';
            return;
        }

        // Baue flache Liste
        let html = '<div class="space-y-1">';

        symbols.forEach(symbol => {
            const name = symbol.name;
            const type = symbol.type;
            const category = symbol.category || 'Variable';

            // Icon basierend auf Typ
            let icon = 'circle';
            if (type.includes('BOOL')) icon = 'toggle-left';
            else if (type.includes('INT') || type.includes('REAL')) icon = 'hash';
            else if (type.includes('STRING')) icon = 'type';

            html += `
                <div class="flex items-center justify-between p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded cursor-pointer group symbol-item"
                     data-symbol="${name}" data-type="${type}">
                    <div class="flex items-center space-x-2 flex-1">
                        <i data-lucide="${icon}" class="w-4 h-4 text-blue-500"></i>
                        <span class="text-sm font-mono text-gray-900 dark:text-white">${name}</span>
                    </div>
                    <div class="flex items-center space-x-2">
                        <span class="text-xs text-gray-500 dark:text-gray-400">${type}</span>
                        <button class="opacity-0 group-hover:opacity-100 px-2 py-1 bg-blue-500 text-white text-xs rounded hover:bg-blue-600 symbol-select-btn">
                            Auswählen
                        </button>
                    </div>
                </div>
            `;
        });

        html += '</div>';
        html += `<p class="text-xs text-gray-500 mt-4">${symbols.length} Symbol(e) gefunden</p>`;

        container.innerHTML = html;

        // Icons aktualisieren
        if (typeof lucide !== 'undefined') {
            lucide.createIcons();
        }

        // Event-Listener für Auswahl-Buttons
        container.querySelectorAll('.symbol-select-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const item = btn.closest('.symbol-item');
                const symbol = item.getAttribute('data-symbol');
                const type = item.getAttribute('data-type');
                this.onSymbolSelected(symbol, type);
            });
        });
    }

    onSymbolSelected(symbol, type) {
        console.log(`✅ Symbol ausgewählt: ${symbol} (${type})`);

        // Zeige Bestätigung
        alert(`Symbol ausgewählt:\n\n${symbol}\nTyp: ${type}\n\nDieses Symbol kann jetzt für Widgets konfiguriert werden.`);

        // TODO: Hier könnte man das Symbol in ein Widget-Konfigurations-Formular einfügen
    }

    async uploadTPY(file) {
        if (!file) return;

        const statusElem = document.getElementById('tpy-upload-status');
        if (statusElem) {
            statusElem.textContent = 'Lade hoch...';
            statusElem.className = 'text-sm text-blue-600';
        }

        console.log(`📤 Lade .tpy Datei hoch: ${file.name}`);

        const formData = new FormData();
        formData.append('file', file);

        try {
            const response = await fetch('/api/plc/symbols/upload', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Upload fehlgeschlagen');
            }

            console.log(`✅ ${data.symbols_count} Symbole geladen`);

            if (statusElem) {
                statusElem.textContent = `✓ ${data.symbols_count} Symbole geladen`;
                statusElem.className = 'text-sm text-green-600';
            }

            // Auto-Suche nach Upload
            setTimeout(() => {
                this.searchPLCSymbols();
            }, 500);

        } catch (error) {
            console.error('❌ Upload-Fehler:', error);
            if (statusElem) {
                statusElem.textContent = `✗ Fehler: ${error.message}`;
                statusElem.className = 'text-sm text-red-600';
            }
        }

        // Reset file input
        const input = document.getElementById('tpy-upload');
        if (input) input.value = '';
    }

    async loadLiveSymbols() {
        console.log('☁️ Lade Symbole live von PLC...');

        const statusElem = document.getElementById('symbol-load-status');
        const btn = document.getElementById('load-live-symbols-btn');

        if (statusElem) {
            statusElem.innerHTML = '<i data-lucide="loader-2" class="w-4 h-4 inline animate-spin mr-1"></i> Lade Symbole von PLC...';
            statusElem.className = 'text-sm text-blue-600 dark:text-blue-400';
            lucide.createIcons();
        }

        if (btn) {
            btn.disabled = true;
            btn.classList.add('opacity-50', 'cursor-not-allowed');
        }

        try {
            const response = await fetch('/api/plc/symbols/live', {
                method: 'POST'
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Live-Abruf fehlgeschlagen');
            }

            console.log(`✅ ${data.symbol_count} Symbole von PLC geladen`);

            if (statusElem) {
                statusElem.innerHTML = `<i data-lucide="check-circle" class="w-4 h-4 inline mr-1"></i> ${data.symbol_count} Symbole von PLC geladen`;
                statusElem.className = 'text-sm text-green-600 dark:text-green-400';
                lucide.createIcons();
            }

            // Auto-Suche nach erfolgreichem Laden
            setTimeout(() => {
                this.searchPLCSymbols();
            }, 500);

        } catch (error) {
            console.error('❌ Live-Abruf-Fehler:', error);
            if (statusElem) {
                statusElem.innerHTML = `<i data-lucide="alert-circle" class="w-4 h-4 inline mr-1"></i> ${error.message}`;
                statusElem.className = 'text-sm text-red-600 dark:text-red-400';
                lucide.createIcons();
            }
        } finally {
            if (btn) {
                btn.disabled = false;
                btn.classList.remove('opacity-50', 'cursor-not-allowed');
            }
        }
    }

    // ====================================================================
    // MQTT INTEGRATION
    // ====================================================================

    async loadMQTTStatus() {
        console.log('🔄 Lade MQTT-Status...');

        try {
            const response = await fetch('/api/mqtt/status');
            const data = await response.json();

            console.log('📊 MQTT-Status:', data);

            // Update Status-Badge
            const badge = document.getElementById('mqtt-status-badge');
            const dot = badge?.querySelector('div');
            const text = badge?.querySelector('span');

            if (data.connected) {
                dot.className = 'w-2 h-2 rounded-full bg-green-500';
                text.textContent = `Verbunden: ${data.broker}:${data.port}`;

                document.getElementById('mqtt-connect-btn').disabled = true;
                document.getElementById('mqtt-disconnect-btn').disabled = false;
                document.getElementById('mqtt-subscribe-btn').disabled = false;
            } else {
                dot.className = 'w-2 h-2 rounded-full bg-gray-400';
                text.textContent = 'Nicht verbunden';

                document.getElementById('mqtt-connect-btn').disabled = false;
                document.getElementById('mqtt-disconnect-btn').disabled = true;
                document.getElementById('mqtt-subscribe-btn').disabled = true;
            }

            // Zeige Installation-Hinweis falls paho-mqtt fehlt
            const installHint = document.getElementById('mqtt-install-hint');
            if (!data.available && installHint) {
                installHint.classList.remove('hidden');
            } else if (installHint) {
                installHint.classList.add('hidden');
            }

            // Lade Werte falls verbunden
            if (data.connected) {
                this.loadMQTTValues();
            }

        } catch (error) {
            console.error('❌ Fehler beim Laden des MQTT-Status:', error);
        }
    }

    async connectMQTT() {
        const broker = document.getElementById('mqtt-broker').value;
        const port = parseInt(document.getElementById('mqtt-port').value);
        const username = document.getElementById('mqtt-username').value;
        const password = document.getElementById('mqtt-password').value;

        console.log('🔌 Verbinde MQTT:', broker, port);

        try {
            const response = await fetch('/api/mqtt/connect', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ broker, port, username, password })
            });

            if (response.ok) {
                console.log('✅ MQTT verbunden');
                this.loadMQTTStatus();
            } else {
                const error = await response.json();
                console.error('❌ MQTT-Verbindung fehlgeschlagen:', error);
                alert(`Fehler: ${error.error}`);
            }
        } catch (error) {
            console.error('❌ MQTT-Verbindung Fehler:', error);
            alert(`Verbindungsfehler: ${error.message}`);
        }
    }

    async disconnectMQTT() {
        console.log('🔌 Trenne MQTT...');

        try {
            const response = await fetch('/api/mqtt/disconnect', {
                method: 'POST'
            });

            if (response.ok) {
                console.log('✅ MQTT getrennt');
                this.loadMQTTStatus();
            }
        } catch (error) {
            console.error('❌ MQTT-Trennung Fehler:', error);
        }
    }

    async subscribeMQTT() {
        const topic = document.getElementById('mqtt-topic').value;

        if (!topic) {
            alert('Bitte Topic eingeben');
            return;
        }

        console.log('📥 Subscribe zu Topic:', topic);

        try {
            const response = await fetch('/api/mqtt/subscribe', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ topic })
            });

            if (response.ok) {
                console.log('✅ Topic abonniert:', topic);
                document.getElementById('mqtt-topic').value = '';
            } else {
                const error = await response.json();
                alert(`Fehler: ${error.error}`);
            }
        } catch (error) {
            console.error('❌ Subscribe Fehler:', error);
            alert(`Fehler: ${error.message}`);
        }
    }

    async loadMQTTValues() {
        try {
            const response = await fetch('/api/mqtt/values');
            const data = await response.json();

            const container = document.getElementById('mqtt-values');
            if (!container) return;

            if (data.count === 0) {
                container.innerHTML = '<p class="text-xs text-gray-500">Keine Werte empfangen</p>';
                return;
            }

            container.innerHTML = '';
            for (const [topic, valueData] of Object.entries(data.values)) {
                const value = valueData.value;
                const div = document.createElement('div');
                div.className = 'text-xs p-2 bg-white dark:bg-gray-800 rounded border border-gray-200 dark:border-gray-700';
                div.innerHTML = `
                    <div class="font-mono text-blue-600 dark:text-blue-400">${topic}</div>
                    <div class="text-gray-700 dark:text-gray-300 mt-1">${JSON.stringify(value)}</div>
                `;
                container.appendChild(div);
            }

        } catch (error) {
            console.error('❌ Fehler beim Laden der MQTT-Werte:', error);
        }
    }

    registerMQTTHandlers() {
        console.log('🔌 Registriere MQTT-Handler');

        const connectBtn = document.getElementById('mqtt-connect-btn');
        const disconnectBtn = document.getElementById('mqtt-disconnect-btn');
        const subscribeBtn = document.getElementById('mqtt-subscribe-btn');

        if (connectBtn) {
            connectBtn.addEventListener('click', () => this.connectMQTT());
        }

        if (disconnectBtn) {
            disconnectBtn.addEventListener('click', () => this.disconnectMQTT());
        }

        if (subscribeBtn) {
            subscribeBtn.addEventListener('click', () => this.subscribeMQTT());
        }

        // Load initial status
        this.loadMQTTStatus();
    }

    // ========================================================================
    // ADMIN PAGE
    // ========================================================================

    async loadAdminPage() {
        console.log('👑 Lade Admin...');

        // ⭐ v5.1.1: Lade Widgets für diese Page
        await this.loadAndRenderWidgets('admin');

        await this.loadPLCConfigs();

        // Lade Logs & Service-Info (NEU)
        await this.loadLogs();
        await this.loadServiceInfo();

        // Event Listeners
        const addPlcBtn = document.getElementById('add-plc-btn');
        const cleanupBtn = document.getElementById('cleanup-tpy-btn');
        const refreshLogsBtn = document.getElementById('refresh-logs-btn');
        const clearLogsBtn = document.getElementById('clear-logs-btn');
        const restartServiceBtn = document.getElementById('restart-service-btn');

        if (addPlcBtn) {
            addPlcBtn.addEventListener('click', () => this.addPLC());
        }

        if (cleanupBtn) {
            cleanupBtn.addEventListener('click', () => this.cleanupTPY());
        }

        if (refreshLogsBtn) {
            refreshLogsBtn.addEventListener('click', () => this.loadLogs());
        }

        if (clearLogsBtn) {
            clearLogsBtn.addEventListener('click', () => this.clearLogs());
        }

        if (restartServiceBtn) {
            restartServiceBtn.addEventListener('click', () => this.restartService());
        }
    }

    async loadLogs() {
        console.log('📋 Lade System-Logs...');

        try {
            const response = await fetch('/api/admin/logs?limit=50');
            if (!response.ok) throw new Error('Logs konnten nicht geladen werden');

            const logs = await response.json();
            const tbody = document.getElementById('log-table-body');

            if (!tbody) return;

            if (logs.length === 0) {
                tbody.innerHTML = `
                    <tr>
                        <td colspan="4" class="px-3 py-4 text-center text-gray-500 dark:text-gray-400">
                            Keine Logs vorhanden
                        </td>
                    </tr>
                `;
                return;
            }

            tbody.innerHTML = logs.map(log => `
                <tr class="border-b dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700/50">
                    <td class="px-3 py-2 text-xs text-gray-500 dark:text-gray-400 whitespace-nowrap">
                        ${log.timestamp}
                    </td>
                    <td class="px-3 py-2 text-xs font-mono text-blue-600 dark:text-blue-400">
                        ${log.module}
                    </td>
                    <td class="px-3 py-2 text-xs font-bold ${
                        log.level === 'ERROR' ? 'text-red-500' :
                        log.level === 'WARNING' ? 'text-orange-500' :
                        'text-yellow-500'
                    }">
                        ${log.level}
                    </td>
                    <td class="px-3 py-2 text-sm text-gray-700 dark:text-gray-300 break-all">
                        ${log.message}
                    </td>
                </tr>
            `).join('');

            console.log(`✅ ${logs.length} Logs geladen`);

        } catch (error) {
            console.error('❌ Fehler beim Laden der Logs:', error);
            const tbody = document.getElementById('log-table-body');
            if (tbody) {
                tbody.innerHTML = `
                    <tr>
                        <td colspan="4" class="px-3 py-4 text-center text-red-500">
                            Fehler: ${error.message}
                        </td>
                    </tr>
                `;
            }
        }
    }

    async loadServiceInfo() {
        console.log('ℹ️ Lade Service-Info...');

        try {
            const response = await fetch('/api/admin/service/info');
            if (!response.ok) throw new Error('Service-Info konnte nicht geladen werden');

            const info = await response.json();

            document.getElementById('service-platform').textContent = info.platform || '-';
            document.getElementById('service-pid').textContent = info.pid || '-';
            document.getElementById('service-python').textContent = info.python || '-';
            document.getElementById('service-restarted').textContent = info.is_restarted ? '✅ Ja' : '❌ Nein';

            console.log('✅ Service-Info geladen:', info);

        } catch (error) {
            console.error('❌ Fehler beim Laden der Service-Info:', error);
        }
    }

    async clearLogs() {
        if (!confirm('Wirklich alle Logs löschen (behalte letzte 100)?')) return;

        try {
            const response = await fetch('/api/admin/logs/clear', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ keep_count: 100 })
            });

            if (!response.ok) throw new Error('Logs konnten nicht gelöscht werden');

            alert('✅ Logs wurden gelöscht');
            await this.loadLogs();

        } catch (error) {
            console.error('❌ Fehler beim Löschen der Logs:', error);
            alert(`❌ Fehler: ${error.message}`);
        }
    }

    async restartService() {
        if (!confirm('🔄 Service wirklich neu starten?\n\nDie Verbindung wird kurz unterbrochen.')) return;

        try {
            const response = await fetch('/api/admin/service/restart', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ delay: 2 })
            });

            if (!response.ok) throw new Error('Restart fehlgeschlagen');

            const data = await response.json();
            alert(`✅ ${data.message}\n\nSeite lädt automatisch neu...`);

            // Countdown und Reload
            let countdown = 3;
            const interval = setInterval(() => {
                countdown--;
                console.log(`Restart in ${countdown}s...`);
                if (countdown === 0) {
                    clearInterval(interval);
                    location.reload();
                }
            }, 1000);

        } catch (error) {
            console.error('❌ Restart fehlgeschlagen:', error);
            alert(`❌ Fehler: ${error.message}`);
        }
    }

    async loadPLCConfigs() {
        try {
            const response = await fetch('/api/admin/plcs');
            const data = await response.json();

            // Update Statistiken
            document.getElementById('stat-total-plcs').textContent = data.statistics.total_plcs;
            document.getElementById('stat-active-plcs').textContent = data.statistics.active_plcs;
            document.getElementById('stat-plcs-with-tpy').textContent = data.statistics.plcs_with_tpy;
            document.getElementById('stat-tpy-size').textContent = data.statistics.total_tpy_size_mb + ' MB';

            // Rendere PLC-Liste
            this.renderPLCList(data.plcs, data.active_plc);

        } catch (error) {
            console.error('❌ Fehler beim Laden der PLCs:', error);
        }
    }

    renderPLCList(plcs, active_plc_id) {
        const container = document.getElementById('plc-list');
        if (!container) return;

        if (Object.keys(plcs).length === 0) {
            container.innerHTML = '<p class="text-gray-500 dark:text-gray-400">Keine PLCs konfiguriert</p>';
            return;
        }

        container.innerHTML = '';

        for (const [plc_id, plc] of Object.entries(plcs)) {
            const isActive = plc_id === active_plc_id;

            const card = document.createElement('div');
            card.className = `p-4 rounded-lg border ${
                isActive
                    ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                    : 'border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900'
            }`;

            card.innerHTML = `
                <div class="flex items-start justify-between">
                    <div class="flex-1">
                        <div class="flex items-center space-x-3 mb-2">
                            <h3 class="text-lg font-semibold text-gray-900 dark:text-white">${plc.name}</h3>
                            ${isActive ? '<span class="px-2 py-1 text-xs bg-blue-500 text-white rounded">Aktiv</span>' : ''}
                            ${plc.tpy_file ? '<i data-lucide="file-check" class="w-4 h-4 text-green-500"></i>' : ''}
                        </div>
                        <div class="text-sm space-y-1 text-gray-700 dark:text-gray-300">
                            <div><span class="text-gray-600 dark:text-gray-400">AMS NetID:</span> ${plc.ams_net_id}</div>
                            <div><span class="text-gray-600 dark:text-gray-400">Port:</span> ${plc.ams_port}</div>
                            ${plc.description ? `<div class="text-gray-500 dark:text-gray-400">${plc.description}</div>` : ''}
                            ${plc.tpy_file ? `<div class="text-xs text-gray-500 dark:text-gray-400">TPY: ${plc.tpy_file}</div>` : ''}
                        </div>
                    </div>
                    <div class="flex items-center space-x-2">
                        ${!isActive ? `<button onclick="app.setActivePLC('${plc_id}')" class="p-2 text-blue-600 dark:text-blue-400 hover:bg-blue-100 dark:hover:bg-blue-900/30 rounded" title="Als aktiv setzen">
                            <i data-lucide="check-circle" class="w-4 h-4"></i>
                        </button>` : ''}
                        <button onclick="app.uploadTPYForPLC('${plc_id}')" class="p-2 text-green-600 dark:text-green-400 hover:bg-green-100 dark:hover:bg-green-900/30 rounded" title="TPY hochladen">
                            <i data-lucide="upload" class="w-4 h-4"></i>
                        </button>
                        <button onclick="app.deletePLC('${plc_id}')" class="p-2 text-red-600 dark:text-red-400 hover:bg-red-100 dark:hover:bg-red-900/30 rounded" title="Löschen">
                            <i data-lucide="trash-2" class="w-4 h-4"></i>
                        </button>
                    </div>
                </div>
            `;

            container.appendChild(card);
        }

        // Re-initialize Lucide icons
        lucide.createIcons();
    }

    async addPLC() {
        const name = prompt('PLC Name:');
        if (!name) return;

        const ams_net_id = prompt('AMS Net ID:', '192.168.1.100.1.1');
        if (!ams_net_id) return;

        const ams_port = prompt('AMS Port:', '851');
        const description = prompt('Beschreibung (optional):', '');

        try {
            const response = await fetch('/api/admin/plcs', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    name,
                    ams_net_id,
                    ams_port: parseInt(ams_port),
                    description
                })
            });

            if (response.ok) {
                await this.loadPLCConfigs();
            } else {
                alert('Fehler beim Hinzufügen der PLC');
            }
        } catch (error) {
            console.error('Fehler:', error);
            alert('Fehler beim Hinzufügen der PLC');
        }
    }

    async setActivePLC(plc_id) {
        try {
            const response = await fetch(`/api/admin/plcs/${plc_id}/set-active`, { method: 'POST' });
            if (response.ok) {
                await this.loadPLCConfigs();
            }
        } catch (error) {
            console.error('Fehler:', error);
        }
    }

    async deletePLC(plc_id) {
        if (!confirm('PLC-Konfiguration wirklich löschen?')) return;

        const deleteTpy = confirm('Auch zugehörige TPY-Datei löschen?');

        try {
            const response = await fetch(`/api/admin/plcs/${plc_id}?delete_tpy=${deleteTpy}`, {
                method: 'DELETE'
            });

            if (response.ok) {
                await this.loadPLCConfigs();
            } else {
                alert('Fehler beim Löschen');
            }
        } catch (error) {
            console.error('Fehler:', error);
            alert('Fehler beim Löschen');
        }
    }

    async uploadTPYForPLC(plc_id) {
        const input = document.createElement('input');
        input.type = 'file';
        input.accept = '.tpy';

        input.onchange = async (e) => {
            const file = e.target.files[0];
            if (!file) return;

            const formData = new FormData();
            formData.append('file', file);

            try {
                const response = await fetch(`/api/admin/plcs/${plc_id}/upload-tpy`, {
                    method: 'POST',
                    body: formData
                });

                if (response.ok) {
                    const result = await response.json();
                    alert(`TPY hochgeladen: ${result.filename} (${(result.size / 1024).toFixed(1)} KB)`);
                    await this.loadPLCConfigs();
                } else {
                    alert('Fehler beim Upload');
                }
            } catch (error) {
                console.error('Fehler:', error);
                alert('Fehler beim Upload');
            }
        };

        input.click();
    }

    async cleanupTPY() {
        if (!confirm('Wirklich alle ungenutzten TPY-Dateien löschen?')) return;

        try {
            const response = await fetch('/api/admin/plcs/cleanup-tpy', { method: 'POST' });
            const result = await response.json();

            if (result.success) {
                alert(`${result.count} Datei(en) gelöscht`);
                await this.loadPLCConfigs();
            }
        } catch (error) {
            console.error('Fehler:', error);
            alert('Fehler beim Cleanup');
        }
    }

    // ========================================================================
    // WIDGETS PAGE - Variable Binding System
    // ========================================================================

    async loadWidgetsPage() {
        console.log('🎨 Lade Widgets-Seite...');

        // ⭐ v5.1.1: Lade Widgets für diese Page
        await this.loadAndRenderWidgets('widgets');

        await this.loadWidgetList();

        // Event Listeners
        const addBtn = document.getElementById('add-widget-btn');
        const form = document.getElementById('widget-form');
        const closeBtn = document.getElementById('close-widget-editor');
        const cancelBtn = document.getElementById('cancel-widget-edit');
        const testBtn = document.getElementById('test-binding-btn');
        const browseBtn = document.getElementById('browse-symbols-btn');

        if (addBtn) {
            addBtn.addEventListener('click', () => this.openWidgetEditor());
        }

        if (form) {
            form.addEventListener('submit', (e) => {
                e.preventDefault();
                this.saveWidget();
            });
        }

        if (closeBtn || cancelBtn) {
            [closeBtn, cancelBtn].forEach(btn => {
                if (btn) btn.addEventListener('click', () => this.closeWidgetEditor());
            });
        }

        if (testBtn) {
            testBtn.addEventListener('click', () => this.testVariableBinding());
        }

        if (browseBtn) {
            browseBtn.addEventListener('click', () => this.browseSymbols());
        }

        // ⭐ v5.1.2: Widget-Type Change Handler (Switch-Config anzeigen/verstecken)
        const widgetTypeSelect = document.getElementById('widget-type');
        const switchConfigSection = document.getElementById('switch-config-section');

        if (widgetTypeSelect && switchConfigSection) {
            widgetTypeSelect.addEventListener('change', () => {
                const type = widgetTypeSelect.value;
                switchConfigSection.style.display = (type === 'switch') ? 'block' : 'none';
            });
        }

        // ⭐ v5.1.2: Switch-Mode Change Handler (Pulse-Duration anzeigen/verstecken)
        const switchModeSelect = document.getElementById('switch-mode');
        const pulseDurationContainer = document.getElementById('pulse-duration-container');

        if (switchModeSelect && pulseDurationContainer) {
            switchModeSelect.addEventListener('change', () => {
                const mode = switchModeSelect.value;
                pulseDurationContainer.style.display = (mode === 'pulse') ? 'block' : 'none';
            });
        }
    }

    async loadWidgetList() {
        try {
            const response = await fetch('/api/widgets');
            const data = await response.json();

            this.renderWidgetList(data.widgets || {});
        } catch (error) {
            console.error('❌ Fehler beim Laden der Widgets:', error);
        }
    }

    renderWidgetList(widgets) {
        const container = document.getElementById('widget-list');
        if (!container) return;

        if (Object.keys(widgets).length === 0) {
            container.innerHTML = '<p class="text-gray-500 dark:text-gray-400">Keine Widgets konfiguriert. Erstelle ein neues Widget!</p>';
            return;
        }

        container.innerHTML = '';

        for (const [id, widget] of Object.entries(widgets)) {
            const card = document.createElement('div');
            card.className = 'p-4 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900';

            const bindingsHtml = Object.entries(widget.bindings || {})
                .map(([key, binding]) => `<div class="text-xs text-gray-500 dark:text-gray-400">
                    <i data-lucide="link" class="w-3 h-3 inline"></i> ${key}: ${binding.variable} (${binding.plc_type})
                </div>`)
                .join('');

            card.innerHTML = `
                <div class="flex items-start justify-between">
                    <div class="flex-1">
                        <div class="flex items-center space-x-3 mb-2">
                            <h3 class="text-lg font-semibold text-gray-900 dark:text-white">${widget.title}</h3>
                            <span class="px-2 py-1 text-xs bg-gray-200 dark:bg-gray-700 rounded">${widget.type}</span>
                            <span class="px-2 py-1 text-xs bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300 rounded">${widget.page}</span>
                        </div>
                        ${bindingsHtml || '<div class="text-xs text-gray-400">Keine Variablen verknüpft</div>'}
                    </div>
                    <div class="flex items-center space-x-2">
                        <button onclick="app.editWidget('${id}')" class="p-2 text-blue-600 dark:text-blue-400 hover:bg-blue-100 dark:hover:bg-blue-900/30 rounded" title="Bearbeiten">
                            <i data-lucide="edit" class="w-4 h-4"></i>
                        </button>
                        <button onclick="app.deleteWidget('${id}')" class="p-2 text-red-600 dark:text-red-400 hover:bg-red-100 dark:hover:bg-red-900/30 rounded" title="Löschen">
                            <i data-lucide="trash-2" class="w-4 h-4"></i>
                        </button>
                    </div>
                </div>
            `;

            container.appendChild(card);
        }

        lucide.createIcons();
    }

    openWidgetEditor(widgetId = null) {
        const modal = document.getElementById('widget-editor-modal');
        if (!modal) return;

        // Reset form
        document.getElementById('widget-form').reset();
        document.getElementById('widget-edit-id').value = widgetId || '';

        if (widgetId) {
            // Load existing widget data
            this.loadWidgetForEdit(widgetId);
        }

        modal.classList.remove('hidden');
    }

    async loadWidgetForEdit(widgetId) {
        try {
            const response = await fetch('/api/widgets');
            const data = await response.json();
            const widget = data.widgets[widgetId];

            if (widget) {
                document.getElementById('widget-title').value = widget.title;
                document.getElementById('widget-type').value = widget.type;
                document.getElementById('widget-page').value = widget.page;

                // Load bindings
                if (widget.bindings && widget.bindings.value) {
                    document.getElementById('binding-value-var').value = widget.bindings.value.variable || '';
                    document.getElementById('binding-value-type').value = widget.bindings.value.plc_type || 'BOOL';
                }

                // ⭐ v5.1.2: Load Feedback-Variable
                if (widget.bindings && widget.bindings.feedback) {
                    document.getElementById('binding-feedback-var').value = widget.bindings.feedback.variable || '';
                    document.getElementById('binding-feedback-type').value = widget.bindings.feedback.plc_type || 'BOOL';
                }

                // ⭐ v5.1.2: Load Switch-Config
                if (widget.type === 'switch' && widget.config) {
                    document.getElementById('switch-mode').value = widget.config.mode || 'toggle';
                    if (widget.config.pulse_duration) {
                        document.getElementById('pulse-duration').value = widget.config.pulse_duration;
                    }

                    // Zeige/verstecke Pulse-Duration basierend auf Mode
                    const pulseDurationContainer = document.getElementById('pulse-duration-container');
                    if (pulseDurationContainer) {
                        pulseDurationContainer.style.display = (widget.config.mode === 'pulse') ? 'block' : 'none';
                    }
                }

                // Zeige/verstecke Switch-Config basierend auf Type
                const switchConfigSection = document.getElementById('switch-config-section');
                if (switchConfigSection) {
                    switchConfigSection.style.display = (widget.type === 'switch') ? 'block' : 'none';
                }
            }
        } catch (error) {
            console.error('❌ Fehler beim Laden des Widgets:', error);
        }
    }

    closeWidgetEditor() {
        const modal = document.getElementById('widget-editor-modal');
        if (modal) {
            modal.classList.add('hidden');
        }
    }

    async saveWidget() {
        const widgetId = document.getElementById('widget-edit-id').value;
        const title = document.getElementById('widget-title').value;
        const type = document.getElementById('widget-type').value;
        const page = document.getElementById('widget-page').value;

        // Bindings
        const bindings = {};
        const valueVar = document.getElementById('binding-value-var').value;
        const valueType = document.getElementById('binding-value-type').value;

        if (valueVar) {
            bindings.value = {
                variable: valueVar,
                plc_type: valueType,
                read_only: false
            };
        }

        // ⭐ v5.1.2: Feedback-Variable
        const feedbackVar = document.getElementById('binding-feedback-var')?.value;
        const feedbackType = document.getElementById('binding-feedback-type')?.value;

        if (feedbackVar) {
            bindings.feedback = {
                variable: feedbackVar,
                plc_type: feedbackType,
                read_only: true
            };
        }

        // ⭐ v5.1.2: Switch-Config (Mode & Pulse Duration)
        const config = {};
        if (type === 'switch') {
            const mode = document.getElementById('switch-mode')?.value || 'toggle';
            config.mode = mode;

            if (mode === 'pulse') {
                const pulseDuration = parseInt(document.getElementById('pulse-duration')?.value || 500);
                config.pulse_duration = pulseDuration;
            }
        }

        const widgetData = {
            title,
            type,
            page,
            bindings,
            config
        };

        try {
            let response;
            if (widgetId) {
                // Update
                response = await fetch(`/api/widgets/${widgetId}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(widgetData)
                });
            } else {
                // Create
                response = await fetch('/api/widgets', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(widgetData)
                });
            }

            if (response.ok) {
                this.closeWidgetEditor();
                await this.loadWidgetList();
            } else {
                alert('Fehler beim Speichern');
            }
        } catch (error) {
            console.error('Fehler:', error);
            alert('Fehler beim Speichern');
        }
    }

    async editWidget(widgetId) {
        this.openWidgetEditor(widgetId);
    }

    async deleteWidget(widgetId) {
        if (!confirm('Widget wirklich löschen?')) return;

        try {
            const response = await fetch(`/api/widgets/${widgetId}`, {
                method: 'DELETE'
            });

            if (response.ok) {
                await this.loadWidgetList();
            } else {
                alert('Fehler beim Löschen');
            }
        } catch (error) {
            console.error('Fehler:', error);
            alert('Fehler beim Löschen');
        }
    }

    async testVariableBinding() {
        const variable = document.getElementById('binding-value-var').value;
        const plcType = document.getElementById('binding-value-type').value;

        if (!variable) {
            alert('Bitte Variable eingeben');
            return;
        }

        try {
            // Test read via PLC write API
            const response = await fetch('/api/plc/symbols?search=' + encodeURIComponent(variable));
            const data = await response.json();

            if (data.symbols && data.symbols.length > 0) {
                alert(`✓ Variable gefunden: ${variable}\nTyp: ${data.symbols[0].type}\n\nHinweis: PLC muss verbunden sein für Live-Test!`);
            } else {
                alert(`⚠️ Variable nicht in Symbolliste gefunden.\nStelle sicher, dass die TPY-Datei hochgeladen ist und die Variable existiert:\n${variable}`);
            }
        } catch (error) {
            console.error('Fehler:', error);
            alert('Fehler beim Testen der Verbindung');
        }
    }

    async browseSymbols() {
        // Open symbol browser from Setup page
        this.showPage('setup');
        // Scroll to symbol browser section
        setTimeout(() => {
            const symbolSection = document.querySelector('#symbol-search');
            if (symbolSection) {
                symbolSection.scrollIntoView({ behavior: 'smooth' });
                symbolSection.focus();
            }
        }, 300);
    }

    // ====================================================================
    // MONITOR DASHBOARD
    // ====================================================================

    async loadMonitorPage() {
        console.log('📊 Lade Monitor-Dashboard...');

        // ⭐ v5.1.1: Lade Widgets für diese Page
        await this.loadAndRenderWidgets('monitor');

        // Initial data load
        await this.loadMonitorData();

        // Setup event listeners
        this.setupMonitorEventListeners();

        // Start auto-refresh if enabled
        const autoRefresh = document.getElementById('monitor-auto-refresh');
        if (autoRefresh && autoRefresh.checked) {
            this.startMonitorAutoRefresh();
        }
    }

    setupMonitorEventListeners() {
        // Auto-Refresh Toggle
        const autoRefreshToggle = document.getElementById('monitor-auto-refresh');
        if (autoRefreshToggle) {
            autoRefreshToggle.addEventListener('change', (e) => {
                if (e.target.checked) {
                    this.startMonitorAutoRefresh();
                } else {
                    this.stopMonitorAutoRefresh();
                }
            });
        }

        // Refresh Button
        const refreshBtn = document.getElementById('monitor-refresh-btn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => this.loadMonitorData());
        }

        // Measure Latency Button
        const latencyBtn = document.getElementById('measure-latency-btn');
        if (latencyBtn) {
            latencyBtn.addEventListener('click', () => this.measureLatency());
        }

        // Export Buttons
        const exportJsonBtn = document.getElementById('export-json-btn');
        if (exportJsonBtn) {
            exportJsonBtn.addEventListener('click', () => this.exportMonitorData('json'));
        }

        const exportCsvBtn = document.getElementById('export-csv-btn');
        if (exportCsvBtn) {
            exportCsvBtn.addEventListener('click', () => this.exportMonitorData('csv'));
        }
    }

    async loadMonitorData() {
        try {
            const response = await fetch('/api/monitor/dataflow');
            if (!response.ok) throw new Error('Failed to fetch monitor data');

            const data = await response.json();

            // Update Statistics Cards
            this.updateMonitorStats(data);

            // Update Data Flow Visualization
            this.updateDataFlowVisualization(data);

            console.log('✓ Monitor-Daten aktualisiert');

        } catch (error) {
            console.error('❌ Fehler beim Laden der Monitor-Daten:', error);
        }
    }

    updateMonitorStats(data) {
        // Active Connections
        const connectionsElem = document.getElementById('monitor-connections');
        if (connectionsElem) {
            connectionsElem.textContent = data.active_connections || 0;
        }

        // PLC Reads
        const plcReadsElem = document.getElementById('monitor-plc-reads');
        if (plcReadsElem) {
            const plcReads = data.protocols.plc?.reads || 0;
            plcReadsElem.textContent = plcReads.toLocaleString();
        }

        // WebSocket Clients
        const wsClientsElem = document.getElementById('monitor-ws-clients');
        if (wsClientsElem) {
            const wsClients = data.protocols.websocket?.active_clients || 0;
            wsClientsElem.textContent = wsClients;
        }

        // Error Rate
        const errorRateElem = document.getElementById('monitor-error-rate');
        if (errorRateElem) {
            const errorRate = data.protocols.plc?.error_rate || '0.0%';
            errorRateElem.textContent = errorRate;
        }
    }

    updateDataFlowVisualization(data) {
        // Update Sources (PLC/MQTT)
        const sourcesContainer = document.getElementById('monitor-sources');
        if (sourcesContainer) {
            let sourcesHtml = '';

            // PLC Source
            if (data.protocols.plc) {
                const plc = data.protocols.plc;
                sourcesHtml += `
                    <div class="p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg mb-2">
                        <div class="font-semibold text-blue-700 dark:text-blue-300">PLC (ADS)</div>
                        <div class="text-sm text-gray-600 dark:text-gray-400">
                            <div>Reads: ${plc.reads || 0}</div>
                            <div>Writes: ${plc.writes || 0}</div>
                            <div>Cache: ${plc.cached_vars || 0}</div>
                        </div>
                    </div>
                `;
            }

            // MQTT Source
            if (data.protocols.mqtt) {
                const mqtt = data.protocols.mqtt;
                sourcesHtml += `
                    <div class="p-3 bg-green-50 dark:bg-green-900/20 rounded-lg">
                        <div class="font-semibold text-green-700 dark:text-green-300">MQTT</div>
                        <div class="text-sm text-gray-600 dark:text-gray-400">
                            <div>Messages: ${mqtt.messages || 0}</div>
                            <div>Topics: ${mqtt.topics || 0}</div>
                        </div>
                    </div>
                `;
            }

            sourcesContainer.innerHTML = sourcesHtml;
        }

        // Update Gateway Info
        const platformElem = document.getElementById('monitor-platform');
        if (platformElem) {
            const platform = data.gateway?.mode || data.gateway?.platform || 'Unknown';
            platformElem.textContent = platform;
        }

        const cacheElem = document.getElementById('monitor-cache');
        if (cacheElem) {
            const cacheVars = data.gateway?.telemetry_cached_variables || 0;
            cacheElem.textContent = `${cacheVars} Variablen`;
        }

        // Update Destinations (WebSocket)
        const destinationsContainer = document.getElementById('monitor-destinations');
        if (destinationsContainer) {
            const wsClients = data.protocols.websocket?.active_clients || 0;
            const wsMessages = data.protocols.websocket?.messages_sent || 0;

            destinationsContainer.innerHTML = `
                <div class="p-3 bg-purple-50 dark:bg-purple-900/20 rounded-lg">
                    <div class="font-semibold text-purple-700 dark:text-purple-300">WebSocket Clients</div>
                    <div class="text-sm text-gray-600 dark:text-gray-400">
                        <div>Aktive Clients: ${wsClients}</div>
                        <div>Gesendete Messages: ${wsMessages}</div>
                    </div>
                </div>
            `;
        }

        // Update Throughput
        const throughputElem = document.getElementById('monitor-throughput');
        if (throughputElem) {
            const throughput = data.total_throughput || 0;
            throughputElem.textContent = `${throughput.toFixed(2)} msg/s`;
        }
    }

    async measureLatency() {
        console.log('⏱️ Messe Latenz...');

        const resultsContainer = document.getElementById('latency-results');
        if (!resultsContainer) return;

        // Show loading
        resultsContainer.innerHTML = '<p class="text-gray-500 dark:text-gray-400">Messe Latenz...</p>';

        try {
            const response = await fetch('/api/monitor/latency');
            if (!response.ok) throw new Error('Failed to measure latency');

            const data = await response.json();

            // Display results
            let resultsHtml = '<div class="space-y-2">';

            // PLC Latency
            if (data.plc) {
                if (data.plc.connected === false) {
                    resultsHtml += `
                        <div class="p-3 bg-red-50 dark:bg-red-900/20 rounded">
                            <div class="font-semibold text-red-700 dark:text-red-300">PLC (ADS)</div>
                            <div class="text-sm text-red-600 dark:text-red-400">Nicht verbunden</div>
                        </div>
                    `;
                } else if (data.plc.success) {
                    resultsHtml += `
                        <div class="p-3 bg-green-50 dark:bg-green-900/20 rounded">
                            <div class="font-semibold text-green-700 dark:text-green-300">PLC (ADS)</div>
                            <div class="text-sm">
                                <span class="text-gray-600 dark:text-gray-400">Latenz:</span>
                                <span class="font-mono">${data.plc.latency_ms.toFixed(2)} ms</span>
                            </div>
                            <div class="text-xs text-gray-500">Variable: ${data.plc.variable || 'MAIN.bTest'}</div>
                        </div>
                    `;
                } else {
                    resultsHtml += `
                        <div class="p-3 bg-red-50 dark:bg-red-900/20 rounded">
                            <div class="font-semibold text-red-700 dark:text-red-300">PLC (ADS)</div>
                            <div class="text-sm text-red-600 dark:text-red-400">Fehler: ${data.plc.error || 'Unbekannter Fehler'}</div>
                        </div>
                    `;
                }
            }

            // WebSocket Latency
            if (data.websocket) {
                const latency = data.websocket.estimated_latency_ms || data.websocket.ping_ms || 5;
                resultsHtml += `
                    <div class="p-3 bg-purple-50 dark:bg-purple-900/20 rounded">
                        <div class="font-semibold text-purple-700 dark:text-purple-300">WebSocket</div>
                        <div class="text-sm">
                            <span class="text-gray-600 dark:text-gray-400">Ping:</span>
                            <span class="font-mono">${latency.toFixed(2)} ms</span>
                        </div>
                        <div class="text-xs text-gray-500">Clients: ${data.websocket.connected_clients || 0}</div>
                    </div>
                `;
            }

            resultsHtml += '</div>';
            resultsContainer.innerHTML = resultsHtml;

            console.log('✓ Latenz gemessen:', data);

        } catch (error) {
            console.error('❌ Fehler beim Messen der Latenz:', error);
            resultsContainer.innerHTML = '<p class="text-red-500">Fehler beim Messen der Latenz</p>';
        }
    }

    async exportMonitorData(format) {
        console.log(`📥 Exportiere Monitor-Daten als ${format.toUpperCase()}...`);

        try {
            // Get time range (last hour)
            const endTime = Date.now();
            const startTime = endTime - (3600 * 1000); // 1 hour ago

            const response = await fetch('/api/monitor/export', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    format: format,
                    start_time: startTime,
                    end_time: endTime
                })
            });

            if (!response.ok) throw new Error('Export failed');

            // Download file
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `monitor_data_${Date.now()}.${format}`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);

            console.log(`✓ Monitor-Daten als ${format.toUpperCase()} exportiert`);

        } catch (error) {
            console.error(`❌ Fehler beim Exportieren als ${format.toUpperCase()}:`, error);
            alert(`Fehler beim Exportieren: ${error.message}`);
        }
    }

    startMonitorAutoRefresh() {
        // Stop existing interval if any
        this.stopMonitorAutoRefresh();

        // Start new interval (refresh every 2 seconds)
        this.monitorRefreshInterval = setInterval(() => {
            this.loadMonitorData();
        }, 2000);

        console.log('✓ Monitor Auto-Refresh gestartet (2s)');
    }

    stopMonitorAutoRefresh() {
        if (this.monitorRefreshInterval) {
            clearInterval(this.monitorRefreshInterval);
            this.monitorRefreshInterval = null;
            console.log('✓ Monitor Auto-Refresh gestoppt');
        }
    }

    // ========================================================================
    // WIDGET RENDERING AUF PAGES
    // ========================================================================

    async loadAndRenderWidgets(pageName) {
        console.log(`🎨 Lade Widgets für Page: ${pageName}`);

        try {
            // Hole alle Widgets vom Server
            const response = await fetch('/api/widgets');
            if (!response.ok) {
                console.error('Fehler beim Laden der Widgets:', response.status);
                return;
            }

            const data = await response.json();
            console.log('🔍 Server Response:', data);  // ⭐ v5.1.2 DEBUG

            // Backend sendet: {"widgets": {...}} oder {"widgets": []}
            // Konvertiere Object zu Array
            let widgets = [];
            if (data.widgets) {
                if (Array.isArray(data.widgets)) {
                    widgets = data.widgets;
                } else if (typeof data.widgets === 'object') {
                    // Object zu Array konvertieren
                    widgets = Object.values(data.widgets);
                }
            }

            console.log(`📦 ${widgets.length} Widgets geladen`, widgets);

            // Filtere Widgets für diese Page
            const pageWidgets = widgets.filter(w => w.page === pageName);
            console.log(`🎯 ${pageWidgets.length} Widgets für ${pageName}`);

            // Finde Container für Widgets
            const container = document.getElementById(`${pageName}-page`);
            if (!container) {
                console.error(`Container #${pageName}-page nicht gefunden`);
                return;
            }

            // ⭐ v5.1.2: Container muss position: relative haben für absolute Widgets
            if (window.getComputedStyle(container).position === 'static') {
                container.style.position = 'relative';
            }
            // Mindesthöhe setzen damit Widgets Platz haben
            container.style.minHeight = '600px';

            // Entferne alte Widgets
            container.querySelectorAll('[data-widget-id]').forEach(w => w.remove());

            // Rendere jedes Widget
            pageWidgets.forEach(widget => {
                this.renderWidget(widget, container);
            });

            console.log(`✅ ${pageWidgets.length} Widgets gerendert`);

        } catch (error) {
            console.error('Fehler beim Laden/Rendern der Widgets:', error);
        }
    }

    renderWidget(widget, container) {
        // Erstelle Widget-Element
        const widgetEl = document.createElement('div');
        widgetEl.className = 'widget bg-white dark:bg-gray-800 p-4 rounded-lg shadow-lg';
        widgetEl.setAttribute('data-widget-id', widget.id);
        widgetEl.style.position = 'absolute';
        // ⭐ v5.1.2: Default-Position (50, 50) statt (0, 0) damit Widget sichtbar ist
        widgetEl.style.left = (widget.position?.x || 50) + 'px';
        widgetEl.style.top = (widget.position?.y || 50) + 'px';
        widgetEl.style.minWidth = '200px';
        widgetEl.style.cursor = 'move';
        widgetEl.style.zIndex = '10';  // ⭐ v5.1.2: Über anderen Elementen

        // ⭐ v5.1.2: Variable-Binding Setup mit Feedback-Support
        if (widget.bindings && widget.bindings.value && widget.bindings.value.variable && this.variableManager) {
            const plcId = widget.plc_id || 'plc_001';

            // Für Switch-Widgets: Subscribe zu Feedback-Variable (falls vorhanden) oder Control-Variable
            const feedbackVar = widget.bindings.feedback?.variable;
            const controlVar = widget.bindings.value.variable;
            const subscribeVar = feedbackVar || controlVar;

            this.variableManager.subscribe(
                widget.id,
                subscribeVar,
                (value, timestamp, type) => {
                    // Update Widget UI
                    this.updateWidgetValue(widget.id, value, type);
                },
                plcId
            );

            if (feedbackVar) {
                console.log(`📌 Widget ${widget.id} subscribed to FEEDBACK ${plcId}/${feedbackVar} (Control: ${controlVar})`);
            } else {
                console.log(`📌 Widget ${widget.id} subscribed to ${plcId}/${subscribeVar} (${widget.bindings.value.plc_type})`);
            }
        }

        // Widget-Typ spezifisches Rendering
        switch(widget.type) {
            case 'switch':
            case 'boolean':
                // ⭐ v5.1.2: Switch-Widget mit Feedback-Support
                const switchValue = widget.value || false;
                const varName = widget.bindings?.value?.variable || 'Keine Variable';
                const feedbackVar = widget.bindings?.feedback?.variable || null;
                const switchMode = widget.config?.mode || 'toggle';  // 'toggle', 'pulse'
                const pulseDuration = widget.config?.pulse_duration || 500;  // ms

                widgetEl.innerHTML = `
                    <div class="widget-header flex justify-between items-center mb-2">
                        <h3 class="text-sm font-bold text-gray-900 dark:text-white">${widget.title}</h3>
                        <button class="text-xs text-red-500 hover:text-red-700" onclick="app.deleteWidget('${widget.id}')">✕</button>
                    </div>
                    <div class="widget-body">
                        <div class="flex items-center space-x-3">
                            <button
                                class="widget-toggle w-16 h-16 rounded-lg ${switchValue ? 'bg-green-500' : 'bg-gray-400 dark:bg-gray-600'} flex flex-col items-center justify-center transition-all duration-200 hover:opacity-80 shadow-lg"
                                onclick="app.toggleSwitch('${widget.id}', '${switchMode}', ${pulseDuration})"
                                data-widget-id="${widget.id}"
                                data-value="${switchValue}">
                                <span class="text-white text-2xl">${switchValue ? '●' : '○'}</span>
                                <span class="text-white text-xs mt-1">${switchValue ? 'ON' : 'OFF'}</span>
                            </button>
                            <div class="flex-1">
                                <div class="text-xs text-gray-600 dark:text-gray-400">
                                    <div class="font-medium">Steuerung: ${varName}</div>
                                    ${feedbackVar ? `<div class="text-xs text-gray-500 mt-1">Feedback: ${feedbackVar}</div>` : ''}
                                    ${switchMode === 'pulse' ? `<div class="text-xs text-blue-500 mt-1">⚡ Impulse (${pulseDuration}ms)</div>` : ''}
                                </div>
                            </div>
                        </div>
                    </div>
                `;
                break;

            case 'number':
                widgetEl.innerHTML = `
                    <div class="widget-header flex justify-between items-center mb-2">
                        <h3 class="text-sm font-bold text-gray-900 dark:text-white">${widget.title}</h3>
                        <button class="text-xs text-red-500 hover:text-red-700" onclick="app.deleteWidget('${widget.id}')">✕</button>
                    </div>
                    <div class="widget-body">
                        <div class="text-3xl font-bold text-blue-600 dark:text-blue-400">
                            ${widget.value || 0}
                        </div>
                        <div class="text-xs text-gray-500 dark:text-gray-400 mt-1">
                            ${widget.variable || 'Keine Variable'}
                        </div>
                    </div>
                `;
                break;

            case 'gauge':
                widgetEl.innerHTML = `
                    <div class="widget-header flex justify-between items-center mb-2">
                        <h3 class="text-sm font-bold text-gray-900 dark:text-white">${widget.title}</h3>
                        <button class="text-xs text-red-500 hover:text-red-700" onclick="app.deleteWidget('${widget.id}')">✕</button>
                    </div>
                    <div class="widget-body">
                        <div class="w-24 h-24 mx-auto">
                            <svg viewBox="0 0 100 100" class="transform -rotate-90">
                                <circle cx="50" cy="50" r="40" fill="none" stroke="#e5e7eb" stroke-width="8"/>
                                <circle cx="50" cy="50" r="40" fill="none" stroke="#3b82f6" stroke-width="8"
                                    stroke-dasharray="${(widget.value || 0) * 2.51} 251.2"
                                    stroke-linecap="round"/>
                            </svg>
                        </div>
                        <div class="text-center mt-2 text-sm text-gray-600 dark:text-gray-400">
                            ${widget.variable || 'Keine Variable'}
                        </div>
                    </div>
                `;
                break;

            default:
                widgetEl.innerHTML = `
                    <div class="widget-header flex justify-between items-center mb-2">
                        <h3 class="text-sm font-bold text-gray-900 dark:text-white">${widget.title}</h3>
                        <button class="text-xs text-red-500 hover:text-red-700" onclick="app.deleteWidget('${widget.id}')">✕</button>
                    </div>
                    <div class="widget-body">
                        <div class="text-xs text-gray-500">
                            Typ: ${widget.type}<br>
                            Variable: ${widget.variable || 'Keine'}
                        </div>
                    </div>
                `;
        }

        container.appendChild(widgetEl);
    }

    async deleteWidget(widgetId) {
        if (!confirm('Widget wirklich löschen?')) return;

        try {
            // ⭐ v5.1.0: Unsubscribe before delete
            if (this.variableManager) {
                this.variableManager.unsubscribe(widgetId);
            }

            const response = await fetch(`/api/widgets/${widgetId}`, {
                method: 'DELETE'
            });

            if (response.ok) {
                console.log(`✅ Widget ${widgetId} gelöscht`);
                // Entferne aus DOM
                const widgetEl = document.querySelector(`[data-widget-id="${widgetId}"]`);
                if (widgetEl) widgetEl.remove();
            } else {
                console.error('Fehler beim Löschen:', response.status);
            }
        } catch (error) {
            console.error('Fehler beim Löschen:', error);
        }
    }

    // ========================================================================
    // ⭐ v5.1.0: VARIABLE MANAGER WIDGET METHODS
    // ========================================================================

    /**
     * Aktualisiert Widget-Wert aus Variable-Update
     *
     * @param {string} widgetId - Widget-ID
     * @param {any} value - Neuer Wert
     * @param {string} type - Variable-Type (BOOL, INT, etc.)
     */
    updateWidgetValue(widgetId, value, type) {
        const widgetEl = document.querySelector(`[data-widget-id="${widgetId}"]`);
        if (!widgetEl) {
            console.warn(`Widget ${widgetId} nicht im DOM gefunden`);
            return;
        }

        // Finde Toggle-Button (Boolean Widget)
        const toggleBtn = widgetEl.querySelector('.widget-toggle');
        if (toggleBtn) {
            // Update Boolean Widget
            const boolValue = Boolean(value);
            toggleBtn.setAttribute('data-value', boolValue);

            // Update CSS Classes
            if (boolValue) {
                toggleBtn.classList.remove('bg-gray-300');
                toggleBtn.classList.add('bg-green-500');
            } else {
                toggleBtn.classList.remove('bg-green-500');
                toggleBtn.classList.add('bg-gray-300');
            }

            // Update Icon
            const iconSpan = toggleBtn.querySelector('span');
            if (iconSpan) {
                iconSpan.textContent = boolValue ? '✓' : '✕';
            }

            console.log(`🔄 Widget ${widgetId} updated: ${value}`);
            return;
        }

        // Number Widget
        const numberDisplay = widgetEl.querySelector('.text-3xl');
        if (numberDisplay) {
            numberDisplay.textContent = value;
            console.log(`🔄 Widget ${widgetId} updated: ${value}`);
            return;
        }

        // Fallback: Console Log
        console.log(`🔄 Widget ${widgetId} update (no handler): ${value} (${type})`);
    }

    /**
     * Toggle Boolean Widget (Click-Handler)
     *
     * @param {string} widgetId - Widget-ID
     */
    async toggleWidget(widgetId) {
        if (!this.variableManager) {
            console.error('Variable Manager nicht verfügbar');
            return;
        }

        // Finde Widget-Element
        const widgetEl = document.querySelector(`[data-widget-id="${widgetId}"]`);
        if (!widgetEl) {
            console.error(`Widget ${widgetId} nicht gefunden`);
            return;
        }

        // Hole Toggle-Button
        const toggleBtn = widgetEl.querySelector('.widget-toggle');
        if (!toggleBtn) {
            console.error(`Widget ${widgetId} hat keinen Toggle-Button`);
            return;
        }

        // Hole aktuellen Wert
        const currentValue = toggleBtn.getAttribute('data-value') === 'true';
        const newValue = !currentValue;

        // Finde Variable-Name (aus HTML)
        const variableText = widgetEl.querySelector('.text-xs.text-gray-500');
        if (!variableText) {
            console.error(`Widget ${widgetId} hat keine Variable-Information`);
            return;
        }

        const variableName = variableText.textContent.trim();
        if (variableName === 'Keine Variable') {
            console.error(`Widget ${widgetId} hat keine Variable zugewiesen`);
            return;
        }

        console.log(`🔘 Toggle Widget ${widgetId}: ${variableName} = ${newValue}`);

        // Optimistic UI Update (sofort sichtbar, bevor PLC antwortet)
        this.updateWidgetValue(widgetId, newValue, 'BOOL');

        // Schreibe zu PLC
        try {
            const success = await this.variableManager.writeVariable(
                variableName,
                newValue,
                'plc_001'
            );

            if (success) {
                console.log(`✅ Toggle erfolgreich: ${widgetId}`);
            } else {
                // Revert bei Fehler
                console.error(`❌ Toggle fehlgeschlagen: ${widgetId} - Revert UI`);
                this.updateWidgetValue(widgetId, currentValue, 'BOOL');
            }
        } catch (error) {
            console.error(`❌ Toggle Error: ${widgetId}`, error);
            // Revert bei Fehler
            this.updateWidgetValue(widgetId, currentValue, 'BOOL');
        }
    }

    /**
     * ⭐ v5.1.2: Toggle Switch Widget mit Feedback & Impulse-Support
     *
     * @param {string} widgetId - Widget-ID
     * @param {string} mode - 'toggle' oder 'pulse'
     * @param {number} pulseDuration - Impulse-Dauer in ms (nur für 'pulse')
     */
    async toggleSwitch(widgetId, mode = 'toggle', pulseDuration = 500) {
        if (!this.variableManager) {
            console.error('❌ Variable Manager nicht verfügbar');
            return;
        }

        // Hole Widget-Config aus gespeicherten Widgets
        let widgetConfig = null;
        try {
            const response = await fetch('/api/widgets');
            const data = await response.json();
            widgetConfig = data.widgets[widgetId];
        } catch (error) {
            console.error('❌ Widget-Config nicht geladen:', error);
            return;
        }

        if (!widgetConfig || !widgetConfig.bindings || !widgetConfig.bindings.value) {
            console.error('❌ Widget-Config ungültig');
            return;
        }

        const controlVar = widgetConfig.bindings.value.variable;
        const feedbackVar = widgetConfig.bindings.feedback?.variable;
        const plcId = widgetConfig.plc_id || 'plc_001';

        console.log(`🔘 Toggle Switch ${widgetId}: Mode=${mode}, Control=${controlVar}, Feedback=${feedbackVar}`);

        try {
            if (mode === 'pulse') {
                // ⚡ IMPULSE-MODUS
                console.log(`⚡ Sende Impulse (${pulseDuration}ms) an ${controlVar}`);

                // 1. Setze auf TRUE
                await this.variableManager.writeVariable(controlVar, true, plcId);

                // 2. Warte pulseDuration ms
                await new Promise(resolve => setTimeout(resolve, pulseDuration));

                // 3. Setze zurück auf FALSE
                await this.variableManager.writeVariable(controlVar, false, plcId);

                console.log(`✅ Impulse gesendet an ${controlVar}`);

            } else {
                // 🔄 TOGGLE-MODUS (Dauersignal)
                // Hole aktuellen Wert vom Feedback (falls vorhanden) oder Control-Variable
                const readVar = feedbackVar || controlVar;
                const currentValue = await this.variableManager.readVariable(readVar, false, plcId);
                const newValue = !currentValue;

                console.log(`🔄 Toggle ${controlVar}: ${currentValue} → ${newValue}`);

                // Optimistic UI Update
                this.updateWidgetValue(widgetId, newValue, 'BOOL');

                // Schreibe zu PLC
                const success = await this.variableManager.writeVariable(controlVar, newValue, plcId);

                if (success) {
                    console.log(`✅ Toggle erfolgreich: ${widgetId}`);
                } else {
                    // Revert bei Fehler
                    console.error(`❌ Toggle fehlgeschlagen - Revert UI`);
                    this.updateWidgetValue(widgetId, currentValue, 'BOOL');
                }
            }
        } catch (error) {
            console.error(`❌ Toggle Error: ${widgetId}`, error);
        }
    }
}

// ========================================================================
// APP START
// ========================================================================

document.addEventListener('DOMContentLoaded', () => {
    window.app = new SmartHomeApp();
});
