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

        // Camera Stream State
        this._hlsInstances = {};
        this._hlsRetryTimers = {};
        this._fullscreenHls = null;
        this._fullscreenCamId = null;
        this._activeCameraStreams = [];
        this._cameraWallHls = {};
        this._cameraWallRetryTimers = {};
        this._cameraWallStreams = [];
        this._rtspSnapshotTimers = {};
        this._rtspSnapshotInFlight = {};
        this._rtspSnapshotObjectUrls = {};
        this._ringSnapshotTimers = {};
        this._ringSnapshotInFlight = {};
        this._ringSnapshotObjectUrls = {};
        this._fullscreenSnapshotTimer = null;
        this._ringPeerConnection = null;
        this._ringWebrtcSessionId = null;
        this._ringWebrtcKeepaliveTimer = null;
        this._ringWidgetConnections = {};
        this._ringWidgetHls = {};
        this._ringWidgetModes = {};
        this._ringLiveEnabled = false;
        this._cameraAlertTimer = null;
        this._cameraAlertRestorePage = null;
        this._cameraTriggerRules = [];
        this._ruleVariableOptions = [];
        this._ruleEditorSelectedIds = new Set();
        this._ruleEditorPage = 1;
        this._ruleEditorPageSize = parseInt(localStorage.getItem('ruleEditorPageSize') || '25', 10) || 25;
        this._ruleEditorActiveGroup = '';
        this._routingConfig = { version: '1.0', description: 'Routing-Konfiguration', routes: [], settings: {} };
        this._routeEditorSelectedId = null;
        this._listenerRegistry = new Map();
        this._listenerScopes = new Map();
        this._featureFlags = {
            'ui.page.camera-wall': true,
            'ui.page.monitor': true,
            'ui.page.admin': true,
            'ui.ring.webrtc': true
        };
        this.customPages = {};
        this.uiSettings = {
            default_page: 'dashboard',
            kiosk_default: false
        };

        // Initialisierung
        this.init();
    }

    init() {
        console.log('🚀 SmartHome App startet...');
        this.setupApiAuthHeaderInjection();

        // Theme anwenden
        this.applyTheme(this.theme);
        this.loadFeatureFlags();
        this._ensureToastContainer();

        // Event-Listener registrieren (nach kurzem Delay für DOM)
        setTimeout(() => {
            this.setupEventListeners();
            console.log('📋 Event-Listener registriert');
        }, 100);

        // Initiale Seite so früh wie möglich anzeigen.
        requestAnimationFrame(() => this.showPage('dashboard'));

        // Nicht-kritische Initialisierung in Idle-Phase verlagern.
        const bootDeferred = async () => {
            await this.loadUISettings();
            await this.loadCustomPages();
            this.applyKioskMode(this.uiSettings.kiosk_default === true);
            if ((this.uiSettings.default_page || 'dashboard') !== 'dashboard') {
                this.showPage(this.uiSettings.default_page || 'dashboard');
            }
            this.initializeSocket();
            this.loadSystemStatus();
            this._loadDevTestScenarios();
        };
        if (typeof window.requestIdleCallback === 'function') {
            window.requestIdleCallback(() => { bootDeferred(); }, { timeout: 1500 });
        } else {
            setTimeout(() => { bootDeferred(); }, 0);
        }

        console.log('✅ SmartHome App bereit');
    }

    _loadDevTestScenarios() {
        try {
            const params = new URLSearchParams(window.location.search || '');
            const enabled = params.get('dev_scenarios') === '1'
                || localStorage.getItem('smarthome_dev_scenarios') === '1';
            if (!enabled) return;
            if (document.getElementById('dev-test-scenarios-script')) return;
            const script = document.createElement('script');
            script.id = 'dev-test-scenarios-script';
            script.src = '/static/js/test_scenarios.js';
            script.defer = true;
            document.body.appendChild(script);
        } catch (error) {
            console.warn('Dev-Test-Szenarien konnten nicht geladen werden:', error.message);
        }
    }

    async loadFeatureFlags() {
        try {
            const response = await fetch('/api/system/feature-flags');
            if (!response.ok) return;
            const payload = await response.json();
            const flags = payload.flags || {};
            if (flags && typeof flags === 'object') {
                this._featureFlags = { ...this._featureFlags, ...flags };
                this.applyFeatureFlagsToNavigation();
            }
        } catch (error) {
            console.warn('⚠️ Feature-Flags konnten nicht geladen werden:', error.message);
        }
    }

    isFeatureEnabled(flagKey, defaultValue = true) {
        if (!(flagKey in this._featureFlags)) return defaultValue;
        return !!this._featureFlags[flagKey];
    }

    applyFeatureFlagsToNavigation() {
        document.querySelectorAll('[data-page]').forEach(btn => {
            const page = btn.getAttribute('data-page');
            const enabled = this.isFeatureEnabled(`ui.page.${page}`, true);
            if (!enabled) {
                btn.classList.add('hidden');
            } else {
                btn.classList.remove('hidden');
            }
        });
    }

    _ensureToastContainer() {
        if (document.getElementById('app-toast-container')) return;
        const container = document.createElement('div');
        container.id = 'app-toast-container';
        container.className = 'fixed top-4 right-4 z-[100] flex flex-col gap-3 w-[92vw] max-w-md';
        document.body.appendChild(container);
    }

    showToast(message, { level = 'info', duration = 5000, actions = [] } = {}) {
        this._ensureToastContainer();
        const container = document.getElementById('app-toast-container');
        if (!container) return;

        const toneClass = level === 'error'
            ? 'border-red-300 bg-red-50 text-red-900'
            : level === 'success'
                ? 'border-green-300 bg-green-50 text-green-900'
                : 'border-blue-300 bg-blue-50 text-blue-900';

        const toast = document.createElement('div');
        toast.className = `rounded-lg border shadow-lg p-3 ${toneClass}`;
        const msg = document.createElement('div');
        msg.className = 'text-sm';
        msg.textContent = String(message || '');
        toast.appendChild(msg);

        if (Array.isArray(actions) && actions.length > 0) {
            const row = document.createElement('div');
            row.className = 'mt-2 flex flex-wrap gap-2';
            actions.slice(0, 2).forEach(action => {
                const btn = document.createElement('button');
                btn.type = 'button';
                btn.className = 'px-2 py-1 text-xs rounded bg-white/90 border border-current';
                btn.textContent = action.label || 'Action';
                btn.addEventListener('click', () => {
                    try { action.onClick && action.onClick(); } catch (e) {}
                    toast.remove();
                });
                row.appendChild(btn);
            });
            toast.appendChild(row);
        }

        container.appendChild(toast);
        if (duration > 0) {
            setTimeout(() => {
                if (toast && toast.parentNode) toast.remove();
            }, duration);
        }
    }

    showRecoverableError(message, retryAction, fallbackPage = null) {
        const actions = [];
        if (typeof retryAction === 'function') {
            actions.push({ label: 'Erneut versuchen', onClick: retryAction });
        }
        if (fallbackPage) {
            actions.push({ label: 'Zu Setup', onClick: () => this.showPage(fallbackPage) });
        }
        this.showToast(message, { level: 'error', duration: 10000, actions });
    }

    setupApiAuthHeaderInjection() {
        if (window.__smarthomeFetchAuthWrapped) {
            return;
        }

        const originalFetch = window.fetch.bind(window);
        window.fetch = async (input, init = {}) => {
            try {
                const path = this._extractApiPath(input);
                if (this._isProtectedApiPath(path)) {
                    const adminKey =
                        localStorage.getItem('smarthome_admin_api_key') ||
                        localStorage.getItem('admin_api_key') ||
                        '';

                    if (adminKey) {
                        const headers = new Headers((init && init.headers) || {});
                        if (!headers.has('X-API-Key') && !headers.has('Authorization')) {
                            headers.set('X-API-Key', adminKey);
                        }
                        init = Object.assign({}, init, { headers });
                    }
                }
            } catch (e) {
                console.warn('API-Key Injection übersprungen:', e);
            }
            return originalFetch(input, init);
        };

        window.__smarthomeFetchAuthWrapped = true;
    }

    _extractApiPath(input) {
        try {
            const raw = typeof input === 'string' ? input : (input && input.url ? input.url : '');
            if (!raw) return '';
            const u = new URL(raw, window.location.origin);
            return u.pathname || '';
        } catch (e) {
            return '';
        }
    }

    _isProtectedApiPath(path) {
        if (!path || !path.startsWith('/api/')) return false;
        if (path.startsWith('/api/admin')) return true;
        if (path.startsWith('/api/cameras/')) return true;
        if (path === '/api/cameras') return true;
        if (path.startsWith('/api/camera-triggers')) return true;
        if (path === '/api/plc/connect') return true;
        if (path === '/api/plc/disconnect') return true;
        if (path.startsWith('/api/plc/ads/route/')) return true;
        if (path === '/api/plc/config') return true;
        if (path === '/api/plc/symbols/upload') return true;
        if (path === '/api/plc/symbols/live') return true;
        if (path === '/api/ring/auth') return true;
        if (path === '/api/ring/cameras/import') return true;
        if (path === '/api/routing/config') return true;
        if (path === '/api/variables/write') return true;
        return false;
    }

    // ========================================================================
    // NAVIGATION
    // ========================================================================

    setupEventListeners() {
        this.bindNavigationButtons();

        // Mobile-Hamburger-Menü
        const hamburger = document.getElementById('hamburger-btn');
        if (hamburger) {
            console.log('🍔 Hamburger-Button gefunden');
            this._bindScopedListener(hamburger, 'click', () => {
                console.log('🍔 Hamburger geklickt');
                this.toggleMobileMenu();
            }, { scope: 'global', key: 'hamburger:click' });
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
            this._bindScopedListener(connectBtn, 'click', () => {
                this.connectPLC();
            }, { scope: 'global', key: 'plc-connect:click' });
        } else {
            console.warn('⚠️ PLC-Connect-Button NICHT gefunden');
        }

        const disconnectBtn = document.getElementById('plc-disconnect-btn');
        if (disconnectBtn) {
            console.log('🔌 PLC-Disconnect-Button gefunden');
            this._bindScopedListener(disconnectBtn, 'click', () => {
                this.disconnectPLC();
            }, { scope: 'global', key: 'plc-disconnect:click' });
        } else {
            console.warn('⚠️ PLC-Disconnect-Button NICHT gefunden');
        }

        const fullscreenSidebar = document.getElementById('fullscreen-toggle-sidebar');
        if (fullscreenSidebar) {
            this._bindScopedListener(fullscreenSidebar, 'click', () => this.toggleFullscreenMode(), { scope: 'global', key: 'fullscreen:sidebar' });
        }
        const fullscreenMobile = document.getElementById('fullscreen-toggle-mobile');
        if (fullscreenMobile) {
            this._bindScopedListener(fullscreenMobile, 'click', () => this.toggleFullscreenMode(), { scope: 'global', key: 'fullscreen:mobile' });
        }
        const kioskSidebar = document.getElementById('kiosk-toggle-sidebar');
        if (kioskSidebar) {
            this._bindScopedListener(kioskSidebar, 'click', () => this.toggleKioskMode(), { scope: 'global', key: 'kiosk:sidebar' });
        }
        const kioskMobile = document.getElementById('kiosk-toggle-mobile');
        if (kioskMobile) {
            this._bindScopedListener(kioskMobile, 'click', () => this.toggleKioskMode(), { scope: 'global', key: 'kiosk:mobile' });
        }
    }

    bindNavigationButtons() {
        const navButtons = document.querySelectorAll('[data-page]');
        console.log(`🔍 Gefundene Navigation-Buttons: ${navButtons.length}`);
        navButtons.forEach((btn, index) => {
            const page = btn.getAttribute('data-page');
            this._bindScopedListener(btn, 'click', (e) => {
                e.preventDefault();
                this.showPage(page);
                this.closeMobileMenu();
            }, { scope: 'global', key: `nav:${page}:click:${index}` });
        });
    }

    async loadCustomPages() {
        try {
            const response = await fetch('/api/pages');
            const data = await response.json();
            this.customPages = data.pages || {};
            this.renderCustomPageNavigation();
            this.refreshWidgetPageOptions();
            this.refreshPanelSettingsUI();
        } catch (error) {
            console.warn('⚠️ Seiten konnten nicht geladen werden:', error.message);
        }
    }

    async loadUISettings() {
        try {
            const response = await fetch('/api/ui-settings');
            if (!response.ok) return;
            const data = await response.json();
            this.uiSettings = {
                default_page: data.default_page || 'dashboard',
                kiosk_default: !!data.kiosk_default
            };
        } catch (error) {
            console.warn('⚠️ UI-Settings konnten nicht geladen werden:', error.message);
        }
    }

    renderCustomPageNavigation() {
        const container = document.getElementById('nav-dynamic-pages');
        if (!container) return;
        const pages = Object.values(this.customPages || {}).sort((a, b) => {
            const oa = Number(a?.order ?? 9999);
            const ob = Number(b?.order ?? 9999);
            if (oa !== ob) return oa - ob;
            return String(a?.name || a?.id || '').localeCompare(String(b?.name || b?.id || ''));
        });
        if (pages.length === 0) {
            container.innerHTML = '<p class="px-4 py-2 text-xs text-gray-500">Keine Räume angelegt</p>';
            return;
        }
        container.innerHTML = pages.map(page => `
            <a href="#" data-page="${this.escapeHtml(page.id)}" class="nav-link flex items-center space-x-3 px-4 py-2 rounded-lg">
                <i data-lucide="${this.escapeHtml(page.icon || 'layout-grid')}" class="w-4 h-4"></i>
                <span>${this.escapeHtml(page.name || page.id)}</span>
            </a>
        `).join('');
        this.bindNavigationButtons();
        if (typeof lucide !== 'undefined') lucide.createIcons();
    }

    toggleFullscreenMode() {
        if (!document.fullscreenElement) {
            document.documentElement.requestFullscreen().catch((error) => {
                console.warn('Vollbild konnte nicht aktiviert werden:', error.message);
            });
        } else {
            document.exitFullscreen().catch(() => {});
        }
    }

    toggleKioskMode() {
        const isEnabled = document.body.classList.contains('kiosk-mode');
        this.applyKioskMode(!isEnabled);
    }

    applyKioskMode(enabled) {
        document.body.classList.toggle('kiosk-mode', !!enabled);
        const iconName = enabled ? 'panel-top-open' : 'panel-top-close';
        [
            ['kiosk-toggle-sidebar', 'w-4 h-4'],
            ['kiosk-toggle-mobile', 'w-5 h-5']
        ].forEach(([id, size]) => {
            const btn = document.getElementById(id);
            if (!btn) return;
            btn.innerHTML = `<i data-lucide="${iconName}" class="${size}"></i>`;
        });
        if (typeof lucide !== 'undefined') lucide.createIcons();
    }

    _bindScopedListener(el, event, handler, { scope = 'global', key = null, options = undefined } = {}) {
        if (!el || typeof el.addEventListener !== 'function') return;
        const listenerKey = key || `${scope}:${event}:${el.id || el.name || el.className || 'anon'}`;

        const existing = this._listenerRegistry.get(listenerKey);
        if (existing) {
            try {
                existing.el.removeEventListener(existing.event, existing.handler, existing.options);
            } catch (e) {}
        }

        el.addEventListener(event, handler, options);
        this._listenerRegistry.set(listenerKey, { el, event, handler, options, scope });

        const scoped = this._listenerScopes.get(scope) || new Set();
        scoped.add(listenerKey);
        this._listenerScopes.set(scope, scoped);
    }

    _removeListenerScope(scope) {
        const scoped = this._listenerScopes.get(scope);
        if (!scoped) return;
        scoped.forEach((listenerKey) => {
            const ref = this._listenerRegistry.get(listenerKey);
            if (!ref) return;
            try {
                ref.el.removeEventListener(ref.event, ref.handler, ref.options);
            } catch (e) {}
            this._listenerRegistry.delete(listenerKey);
        });
        this._listenerScopes.delete(scope);
    }

    showPage(pageName) {
        console.log(`🔄 Zeige Seite: ${pageName}`);
        this.ensureDynamicPage(pageName);
        if (!this.isFeatureEnabled(`ui.page.${pageName}`, true)) {
            this.showToast(`Feature für Seite '${pageName}' ist aktuell deaktiviert.`, { level: 'info' });
            pageName = 'dashboard';
        }

        // Cleanup beim Verlassen der Kamera-Seiten
        if (this.currentPage === 'cameras' && pageName !== 'cameras') {
            this._cleanupCameraStreams();
        }
        if (this.currentPage === 'camera-wall' && pageName !== 'camera-wall') {
            this._cleanupCameraWallStreams();
        }
        this._removeListenerScope(`page:${this.currentPage}`);

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
            const mobileTitle = document.getElementById('page-title-mobile');
            if (mobileTitle) {
                const customName = this.customPages?.[pageName]?.name;
                mobileTitle.textContent = customName || pageName.charAt(0).toUpperCase() + pageName.slice(1);
            }

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
            case 'camera-wall':
                this.loadCameraWallPage();
                break;
            default:
                if (this.customPages && this.customPages[pageName]) {
                    this.loadAndRenderWidgets(pageName);
                }
                break;
        }
    }

    ensureDynamicPage(pageName) {
        if (!this.customPages || !this.customPages[pageName]) return;
        const existing = document.getElementById(`${pageName}-page`);
        if (existing) return;

        const main = document.querySelector('main');
        if (!main) return;

        const title = this.customPages[pageName]?.name || pageName;
        const page = document.createElement('div');
        page.id = `${pageName}-page`;
        page.className = 'page page-container p-6';
        page.innerHTML = `
            <h1 class="text-2xl font-bold text-gray-900 dark:text-white mb-6 hidden md:block">${this.escapeHtml(title)}</h1>
            <div id="${this.escapeHtml(pageName)}-widgets-dynamic" class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4 mb-6"></div>
            <div data-legacy-page="${this.escapeHtml(pageName)}" class="text-sm text-gray-500 dark:text-gray-400">Keine Widgets auf dieser Seite.</div>
        `;
        main.appendChild(page);
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

        // ⭐ v4.6.0: Initialize Variable Manager
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

        this.socket.registerCallback('camera_alert', (data) => {
            this._handleCameraAlert(data);
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
            this.showRecoverableError(
                `System-Status konnte nicht geladen werden: ${error.message}`,
                () => this.loadSystemStatus(),
                'setup'
            );
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
        const runtimeType = (document.getElementById('plc-runtime-type')?.value || 'TC3').toUpperCase();

        if (!amsId) {
            this.showToast('Bitte AMS Net ID eingeben.', { level: 'error' });
            return;
        }

        console.log('🔌 Verbinde PLC:', amsId);

        // Speichere Konfiguration in LocalStorage
        localStorage.setItem('plc_ams_id', amsId);
        localStorage.setItem('plc_ams_port', amsPort.toString());
        localStorage.setItem('plc_ip_address', ipAddress);
        localStorage.setItem('plc_runtime_type', runtimeType);

        try {
            const response = await fetch('/api/plc/connect', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    ams_id: amsId,
                    ams_port: amsPort,
                    ip_address: ipAddress,
                    runtime_type: runtimeType
                })
            });

            const data = await response.json();

            if (data.success) {
                this.plcConnected = true;
                this.updatePLCStatus(true);
                console.log('✅ PLC verbunden');
                this.showToast('PLC erfolgreich verbunden.', { level: 'success', duration: 3000 });
            } else {
                this.showRecoverableError(
                    'PLC-Verbindung fehlgeschlagen: ' + (data.error || 'Unbekannter Fehler'),
                    () => this.connectPLC(),
                    'setup'
                );
            }
        } catch (error) {
            console.error('Fehler bei PLC-Verbindung:', error);
            this.showRecoverableError(
                'Fehler bei PLC-Verbindung: ' + error.message,
                () => this.connectPLC(),
                'setup'
            );
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
                this.showToast('PLC getrennt.', { level: 'info', duration: 2500 });
            }
        } catch (error) {
            console.error('Fehler beim Trennen der PLC:', error);
            this.showRecoverableError(
                'Fehler beim Trennen der PLC: ' + error.message,
                () => this.disconnectPLC(),
                'setup'
            );
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

    escapeHtml(value) {
        if (value === null || value === undefined) return '';
        return String(value)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
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
        const quickActions = document.querySelectorAll('#dashboard-page [data-legacy-page="dashboard"] .grid button');
        if (!quickActions || quickActions.length === 0) return;

        quickActions.forEach((btn, index) => {
            const span = btn.querySelector('span');
            if (!span) return;

            const actionName = span.textContent.trim();

            // Entferne alte Event-Listener
            btn.replaceWith(btn.cloneNode(true));
            const newBtn = document.querySelectorAll('#dashboard-page [data-legacy-page="dashboard"] .grid button')[index];

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

        // ⭐ v4.6.0: Lade Widgets für diese Page
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

        // ⭐ v4.6.0: Lade Widgets für diese Page
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

        // ⭐ v4.6.0: Lade Widgets für diese Page
        await this.loadAndRenderWidgets('energy');

        // Energie-Widgets werden über Telemetrie aktualisiert
        // Hier könnten Charts/Graphen initialisiert werden
    }

    async loadCamerasPage() {
        console.log('📹 Lade Kameras...');
        const scope = 'page:cameras';

        // ⭐ v4.6.0: Lade Widgets für diese Page
        await this.loadAndRenderWidgets('cameras');

        // Grid-Layout aus localStorage laden
        this._applyGridLayout();
        this._setupGridLayoutToggle();

        // Registriere Add-Camera-Button
        const addCameraBtn = document.getElementById('add-camera-btn');
        if (addCameraBtn) this._bindScopedListener(addCameraBtn, 'click', () => this.addCamera(), { scope, key: 'cameras:add-camera' });

        // Diagnose-Button registrieren
        const diagnoseBtn = document.getElementById('diagnose-btn');
        if (diagnoseBtn) this._bindScopedListener(diagnoseBtn, 'click', () => this._runCameraDiagnose(), { scope, key: 'cameras:diagnose' });

        // Netzwerk-Scan-Button registrieren
        const scanBtn = document.getElementById('network-scan-btn');
        if (scanBtn) this._bindScopedListener(scanBtn, 'click', () => this._runNetworkScan(), { scope, key: 'cameras:scan' });

        // Ring-Import-Button registrieren
        const ringImportBtn = document.getElementById('import-ring-btn');
        if (ringImportBtn) this._bindScopedListener(ringImportBtn, 'click', () => this._openRingImport(), { scope, key: 'cameras:ring-import' });

        const ringAuthBtn = document.getElementById('ring-auth-btn');
        if (ringAuthBtn) this._bindScopedListener(ringAuthBtn, 'click', () => this._ringAuthenticateFromForm(), { scope, key: 'cameras:ring-auth' });

        const ringWebrtcPreferred = document.getElementById('ring-webrtc-preferred');
        if (ringWebrtcPreferred) {
            const stored = localStorage.getItem('ringWebrtcPreferred');
            ringWebrtcPreferred.checked = stored !== '0';
            this._bindScopedListener(ringWebrtcPreferred, 'change', () => {
                localStorage.setItem('ringWebrtcPreferred', ringWebrtcPreferred.checked ? '1' : '0');
            }, { scope, key: 'cameras:ring-webrtc-preferred' });
        }

        this._refreshRingStatus();

        // Lade gespeicherte Kameras und starte On-Demand Streams
        this.loadSavedCameras();
    }

    _getScanOptions() {
        // Ports aus Checkboxen
        const ports = [];
        document.querySelectorAll('.scan-port-cb:checked').forEach(cb => {
            ports.push(parseInt(cb.value));
        });
        // Custom Ports
        const customPorts = document.getElementById('scan-custom-ports')?.value?.trim();
        if (customPorts) {
            customPorts.split(/[,\s]+/).forEach(p => {
                const num = parseInt(p);
                if (num > 0 && num <= 65535 && !ports.includes(num)) ports.push(num);
            });
        }
        // Credentials
        const user = document.getElementById('scan-user')?.value?.trim() || 'admin';
        const password = document.getElementById('scan-password')?.value?.trim() || 'admin';
        return { ports, user, password };
    }

    async _runNetworkScan() {
        const resultPanel = document.getElementById('scan-result');
        const btn = document.getElementById('network-scan-btn');
        const opts = this._getScanOptions();

        btn.disabled = true;
        btn.innerHTML = '<span class="animate-pulse">Scanne Netzwerk...</span>';
        resultPanel.classList.remove('hidden');
        resultPanel.innerHTML = `<p class="text-gray-500 animate-pulse">WS-Discovery + Port-Scan (${opts.ports.join(', ')}) laeuft, bitte warten...</p>`;

        try {
            const resp = await fetch('/api/cameras/scan', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ ports: opts.ports, user: opts.user, password: opts.password })
            });
            const data = await resp.json();

            if (!resp.ok) {
                resultPanel.innerHTML = `<p class="text-red-500">Fehler: ${data.error || 'Unbekannt'}</p>`;
                return;
            }

            let html = `<div class="mb-2 text-xs text-gray-500">Subnet: ${data.subnet}.0/24 | Methoden: ${(data.scan_method || []).join(', ')}</div>`;

            if (!data.devices || data.devices.length === 0) {
                html += '<p class="text-gray-500">Keine Kameras im Netzwerk gefunden</p>';
            } else {
                html += `<p class="font-semibold text-gray-900 dark:text-white mb-2">${data.devices.length} Geraet(e) gefunden:</p>`;
                html += '<div class="space-y-2">';
                data.devices.forEach(dev => {
                    const typeColor = dev.type === 'camera'
                        ? 'bg-green-100 text-green-800 dark:bg-green-800 dark:text-green-100'
                        : 'bg-yellow-100 text-yellow-800 dark:bg-yellow-800 dark:text-yellow-100';
                    const typeLabel = dev.type === 'camera' ? 'Kamera' : 'Moeglich';
                    const discoveryBadge = dev.discovery === 'onvif'
                        ? '<span class="px-1.5 py-0.5 rounded text-xs bg-blue-100 text-blue-800 dark:bg-blue-800 dark:text-blue-100">ONVIF</span>'
                        : '';
                    const ports = (dev.ports || []).map(p => `<span class="px-1.5 py-0.5 rounded text-xs bg-gray-200 dark:bg-gray-600 text-gray-700 dark:text-gray-300">${p}</span>`).join(' ');

                    html += `
                        <div class="flex items-center justify-between p-2 bg-white dark:bg-gray-800 rounded border border-gray-200 dark:border-gray-600">
                            <div class="flex items-center space-x-3">
                                <span class="font-mono text-sm font-semibold text-gray-900 dark:text-white">${dev.host}</span>
                                <span class="px-1.5 py-0.5 rounded text-xs ${typeColor}">${typeLabel}</span>
                                ${discoveryBadge}
                                <span class="text-xs text-gray-500">${dev.name || ''}</span>
                            </div>
                            <div class="flex items-center space-x-2">
                                <span class="text-xs text-gray-400">Ports: ${ports}</span>
                                <button class="scan-diagnose-btn px-3 py-1 bg-green-600 text-white text-xs rounded hover:bg-green-700" data-host="${dev.host}">Diagnose</button>
                            </div>
                        </div>`;
                });
                html += '</div>';
            }

            resultPanel.innerHTML = html;

            // Diagnose-Buttons: IP ins Diagnose-Feld eintragen und Diagnose starten
            resultPanel.querySelectorAll('.scan-diagnose-btn').forEach(b => {
                b.addEventListener('click', () => {
                    const ip = b.getAttribute('data-host');
                    const ipInput = document.getElementById('diagnose-ip');
                    if (ipInput) ipInput.value = ip;
                    this._runCameraDiagnose();
                });
            });

            if (typeof lucide !== 'undefined') lucide.createIcons();

        } catch (e) {
            resultPanel.innerHTML = `<p class="text-red-500">Verbindungsfehler: ${e.message}</p>`;
        } finally {
            btn.disabled = false;
            btn.innerHTML = '<i data-lucide="radar" class="w-4 h-4"></i><span>Netzwerk scannen</span>';
            if (typeof lucide !== 'undefined') lucide.createIcons();
        }
    }

    async _runCameraDiagnose() {
        const ipInput = document.getElementById('diagnose-ip');
        const resultPanel = document.getElementById('diagnose-result');
        const btn = document.getElementById('diagnose-btn');
        const ip = ipInput?.value?.trim();
        const opts = this._getScanOptions();

        if (!ip) {
            alert('Bitte IP-Adresse eingeben');
            return;
        }

        // UI: Ladezustand
        btn.disabled = true;
        btn.innerHTML = '<span class="animate-pulse">Scanne...</span>';
        resultPanel.classList.remove('hidden');
        resultPanel.innerHTML = '<p class="text-gray-500 animate-pulse">Diagnose laeuft, bitte warten...</p>';

        try {
            const resp = await fetch('/api/cameras/diagnose', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ host: ip, user: opts.user, password: opts.password })
            });
            const data = await resp.json();

            if (!resp.ok) {
                resultPanel.innerHTML = `<p class="text-red-500">Fehler: ${data.error || 'Unbekannt'}</p>`;
                return;
            }

            // Ergebnis rendern
            let html = '';

            // Offene Ports
            html += `<div class="mb-3"><span class="font-semibold text-gray-900 dark:text-white">Offene Ports:</span> `;
            if (data.ports && data.ports.length > 0) {
                html += data.ports.map(p => `<span class="inline-block px-2 py-0.5 bg-green-100 text-green-800 dark:bg-green-800 dark:text-green-100 rounded text-xs mr-1">${p}</span>`).join('');
            } else {
                html += '<span class="text-gray-500">Keine gefunden</span>';
            }
            html += '</div>';

            // Streams
            html += '<div class="mb-3"><span class="font-semibold text-gray-900 dark:text-white">Erkannte Streams:</span>';
            if (data.streams && data.streams.length > 0) {
                html += '<div class="mt-1 space-y-1">';
                data.streams.forEach(s => {
                    const label = s.stream_type === 'mainstream' ? 'Main' : 'Sub';
                    const badge = s.stream_type === 'mainstream'
                        ? 'bg-blue-100 text-blue-800 dark:bg-blue-800 dark:text-blue-100'
                        : 'bg-purple-100 text-purple-800 dark:bg-purple-800 dark:text-purple-100';
                    html += `<div class="flex items-center space-x-2">
                        <span class="px-2 py-0.5 rounded text-xs ${badge}">${label}</span>
                        <span class="font-mono text-xs text-gray-700 dark:text-gray-300">${s.url}</span>
                        <span class="text-xs text-gray-500">${s.codec} ${s.width}x${s.height} ${s.fps || '?'}fps</span>
                    </div>`;
                });
                html += '</div>';
            } else {
                html += ' <span class="text-gray-500">Keine gefunden</span>';
            }
            html += '</div>';

            // ONVIF
            html += '<div class="mb-3"><span class="font-semibold text-gray-900 dark:text-white">ONVIF:</span> ';
            if (data.onvif && data.onvif.available) {
                html += `<span class="text-green-600 dark:text-green-400">Ja (Port ${data.onvif.port})</span>`;
                if (data.onvif.device_info) {
                    const di = data.onvif.device_info;
                    html += `<span class="text-xs text-gray-500 ml-2">${di.manufacturer} ${di.model}</span>`;
                }
                if (data.onvif.ptz_available) {
                    html += ' <span class="px-2 py-0.5 bg-yellow-100 text-yellow-800 dark:bg-yellow-800 dark:text-yellow-100 rounded text-xs">PTZ</span>';
                }
            } else {
                html += '<span class="text-gray-500">Nicht gefunden</span>';
            }
            html += '</div>';

            // Snapshot
            html += '<div class="mb-3"><span class="font-semibold text-gray-900 dark:text-white">Snapshot:</span> ';
            if (data.snapshot) {
                html += `<span class="text-green-600 dark:text-green-400 font-mono text-xs">${data.snapshot.url}</span>`;
            } else {
                html += '<span class="text-gray-500">Nicht gefunden</span>';
            }
            html += '</div>';

            // Uebernehmen-Button
            if (data.streams && data.streams.length > 0) {
                // Daten fuer Uebernahme vorbereiten
                const mainstream = data.streams.find(s => s.stream_type === 'mainstream');
                const substream = data.streams.find(s => s.stream_type === 'substream');
                const mainUrl = mainstream ? mainstream.url : (data.streams[0] ? data.streams[0].url : '');
                const subUrl = substream ? substream.url : '';

                html += `<button id="diagnose-apply-btn" class="mt-2 px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700"
                    data-main-url="${mainUrl}"
                    data-sub-url="${subUrl}"
                    data-onvif-port="${data.onvif ? data.onvif.port : ''}"
                    data-host="${ip}">
                    Uebernehmen
                </button>`;
            }

            resultPanel.innerHTML = html;

            // Uebernehmen-Handler
            const applyBtn = document.getElementById('diagnose-apply-btn');
            if (applyBtn) {
                applyBtn.addEventListener('click', () => {
                    const nameInput = document.getElementById('camera-name');
                    const urlInput = document.getElementById('camera-rtsp-url');
                    if (nameInput) nameInput.value = `Kamera ${applyBtn.dataset.host}`;
                    if (urlInput) urlInput.value = applyBtn.dataset.mainUrl;
                });
            }

            if (typeof lucide !== 'undefined') lucide.createIcons();

        } catch (e) {
            resultPanel.innerHTML = `<p class="text-red-500">Verbindungsfehler: ${e.message}</p>`;
        } finally {
            btn.disabled = false;
            btn.innerHTML = '<i data-lucide="search" class="w-4 h-4"></i><span>Diagnose</span>';
            if (typeof lucide !== 'undefined') lucide.createIcons();
        }
    }

    async _refreshRingStatus() {
        const statusEl = document.getElementById('ring-status');
        const userAgentInput = document.getElementById('ring-user-agent');
        if (!statusEl) return { available: false, configured: false };

        try {
            const resp = await fetch('/api/ring/status');
            const data = await resp.json();

            if (!resp.ok) {
                statusEl.textContent = `Ring Status: Fehler (${data.error || 'Unbekannt'})`;
                return { available: false, configured: false };
            }

            if (userAgentInput && data.user_agent && !userAgentInput.value) {
                userAgentInput.value = data.user_agent;
            }

            if (!data.available) {
                statusEl.textContent = 'Ring Status: Modul nicht installiert (ring_doorbell fehlt)';
            } else if (data.configured) {
                statusEl.textContent = `Ring Status: verbunden (User-Agent: ${data.user_agent || 'n/a'})`;
            } else {
                statusEl.textContent = 'Ring Status: nicht verbunden';
            }

            return data;
        } catch (e) {
            statusEl.textContent = `Ring Status: Fehler (${e.message})`;
            return { available: false, configured: false };
        }
    }

    async _ringAuthenticateFromForm() {
        const username = document.getElementById('ring-username')?.value?.trim();
        const password = document.getElementById('ring-password')?.value || '';
        const otpRaw = document.getElementById('ring-otp')?.value?.trim() || '';
        const otp = otpRaw.replace(/\D/g, '');
        const userAgent = document.getElementById('ring-user-agent')?.value?.trim() || '';

        if (!username || !password) {
            alert('Bitte Ring Benutzer/E-Mail und Passwort eintragen.');
            return false;
        }

        const resp = await fetch('/api/ring/auth', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                username,
                password,
                otp: otp || undefined,
                user_agent: userAgent || undefined
            })
        });
        const data = await resp.json();
        if (!resp.ok || !data.success) {
            alert(`Ring-Authentifizierung fehlgeschlagen: ${data.error || 'Unbekannt'}`);
            await this._refreshRingStatus();
            return false;
        }

        // OTP nach Erfolg leeren
        const otpInput = document.getElementById('ring-otp');
        if (otpInput) otpInput.value = '';

        await this._refreshRingStatus();
        return true;
    }

    async _ringEnsureAuthenticated() {
        const status = await this._refreshRingStatus();
        if (!status.available) {
            alert('Ring-Integration ist nicht verfügbar. Bitte ring_doorbell installieren.');
            return false;
        }
        if (status.configured) return true;

        return await this._ringAuthenticateFromForm();
    }

    async _openRingImport() {
        const panel = document.getElementById('ring-import-result');
        if (!panel) return;

        panel.classList.remove('hidden');
        panel.innerHTML = '<p class="text-gray-500 animate-pulse">Lade Ring-Kameras...</p>';

        try {
            const ok = await this._ringEnsureAuthenticated();
            if (!ok) {
                panel.innerHTML = '<p class="text-yellow-600">Ring-Authentifizierung abgebrochen.</p>';
                return;
            }

            const resp = await fetch('/api/ring/cameras');
            const data = await resp.json();
            if (!resp.ok || !data.success) {
                // Token kann als "configured" gelten, aber serverseitig ungueltig sein.
                // Bei 401 versuchen wir automatisch einen Re-Auth mit den Formdaten.
                if (resp.status === 401) {
                    const reauthed = await this._ringAuthenticateFromForm();
                    if (reauthed) {
                        const retryResp = await fetch('/api/ring/cameras');
                        const retryData = await retryResp.json();
                        if (retryResp.ok && retryData.success) {
                            return this._renderRingImportPanel(panel, retryData.cameras || []);
                        }
                        panel.innerHTML = `<p class=\"text-red-500\">Fehler nach Re-Auth: ${retryData.error || 'Unbekannt'}</p>`;
                        return;
                    }
                }
                panel.innerHTML = `<p class=\"text-red-500\">Fehler: ${data.error || 'Unbekannt'}</p>`;
                return;
            }

            this._renderRingImportPanel(panel, data.cameras || []);
        } catch (e) {
            panel.innerHTML = `<p class=\"text-red-500\">Fehler: ${e.message}</p>`;
        }
    }

    _renderRingImportPanel(panel, cameras) {
        if (!panel) return;
        if (!cameras || cameras.length === 0) {
            panel.innerHTML = '<p class="text-gray-500">Keine Ring-Kameras gefunden.</p>';
            return;
        }

        let html = '<div class="space-y-2">';
        cameras.forEach((cam) => {
            html += `
                <div class="flex items-center justify-between p-2 rounded border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-800">
                    <div class="min-w-0">
                        <p class="font-medium text-gray-900 dark:text-white">${cam.name}</p>
                        <p class="text-xs text-gray-500 font-mono">device_id: ${cam.device_id}</p>
                    </div>
                    <button class="ring-import-device-btn px-3 py-1.5 bg-orange-600 text-white text-xs rounded hover:bg-orange-700"
                            data-device-id="${cam.device_id}" data-device-name="${cam.name}">
                        Importieren
                    </button>
                </div>
            `;
        });
        html += '</div>';
        panel.innerHTML = html;

        panel.querySelectorAll('.ring-import-device-btn').forEach(btn => {
            btn.addEventListener('click', async () => {
                const ringDeviceId = btn.getAttribute('data-device-id');
                const ringDeviceName = btn.getAttribute('data-device-name');
                await this._importRingDevice(ringDeviceId, ringDeviceName);
            });
        });
    }

    async _importRingDevice(ringDeviceId, ringDeviceName) {
        const camId = `ring_${ringDeviceId}`;
        const resp = await fetch('/api/ring/cameras/import', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                id: camId,
                ring_device_id: ringDeviceId,
                name: ringDeviceName
            })
        });
        const data = await resp.json();
        if (!resp.ok || !data.success) {
            alert(`Import fehlgeschlagen: ${data.error || 'Unbekannt'}`);
            return;
        }

        this.loadSavedCameras();
    }

    async addCamera() {
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

        const streamType = isRTSP ? 'rtsp' : 'mjpeg';
        const camId = 'cam_' + Date.now();

        try {
            const resp = await fetch('/api/cameras', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    id: camId,
                    name: name,
                    url: streamUrl,
                    type: streamType,
                    autostart: true
                })
            });
            const result = await resp.json();
            if (!resp.ok) {
                alert('Fehler: ' + (result.error || 'Unbekannt'));
                return;
            }
            console.log(`Kamera hinzugefuegt: ${name} (${camId})`);
        } catch (e) {
            console.error('Fehler beim Hinzufuegen der Kamera:', e);
            alert('Server nicht erreichbar');
            return;
        }

        // Leere Inputs
        if (nameInput) nameInput.value = '';
        if (urlInput) urlInput.value = '';

        // Lade Liste neu
        this.loadSavedCameras();
    }

    async loadSavedCameras() {
        const cameraListContainer = document.getElementById('camera-list');
        const camerasGridContainer = document.getElementById('cameras-grid');

        if (!cameraListContainer || !camerasGridContainer) return;

        // Lade Kameras vom Server
        let cameras = {};
        try {
            const resp = await fetch('/api/cameras');
            const data = await resp.json();
            cameras = data.cameras || {};
        } catch (e) {
            console.error('Fehler beim Laden der Kameras:', e);
            cameraListContainer.innerHTML = '<p class="text-sm text-red-500">Server nicht erreichbar</p>';
            return;
        }

        const camIds = Object.keys(cameras);
        this._clearRtspSnapshotTimers();
        this._clearRingSnapshotTimers();
        for (const timer of Object.values(this._hlsRetryTimers)) {
            clearTimeout(timer);
        }
        this._hlsRetryTimers = {};
        for (const [camId, hls] of Object.entries(this._hlsInstances)) {
            try { hls.destroy(); } catch (e) {}
        }
        this._hlsInstances = {};
        if (camIds.length === 0) {
            cameraListContainer.innerHTML = '<p class="text-sm text-gray-500">Keine Kameras konfiguriert</p>';
            camerasGridContainer.innerHTML = '<p class="text-gray-500">Kameras werden nach Konfiguration hier angezeigt...</p>';
            return;
        }

        // Rendere Kamera-Liste (Config-Bereich)
        let listHtml = '<div class="space-y-2">';
        camIds.forEach(camId => {
            const cam = cameras[camId];
            const streamType = (cam.type || 'rtsp').toUpperCase();
            const statusDot = cam.stream_running
                ? '<span class="w-2 h-2 rounded-full bg-green-500 inline-block mr-1"></span>'
                : '<span class="w-2 h-2 rounded-full bg-gray-400 inline-block mr-1"></span>';

            const onvifHost = cam.onvif?.host || '';
            const onvifPort = cam.onvif?.port || '';
            const onvifUser = cam.onvif?.user || 'admin';
            const onvifPass = cam.onvif?.password || 'admin';

            listHtml += `
                <div class="p-3 bg-gray-50 dark:bg-gray-700 rounded-lg" id="cam-entry-${camId}">
                    <!-- Anzeige-Modus -->
                    <div class="cam-display flex items-center justify-between">
                        <div class="flex items-center space-x-3 min-w-0">
                            <i data-lucide="video" class="w-5 h-5 text-blue-500 flex-shrink-0"></i>
                            <div class="min-w-0">
                                <p class="font-medium text-gray-900 dark:text-white">${statusDot}${cam.name}</p>
                                <p class="text-xs text-gray-500 font-mono truncate">${cam.url}</p>
                                ${cam.substream_url ? `<p class="text-xs text-gray-400 font-mono truncate">Sub: ${cam.substream_url}</p>` : ''}
                                <div class="flex items-center space-x-1 mt-0.5">
                                    <span class="text-xs px-2 py-0.5 rounded ${streamType === 'MJPEG' ? 'bg-green-100 text-green-800' : streamType === 'RING' ? 'bg-orange-100 text-orange-800' : 'bg-blue-100 text-blue-800'}">${streamType}</span>
                                    ${cam.onvif ? '<span class="text-xs px-2 py-0.5 rounded bg-yellow-100 text-yellow-800">ONVIF</span>' : ''}
                                </div>
                            </div>
                        </div>
                        <div class="flex items-center space-x-2 flex-shrink-0">
                            <button class="px-3 py-1 bg-gray-500 text-white text-sm rounded hover:bg-gray-600 edit-camera-btn"
                                    data-camera-id="${camId}">
                                <i data-lucide="pencil" class="w-4 h-4 inline"></i>
                            </button>
                            <button class="px-3 py-1 bg-red-500 text-white text-sm rounded hover:bg-red-600 remove-camera-btn"
                                    data-camera-id="${camId}">
                                <i data-lucide="trash-2" class="w-4 h-4 inline"></i>
                            </button>
                        </div>
                    </div>
                    <!-- Edit-Modus (versteckt) -->
                    <div class="cam-edit hidden mt-3 pt-3 border-t border-gray-200 dark:border-gray-600">
                        <div class="grid grid-cols-1 md:grid-cols-2 gap-2 mb-2">
                            <div>
                                <label class="text-xs text-gray-500 dark:text-gray-400">Name</label>
                                <input type="text" class="cam-edit-name w-full px-2 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-800 text-gray-900 dark:text-white" value="${cam.name}">
                            </div>
                            <div>
                                <label class="text-xs text-gray-500 dark:text-gray-400">Typ</label>
                                <select class="cam-edit-type w-full px-2 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-800 text-gray-900 dark:text-white">
                                    <option value="rtsp" ${cam.type === 'rtsp' ? 'selected' : ''}>RTSP</option>
                                    <option value="mjpeg" ${cam.type === 'mjpeg' ? 'selected' : ''}>MJPEG</option>
                                    <option value="ring" ${cam.type === 'ring' ? 'selected' : ''}>Ring Snapshot</option>
                                </select>
                            </div>
                        </div>
                        <div class="space-y-2 mb-2">
                            <div>
                                <label class="text-xs text-gray-500 dark:text-gray-400">Stream-URL (MainStream)</label>
                                <input type="text" class="cam-edit-url w-full px-2 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-800 text-gray-900 dark:text-white font-mono" value="${cam.url}">
                            </div>
                            <div>
                                <label class="text-xs text-gray-500 dark:text-gray-400">SubStream-URL (optional, fuer Widget)</label>
                                <input type="text" class="cam-edit-substream w-full px-2 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-800 text-gray-900 dark:text-white font-mono" value="${cam.substream_url || ''}">
                            </div>
                        </div>
                        <details class="mb-2">
                            <summary class="text-xs font-semibold text-gray-600 dark:text-gray-400 cursor-pointer">ONVIF-Konfiguration</summary>
                            <div class="grid grid-cols-2 md:grid-cols-4 gap-2 mt-2">
                                <div>
                                    <label class="text-xs text-gray-500 dark:text-gray-400">Host</label>
                                    <input type="text" class="cam-edit-onvif-host w-full px-2 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-800 text-gray-900 dark:text-white" value="${onvifHost}">
                                </div>
                                <div>
                                    <label class="text-xs text-gray-500 dark:text-gray-400">Port</label>
                                    <input type="number" class="cam-edit-onvif-port w-full px-2 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-800 text-gray-900 dark:text-white" value="${onvifPort}">
                                </div>
                                <div>
                                    <label class="text-xs text-gray-500 dark:text-gray-400">User</label>
                                    <input type="text" class="cam-edit-onvif-user w-full px-2 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-800 text-gray-900 dark:text-white" value="${onvifUser}">
                                </div>
                                <div>
                                    <label class="text-xs text-gray-500 dark:text-gray-400">Passwort</label>
                                    <input type="text" class="cam-edit-onvif-pass w-full px-2 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-800 text-gray-900 dark:text-white" value="${onvifPass}">
                                </div>
                            </div>
                        </details>
                        <div class="flex items-center space-x-2">
                            <button class="save-camera-btn px-4 py-1.5 bg-green-600 text-white text-sm rounded hover:bg-green-700" data-camera-id="${camId}">Speichern</button>
                            <button class="cancel-edit-btn px-4 py-1.5 bg-gray-400 text-white text-sm rounded hover:bg-gray-500" data-camera-id="${camId}">Abbrechen</button>
                        </div>
                    </div>
                </div>
            `;
        });
        listHtml += '</div>';
        cameraListContainer.innerHTML = listHtml;

        // On-Demand: Starte Widget-Streams (640x360) für RTSP-Kameras
        const rtspCams = camIds.filter(id => (cameras[id].type || 'rtsp') === 'rtsp');
        const startedRtspCams = new Set();
        this._activeCameraStreams = [];
        for (const camId of rtspCams) {
            try {
                await fetch(`/api/cameras/${camId}/start`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ use_substream: true })
                });
                this._activeCameraStreams.push(camId);
                startedRtspCams.add(camId);
                console.log(`On-Demand Stream gestartet: ${camId} (SubStream)`);
            } catch (e) {
                console.error(`Stream-Start fehlgeschlagen fuer ${camId}:`, e);
            }
        }

        // Rendere Live-Streams (Grid) - alle bekommen Video-Element
        let gridHtml = '';
        camIds.forEach(camId => {
            const cam = cameras[camId];
            const streamType = (cam.type || 'rtsp').toLowerCase();

            if (streamType === 'mjpeg') {
                gridHtml += `
                    <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-4 camera-card" data-cam-id="${camId}" data-cam-name="${cam.name}" data-cam-type="mjpeg">
                        <h3 class="font-semibold text-gray-900 dark:text-white mb-2">${cam.name}</h3>
                        <div class="aspect-video bg-gray-900 rounded overflow-hidden relative">
                            <img id="cam-image-${camId}" src="${cam.url}" alt="${cam.name}" class="w-full h-full object-cover"
                                 onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';">
                            <div class="w-full h-full flex items-center justify-center text-white bg-gray-900" style="display:none;">
                                <div class="text-center">
                                    <i data-lucide="alert-circle" class="w-12 h-12 mx-auto mb-2 text-red-500"></i>
                                    <p class="text-sm">Stream nicht erreichbar</p>
                                </div>
                            </div>
                        </div>
                        <!-- Toolbar -->
                        <div class="flex items-center space-x-2 mt-2">
                            <button class="cam-fullscreen-btn px-3 py-1.5 bg-gray-700 text-white text-xs rounded hover:bg-gray-600 flex items-center space-x-1"
                                    data-cam-id="${camId}" data-cam-name="${cam.name}" data-cam-type="mjpeg">
                                <i data-lucide="maximize-2" class="w-3.5 h-3.5"></i><span>Vollbild</span>
                            </button>
                            <button class="cam-ptz-toggle-btn px-3 py-1.5 bg-blue-600 text-white text-xs rounded hover:bg-blue-500 flex items-center space-x-1"
                                    data-cam-id="${camId}" style="display:none;">
                                <i data-lucide="move" class="w-3.5 h-3.5"></i><span>PTZ</span>
                            </button>
                            <span class="text-xs px-2 py-0.5 rounded bg-green-100 text-green-800">MJPEG</span>
                        </div>
                        <!-- Inline PTZ Controls (versteckt) -->
                        <div id="widget-ptz-${camId}" class="widget-ptz-panel hidden mt-2 p-2 bg-gray-100 dark:bg-gray-700 rounded-lg select-none"></div>
                    </div>
                `;
            } else if (streamType === 'ring') {
                gridHtml += `
                    <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-4 camera-card" data-cam-id="${camId}" data-cam-name="${cam.name}" data-cam-type="ring">
                        <h3 class="font-semibold text-gray-900 dark:text-white mb-2">${cam.name}</h3>
                        <div class="aspect-video bg-gray-900 rounded overflow-hidden relative">
                            <video id="ring-video-${camId}" class="w-full h-full object-cover" muted autoplay playsinline style="display:none;"></video>
                            <img id="cam-image-${camId}" src="" alt="${cam.name}" class="w-full h-full object-cover">
                            <div id="ring-loading-${camId}" class="absolute inset-0 flex items-center justify-center text-white bg-gray-900 bg-opacity-60">
                                <div class="text-center">
                                    <i data-lucide="loader" class="w-8 h-8 mx-auto mb-2 animate-spin"></i>
                                    <p class="text-sm">Ring Stream wird geladen...</p>
                                </div>
                            </div>
                        </div>
                        <div class="flex items-center space-x-2 mt-2">
                            <button class="cam-fullscreen-btn px-3 py-1.5 bg-gray-700 text-white text-xs rounded hover:bg-gray-600 flex items-center space-x-1"
                                    data-cam-id="${camId}" data-cam-name="${cam.name}" data-cam-type="ring">
                                <i data-lucide="maximize-2" class="w-3.5 h-3.5"></i><span>Vollbild</span>
                            </button>
                            <button class="ring-widget-mode-btn px-3 py-1.5 bg-orange-600 text-white text-xs rounded hover:bg-orange-500 flex items-center space-x-1"
                                    data-cam-id="${camId}" data-mode="snapshot">
                                <i data-lucide="refresh-cw" class="w-3.5 h-3.5"></i><span id="ring-mode-label-${camId}">Snapshot</span>
                            </button>
                            <span class="text-xs px-2 py-0.5 rounded bg-orange-100 text-orange-800">RING</span>
                        </div>
                        <div id="widget-ptz-${camId}" class="widget-ptz-panel hidden mt-2 p-2 bg-gray-100 dark:bg-gray-700 rounded-lg select-none"></div>
                    </div>
                `;
            } else {
                // RTSP: Video wird nach kurzer Verzögerung via HLS geladen
                gridHtml += `
                    <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-4 camera-card" data-cam-id="${camId}" data-cam-name="${cam.name}" data-cam-type="rtsp">
                        <h3 class="font-semibold text-gray-900 dark:text-white mb-2">${cam.name}</h3>
                        <div class="aspect-video bg-gray-900 rounded overflow-hidden relative">
                            <img id="cam-image-${camId}" src="" alt="${cam.name}" class="w-full h-full object-cover">
                            <video id="hls-video-${camId}" class="w-full h-full object-cover" muted autoplay playsinline style="display:none;"></video>
                            <div id="hls-loading-${camId}" class="absolute inset-0 flex items-center justify-center text-white bg-gray-900">
                                <div class="text-center">
                                    <i data-lucide="loader" class="w-8 h-8 mx-auto mb-2 animate-spin"></i>
                                    <p class="text-sm">Stream wird geladen...</p>
                                </div>
                            </div>
                        </div>
                        <!-- Toolbar -->
                        <div class="flex items-center space-x-2 mt-2">
                            <button class="cam-fullscreen-btn px-3 py-1.5 bg-gray-700 text-white text-xs rounded hover:bg-gray-600 flex items-center space-x-1"
                                    data-cam-id="${camId}" data-cam-name="${cam.name}" data-cam-type="rtsp">
                                <i data-lucide="maximize-2" class="w-3.5 h-3.5"></i><span>Vollbild</span>
                            </button>
                            <button class="cam-ptz-toggle-btn px-3 py-1.5 bg-blue-600 text-white text-xs rounded hover:bg-blue-500 flex items-center space-x-1"
                                    data-cam-id="${camId}" style="display:none;">
                                <i data-lucide="move" class="w-3.5 h-3.5"></i><span>PTZ</span>
                            </button>
                            <span class="text-xs px-2 py-0.5 rounded bg-blue-100 text-blue-800">HLS</span>
                        </div>
                        <!-- Inline PTZ Controls (versteckt) -->
                        <div id="widget-ptz-${camId}" class="widget-ptz-panel hidden mt-2 p-2 bg-gray-100 dark:bg-gray-700 rounded-lg select-none"></div>
                    </div>
                `;
            }
        });
        camerasGridContainer.innerHTML = gridHtml;

        // Icons aktualisieren
        if (typeof lucide !== 'undefined') {
            lucide.createIcons();
        }

        // RTSP-Snapshot sofort anzeigen, bis HLS erfolgreich gestartet ist.
        rtspCams.forEach(camId => {
            this._loadRtspSnapshot(camId, `cam-image-${camId}`, 4500);
            this._startRtspSnapshotRefresh(camId, `cam-image-${camId}`, 3500);
        });

        // HLS.js Player nach kurzer Verzoegerung initialisieren (FFmpeg braucht Zeit)
        setTimeout(() => {
            (async () => {
                for (const camId of rtspCams) {
                    const videoEl = document.getElementById(`hls-video-${camId}`);
                    if (!videoEl) continue;

                    let hlsUrl = `/static/hls/${camId}.m3u8`;
                    if (!startedRtspCams.has(camId)) {
                        try {
                            const startResp = await fetch(`/api/cameras/${camId}/start`, {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({ use_substream: true })
                            });
                            const startData = await startResp.json();
                            if (startResp.ok && startData.success && startData.hls_url) {
                                hlsUrl = startData.hls_url;
                            }
                        } catch (e) {}
                    }

                    this._initHlsPlayer(videoEl, hlsUrl, camId);
                }
            })();
        }, 1200);

        let ringStatus = { available: false, configured: false };
        try {
            const ringStatusResp = await fetch('/api/ring/status');
            ringStatus = await ringStatusResp.json();
            this._ringLiveEnabled = !!ringStatus.live_enabled;
        } catch (e) {}

        camIds.forEach(camId => {
            const cam = cameras[camId];
            if ((cam.type || 'rtsp').toLowerCase() === 'ring') {
                const loadingEl = document.getElementById(`ring-loading-${camId}`);

                if (!ringStatus.available || !ringStatus.configured) {
                    if (loadingEl) {
                        loadingEl.innerHTML = '<p class="text-sm text-yellow-300 px-3 text-center">Ring nicht verbunden. Bitte im Bereich "Ring Integration" erneut anmelden.</p>';
                    }
                    return;
                }

                this._syncRingWidgetModeButton(camId);
                this._applyRingWidgetMode(camId, ringStatus).catch((e) => {
                    console.warn(`Ring-Widget-Modus konnte nicht gesetzt werden (${camId}):`, e);
                    if (loadingEl) loadingEl.style.display = 'none';
                });
            }
        });

        // Event-Listener: Loeschen-Buttons
        document.querySelectorAll('.remove-camera-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const cameraId = btn.getAttribute('data-camera-id');
                if (confirm(`Kamera "${cameras[cameraId]?.name || cameraId}" wirklich loeschen?`)) {
                    this.removeCamera(cameraId);
                }
            });
        });

        // Event-Listener: Edit-Buttons
        document.querySelectorAll('.edit-camera-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const camId = btn.getAttribute('data-camera-id');
                const entry = document.getElementById(`cam-entry-${camId}`);
                if (entry) {
                    entry.querySelector('.cam-display').classList.add('hidden');
                    entry.querySelector('.cam-edit').classList.remove('hidden');
                }
            });
        });

        // Event-Listener: Cancel-Buttons
        document.querySelectorAll('.cancel-edit-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const camId = btn.getAttribute('data-camera-id');
                const entry = document.getElementById(`cam-entry-${camId}`);
                if (entry) {
                    entry.querySelector('.cam-display').classList.remove('hidden');
                    entry.querySelector('.cam-edit').classList.add('hidden');
                }
            });
        });

        // Event-Listener: Save-Buttons
        document.querySelectorAll('.save-camera-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const camId = btn.getAttribute('data-camera-id');
                this._saveCamera(camId);
            });
        });

        document.querySelectorAll('.ring-widget-mode-btn').forEach(btn => {
            btn.addEventListener('click', async () => {
                const camId = btn.getAttribute('data-cam-id');
                await this._toggleRingWidgetMode(camId);
            });
        });

        // Event-Listener: Vollbild-Buttons
        document.querySelectorAll('.cam-fullscreen-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const camId = btn.getAttribute('data-cam-id');
                const camName = btn.getAttribute('data-cam-name');
                const camType = btn.getAttribute('data-cam-type');
                this.openCameraFullscreen(camId, camName, camType);
            });
        });

        // PTZ-Faehigkeit pruefen und Buttons einblenden
        camIds.forEach(camId => {
            this._checkWidgetPTZ(camId);
        });

        // Event-Listener: PTZ-Toggle-Buttons
        document.querySelectorAll('.cam-ptz-toggle-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const camId = btn.getAttribute('data-cam-id');
                this._toggleWidgetPTZ(camId);
            });
        });
    }

    async _saveCamera(camId) {
        const entry = document.getElementById(`cam-entry-${camId}`);
        if (!entry) return;

        const name = entry.querySelector('.cam-edit-name')?.value?.trim();
        const url = entry.querySelector('.cam-edit-url')?.value?.trim();
        const substreamUrl = entry.querySelector('.cam-edit-substream')?.value?.trim();
        const type = entry.querySelector('.cam-edit-type')?.value;
        const onvifHost = entry.querySelector('.cam-edit-onvif-host')?.value?.trim();
        const onvifPort = entry.querySelector('.cam-edit-onvif-port')?.value?.trim();
        const onvifUser = entry.querySelector('.cam-edit-onvif-user')?.value?.trim();
        const onvifPass = entry.querySelector('.cam-edit-onvif-pass')?.value?.trim();

        if (!name || !url) {
            alert('Name und Stream-URL sind Pflichtfelder');
            return;
        }

        const data = { name, url, type, substream_url: substreamUrl || '' };

        // ONVIF nur wenn Host angegeben
        if (onvifHost) {
            data.onvif = {
                host: onvifHost,
                port: parseInt(onvifPort) || 80,
                user: onvifUser || 'admin',
                password: onvifPass || 'admin'
            };
        } else {
            data.onvif = null;
        }

        try {
            const resp = await fetch(`/api/cameras/${camId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            const result = await resp.json();
            if (!resp.ok) {
                alert('Fehler: ' + (result.error || 'Unbekannt'));
                return;
            }
            console.log(`Kamera aktualisiert: ${camId}`);
            // Liste neu laden (Stream wird ggf. neu gestartet)
            this.loadSavedCameras();
        } catch (e) {
            console.error('Fehler beim Speichern:', e);
            alert('Server nicht erreichbar');
        }
    }

    _initHlsPlayer(videoEl, hlsUrl, camId) {
        const cacheBustedHlsUrl = `${hlsUrl}${hlsUrl.includes('?') ? '&' : '?'}ts=${Date.now()}`;
        if (typeof Hls !== 'undefined' && Hls.isSupported()) {
            if (camId && this._hlsInstances[camId]) {
                try { this._hlsInstances[camId].destroy(); } catch (e) {}
                delete this._hlsInstances[camId];
            }
            const hls = new Hls({
                enableWorker: true,
                lowLatencyMode: true,
                liveSyncDurationCount: 1,
                liveMaxLatencyDurationCount: 3,
                maxBufferLength: 2,
                backBufferLength: 0,
                maxLiveSyncPlaybackRate: 1.5
            });
            hls.loadSource(cacheBustedHlsUrl);
            hls.attachMedia(videoEl);
            hls.on(Hls.Events.MANIFEST_PARSED, () => {
                videoEl.play().catch(() => {});
                videoEl.style.display = '';
                const imageEl = camId ? document.getElementById(`cam-image-${camId}`) : null;
                if (imageEl) imageEl.style.display = 'none';
                if (camId) this._stopRtspSnapshotRefresh(camId, `cam-image-${camId}`);
                // Loading-Overlay ausblenden
                const loading = document.getElementById(`hls-loading-${camId}`);
                if (loading) loading.style.display = 'none';
            });
            hls.on(Hls.Events.ERROR, (event, data) => {
                if (data.fatal) {
                    if (camId && this._hlsRetryTimers[camId]) return;
                    console.warn('HLS fatal error, retrying in 3s...', data.type);
                    const imageEl = camId ? document.getElementById(`cam-image-${camId}`) : null;
                    if (imageEl) imageEl.style.display = '';
                    if (videoEl) videoEl.style.display = 'none';
                    if (camId) this._startRtspSnapshotRefresh(camId, `cam-image-${camId}`, 3000);
                    const retryTimer = setTimeout(async () => {
                        hls.destroy();
                        if (camId) {
                            delete this._hlsInstances[camId];
                            await this._restartRtspStream(camId);
                            await this._loadRtspSnapshot(camId, `cam-image-${camId}`, 4500);
                            delete this._hlsRetryTimers[camId];
                        }
                        this._initHlsPlayer(videoEl, hlsUrl, camId);
                    }, 3000);
                    if (camId) this._hlsRetryTimers[camId] = retryTimer;
                }
            });
            // Speichere HLS-Instanz für Cleanup
            if (camId) {
                this._hlsInstances[camId] = hls;
            }
            return hls;
        } else if (videoEl.canPlayType('application/vnd.apple.mpegurl')) {
            // Safari native HLS
            videoEl.src = cacheBustedHlsUrl;
            videoEl.addEventListener('loadedmetadata', () => {
                videoEl.play().catch(() => {});
                videoEl.style.display = '';
                const imageEl = camId ? document.getElementById(`cam-image-${camId}`) : null;
                if (imageEl) imageEl.style.display = 'none';
                if (camId) this._stopRtspSnapshotRefresh(camId, `cam-image-${camId}`);
                const loading = document.getElementById(`hls-loading-${camId}`);
                if (loading) loading.style.display = 'none';
            });
        }
        return null;
    }

    async _restartRtspStream(camId) {
        if (!camId) return;
        try {
            await fetch(`/api/cameras/${camId}/start`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ use_substream: true })
            });
        } catch (e) {}
    }

    async _loadRtspSnapshot(camId, imgElementId, timeoutMs = 4500) {
        const key = `${camId}:${imgElementId}`;
        if (this._rtspSnapshotInFlight[key]) return;

        const img = document.getElementById(imgElementId);
        if (!img) return;

        this._rtspSnapshotInFlight[key] = true;
        const controller = new AbortController();
        const timeoutHandle = setTimeout(() => controller.abort(), timeoutMs);
        try {
            const resp = await fetch(`/api/cameras/${camId}/snapshot?ts=${Date.now()}&timeout=6`, {
                signal: controller.signal,
                cache: 'no-store'
            });
            if (!resp.ok) return;
            const blob = await resp.blob();
            if (!blob || !blob.size) return;

            const newUrl = URL.createObjectURL(blob);
            img.src = newUrl;
            const loading = document.getElementById(`hls-loading-${camId}`);
            if (loading) loading.style.display = 'none';
            if (this._rtspSnapshotObjectUrls[key]) {
                URL.revokeObjectURL(this._rtspSnapshotObjectUrls[key]);
            }
            this._rtspSnapshotObjectUrls[key] = newUrl;
        } catch (e) {
        } finally {
            clearTimeout(timeoutHandle);
            this._rtspSnapshotInFlight[key] = false;
        }
    }

    _startRtspSnapshotRefresh(camId, imgElementId, intervalMs = 3500) {
        const key = `${camId}:${imgElementId}`;
        if (this._rtspSnapshotTimers[key]) {
            clearInterval(this._rtspSnapshotTimers[key]);
        }
        this._rtspSnapshotTimers[key] = setInterval(async () => {
            await this._loadRtspSnapshot(camId, imgElementId, 4500);
        }, intervalMs);
    }

    _stopRtspSnapshotRefresh(camId, imgElementId) {
        const key = `${camId}:${imgElementId}`;
        if (this._rtspSnapshotTimers[key]) {
            clearInterval(this._rtspSnapshotTimers[key]);
            delete this._rtspSnapshotTimers[key];
        }
    }

    _clearRtspSnapshotTimers() {
        Object.values(this._rtspSnapshotTimers).forEach(timer => clearInterval(timer));
        this._rtspSnapshotTimers = {};
        this._rtspSnapshotInFlight = {};
        Object.values(this._rtspSnapshotObjectUrls).forEach(url => {
            try { URL.revokeObjectURL(url); } catch (e) {}
        });
        this._rtspSnapshotObjectUrls = {};
    }

    _getRingWidgetMode(camId) {
        if (!camId) return 'snapshot';
        if (this._ringWidgetModes[camId]) return this._ringWidgetModes[camId];

        const stored = localStorage.getItem(`ringWidgetMode:${camId}`);
        const mode = stored === 'live' ? 'live' : 'snapshot';
        this._ringWidgetModes[camId] = mode;
        return mode;
    }

    _setRingWidgetMode(camId, mode) {
        const normalized = mode === 'live' ? 'live' : 'snapshot';
        this._ringWidgetModes[camId] = normalized;
        localStorage.setItem(`ringWidgetMode:${camId}`, normalized);
        this._syncRingWidgetModeButton(camId);
    }

    _syncRingWidgetModeButton(camId) {
        const btn = document.querySelector(`.ring-widget-mode-btn[data-cam-id="${camId}"]`);
        const label = document.getElementById(`ring-mode-label-${camId}`);
        const mode = this._getRingWidgetMode(camId);
        if (!btn || !label) return;

        if (!this._ringLiveEnabled) {
            btn.setAttribute('data-mode', 'snapshot');
            btn.disabled = true;
            btn.classList.remove('bg-green-600', 'hover:bg-green-500');
            btn.classList.remove('bg-orange-600', 'hover:bg-orange-500');
            btn.classList.add('bg-gray-500');
            label.textContent = 'Snapshot';
            return;
        }

        btn.disabled = false;
        btn.classList.remove('bg-gray-500');

        if (mode === 'live') {
            btn.setAttribute('data-mode', 'live');
            label.textContent = 'Live';
            btn.classList.remove('bg-orange-600', 'hover:bg-orange-500');
            btn.classList.add('bg-green-600', 'hover:bg-green-500');
        } else {
            btn.setAttribute('data-mode', 'snapshot');
            label.textContent = 'Snapshot';
            btn.classList.remove('bg-green-600', 'hover:bg-green-500');
            btn.classList.add('bg-orange-600', 'hover:bg-orange-500');
        }
    }

    async _toggleRingWidgetMode(camId) {
        if (!this._ringLiveEnabled) {
            this._setRingWidgetMode(camId, 'snapshot');
            return;
        }
        const nextMode = this._getRingWidgetMode(camId) === 'live' ? 'snapshot' : 'live';
        this._setRingWidgetMode(camId, nextMode);
        await this._applyRingWidgetMode(camId);
    }

    async _stopRingWidgetLive(camId) {
        const hls = this._ringWidgetHls[camId];
        if (hls) {
            try { hls.destroy(); } catch (e) {}
            delete this._ringWidgetHls[camId];
        }
        await this._stopRingWidgetWebrtc(camId);
        try {
            await fetch(`/api/cameras/${camId}/stop`, { method: 'POST' });
        } catch (e) {}
    }

    async _startRingWidgetLiveHls(camId, videoEl, imageEl, loadingEl) {
        await this._stopRingWidgetLive(camId);

        const startResp = await fetch(`/api/cameras/${camId}/start`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        const startData = await startResp.json();
        if (!startResp.ok || !startData.success || !startData.hls_url) {
            throw new Error(startData.error || 'Ring Live-Start fehlgeschlagen');
        }

        const hlsUrl = `${startData.hls_url}${startData.hls_url.includes('?') ? '&' : '?'}ts=${Date.now()}`;

        await new Promise((resolve, reject) => {
            if (typeof Hls !== 'undefined' && Hls.isSupported()) {
                const hls = new Hls({
                    enableWorker: true,
                    lowLatencyMode: true,
                    liveSyncDurationCount: 1,
                    liveMaxLatencyDurationCount: 3,
                    maxBufferLength: 2,
                    backBufferLength: 0
                });
                this._ringWidgetHls[camId] = hls;
                let settled = false;

                const fail = (err) => {
                    if (settled) return;
                    settled = true;
                    try { hls.destroy(); } catch (e) {}
                    delete this._ringWidgetHls[camId];
                    reject(err);
                };

                hls.on(Hls.Events.MANIFEST_PARSED, () => {
                    if (settled) return;
                    settled = true;
                    videoEl.play().catch(() => {});
                    videoEl.style.display = '';
                    imageEl.style.display = 'none';
                    if (loadingEl) loadingEl.style.display = 'none';
                    resolve();
                });
                hls.on(Hls.Events.ERROR, (event, data) => {
                    if (data && data.fatal) {
                        fail(new Error(data.type || 'HLS fatal'));
                    }
                });

                hls.loadSource(hlsUrl);
                hls.attachMedia(videoEl);
                return;
            }

            if (videoEl.canPlayType('application/vnd.apple.mpegurl')) {
                videoEl.src = hlsUrl;
                videoEl.onloadedmetadata = () => {
                    videoEl.play().catch(() => {});
                    videoEl.style.display = '';
                    imageEl.style.display = 'none';
                    if (loadingEl) loadingEl.style.display = 'none';
                    resolve();
                };
                videoEl.onerror = () => reject(new Error('Native HLS Fehler'));
                return;
            }

            reject(new Error('HLS im Browser nicht unterstützt'));
        });
    }

    async _applyRingWidgetMode(camId, ringStatus = null) {
        if (!camId) return;

        const imageEl = document.getElementById(`cam-image-${camId}`);
        const videoEl = document.getElementById(`ring-video-${camId}`);
        const loadingEl = document.getElementById(`ring-loading-${camId}`);
        const imgElementId = `cam-image-${camId}`;
        if (!imageEl || !videoEl) return;

        let status = ringStatus;
        if (!status) {
            try {
                const resp = await fetch('/api/ring/status');
                status = await resp.json();
                this._ringLiveEnabled = !!status.live_enabled;
            } catch (e) {
                status = { available: false, configured: false };
            }
        }
        if (!status.available || !status.configured) {
            if (loadingEl) {
                loadingEl.innerHTML = '<p class="text-sm text-yellow-300 px-3 text-center">Ring nicht verbunden.</p>';
                loadingEl.style.display = '';
            }
            return;
        }

        const mode = this._getRingWidgetMode(camId);
        if (mode === 'live' && this._ringLiveEnabled) {
            if (loadingEl) {
                loadingEl.innerHTML = '<div class="text-center"><i data-lucide="loader" class="w-8 h-8 mx-auto mb-2 animate-spin"></i><p class="text-sm">Ring Live wird geladen...</p></div>';
                loadingEl.style.display = '';
                if (typeof lucide !== 'undefined') lucide.createIcons();
            }
            this._stopRingSnapshotRefresh(camId, imgElementId);
            try {
                await this._startRingWidgetLiveHls(camId, videoEl, imageEl, loadingEl);
            } catch (e) {
                console.warn(`Ring Live fehlgeschlagen (${camId}), fallback auf Snapshot`, e);
                this._setRingWidgetMode(camId, 'snapshot');
                await this._applyRingWidgetMode(camId, status);
            }
            return;
        }

        await this._stopRingWidgetLive(camId);
        videoEl.style.display = 'none';
        imageEl.style.display = '';
        if (loadingEl) loadingEl.style.display = 'none';

        await this._loadRingSnapshot(camId, imgElementId, 9000, 1, 1, 8);
        this._startRingSnapshotRefresh(camId, imgElementId, 15000);
    }

    async _loadRingSnapshot(camId, imgElementId, timeoutMs = 9000, retries = 1, delay = 1, timeoutSec = 8) {
        const key = `${camId}:${imgElementId}`;
        if (this._ringSnapshotInFlight[key]) return;

        const img = document.getElementById(imgElementId);
        if (!img) return;

        this._ringSnapshotInFlight[key] = true;
        const controller = new AbortController();
        const timeoutHandle = setTimeout(() => controller.abort(), timeoutMs);

        try {
            const resp = await fetch(`/api/cameras/${camId}/snapshot?ts=${Date.now()}&retries=${retries}&delay=${delay}&timeout=${timeoutSec}`, {
                signal: controller.signal,
                cache: 'no-store'
            });
            if (!resp.ok) return;

            const blob = await resp.blob();
            if (!blob || !blob.size) return;

            const newUrl = URL.createObjectURL(blob);
            img.src = newUrl;

            if (this._ringSnapshotObjectUrls[key]) {
                URL.revokeObjectURL(this._ringSnapshotObjectUrls[key]);
            }
            this._ringSnapshotObjectUrls[key] = newUrl;
        } catch (e) {
            // Snapshot-Ausfall ist tolerierbar; WebRTC oder nächster Zyklus übernimmt.
        } finally {
            clearTimeout(timeoutHandle);
            this._ringSnapshotInFlight[key] = false;
        }
    }

    _startRingSnapshotRefresh(camId, imgElementId, intervalMs = 15000) {
        const key = `${camId}:${imgElementId}`;
        if (this._ringSnapshotTimers[key]) {
            clearInterval(this._ringSnapshotTimers[key]);
        }

        this._ringSnapshotTimers[key] = setInterval(async () => {
            await this._loadRingSnapshot(camId, imgElementId, 9000, 1, 1, 8);
        }, intervalMs);
    }

    _stopRingSnapshotRefresh(camId, imgElementId) {
        const key = `${camId}:${imgElementId}`;
        if (this._ringSnapshotTimers[key]) {
            clearInterval(this._ringSnapshotTimers[key]);
            delete this._ringSnapshotTimers[key];
        }
    }

    _clearRingSnapshotTimers() {
        Object.values(this._ringSnapshotTimers).forEach(timer => clearInterval(timer));
        this._ringSnapshotTimers = {};
        this._ringSnapshotInFlight = {};
        Object.values(this._ringSnapshotObjectUrls).forEach(url => {
            try { URL.revokeObjectURL(url); } catch (e) {}
        });
        this._ringSnapshotObjectUrls = {};
    }

    async _stopRingWebrtc(camId) {
        if (this._ringWebrtcKeepaliveTimer) {
            clearInterval(this._ringWebrtcKeepaliveTimer);
            this._ringWebrtcKeepaliveTimer = null;
        }

        if (this._ringPeerConnection) {
            try { this._ringPeerConnection.close(); } catch (e) {}
            this._ringPeerConnection = null;
        }

        if (this._ringWebrtcSessionId && camId) {
            try {
                await fetch(`/api/cameras/${camId}/ring/webrtc/stop`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ session_id: this._ringWebrtcSessionId })
                });
            } catch (e) {}
        }
        this._ringWebrtcSessionId = null;
    }

    async _startRingWebrtc(camId, videoEl) {
        await this._stopRingWebrtc(camId);

        const pc = new RTCPeerConnection();
        this._ringPeerConnection = pc;

        pc.ontrack = (event) => {
            if (event.streams && event.streams[0]) {
                videoEl.srcObject = event.streams[0];
                videoEl.play().catch(() => {});
            }
        };

        pc.onicecandidate = async (event) => {
            if (!event.candidate || !this._ringWebrtcSessionId) return;
            try {
                await fetch(`/api/cameras/${camId}/ring/webrtc/candidate`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        session_id: this._ringWebrtcSessionId,
                        candidate: event.candidate.candidate,
                        sdpMLineIndex: event.candidate.sdpMLineIndex
                    })
                });
            } catch (e) {
                console.warn('Ring ICE candidate send failed', e);
            }
        };

        // Ring stream is receive-only from browser perspective.
        pc.addTransceiver('video', { direction: 'recvonly' });
        pc.addTransceiver('audio', { direction: 'recvonly' });

        const offer = await pc.createOffer();
        await pc.setLocalDescription(offer);

        const resp = await fetch(`/api/cameras/${camId}/ring/webrtc/start`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                offer: offer.sdp,
                keep_alive_timeout: 45
            })
        });
        const data = await resp.json();
        if (!resp.ok || !data.success) {
            await this._stopRingWebrtc(camId);
            throw new Error(data.error || 'Ring WebRTC Start fehlgeschlagen');
        }

        this._ringWebrtcSessionId = data.session_id;
        await pc.setRemoteDescription({ type: 'answer', sdp: data.answer });

        this._ringWebrtcKeepaliveTimer = setInterval(async () => {
            if (!this._ringWebrtcSessionId) return;
            try {
                await fetch(`/api/cameras/${camId}/ring/webrtc/keepalive`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ session_id: this._ringWebrtcSessionId })
                });
            } catch (e) {}
        }, 10000);
    }

    async _stopRingWidgetWebrtc(camId) {
        const conn = this._ringWidgetConnections[camId];
        if (!conn) return;

        if (conn.keepaliveTimer) {
            clearInterval(conn.keepaliveTimer);
        }
        if (conn.pc) {
            try { conn.pc.close(); } catch (e) {}
        }
        if (conn.sessionId) {
            try {
                await fetch(`/api/cameras/${camId}/ring/webrtc/stop`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ session_id: conn.sessionId })
                });
            } catch (e) {}
        }

        delete this._ringWidgetConnections[camId];
    }

    async _startRingWidgetWebrtc(camId, videoEl, fallbackImageEl = null) {
        await this._stopRingWidgetWebrtc(camId);

        const pc = new RTCPeerConnection();
        const conn = { pc, sessionId: null, keepaliveTimer: null };
        this._ringWidgetConnections[camId] = conn;

        pc.ontrack = (event) => {
            if (event.streams && event.streams[0]) {
                videoEl.srcObject = event.streams[0];
                videoEl.play().catch(() => {});
                videoEl.style.display = '';
                if (fallbackImageEl) fallbackImageEl.style.display = 'none';
            }
        };

        pc.onicecandidate = async (event) => {
            if (!event.candidate || !conn.sessionId) return;
            try {
                await fetch(`/api/cameras/${camId}/ring/webrtc/candidate`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        session_id: conn.sessionId,
                        candidate: event.candidate.candidate,
                        sdpMLineIndex: event.candidate.sdpMLineIndex
                    })
                });
            } catch (e) {}
        };

        pc.addTransceiver('video', { direction: 'recvonly' });
        pc.addTransceiver('audio', { direction: 'recvonly' });

        const offer = await pc.createOffer();
        await pc.setLocalDescription(offer);

        const resp = await fetch(`/api/cameras/${camId}/ring/webrtc/start`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ offer: offer.sdp, keep_alive_timeout: 45 })
        });
        const data = await resp.json();
        if (!resp.ok || !data.success) {
            throw new Error(data.error || 'Ring Widget WebRTC Start fehlgeschlagen');
        }

        conn.sessionId = data.session_id;
        await pc.setRemoteDescription({ type: 'answer', sdp: data.answer });

        conn.keepaliveTimer = setInterval(async () => {
            if (!conn.sessionId) return;
            try {
                await fetch(`/api/cameras/${camId}/ring/webrtc/keepalive`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ session_id: conn.sessionId })
                });
            } catch (e) {}
        }, 10000);
    }

    // ========================================================================
    // ON-DEMAND STREAM CLEANUP
    // ========================================================================

    async _cleanupCameraStreams() {
        console.log('Stoppe Camera-Widget-Streams...');
        this._clearRtspSnapshotTimers();
        this._clearRingSnapshotTimers();
        for (const timer of Object.values(this._hlsRetryTimers)) {
            clearTimeout(timer);
        }
        this._hlsRetryTimers = {};
        for (const timer of Object.values(this._cameraWallRetryTimers)) {
            clearTimeout(timer);
        }
        this._cameraWallRetryTimers = {};
        const ringCamIds = Object.keys(this._ringWidgetConnections);
        for (const camId of ringCamIds) {
            await this._stopRingWidgetWebrtc(camId);
        }
        for (const [camId, hls] of Object.entries(this._ringWidgetHls)) {
            try { hls.destroy(); } catch (e) {}
            try { await fetch(`/api/cameras/${camId}/stop`, { method: 'POST' }); } catch (e) {}
        }
        this._ringWidgetHls = {};
        // HLS-Instanzen zerstören
        for (const [camId, hls] of Object.entries(this._hlsInstances)) {
            try {
                hls.destroy();
            } catch (e) {}
        }
        this._hlsInstances = {};

        // Streams auf Server stoppen
        for (const camId of this._activeCameraStreams) {
            try {
                await fetch(`/api/cameras/${camId}/stop`, { method: 'POST' });
                console.log(`Stream gestoppt: ${camId}`);
            } catch (e) {
                console.error(`Stream-Stop fehlgeschlagen: ${camId}`, e);
            }
        }
        this._activeCameraStreams = [];
    }

    async _cleanupCameraWallStreams() {
        console.log('Stoppe Camera-Wall-Streams...');
        this._clearRtspSnapshotTimers();
        this._clearRingSnapshotTimers();
        for (const timer of Object.values(this._hlsRetryTimers)) {
            clearTimeout(timer);
        }
        this._hlsRetryTimers = {};
        for (const timer of Object.values(this._cameraWallRetryTimers)) {
            clearTimeout(timer);
        }
        this._cameraWallRetryTimers = {};
        const ringCamIds = Object.keys(this._ringWidgetConnections);
        for (const camId of ringCamIds) {
            await this._stopRingWidgetWebrtc(camId);
        }
        for (const [camId, hls] of Object.entries(this._ringWidgetHls)) {
            try { hls.destroy(); } catch (e) {}
            try { await fetch(`/api/cameras/${camId}/stop`, { method: 'POST' }); } catch (e) {}
        }
        this._ringWidgetHls = {};
        for (const [camId, hls] of Object.entries(this._cameraWallHls)) {
            try {
                hls.destroy();
            } catch (e) {}
        }
        this._cameraWallHls = {};

        for (const camId of this._cameraWallStreams) {
            try {
                await fetch(`/api/cameras/${camId}/stop`, { method: 'POST' });
            } catch (e) {}
        }
        this._cameraWallStreams = [];
    }

    // ========================================================================
    // FULLSCREEN OVERLAY
    // ========================================================================

    _loadFullscreenHls(videoEl, camId, attempt = 0, customHlsUrl = null, fastStart = false) {
        const maxAttempts = 5;
        const hlsUrl = customHlsUrl || `/static/hls/${camId}.m3u8`;

        // RTSP benötigt oft Startpuffer; Ring-Bridge kann schneller starten.
        const delay = attempt === 0 ? (fastStart ? 300 : 3000) : (fastStart ? 1000 : 2000);

        setTimeout(() => {
            // Abbruch wenn Fullscreen schon geschlossen wurde
            if (this._fullscreenCamId !== camId) return;

            if (typeof Hls !== 'undefined' && Hls.isSupported()) {
                // Alte Instanz aufraeumen
                if (this._fullscreenHls) {
                    try { this._fullscreenHls.destroy(); } catch (e) {}
                    this._fullscreenHls = null;
                }

                const hls = new Hls({
                    liveDurationInfinity: true,
                    enableWorker: true,
                    lowLatencyMode: true
                });
                hls.loadSource(hlsUrl);
                hls.attachMedia(videoEl);
                hls.on(Hls.Events.MANIFEST_PARSED, () => {
                    videoEl.play().catch(() => {});
                });
                hls.on(Hls.Events.ERROR, (event, data) => {
                    if (data.fatal && attempt < maxAttempts) {
                        console.warn(`Fullscreen HLS Fehler (Versuch ${attempt + 1}/${maxAttempts}), retry...`);
                        hls.destroy();
                        this._fullscreenHls = null;
                        this._loadFullscreenHls(videoEl, camId, attempt + 1, customHlsUrl, fastStart);
                    }
                });
                this._fullscreenHls = hls;
            } else if (videoEl.canPlayType('application/vnd.apple.mpegurl')) {
                videoEl.src = hlsUrl;
                videoEl.play().catch(() => {});
            }
        }, delay);
    }

    async openCameraFullscreen(camId, camName, camType) {
        const overlay = document.getElementById('camera-fullscreen-overlay');
        const videoEl = document.getElementById('fullscreen-video');
        const imageEl = document.getElementById('fullscreen-image');
        const nameEl = document.getElementById('fullscreen-cam-name');
        const closeBtn = document.getElementById('fullscreen-close');

        if (!overlay || !videoEl || !imageEl) return;

        this._fullscreenCamId = camId;
        nameEl.textContent = camName || camId;
        overlay.classList.remove('hidden');
        videoEl.style.display = 'none';
        imageEl.style.display = 'none';
        if (this._fullscreenSnapshotTimer) {
            clearInterval(this._fullscreenSnapshotTimer);
            this._fullscreenSnapshotTimer = null;
        }

        if (camType === 'rtsp') {
            videoEl.style.display = '';
            // Widget-HLS-Instanz zerstoeren (verhindert Konflikte)
            if (this._hlsInstances[camId]) {
                try { this._hlsInstances[camId].destroy(); } catch (e) {}
                delete this._hlsInstances[camId];
            }

            // Stoppe Widget-Stream, starte Full-Res
            try {
                await fetch(`/api/cameras/${camId}/stop`, { method: 'POST' });
            } catch (e) {}
            // Warte kurz
            await new Promise(r => setTimeout(r, 1000));
            // Starte MainStream ohne resolution = copy passthrough
            try {
                await fetch(`/api/cameras/${camId}/start`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({})
                });
            } catch (e) {}

            // Warte auf HLS-Segmente, dann lade mit Retry-Logik
            this._loadFullscreenHls(videoEl, camId);
        } else if (camType === 'ring') {
            let ringStatus = { webrtc_available: false, live_enabled: false, live_on_ding_active: [] };
            try {
                const statusResp = await fetch('/api/ring/status');
                if (statusResp.ok) {
                    ringStatus = await statusResp.json();
                    this._ringLiveEnabled = !!ringStatus.live_enabled;
                }
            } catch (e) {}

            const liveAllowedForCamera = !!ringStatus.live_enabled ||
                (Array.isArray(ringStatus.live_on_ding_active) && ringStatus.live_on_ding_active.includes(camId));

            // Prefer backend bridge stream for fullscreen quality/latency.
            if (liveAllowedForCamera) {
                try {
                    const bridgeResp = await fetch(`/api/cameras/${camId}/start`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' }
                    });
                    const bridgeData = await bridgeResp.json();
                    if (bridgeResp.ok && bridgeData.success && bridgeData.hls_url) {
                        imageEl.style.display = 'none';
                        videoEl.style.display = '';
                        this._loadFullscreenHls(videoEl, camId, 0, bridgeData.hls_url, true);
                        return;
                    }
                } catch (e) {
                    console.warn('Ring bridge start fehlgeschlagen, nutze Snapshot-Fallback:', e);
                }
            }

            const preferWebrtc = this.isFeatureEnabled('ui.ring.webrtc', true)
                && !!ringStatus.webrtc_available
                && (localStorage.getItem('ringWebrtcPreferred') || '1') === '1';
            if (liveAllowedForCamera && preferWebrtc && window.RTCPeerConnection) {
                videoEl.style.display = '';
                try {
                    await this._startRingWebrtc(camId, videoEl);
                } catch (e) {
                    console.warn('Ring WebRTC fehlgeschlagen, nutze Snapshot-Fallback:', e);
                    videoEl.style.display = 'none';
                    imageEl.style.display = '';
                    await this._loadRingSnapshot(camId, 'fullscreen-image', 9000, 1, 1, 8);
                    this._fullscreenSnapshotTimer = setInterval(() => {
                        this._loadRingSnapshot(camId, 'fullscreen-image', 9000, 1, 1, 8);
                    }, 2500);
                }
            } else {
                imageEl.style.display = '';
                await this._loadRingSnapshot(camId, 'fullscreen-image', 9000, 1, 1, 8);
                this._fullscreenSnapshotTimer = setInterval(() => {
                    this._loadRingSnapshot(camId, 'fullscreen-image', 9000, 1, 1, 8);
                }, 2500);
            }
        } else {
            imageEl.style.display = '';
            const widgetImage = document.getElementById(`cam-image-${camId}`);
            imageEl.src = widgetImage ? widgetImage.src : '';
        }

        // PTZ Controls initialisieren
        this._initPTZControls(camId);

        // Close-Button
        const closeHandler = () => {
            this.closeCameraFullscreen();
            closeBtn.removeEventListener('click', closeHandler);
        };
        closeBtn.addEventListener('click', closeHandler);

        // ESC zum Schliessen
        const escHandler = (e) => {
            if (e.key === 'Escape') {
                this.closeCameraFullscreen();
                document.removeEventListener('keydown', escHandler);
            }
        };
        document.addEventListener('keydown', escHandler);
    }

    async closeCameraFullscreen() {
        const overlay = document.getElementById('camera-fullscreen-overlay');
        const videoEl = document.getElementById('fullscreen-video');
        const imageEl = document.getElementById('fullscreen-image');

        // PTZ Controls ausblenden und Listener entfernen
        this._cleanupPTZControls();

        if (overlay) overlay.classList.add('hidden');

        const camId = this._fullscreenCamId;
        await this._stopRingWebrtc(camId);

        // Fullscreen-HLS zerstören
        if (this._fullscreenHls) {
            this._fullscreenHls.destroy();
            this._fullscreenHls = null;
        }
        if (videoEl) videoEl.src = '';
        if (imageEl) imageEl.src = '';
        if (imageEl) imageEl.style.display = 'none';
        if (videoEl) videoEl.style.display = '';
        if (this._fullscreenSnapshotTimer) {
            clearInterval(this._fullscreenSnapshotTimer);
            this._fullscreenSnapshotTimer = null;
        }

        // Full-Res Stream stoppen und Widget-Stream wieder starten
        if (camId) {
            let camType = null;
            const camCard = document.querySelector(`.camera-card[data-cam-id="${camId}"]`);
            if (camCard) {
                camType = camCard.getAttribute('data-cam-type');
            }
            if (camType === 'ring') {
                try {
                    await fetch(`/api/cameras/${camId}/stop`, { method: 'POST' });
                } catch (e) {}
                this._fullscreenCamId = null;
                return;
            }
            if (camType !== 'rtsp') {
                this._fullscreenCamId = null;
                return;
            }

            try {
                await fetch(`/api/cameras/${camId}/stop`, { method: 'POST' });
            } catch (e) {}

            // Widget-Stream wieder starten (SubStream)
            await new Promise(r => setTimeout(r, 1000));
            try {
                await fetch(`/api/cameras/${camId}/start`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ use_substream: true })
                });
            } catch (e) {}

            // HLS-Player im Widget neu laden
            setTimeout(() => {
                const widgetVideo = document.getElementById(`hls-video-${camId}`);
                if (widgetVideo) {
                    const hlsUrl = `/static/hls/${camId}.m3u8`;
                    this._initHlsPlayer(widgetVideo, hlsUrl, camId);
                }
            }, 3000);

            this._fullscreenCamId = null;
        }
    }

    async _handleCameraAlert(data) {
        const camId = data?.cam_id || data?.camera_id || data?.id;
        if (!camId) return;
        const durationMs = Math.max(5000, Math.min(120000, (parseInt(data?.duration_seconds, 10) || 30) * 1000));

        const previousPage = this.currentPage;
        if (this.currentPage !== 'cameras') {
            this.showPage('cameras');
            await new Promise(r => setTimeout(r, 500));
        }

        const card = document.querySelector(`.camera-card[data-cam-id="${camId}"]`);
        const camName = data?.name || card?.getAttribute('data-cam-name') || camId;
        const camType = data?.type || card?.getAttribute('data-cam-type') || 'ring';

        if (card) {
            card.classList.add('ring-4', 'ring-red-500', 'ring-offset-2');
            setTimeout(() => {
                card.classList.remove('ring-4', 'ring-red-500', 'ring-offset-2');
            }, durationMs);
            card.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }

        await this.openCameraFullscreen(camId, camName, camType);

        if (this._cameraAlertTimer) {
            clearTimeout(this._cameraAlertTimer);
            this._cameraAlertTimer = null;
        }
        this._cameraAlertRestorePage = previousPage !== 'cameras' ? previousPage : null;
        this._cameraAlertTimer = setTimeout(async () => {
            if (this._fullscreenCamId === camId) {
                await this.closeCameraFullscreen();
            }
            if (this._cameraAlertRestorePage) {
                this.showPage(this._cameraAlertRestorePage);
            }
            this._cameraAlertRestorePage = null;
            this._cameraAlertTimer = null;
        }, durationMs);
    }

    // ========================================================================
    // GRID-LAYOUT TOGGLE
    // ========================================================================

    _applyGridLayout() {
        const cols = localStorage.getItem('cameraGridCols') || '2';
        const grid = document.getElementById('cameras-grid');
        if (!grid) return;

        // Entferne alte Grid-Klassen
        grid.className = grid.className.replace(/grid-cols-\d+|md:grid-cols-\d+|lg:grid-cols-\d+/g, '').trim();

        switch (cols) {
            case '1':
                grid.classList.add('grid-cols-1');
                break;
            case '2':
                grid.classList.add('grid-cols-1', 'md:grid-cols-2');
                break;
            case '3':
                grid.classList.add('grid-cols-1', 'md:grid-cols-2', 'lg:grid-cols-3');
                break;
        }
        // Ensure base grid class
        if (!grid.classList.contains('grid')) grid.classList.add('grid');
        if (!grid.classList.contains('gap-4')) grid.classList.add('gap-4');

        // Buttons aktualisieren
        document.querySelectorAll('.grid-layout-btn').forEach(btn => {
            const btnCols = btn.getAttribute('data-grid-cols');
            if (btnCols === cols) {
                btn.classList.add('bg-blue-500', 'text-white', 'border-blue-500');
                btn.classList.remove('text-gray-700', 'dark:text-gray-300');
            } else {
                btn.classList.remove('bg-blue-500', 'text-white', 'border-blue-500');
            }
        });
    }

    _setupGridLayoutToggle() {
        document.querySelectorAll('.grid-layout-btn').forEach(btn => {
            const colsKey = btn.getAttribute('data-grid-cols') || 'unknown';
            this._bindScopedListener(btn, 'click', () => {
                const cols = btn.getAttribute('data-grid-cols');
                localStorage.setItem('cameraGridCols', cols);
                this._applyGridLayout();
            }, { scope: 'page:cameras', key: `cameras:grid-layout:${colsKey}` });
        });
    }

    // ========================================================================
    // CAMERA WALL PAGE
    // ========================================================================

    async loadCameraWallPage() {
        console.log('Lade Kamera-Wand...');
        const scope = 'page:camera-wall';

        let cameras = {};
        try {
            const resp = await fetch('/api/cameras');
            const data = await resp.json();
            cameras = data.cameras || {};
        } catch (e) {
            console.error('Fehler beim Laden der Kameras:', e);
            return;
        }

        const camIds = Object.keys(cameras);

        // Kamera-Auswahl Checkboxes
        const checkboxContainer = document.getElementById('camera-wall-checkboxes');
        if (checkboxContainer) {
            if (camIds.length === 0) {
                checkboxContainer.innerHTML = '<p class="text-sm text-gray-500">Keine Kameras konfiguriert</p>';
            } else {
                let html = '';
                camIds.forEach(camId => {
                    const cam = cameras[camId];
                    html += `
                        <label class="flex items-center space-x-2 px-3 py-2 bg-gray-50 dark:bg-gray-700 rounded-lg cursor-pointer">
                            <input type="checkbox" class="wall-cam-checkbox rounded" data-cam-id="${camId}" data-cam-name="${cam.name}" data-cam-type="${cam.type || 'rtsp'}" data-cam-url="${cam.url || ''}">
                            <span class="text-sm text-gray-900 dark:text-white">${cam.name}</span>
                        </label>
                    `;
                });
                checkboxContainer.innerHTML = html;

                // Checkbox Event-Listener
                document.querySelectorAll('.wall-cam-checkbox').forEach(cb => {
                    const camId = cb.getAttribute('data-cam-id') || 'unknown';
                    this._bindScopedListener(cb, 'change', () => {
                        this._updateCameraWall();
                    }, { scope, key: `camera-wall:checkbox:${camId}` });
                });
            }
        }

        // Layout-Buttons
        this._setupWallLayoutToggle();

        // Vollbild-Button
        const fsBtn = document.getElementById('wall-fullscreen-btn');
        if (fsBtn) {
            this._bindScopedListener(fsBtn, 'click', () => {
                const wallGrid = document.getElementById('camera-wall-grid');
                if (wallGrid && wallGrid.requestFullscreen) {
                    wallGrid.requestFullscreen().catch(() => {
                        // Fallback: ganzes Dokument
                        document.documentElement.requestFullscreen().catch(() => {});
                    });
                }
            }, { scope, key: 'camera-wall:fullscreen' });
        }
    }

    _setupWallLayoutToggle() {
        document.querySelectorAll('.wall-layout-btn').forEach(btn => {
            const layout = btn.getAttribute('data-wall-layout') || 'unknown';
            this._bindScopedListener(btn, 'click', () => {
                const layout = btn.getAttribute('data-wall-layout');
                this._applyWallLayout(layout);

                // Buttons aktualisieren
                document.querySelectorAll('.wall-layout-btn').forEach(b => {
                    b.classList.remove('bg-blue-500', 'text-white', 'border-blue-500');
                });
                btn.classList.add('bg-blue-500', 'text-white', 'border-blue-500');
            }, { scope: 'page:camera-wall', key: `camera-wall:layout:${layout}` });
        });
    }

    _applyWallLayout(cols) {
        const grid = document.getElementById('camera-wall-grid');
        if (!grid) return;

        grid.className = grid.className.replace(/grid-cols-\d+|md:grid-cols-\d+|lg:grid-cols-\d+/g, '').trim();

        switch (cols) {
            case '1':
                grid.classList.add('grid-cols-1');
                break;
            case '2':
                grid.classList.add('grid-cols-1', 'md:grid-cols-2');
                break;
            case '3':
                grid.classList.add('grid-cols-1', 'md:grid-cols-2', 'lg:grid-cols-3');
                break;
        }
        if (!grid.classList.contains('grid')) grid.classList.add('grid');
        if (!grid.classList.contains('gap-4')) grid.classList.add('gap-4');
    }

    async _updateCameraWall() {
        const grid = document.getElementById('camera-wall-grid');
        if (!grid) return;

        // Cleanup alte Streams
        await this._cleanupCameraWallStreams();

        // Ausgewählte Kameras ermitteln
        const selected = [];
        document.querySelectorAll('.wall-cam-checkbox:checked').forEach(cb => {
            selected.push({
                id: cb.getAttribute('data-cam-id'),
                name: cb.getAttribute('data-cam-name'),
                type: cb.getAttribute('data-cam-type'),
                url: cb.getAttribute('data-cam-url') || ''
            });
        });

        if (selected.length === 0) {
            grid.innerHTML = '<p class="text-gray-500">Kameras auswählen um sie hier anzuzeigen...</p>';
            return;
        }

        // Starte Streams und rendere Grid
        let html = '';
        for (const cam of selected) {
            if (cam.type === 'rtsp') {
                try {
                    await fetch(`/api/cameras/${cam.id}/start`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ use_substream: true })
                    });
                    this._cameraWallStreams.push(cam.id);
                } catch (e) {}
            }

            if (cam.type === 'rtsp') {
                html += `
                    <div class="bg-black rounded-lg overflow-hidden relative">
                        <div class="aspect-video">
                            <video id="wall-video-${cam.id}" class="w-full h-full object-contain" muted autoplay playsinline></video>
                            <div id="wall-loading-${cam.id}" class="absolute inset-0 flex items-center justify-center text-white">
                                <p class="text-sm">Lade ${cam.name}...</p>
                            </div>
                        </div>
                        <div class="absolute bottom-2 left-2 text-white text-sm font-semibold bg-black bg-opacity-50 px-2 py-1 rounded">${cam.name}</div>
                    </div>
                `;
            } else if (cam.type === 'ring') {
                html += `
                    <div class="bg-black rounded-lg overflow-hidden relative">
                        <div class="aspect-video">
                            <img id="wall-image-${cam.id}" src="/api/cameras/${cam.id}/snapshot?ts=${Date.now()}" class="w-full h-full object-contain" alt="${cam.name}">
                        </div>
                        <div class="absolute bottom-2 left-2 text-white text-sm font-semibold bg-black bg-opacity-50 px-2 py-1 rounded">${cam.name}</div>
                    </div>
                `;
            } else {
                html += `
                    <div class="bg-black rounded-lg overflow-hidden relative">
                        <div class="aspect-video">
                            <img id="wall-image-${cam.id}" src="${cam.url}" class="w-full h-full object-contain" alt="${cam.name}">
                        </div>
                        <div class="absolute bottom-2 left-2 text-white text-sm font-semibold bg-black bg-opacity-50 px-2 py-1 rounded">${cam.name}</div>
                    </div>
                `;
            }
        }
        grid.innerHTML = html;

        if (typeof lucide !== 'undefined') lucide.createIcons();

        // HLS Player nach Verzögerung
        setTimeout(() => {
            for (const cam of selected) {
                if (cam.type === 'rtsp') {
                    const videoEl = document.getElementById(`wall-video-${cam.id}`);
                    if (videoEl) {
                        const hlsUrl = `/static/hls/${cam.id}.m3u8`;
                        const hls = this._initWallHlsPlayer(videoEl, hlsUrl, cam.id);
                        if (hls) this._cameraWallHls[cam.id] = hls;
                    }
                } else if (cam.type === 'ring') {
                    this._startRingSnapshotRefresh(cam.id, `wall-image-${cam.id}`, 5000);
                }
            }
        }, 3000);
    }

    _initWallHlsPlayer(videoEl, hlsUrl, camId) {
        if (typeof Hls !== 'undefined' && Hls.isSupported()) {
            if (camId && this._cameraWallHls[camId]) {
                try { this._cameraWallHls[camId].destroy(); } catch (e) {}
                delete this._cameraWallHls[camId];
            }
            const hls = new Hls({
                liveDurationInfinity: true,
                enableWorker: true,
                lowLatencyMode: true
            });
            hls.loadSource(hlsUrl);
            hls.attachMedia(videoEl);
            hls.on(Hls.Events.MANIFEST_PARSED, () => {
                videoEl.play().catch(() => {});
                const loading = document.getElementById(`wall-loading-${camId}`);
                if (loading) loading.style.display = 'none';
            });
            hls.on(Hls.Events.ERROR, (event, data) => {
                if (data.fatal) {
                    if (camId && this._cameraWallRetryTimers[camId]) return;
                    const retryTimer = setTimeout(() => {
                        hls.destroy();
                        delete this._cameraWallHls[camId];
                        if (camId) delete this._cameraWallRetryTimers[camId];
                        this._initWallHlsPlayer(videoEl, hlsUrl, camId);
                    }, 3000);
                    if (camId) this._cameraWallRetryTimers[camId] = retryTimer;
                }
            });
            return hls;
        }
        return null;
    }

    async removeCamera(cameraId) {
        try {
            await fetch(`/api/cameras/${cameraId}`, { method: 'DELETE' });
            console.log(`Kamera entfernt: ${cameraId}`);
        } catch (e) {
            console.error('Fehler beim Entfernen der Kamera:', e);
        }
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
        const scope = 'page:setup';

        // ⭐ v4.6.0: Lade Widgets für diese Page
        await this.loadAndRenderWidgets('setup');

        // Lade gespeicherte PLC-Konfiguration aus LocalStorage
        const savedAmsId = localStorage.getItem('plc_ams_id');
        const savedAmsPort = localStorage.getItem('plc_ams_port');
        const savedIpAddress = localStorage.getItem('plc_ip_address');
        const savedRuntimeType = (localStorage.getItem('plc_runtime_type') || 'TC3').toUpperCase();

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

        const runtimeInput = document.getElementById('plc-runtime-type');
        const amsPortInput = document.getElementById('plc-ams-port');
        if (runtimeInput) {
            runtimeInput.value = savedRuntimeType === 'TC2' ? 'TC2' : 'TC3';
            this._bindScopedListener(runtimeInput, 'change', () => {
                const rt = (runtimeInput.value || 'TC3').toUpperCase();
                localStorage.setItem('plc_runtime_type', rt);
                if (amsPortInput && amsPortInput.getAttribute('data-user-edited') !== '1') {
                    amsPortInput.value = rt === 'TC2' ? '801' : '851';
                }
            }, { scope, key: 'setup:runtime-change' });
        }
        if (amsPortInput) {
            this._bindScopedListener(amsPortInput, 'input', () => {
                amsPortInput.setAttribute('data-user-edited', '1');
            }, { scope, key: 'setup:ams-port-input' });
        }

        // Setup PLC-Button Event-Listener (falls noch nicht registriert)
        const connectBtn = document.getElementById('plc-connect-btn');
        if (connectBtn) this._bindScopedListener(connectBtn, 'click', () => this.connectPLC(), { scope, key: 'setup:plc-connect' });

        const disconnectBtn = document.getElementById('plc-disconnect-btn');
        if (disconnectBtn) this._bindScopedListener(disconnectBtn, 'click', () => this.disconnectPLC(), { scope, key: 'setup:plc-disconnect' });

        // Setup Symbol-Browser (falls noch nicht registriert)
        const symbolSearchBtn = document.getElementById('symbol-search-btn');
        if (symbolSearchBtn) {
            this._bindScopedListener(symbolSearchBtn, 'click', () => this.searchPLCSymbols(), { scope, key: 'setup:symbol-search-btn' });

            // Enter-Taste im Suchfeld
            const symbolSearch = document.getElementById('symbol-search');
            if (symbolSearch) {
                this._bindScopedListener(symbolSearch, 'keypress', (e) => {
                    if (e.key === 'Enter') {
                        this.searchPLCSymbols();
                    }
                }, { scope, key: 'setup:symbol-search-keypress' });
            }
        }

        // Setup Live-Symbol-Abruf
        const loadLiveSymbolsBtn = document.getElementById('load-live-symbols-btn');
        if (loadLiveSymbolsBtn) this._bindScopedListener(loadLiveSymbolsBtn, 'click', () => this.loadLiveSymbols(), { scope, key: 'setup:live-symbols-btn' });

        // Setup TPY-Upload
        const tpyUploadBtn = document.getElementById('tpy-upload-btn');
        const tpyUploadInput = document.getElementById('tpy-upload');
        if (tpyUploadBtn && tpyUploadInput) {
            this._bindScopedListener(tpyUploadBtn, 'click', () => tpyUploadInput.click(), { scope, key: 'setup:tpy-upload-open' });
            this._bindScopedListener(tpyUploadInput, 'change', (e) => this.uploadTPY(e.target.files[0]), { scope, key: 'setup:tpy-upload-change' });
        }

        // Setup MQTT-Handler (falls noch nicht registriert)
        const mqttConnectBtn = document.getElementById('mqtt-connect-btn');
        if (mqttConnectBtn) {
            this.registerMQTTHandlers();
        }

        // Setup Symbol-Suche Event-Listener
        const symbolSearchInput = document.getElementById('symbol-search');
        if (symbolSearchInput) {
            // Input Event für Live-Suche
            this._bindScopedListener(symbolSearchInput, 'input', () => {
                // Debounce: Warte 300ms nach letzter Eingabe
                clearTimeout(this.searchDebounceTimer);
                this.searchDebounceTimer = setTimeout(() => {
                    this.searchPLCSymbols();
                }, 300);
            }, { scope, key: 'setup:symbol-search-input' });

            // Enter-Key für sofortige Suche
            this._bindScopedListener(symbolSearchInput, 'keydown', (e) => {
                if (e.key === 'Enter') {
                    clearTimeout(this.searchDebounceTimer);
                    this.searchPLCSymbols();
                }
            }, { scope, key: 'setup:symbol-search-keydown' });
        }

        // Setup Type-Filter Event-Listener
        const typeFilterSelect = document.getElementById('symbol-type-filter');
        if (typeFilterSelect) {
            this._bindScopedListener(typeFilterSelect, 'change', () => {
                this.searchPLCSymbols();
            }, { scope, key: 'setup:symbol-type-filter-change' });
        }

        // Setup View-Mode-Umschaltung
        document.querySelectorAll('input[name="symbol-view"]').forEach(radio => {
            const mode = radio.value || 'unknown';
            this._bindScopedListener(radio, 'change', () => {
                if (this.currentSymbols && this.currentSymbols.length > 0) {
                    const viewMode = radio.value;
                    const symbolTree = document.getElementById('symbol-tree');

                    if (viewMode === 'tree') {
                        this.renderSymbolTree(this.currentSymbols, symbolTree);
                    } else {
                        this.renderSymbolList(this.currentSymbols, symbolTree);
                    }
                }
            }, { scope, key: `setup:symbol-view:${mode}` });
        });

        // Lade System-Status (mit Delay für DOM)
        setTimeout(() => {
            this.loadSystemStatus();
        }, 200);

        // Lade Symbole automatisch beim Seitenwechsel
        setTimeout(() => {
            this.searchPLCSymbols();
        }, 300);

        // Trigger-Regel-Editor laden
        setTimeout(() => {
            this._initCameraRuleEditor();
        }, 150);

        // Routing-Editor laden
        setTimeout(() => {
            this._initRoutingEditor();
        }, 180);

        // ADS-Routen Setup laden
        setTimeout(() => {
            this._initAdsRouteTools();
        }, 220);
    }

    async _initAdsRouteTools() {
        const statusEl = document.getElementById('ads-route-status');
        if (!statusEl) return;
        this._bindAdsRouteEvents();
        this._prefillAdsRouteInputs();
        await this._loadAdsRouteStatus();
    }

    _bindAdsRouteEvents() {
        const bindOnce = (id, fn, eventName = 'click') => {
            const el = document.getElementById(id);
            if (!el || el.hasAttribute('data-listener-attached')) return;
            el.addEventListener(eventName, fn);
            el.setAttribute('data-listener-attached', 'true');
        };
        bindOnce('ads-route-status-btn', () => this._loadAdsRouteStatus());
        bindOnce('ads-route-add-btn', () => this._addAdsRoute());
        bindOnce('ads-route-test-btn', () => this._testAdsRoute());
    }

    _prefillAdsRouteInputs() {
        const setVal = (id, value) => {
            const el = document.getElementById(id);
            if (el && value) el.value = value;
        };

        const plcAms = localStorage.getItem('plc_ams_id') || '';
        const plcIp = localStorage.getItem('plc_ip_address') || '';

        setVal('ads-plc-ams-net-id', plcAms);
        setVal('ads-plc-ip', plcIp);
        setVal('ads-plc-user', localStorage.getItem('ads_plc_user') || 'Administrator');
        setVal('ads-route-name', localStorage.getItem('ads_route_name') || 'SmartHomeWeb');
        setVal('ads-local-ams-net-id', localStorage.getItem('ads_local_ams_net_id') || '');
        setVal('ads-local-ip', localStorage.getItem('ads_local_ip') || '');
    }

    async _loadAdsRouteStatus() {
        const statusEl = document.getElementById('ads-route-status');
        if (!statusEl) return;
        statusEl.textContent = 'Lade ADS-Status...';
        try {
            const resp = await fetch('/api/plc/ads/route/status');
            const data = await resp.json();
            if (!resp.ok || data.success === false) {
                throw new Error(data.error || 'Status fehlgeschlagen');
            }
            if (!data.available) {
                statusEl.innerHTML = `<span class="text-red-500">pyads nicht verfügbar</span>${data.error ? `: ${data.error}` : ''}`;
                return;
            }
            if (data.local_ams_net_id) {
                const localAmsInput = document.getElementById('ads-local-ams-net-id');
                if (localAmsInput && !localAmsInput.value.trim()) {
                    localAmsInput.value = data.local_ams_net_id;
                }
            }
            statusEl.innerHTML = `<span class="text-green-600 dark:text-green-400">pyads verfügbar</span> | Lokale AMS: ${data.local_ams_net_id || 'nicht gesetzt'} | Defaults: TC2=801, TC3=851`;
        } catch (e) {
            statusEl.innerHTML = `<span class="text-red-500">ADS-Status Fehler:</span> ${e.message}`;
        }
    }

    _collectAdsRouteForm() {
        const getVal = (id) => (document.getElementById(id)?.value || '').trim();
        return {
            local_ams_net_id: getVal('ads-local-ams-net-id'),
            local_ip: getVal('ads-local-ip'),
            plc_ams_net_id: getVal('ads-plc-ams-net-id'),
            plc_ip: getVal('ads-plc-ip'),
            username: getVal('ads-plc-user'),
            password: document.getElementById('ads-plc-password')?.value || '',
            route_name: getVal('ads-route-name') || 'SmartHomeWeb'
        };
    }

    async _addAdsRoute() {
        const statusEl = document.getElementById('ads-route-status');
        const payload = this._collectAdsRouteForm();
        if (!payload.local_ams_net_id || !payload.plc_ams_net_id || !payload.plc_ip || !payload.username || !payload.password) {
            alert('Bitte lokale AMS, PLC AMS/IP, Benutzer und Passwort ausfüllen');
            return;
        }

        localStorage.setItem('ads_local_ams_net_id', payload.local_ams_net_id);
        localStorage.setItem('ads_local_ip', payload.local_ip || '');
        localStorage.setItem('ads_plc_user', payload.username);
        localStorage.setItem('ads_route_name', payload.route_name);

        if (statusEl) statusEl.textContent = 'Lege ADS-Route an...';

        try {
            const resp = await fetch('/api/plc/ads/route/add', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const data = await resp.json();
            if (!resp.ok || !data.success) {
                throw new Error(data.error || 'Route anlegen fehlgeschlagen');
            }
            const warnTxt = Array.isArray(data.warnings) && data.warnings.length ? ` | Hinweise: ${data.warnings.join(' | ')}` : '';
            if (statusEl) statusEl.innerHTML = `<span class="text-green-600 dark:text-green-400">ADS-Route erfolgreich angelegt</span>${warnTxt}`;
        } catch (e) {
            if (statusEl) statusEl.innerHTML = `<span class="text-red-500">ADS-Route Fehler:</span> ${e.message}`;
        }
    }

    async _testAdsRoute() {
        const statusEl = document.getElementById('ads-route-status');
        const getVal = (id) => (document.getElementById(id)?.value || '').trim();
        const payload = {
            plc_ams_net_id: getVal('ads-plc-ams-net-id'),
            plc_ip: getVal('ads-plc-ip'),
            ams_port: parseInt(document.getElementById('plc-ams-port')?.value || '801', 10)
        };
        if (!payload.plc_ams_net_id || !payload.plc_ip) {
            alert('Bitte PLC AMS Net ID und PLC IP ausfüllen');
            return;
        }
        if (statusEl) statusEl.textContent = 'Teste ADS-Verbindung...';
        try {
            const resp = await fetch('/api/plc/ads/route/test', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const data = await resp.json();
            if (!resp.ok || !data.success) {
                throw new Error(data.error || 'ADS-Test fehlgeschlagen');
            }
            const v = data.version || {};
            if (statusEl) statusEl.innerHTML = `<span class="text-green-600 dark:text-green-400">ADS-Test erfolgreich</span> | ${data.device_name || 'PLC'} v${v.version || 0}.${v.revision || 0}.${v.build || 0}`;
        } catch (e) {
            if (statusEl) statusEl.innerHTML = `<span class="text-red-500">ADS-Test Fehler:</span> ${e.message}`;
        }
    }

    async _initRoutingEditor() {
        const list = document.getElementById('route-list');
        if (!list) return;
        this._bindRoutingEditorEvents();
        await this._loadRoutingConfig();
    }

    _bindRoutingEditorEvents() {
        const bindOnce = (id, fn, eventName = 'click') => {
            const el = document.getElementById(id);
            if (!el || el.hasAttribute('data-listener-attached')) return;
            el.addEventListener(eventName, fn);
            el.setAttribute('data-listener-attached', 'true');
        };

        bindOnce('route-refresh-btn', () => this._loadRoutingConfig());
        bindOnce('route-add-btn', () => this._clearRouteForm());
        bindOnce('route-save-btn', () => this._saveRouteFromForm());
        bindOnce('route-delete-btn', () => this._deleteRouteFromForm());
    }

    async _loadRoutingConfig() {
        const list = document.getElementById('route-list');
        if (list) {
            list.innerHTML = '<p class="text-xs text-gray-500">Lade Routen...</p>';
        }
        try {
            const resp = await fetch('/api/routing/config');
            const data = await resp.json();
            if (!resp.ok) {
                throw new Error(data.error || 'Routing-Laden fehlgeschlagen');
            }
            this._routingConfig = {
                version: data.version || '1.0',
                description: data.description || 'Routing-Konfiguration',
                routes: Array.isArray(data.routes) ? data.routes : [],
                settings: data.settings && typeof data.settings === 'object' ? data.settings : {}
            };
            this._renderRouteList();
        } catch (e) {
            if (list) {
                list.innerHTML = `<p class="text-xs text-red-500">${e.message}</p>`;
            }
        }
    }

    _renderRouteList() {
        const list = document.getElementById('route-list');
        if (!list) return;
        const routes = Array.isArray(this._routingConfig.routes) ? this._routingConfig.routes : [];
        if (routes.length === 0) {
            list.innerHTML = '<p class="text-xs text-gray-500">Keine Routen vorhanden</p>';
            return;
        }

        list.innerHTML = routes.map((route) => {
            const id = String(route.id || '');
            const enabled = route.enabled !== false;
            const selected = id && id === this._routeEditorSelectedId;
            return `
                <button class="route-item-btn w-full text-left p-2 rounded border ${selected ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/30' : 'border-gray-200 dark:border-gray-700'} hover:border-blue-400"
                        data-route-id="${id}">
                    <div class="flex items-center justify-between">
                        <span class="text-sm font-medium text-gray-900 dark:text-white">${id || '(ohne ID)'}</span>
                        <span class="text-[11px] px-2 py-0.5 rounded ${enabled ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300' : 'bg-gray-200 text-gray-700 dark:bg-gray-700 dark:text-gray-300'}">${enabled ? 'aktiv' : 'inaktiv'}</span>
                    </div>
                    <div class="text-xs text-gray-500 dark:text-gray-400 truncate mt-1">${String(route.from || '')} → ${(Array.isArray(route.to) ? route.to.join(', ') : String(route.to || ''))}</div>
                </button>
            `;
        }).join('');

        list.querySelectorAll('.route-item-btn').forEach((btn) => {
            btn.addEventListener('click', () => {
                const routeId = btn.getAttribute('data-route-id') || '';
                const route = (this._routingConfig.routes || []).find((r) => String(r.id || '') === routeId);
                if (!route) return;
                this._routeEditorSelectedId = routeId;
                this._fillRouteForm(route);
                this._renderRouteList();
            });
        });
    }

    _fillRouteForm(route) {
        document.getElementById('route-edit-id').value = String(route.id || '');
        document.getElementById('route-id').value = String(route.id || '');
        document.getElementById('route-description').value = String(route.description || '');
        document.getElementById('route-from').value = String(route.from || '');
        document.getElementById('route-to').value = Array.isArray(route.to) ? route.to.join(', ') : String(route.to || '');
        document.getElementById('route-enabled').checked = route.enabled !== false;
    }

    _clearRouteForm() {
        this._routeEditorSelectedId = null;
        document.getElementById('route-edit-id').value = '';
        document.getElementById('route-id').value = '';
        document.getElementById('route-description').value = '';
        document.getElementById('route-from').value = '';
        document.getElementById('route-to').value = '';
        document.getElementById('route-enabled').checked = true;
        this._renderRouteList();
    }

    _collectRouteForm() {
        const editId = (document.getElementById('route-edit-id')?.value || '').trim();
        const id = (document.getElementById('route-id')?.value || '').trim();
        const description = (document.getElementById('route-description')?.value || '').trim();
        const from = (document.getElementById('route-from')?.value || '').trim();
        const toRaw = (document.getElementById('route-to')?.value || '').trim();
        const enabled = !!document.getElementById('route-enabled')?.checked;
        const to = toRaw.split(',').map((v) => v.trim()).filter(Boolean);
        return { editId, id, description, from, to, enabled };
    }

    async _saveRouteFromForm() {
        const form = this._collectRouteForm();
        if (!form.id) {
            alert('Route-ID fehlt');
            return;
        }
        if (!form.from) {
            alert('From Pattern fehlt');
            return;
        }
        if (!form.to.length) {
            alert('Mindestens ein Ziel (to) erforderlich');
            return;
        }

        const routes = Array.isArray(this._routingConfig.routes) ? [...this._routingConfig.routes] : [];
        const oldId = form.editId || form.id;
        const oldIdx = routes.findIndex((r) => String(r.id || '') === oldId);
        const routeObj = {
            id: form.id,
            description: form.description || form.id,
            from: form.from,
            to: form.to,
            enabled: form.enabled
        };
        if (oldIdx >= 0) {
            routes[oldIdx] = routeObj;
        } else {
            routes.push(routeObj);
        }

        await this._persistRoutingConfig(routes, form.id);
    }

    async _deleteRouteFromForm() {
        const form = this._collectRouteForm();
        const routeId = form.editId || form.id;
        if (!routeId) {
            alert('Keine Route ausgewählt');
            return;
        }
        if (!confirm(`Route "${routeId}" wirklich löschen?`)) return;
        const routes = (this._routingConfig.routes || []).filter((r) => String(r.id || '') !== routeId);
        await this._persistRoutingConfig(routes, null);
        this._clearRouteForm();
    }

    async _persistRoutingConfig(routes, selectedId = null) {
        try {
            const payload = {
                version: this._routingConfig.version || '1.0',
                description: this._routingConfig.description || 'Routing-Konfiguration',
                settings: this._routingConfig.settings || {},
                routes
            };
            const resp = await fetch('/api/routing/config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const data = await resp.json();
            if (!resp.ok || !data.success) {
                throw new Error(data.error || 'Speichern fehlgeschlagen');
            }
            this._routingConfig = data.config || payload;
            this._routeEditorSelectedId = selectedId;
            if (selectedId) {
                const selected = (this._routingConfig.routes || []).find((r) => String(r.id || '') === selectedId);
                if (selected) this._fillRouteForm(selected);
            }
            this._renderRouteList();
        } catch (e) {
            alert(`Routing speichern fehlgeschlagen: ${e.message}`);
        }
    }

    async _initCameraRuleEditor() {
        const list = document.getElementById('rule-editor-list');
        if (!list) return;

        this._bindCameraRuleEditorEvents();
        await this._loadRuleCameraOptions();
        await this._searchRuleVariables('');
        const pageSizeEl = document.getElementById('rule-page-size');
        if (pageSizeEl) pageSizeEl.value = String(this._ruleEditorPageSize);
        await this._loadCameraTriggerRules();
    }

    _bindCameraRuleEditorEvents() {
        const bindOnce = (id, fn, eventName = 'click') => {
            const el = document.getElementById(id);
            if (!el || el.hasAttribute('data-listener-attached')) return;
            el.addEventListener(eventName, fn);
            el.setAttribute('data-listener-attached', 'true');
        };

        bindOnce('rule-refresh-btn', () => this._loadCameraTriggerRules());
        bindOnce('rule-export-btn', () => this._exportCameraTriggerRules());
        bindOnce('rule-import-btn', () => {
            const input = document.getElementById('rule-import-file');
            if (input) input.click();
        });
        bindOnce('rule-var-search-btn', () => {
            const q = document.getElementById('rule-var-search')?.value || '';
            this._searchRuleVariables(q);
        });
        bindOnce('rule-filter-search', () => {
            this._ruleEditorPage = 1;
            this._renderRuleEditorList();
        }, 'input');
        bindOnce('rule-filter-tag', () => {
            this._ruleEditorPage = 1;
            this._renderRuleEditorList();
        }, 'input');
        bindOnce('rule-filter-camera', () => {
            this._ruleEditorPage = 1;
            this._renderRuleEditorList();
        }, 'change');
        bindOnce('rule-filter-category', () => {
            this._ruleEditorPage = 1;
            this._renderRuleEditorList();
        }, 'change');
        bindOnce('rule-filter-enabled', () => {
            this._ruleEditorPage = 1;
            this._renderRuleEditorList();
        }, 'change');
        bindOnce('rule-page-size', () => {
            const size = parseInt(document.getElementById('rule-page-size')?.value || '25', 10);
            this._ruleEditorPageSize = [25, 50, 100].includes(size) ? size : 25;
            localStorage.setItem('ruleEditorPageSize', String(this._ruleEditorPageSize));
            this._ruleEditorPage = 1;
            this._renderRuleEditorList();
        }, 'change');
        bindOnce('rule-page-prev-btn', () => {
            this._ruleEditorPage = Math.max(1, this._ruleEditorPage - 1);
            this._renderRuleEditorList();
        });
        bindOnce('rule-page-next-btn', () => {
            const totalPages = this._getRuleEditorTotalPages();
            this._ruleEditorPage = Math.min(totalPages, this._ruleEditorPage + 1);
            this._renderRuleEditorList();
        });
        bindOnce('rule-select-page-btn', () => {
            const pageRules = this._getRuleEditorPageRules();
            pageRules.forEach((r) => this._ruleEditorSelectedIds.add(r.id));
            this._renderRuleEditorList();
        });
        bindOnce('rule-select-none-btn', () => {
            this._ruleEditorSelectedIds.clear();
            this._renderRuleEditorList();
        });
        bindOnce('rule-bulk-enable-btn', () => this._applyBulkRuleAction('enable'));
        bindOnce('rule-bulk-disable-btn', () => this._applyBulkRuleAction('disable'));
        bindOnce('rule-bulk-delete-btn', () => this._applyBulkRuleAction('delete'));
        bindOnce('rule-add-btn', () => this._clearRuleForm());
        bindOnce('rule-save-btn', () => this._saveRuleFromForm());
        bindOnce('rule-delete-btn', () => this._deleteRuleFromForm());

        const varSearchInput = document.getElementById('rule-var-search');
        if (varSearchInput && !varSearchInput.hasAttribute('data-listener-attached')) {
            varSearchInput.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') {
                    this._searchRuleVariables(varSearchInput.value || '');
                }
            });
            varSearchInput.setAttribute('data-listener-attached', 'true');
        }

        const importFileInput = document.getElementById('rule-import-file');
        if (importFileInput && !importFileInput.hasAttribute('data-listener-attached')) {
            importFileInput.addEventListener('change', async () => {
                const file = importFileInput.files && importFileInput.files[0];
                if (!file) return;
                await this._importCameraTriggerRulesFromFile(file);
                importFileInput.value = '';
            });
            importFileInput.setAttribute('data-listener-attached', 'true');
        }

        document.querySelectorAll('.rule-group-btn').forEach((btn) => {
            if (btn.hasAttribute('data-listener-attached')) return;
            btn.addEventListener('click', () => {
                this._ruleEditorActiveGroup = btn.getAttribute('data-group') || '';
                this._ruleEditorPage = 1;
                this._renderRuleEditorList();
            });
            btn.setAttribute('data-listener-attached', 'true');
        });
    }

    async _loadRuleCameraOptions() {
        const select = document.getElementById('rule-camera-id');
        if (!select) return;

        try {
            const resp = await fetch('/api/cameras');
            const data = await resp.json();
            const cams = data.cameras || {};
            const ids = Object.keys(cams);

            if (ids.length === 0) {
                select.innerHTML = '<option value="">Keine Kamera</option>';
                return;
            }

            const options = ids.map((id) => {
                const cam = cams[id] || {};
                return `<option value="${id}">${cam.name || id} (${id})</option>`;
            }).join('');
            select.innerHTML = options;

            const filterSelect = document.getElementById('rule-filter-camera');
            if (filterSelect) {
                filterSelect.innerHTML = `<option value="">Alle Kameras</option>${options}`;
            }
        } catch (e) {
            select.innerHTML = '<option value="">Fehler beim Laden</option>';
        }
    }

    async _searchRuleVariables(query) {
        const select = document.getElementById('rule-variable');
        if (!select) return;
        try {
            const params = new URLSearchParams();
            params.set('limit', '200');
            if (query && query.trim()) params.set('q', query.trim());
            const resp = await fetch(`/api/variables/search?${params.toString()}`);
            const data = await resp.json();
            const vars = data.variables || [];
            this._ruleVariableOptions = vars;

            if (vars.length === 0) {
                select.innerHTML = '<option value="">Keine Variablen gefunden</option>';
                return;
            }
            select.innerHTML = vars.map((v) =>
                `<option value="${v.name}">${v.name} (${v.type || 'UNKNOWN'})</option>`
            ).join('');
        } catch (e) {
            select.innerHTML = '<option value="">Fehler bei Variablensuche</option>';
        }
    }

    async _loadCameraTriggerRules() {
        const list = document.getElementById('rule-editor-list');
        if (!list) return;
        try {
            const resp = await fetch('/api/camera-triggers');
            const data = await resp.json();
            this._cameraTriggerRules = data.rules || [];
            this._ruleEditorSelectedIds.clear();
            this._ruleEditorPage = 1;
            this._refreshRuleCategoryFilterOptions();
            this._renderRuleEditorList();
            if (this._cameraTriggerRules.length > 0) {
                this._fillRuleForm(this._cameraTriggerRules[0]);
            } else {
                this._clearRuleForm();
            }
        } catch (e) {
            list.innerHTML = '<p class="text-xs text-red-500">Regeln konnten nicht geladen werden</p>';
        }
    }

    _refreshRuleCategoryFilterOptions() {
        const categorySelect = document.getElementById('rule-filter-category');
        if (!categorySelect) return;
        const current = categorySelect.value || '';
        const categories = Array.from(new Set(
            this._cameraTriggerRules
                .map((r) => String(r.category || 'general').trim().toLowerCase())
                .filter(Boolean)
        )).sort();
        const options = categories.map((c) => `<option value="${c}">${c}</option>`).join('');
        categorySelect.innerHTML = `<option value="">Alle Kategorien</option>${options}`;
        if (categories.includes(current)) categorySelect.value = current;
    }

    _getRuleEditorFilteredRules() {
        const q = (document.getElementById('rule-filter-search')?.value || '').trim().toLowerCase();
        const cameraId = (document.getElementById('rule-filter-camera')?.value || '').trim();
        const category = (document.getElementById('rule-filter-category')?.value || '').trim().toLowerCase();
        const tagFilter = (document.getElementById('rule-filter-tag')?.value || '').trim().toLowerCase();
        const enabledFilter = (document.getElementById('rule-filter-enabled')?.value || '').trim();
        const group = (this._ruleEditorActiveGroup || '').trim().toLowerCase();

        return this._cameraTriggerRules.filter((r) => {
            if (cameraId && r.camera_id !== cameraId) return false;
            const rCategory = String(r.category || 'general').trim().toLowerCase();
            const rTags = Array.isArray(r.tags) ? r.tags.map((t) => String(t).toLowerCase()) : [];
            if (category && rCategory !== category) return false;
            if (tagFilter && !rTags.some((t) => t.includes(tagFilter))) return false;
            if (group && rCategory !== group && !rTags.includes(group)) return false;
            if (enabledFilter === '1' && !r.enabled) return false;
            if (enabledFilter === '0' && !!r.enabled) return false;
            if (!q) return true;

            const haystack = `${r.id || ''} ${r.name || ''} ${r.variable || ''} ${r.camera_id || ''} ${rCategory} ${(rTags || []).join(' ')}`.toLowerCase();
            return haystack.includes(q);
        });
    }

    _getRuleEditorTotalPages() {
        const total = this._getRuleEditorFilteredRules().length;
        return Math.max(1, Math.ceil(total / this._ruleEditorPageSize));
    }

    _getRuleEditorPageRules() {
        const filtered = this._getRuleEditorFilteredRules();
        const totalPages = Math.max(1, Math.ceil(filtered.length / this._ruleEditorPageSize));
        if (this._ruleEditorPage > totalPages) this._ruleEditorPage = totalPages;
        const start = (this._ruleEditorPage - 1) * this._ruleEditorPageSize;
        return filtered.slice(start, start + this._ruleEditorPageSize);
    }

    _renderRuleEditorList() {
        const list = document.getElementById('rule-editor-list');
        if (!list) return;
        document.querySelectorAll('.rule-group-btn').forEach((btn) => {
            const group = btn.getAttribute('data-group') || '';
            if (group === (this._ruleEditorActiveGroup || '')) {
                btn.classList.add('ring-2', 'ring-offset-1', 'ring-white');
            } else {
                btn.classList.remove('ring-2', 'ring-offset-1', 'ring-white');
            }
        });

        const statsEl = document.getElementById('rule-list-stats');
        const pageInfoEl = document.getElementById('rule-page-info');
        const prevBtn = document.getElementById('rule-page-prev-btn');
        const nextBtn = document.getElementById('rule-page-next-btn');

        if (!this._cameraTriggerRules.length) {
            list.innerHTML = '<p class="text-xs text-gray-500">Keine Regeln vorhanden</p>';
            if (statsEl) statsEl.textContent = '0 Regeln';
            if (pageInfoEl) pageInfoEl.textContent = 'Seite 1/1';
            if (prevBtn) prevBtn.disabled = true;
            if (nextBtn) nextBtn.disabled = true;
            return;
        }

        const filtered = this._getRuleEditorFilteredRules();
        const totalPages = this._getRuleEditorTotalPages();
        const pageRules = this._getRuleEditorPageRules();

        if (!filtered.length) {
            list.innerHTML = '<p class="text-xs text-gray-500">Keine Treffer für den aktuellen Filter</p>';
            if (statsEl) statsEl.textContent = `0 Treffer von ${this._cameraTriggerRules.length} Regeln`;
            if (pageInfoEl) pageInfoEl.textContent = 'Seite 1/1';
            if (prevBtn) prevBtn.disabled = true;
            if (nextBtn) nextBtn.disabled = true;
            return;
        }

        list.innerHTML = pageRules.map((r) => {
            const state = r.enabled ? 'bg-green-100 text-green-800' : 'bg-gray-200 text-gray-700';
            const op = r.operator || 'eq';
            const checked = this._ruleEditorSelectedIds.has(r.id) ? 'checked' : '';
            const category = String(r.category || 'general');
            const tags = Array.isArray(r.tags) ? r.tags : [];
            const tagHtml = tags.slice(0, 4).map((t) => `<span class="text-[10px] px-1.5 py-0.5 rounded bg-gray-200 text-gray-700 dark:bg-gray-700 dark:text-gray-200">${t}</span>`).join('');
            return `
                <div class="flex items-start gap-2 p-2 rounded border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700">
                    <input type="checkbox" class="rule-select mt-1" data-rule-id="${r.id}" ${checked}>
                    <button class="rule-row flex-1 text-left" data-rule-id="${r.id}">
                        <div class="flex items-center justify-between">
                            <span class="text-sm font-medium text-gray-900 dark:text-white">${r.name || r.id}</span>
                            <span class="text-[10px] px-2 py-0.5 rounded ${state}">${r.enabled ? 'aktiv' : 'aus'}</span>
                        </div>
                        <div class="text-xs text-gray-500 dark:text-gray-400 truncate">${r.variable} ${op} ${JSON.stringify(r.on_value)}</div>
                        <div class="text-[11px] text-gray-500 dark:text-gray-400">→ ${r.camera_id} (${r.duration_seconds || 30}s)</div>
                        <div class="mt-1 flex items-center gap-1 flex-wrap">
                            <span class="text-[10px] px-1.5 py-0.5 rounded bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-200">${category}</span>
                            ${tagHtml}
                        </div>
                    </button>
                </div>
            `;
        }).join('');

        if (statsEl) {
            statsEl.textContent = `${filtered.length} Treffer von ${this._cameraTriggerRules.length} Regeln · ${this._ruleEditorSelectedIds.size} markiert`;
        }
        if (pageInfoEl) {
            pageInfoEl.textContent = `Seite ${this._ruleEditorPage}/${totalPages}`;
        }
        if (prevBtn) prevBtn.disabled = this._ruleEditorPage <= 1;
        if (nextBtn) nextBtn.disabled = this._ruleEditorPage >= totalPages;

        list.querySelectorAll('.rule-row').forEach((el) => {
            el.addEventListener('click', () => {
                const id = el.getAttribute('data-rule-id');
                const rule = this._cameraTriggerRules.find((r) => r.id === id);
                if (rule) this._fillRuleForm(rule);
            });
        });

        list.querySelectorAll('.rule-select').forEach((el) => {
            el.addEventListener('change', () => {
                const id = el.getAttribute('data-rule-id');
                if (!id) return;
                if (el.checked) this._ruleEditorSelectedIds.add(id);
                else this._ruleEditorSelectedIds.delete(id);
                if (statsEl) {
                    statsEl.textContent = `${filtered.length} Treffer von ${this._cameraTriggerRules.length} Regeln · ${this._ruleEditorSelectedIds.size} markiert`;
                }
            });
        });
    }

    async _exportCameraTriggerRules() {
        try {
            const resp = await fetch('/api/camera-triggers/export');
            if (!resp.ok) {
                throw new Error(`HTTP ${resp.status}`);
            }
            const blob = await resp.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            const ts = new Date().toISOString().replace(/[:.]/g, '-');
            a.href = url;
            a.download = `camera_trigger_rules_${ts}.json`;
            document.body.appendChild(a);
            a.click();
            a.remove();
            URL.revokeObjectURL(url);
        } catch (e) {
            alert(`Export fehlgeschlagen: ${e.message}`);
        }
    }

    async _importCameraTriggerRulesFromFile(file) {
        try {
            const text = await file.text();
            let payload = null;
            try {
                payload = JSON.parse(text);
            } catch (e) {
                throw new Error('Datei ist kein gültiges JSON');
            }

            const mode = confirm('Regeln zusammenführen? "OK" = Merge, "Abbrechen" = Ersetzen') ? 'merge' : 'replace';
            const resp = await fetch('/api/camera-triggers/import', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ payload, mode })
            });
            const data = await resp.json();
            if (!resp.ok || !data.success) {
                const details = (data.errors && data.errors.length) ? `\n${data.errors.slice(0, 5).join('\n')}` : '';
                throw new Error((data.error || 'Import fehlgeschlagen') + details);
            }

            this._cameraTriggerRules = data.rules || [];
            this._ruleEditorSelectedIds.clear();
            this._ruleEditorPage = 1;
            this._refreshRuleCategoryFilterOptions();
            this._renderRuleEditorList();
            if (this._cameraTriggerRules.length > 0) this._fillRuleForm(this._cameraTriggerRules[0]);
            else this._clearRuleForm();

            if (data.warnings && data.warnings.length) {
                alert(`Import erfolgreich mit Warnungen:\n${data.warnings.slice(0, 10).join('\n')}`);
            }
        } catch (e) {
            alert(`Import fehlgeschlagen: ${e.message}`);
        }
    }

    async _persistCameraTriggerRules() {
        const resp = await fetch('/api/camera-triggers', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ version: '2.0', rules: this._cameraTriggerRules })
        });
        const data = await resp.json();
        if (!resp.ok || !data.success) {
            throw new Error(data.error || 'Regeln konnten nicht gespeichert werden');
        }
        this._cameraTriggerRules = data.rules || [];
        this._refreshRuleCategoryFilterOptions();
        if (data.warnings && data.warnings.length) {
            console.warn('Trigger-Regel Warnungen:', data.warnings);
        }
    }

    async _applyBulkRuleAction(action) {
        const ids = Array.from(this._ruleEditorSelectedIds);
        if (!ids.length) return;

        if (action === 'delete') {
            const ok = confirm(`${ids.length} markierte Regel(n) wirklich löschen?`);
            if (!ok) return;
        }

        if (action === 'enable' || action === 'disable') {
            const enableValue = action === 'enable';
            this._cameraTriggerRules = this._cameraTriggerRules.map((r) => (
                ids.includes(r.id) ? { ...r, enabled: enableValue } : r
            ));
        } else if (action === 'delete') {
            this._cameraTriggerRules = this._cameraTriggerRules.filter((r) => !ids.includes(r.id));
        } else {
            return;
        }

        try {
            await this._persistCameraTriggerRules();
            this._ruleEditorSelectedIds.clear();
            this._renderRuleEditorList();
            const currentId = document.getElementById('rule-edit-id')?.value?.trim();
            if (currentId && !this._cameraTriggerRules.some((r) => r.id === currentId)) {
                this._clearRuleForm();
            }
        } catch (e) {
            alert(`Bulk-Aktion fehlgeschlagen: ${e.message}`);
        }
    }

    _fillRuleForm(rule) {
        if (!rule) return;
        const setVal = (id, value) => {
            const el = document.getElementById(id);
            if (el) el.value = value ?? '';
        };
        setVal('rule-edit-id', rule.id || '');
        setVal('rule-name', rule.name || '');
        setVal('rule-variable', rule.variable || '');
        setVal('rule-operator', rule.operator || 'eq');
        setVal('rule-on-value', typeof rule.on_value === 'string' ? rule.on_value : JSON.stringify(rule.on_value));
        setVal('rule-category', rule.category || 'general');
        setVal('rule-tags', Array.isArray(rule.tags) ? rule.tags.join(',') : '');
        setVal('rule-camera-id', rule.camera_id || '');
        setVal('rule-duration-seconds', rule.duration_seconds || 30);
        setVal('rule-cooldown-seconds', rule.cooldown_seconds || 0);
        const enabled = document.getElementById('rule-enabled');
        if (enabled) enabled.checked = !!rule.enabled;
    }

    _clearRuleForm() {
        this._fillRuleForm({
            id: '',
            name: '',
            variable: '',
            operator: 'eq',
            on_value: true,
            category: 'general',
            tags: [],
            camera_id: '',
            duration_seconds: 30,
            cooldown_seconds: 0,
            enabled: true
        });
    }

    _parseRuleInputValue(raw) {
        const v = (raw || '').trim();
        if (!v.length) return true;
        const lower = v.toLowerCase();
        if (lower === 'true') return true;
        if (lower === 'false') return false;
        if (!Number.isNaN(Number(v)) && v !== '') return Number(v);
        try {
            return JSON.parse(v);
        } catch (e) {
            return v;
        }
    }

    _collectRuleForm() {
        const getVal = (id) => document.getElementById(id)?.value ?? '';
        const enabled = document.getElementById('rule-enabled')?.checked ?? true;
        const editId = getVal('rule-edit-id').trim();
        const variable = getVal('rule-variable').trim();
        const cameraId = getVal('rule-camera-id').trim();
        const name = getVal('rule-name').trim() || `${variable} -> ${cameraId}`;
        const operator = getVal('rule-operator').trim() || 'eq';
        const onValue = this._parseRuleInputValue(getVal('rule-on-value'));
        const category = (getVal('rule-category').trim().toLowerCase() || 'general').replace(/[^a-z0-9_-]/g, '');
        const tags = getVal('rule-tags')
            .split(',')
            .map((t) => t.trim().toLowerCase())
            .filter((t) => !!t);
        const duration = Math.max(5, Math.min(parseInt(getVal('rule-duration-seconds') || '30', 10), 300));
        const cooldown = Math.max(0, Math.min(parseInt(getVal('rule-cooldown-seconds') || '0', 10), 3600));

        if (!variable || !cameraId) {
            throw new Error('Variable und Kamera sind erforderlich');
        }
        return {
            id: editId || `rule_${Date.now()}`,
            name,
            enabled,
            variable,
            operator,
            on_value: onValue,
            category: category || 'general',
            tags: Array.from(new Set(tags)),
            camera_id: cameraId,
            camera_type: 'ring',
            duration_seconds: duration,
            cooldown_seconds: cooldown
        };
    }

    async _saveRuleFromForm() {
        try {
            const rule = this._collectRuleForm();
            const idx = this._cameraTriggerRules.findIndex((r) => r.id === rule.id);
            if (idx >= 0) this._cameraTriggerRules[idx] = rule;
            else this._cameraTriggerRules.unshift(rule);

            await this._persistCameraTriggerRules();
            this._renderRuleEditorList();
            this._fillRuleForm(rule);
        } catch (e) {
            alert(`Regel speichern fehlgeschlagen: ${e.message}`);
        }
    }

    async _deleteRuleFromForm() {
        const editId = document.getElementById('rule-edit-id')?.value?.trim();
        if (!editId) return;
        this._cameraTriggerRules = this._cameraTriggerRules.filter((r) => r.id !== editId);
        this._ruleEditorSelectedIds.delete(editId);
        try {
            await this._persistCameraTriggerRules();
            this._renderRuleEditorList();
            this._clearRuleForm();
        } catch (e) {
            alert(`Regel löschen fehlgeschlagen: ${e.message}`);
        }
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
        const scope = 'page:setup';

        const connectBtn = document.getElementById('mqtt-connect-btn');
        const disconnectBtn = document.getElementById('mqtt-disconnect-btn');
        const subscribeBtn = document.getElementById('mqtt-subscribe-btn');

        if (connectBtn) {
            this._bindScopedListener(connectBtn, 'click', () => this.connectMQTT(), { scope, key: 'setup:mqtt-connect' });
        }

        if (disconnectBtn) {
            this._bindScopedListener(disconnectBtn, 'click', () => this.disconnectMQTT(), { scope, key: 'setup:mqtt-disconnect' });
        }

        if (subscribeBtn) {
            this._bindScopedListener(subscribeBtn, 'click', () => this.subscribeMQTT(), { scope, key: 'setup:mqtt-subscribe' });
        }

        // Load initial status
        this.loadMQTTStatus();
    }

    // ========================================================================
    // ADMIN PAGE
    // ========================================================================

    async loadAdminPage() {
        console.log('👑 Lade Admin...');
        const scope = 'page:admin';
        if (!this._adminLogFilter) {
            this._adminLogFilter = 'all';
        }

        // ⭐ v4.6.0: Lade Widgets für diese Page
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
        const restartDaemonBtn = document.getElementById('restart-daemon-btn');
        const logsFilterSelect = document.getElementById('logs-filter-select');

        if (addPlcBtn) {
            this._bindScopedListener(addPlcBtn, 'click', () => this.addPLC(), { scope, key: 'admin:add-plc' });
        }

        if (cleanupBtn) {
            this._bindScopedListener(cleanupBtn, 'click', () => this.cleanupTPY(), { scope, key: 'admin:cleanup-tpy' });
        }

        if (refreshLogsBtn) {
            this._bindScopedListener(refreshLogsBtn, 'click', () => this.loadLogs(), { scope, key: 'admin:refresh-logs' });
        }

        if (logsFilterSelect) {
            logsFilterSelect.value = this._adminLogFilter || 'all';
            this._bindScopedListener(logsFilterSelect, 'change', () => {
                this._adminLogFilter = logsFilterSelect.value || 'all';
                this.loadLogs();
            }, { scope, key: 'admin:logs-filter-change' });
        }

        if (clearLogsBtn) {
            this._bindScopedListener(clearLogsBtn, 'click', () => this.clearLogs(), { scope, key: 'admin:clear-logs' });
        }

        if (restartServiceBtn) {
            this._bindScopedListener(restartServiceBtn, 'click', () => this.restartService(), { scope, key: 'admin:restart-service' });
        }
        if (restartDaemonBtn) {
            this._bindScopedListener(restartDaemonBtn, 'click', () => this.restartDaemonService(), { scope, key: 'admin:restart-daemon' });
        }
    }

    async loadLogs() {
        console.log('📋 Lade System-Logs...');

        try {
            const filter = this._adminLogFilter || 'all';
            const response = await fetch(`/api/admin/logs?limit=50&filter=${encodeURIComponent(filter)}`);
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

    async restartDaemonService() {
        if (!confirm('🔄 Dienst wirklich neu starten?\n\nDies führt scripts/web_server_ctl.sh restart aus. Die Verbindung wird kurz unterbrochen.')) return;

        try {
            const response = await fetch('/api/admin/service/restart-daemon', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ delay: 1 })
            });

            const data = await response.json();
            if (!response.ok || !data.success) {
                throw new Error(data.error || 'Dienst-Restart fehlgeschlagen');
            }

            alert(`✅ ${data.message}\n\nSeite lädt automatisch neu...`);

            let countdown = 5;
            const interval = setInterval(() => {
                countdown--;
                console.log(`Dienst-Restart in ${countdown}s...`);
                if (countdown === 0) {
                    clearInterval(interval);
                    location.reload();
                }
            }, 1000);
        } catch (error) {
            console.error('❌ Dienst-Restart fehlgeschlagen:', error);
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
        const scope = 'page:widgets';

        // ⭐ v4.6.0: Lade Widgets für diese Page
        await this.loadAndRenderWidgets('widgets');
        await this.loadCustomPages();

        await this.loadWidgetList();
        this.renderRoomList();

        // Event Listeners
        const addBtn = document.getElementById('add-widget-btn');
        const form = document.getElementById('widget-form');
        const closeBtn = document.getElementById('close-widget-editor');
        const cancelBtn = document.getElementById('cancel-widget-edit');
        const testBtn = document.getElementById('test-binding-btn');
        const browseBtn = document.getElementById('browse-symbols-btn');
        const addRoomBtn = document.getElementById('add-room-btn');
        const savePanelBtn = document.getElementById('save-panel-settings-btn');

        if (addBtn) {
            this._bindScopedListener(addBtn, 'click', () => this.openWidgetEditor(), { scope, key: 'widgets:add-open-editor' });
        }

        if (form) {
            this._bindScopedListener(form, 'submit', (e) => {
                e.preventDefault();
                this.saveWidget();
            }, { scope, key: 'widgets:form-submit' });
        }

        if (closeBtn || cancelBtn) {
            [closeBtn, cancelBtn].forEach(btn => {
                if (!btn) return;
                const key = btn.id ? `widgets:close:${btn.id}` : 'widgets:close:anon';
                this._bindScopedListener(btn, 'click', () => this.closeWidgetEditor(), { scope, key });
            });
        }

        if (testBtn) {
            this._bindScopedListener(testBtn, 'click', () => this.testVariableBinding(), { scope, key: 'widgets:test-binding' });
        }

        if (browseBtn) {
            this._bindScopedListener(browseBtn, 'click', () => this.browseSymbols(), { scope, key: 'widgets:browse-symbols' });
        }
        if (addRoomBtn) {
            this._bindScopedListener(addRoomBtn, 'click', () => this.createRoomPage(), { scope, key: 'widgets:add-room' });
        }
        if (savePanelBtn) {
            this._bindScopedListener(savePanelBtn, 'click', () => this.savePanelSettings(), { scope, key: 'widgets:save-panel-settings' });
        }

        const iconInput = document.getElementById('widget-icon');
        if (iconInput) {
            this._bindScopedListener(iconInput, 'input', () => {
                this.updateWidgetIconPreview(iconInput.value || 'box');
            }, { scope, key: 'widgets:icon-preview' });
        }

        // ⭐ v5.1.2: Widget-Type Change Handler (Switch-Config anzeigen/verstecken)
        const widgetTypeSelect = document.getElementById('widget-type');
        const switchConfigSection = document.getElementById('switch-config-section');

        if (widgetTypeSelect && switchConfigSection) {
            this._bindScopedListener(widgetTypeSelect, 'change', () => {
                const type = widgetTypeSelect.value;
                switchConfigSection.style.display = (type === 'switch') ? 'block' : 'none';
            }, { scope, key: 'widgets:type-change' });
        }

        // ⭐ v5.1.2: Switch-Mode Change Handler (Pulse-Duration anzeigen/verstecken)
        const switchModeSelect = document.getElementById('switch-mode');
        const pulseDurationContainer = document.getElementById('pulse-duration-container');

        if (switchModeSelect && pulseDurationContainer) {
            this._bindScopedListener(switchModeSelect, 'change', () => {
                const mode = switchModeSelect.value;
                pulseDurationContainer.style.display = (mode === 'pulse') ? 'block' : 'none';
            }, { scope, key: 'widgets:switch-mode-change' });
        }

        this.refreshPanelSettingsUI();
        this.renderWidgetIconQuickpick();
    }

    getAvailablePageOptions() {
        const staticPages = [
            ['dashboard', 'Dashboard'],
            ['lighting', 'Beleuchtung'],
            ['climate', 'Klima'],
            ['energy', 'Energie'],
            ['cameras', 'Kameras'],
            ['monitor', 'Monitor'],
            ['widgets', 'Widgets']
        ];
        const dynamicPages = Object.values(this.customPages || {})
            .sort((a, b) => Number(a?.order ?? 9999) - Number(b?.order ?? 9999))
            .map(page => [page.id, `Raum: ${page.name}`]);
        return [...staticPages, ...dynamicPages];
    }

    refreshWidgetPageOptions(selectedPage = '') {
        const select = document.getElementById('widget-page');
        if (!select) return;
        select.innerHTML = this.getAvailablePageOptions().map(([id, label]) =>
            `<option value="${this.escapeHtml(id)}">${this.escapeHtml(label)}</option>`
        ).join('');
        if (selectedPage) {
            select.value = selectedPage;
        }
    }

    refreshPanelSettingsUI() {
        const select = document.getElementById('panel-start-page');
        const kioskCheckbox = document.getElementById('panel-kiosk-default');
        if (select) {
            select.innerHTML = this.getAvailablePageOptions().map(([id, label]) =>
                `<option value="${this.escapeHtml(id)}">${this.escapeHtml(label)}</option>`
            ).join('');
            select.value = this.uiSettings?.default_page || 'dashboard';
        }
        if (kioskCheckbox) {
            kioskCheckbox.checked = !!this.uiSettings?.kiosk_default;
        }
    }

    renderRoomList() {
        const container = document.getElementById('room-list');
        if (!container) return;
        const pages = Object.values(this.customPages || {}).sort((a, b) => {
            const oa = Number(a?.order ?? 9999);
            const ob = Number(b?.order ?? 9999);
            if (oa !== ob) return oa - ob;
            return String(a?.name || a?.id || '').localeCompare(String(b?.name || b?.id || ''));
        });
        if (pages.length === 0) {
            container.innerHTML = '<p class="text-sm text-gray-500 dark:text-gray-400">Noch keine Räume angelegt.</p>';
            return;
        }
        container.innerHTML = pages.map(page => `
            <div class="room-list-item p-3 rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900 flex items-center justify-between"
                 data-page-id="${this.escapeHtml(page.id)}" draggable="true">
                <div class="flex items-center gap-2">
                    <button class="room-drag-handle p-1 rounded bg-gray-100 dark:bg-gray-800 text-gray-500 cursor-grab" title="Ziehen">
                        <i data-lucide="grip-vertical" class="w-4 h-4"></i>
                    </button>
                    <i data-lucide="${this.escapeHtml(page.icon || 'layout-grid')}" class="w-4 h-4 text-blue-500"></i>
                    <span class="text-sm font-medium text-gray-800 dark:text-gray-200">${this.escapeHtml(page.name)}</span>
                    <span class="text-xs text-gray-500">(${this.escapeHtml(page.id)})</span>
                </div>
                <div class="flex items-center gap-2">
                    <button class="room-move-up-btn px-2 py-1 text-xs bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-200 rounded hover:bg-gray-300 dark:hover:bg-gray-600" data-page-id="${this.escapeHtml(page.id)}">↑</button>
                    <button class="room-move-down-btn px-2 py-1 text-xs bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-200 rounded hover:bg-gray-300 dark:hover:bg-gray-600" data-page-id="${this.escapeHtml(page.id)}">↓</button>
                    <button class="room-edit-btn px-3 py-1 text-xs bg-amber-600 text-white rounded hover:bg-amber-700" data-page-id="${this.escapeHtml(page.id)}">Bearbeiten</button>
                    <button class="room-open-btn px-3 py-1 text-xs bg-blue-600 text-white rounded hover:bg-blue-700" data-page-id="${this.escapeHtml(page.id)}">Öffnen</button>
                    <button class="room-delete-btn px-3 py-1 text-xs bg-red-600 text-white rounded hover:bg-red-700" data-page-id="${this.escapeHtml(page.id)}">Löschen</button>
                </div>
            </div>
        `).join('');

        container.querySelectorAll('.room-open-btn').forEach(btn => {
            btn.addEventListener('click', () => this.showPage(btn.dataset.pageId));
        });
        container.querySelectorAll('.room-delete-btn').forEach(btn => {
            btn.addEventListener('click', () => this.deleteRoomPage(btn.dataset.pageId));
        });
        container.querySelectorAll('.room-edit-btn').forEach(btn => {
            btn.addEventListener('click', () => this.editRoomPage(btn.dataset.pageId));
        });
        container.querySelectorAll('.room-move-up-btn').forEach(btn => {
            btn.addEventListener('click', () => this.moveRoomByStep(btn.dataset.pageId, -1));
        });
        container.querySelectorAll('.room-move-down-btn').forEach(btn => {
            btn.addEventListener('click', () => this.moveRoomByStep(btn.dataset.pageId, 1));
        });
        this.setupRoomDnD(container);
        if (typeof lucide !== 'undefined') lucide.createIcons();
    }

    setupRoomDnD(container) {
        let draggingId = null;
        container.querySelectorAll('.room-list-item').forEach(item => {
            item.addEventListener('dragstart', () => {
                draggingId = item.dataset.pageId;
                item.classList.add('opacity-40');
            });
            item.addEventListener('dragend', () => {
                draggingId = null;
                item.classList.remove('opacity-40');
            });
            item.addEventListener('dragover', (e) => {
                if (!draggingId) return;
                e.preventDefault();
            });
            item.addEventListener('drop', async (e) => {
                if (!draggingId) return;
                e.preventDefault();
                const source = container.querySelector(`.room-list-item[data-page-id="${draggingId}"]`);
                if (!source || source === item) return;
                container.insertBefore(source, item);
                await this.persistRoomOrderFromDom(container);
            });
        });
    }

    async moveRoomByStep(pageId, delta) {
        const container = document.getElementById('room-list');
        if (!container) return;
        const items = Array.from(container.querySelectorAll('.room-list-item'));
        const current = items.find(el => el.dataset.pageId === pageId);
        if (!current) return;
        const index = items.indexOf(current);
        const targetIndex = index + delta;
        if (targetIndex < 0 || targetIndex >= items.length) return;
        const target = items[targetIndex];
        if (delta < 0) {
            container.insertBefore(current, target);
        } else {
            container.insertBefore(target, current);
        }
        await this.persistRoomOrderFromDom(container);
    }

    async persistRoomOrderFromDom(container) {
        const orderedIds = Array.from(container.querySelectorAll('.room-list-item'))
            .map(el => el.dataset.pageId)
            .filter(Boolean);
        await this.persistRoomOrder(orderedIds);
    }

    async persistRoomOrder(orderedIds) {
        try {
            const response = await fetch('/api/pages/reorder', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ ordered_ids: orderedIds })
            });
            const data = await response.json();
            if (!response.ok) {
                this.showToast(data.error || 'Raum-Reihenfolge konnte nicht gespeichert werden.', { level: 'error' });
                return;
            }
            await this.loadCustomPages();
            this.renderRoomList();
        } catch (error) {
            this.showToast(`Raum-Reihenfolge konnte nicht gespeichert werden: ${error.message}`, { level: 'error' });
        }
    }

    async createRoomPage() {
        const nameInput = document.getElementById('new-room-name');
        const iconInput = document.getElementById('new-room-icon');
        const name = (nameInput?.value || '').trim();
        const icon = (iconInput?.value || 'layout-grid').trim() || 'layout-grid';
        if (!name) {
            this.showToast('Bitte einen Raumnamen eingeben.', { level: 'error' });
            return;
        }
        try {
            const response = await fetch('/api/pages', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name, icon })
            });
            const data = await response.json();
            if (!response.ok) {
                this.showToast(data.error || 'Seite konnte nicht erstellt werden.', { level: 'error' });
                return;
            }
            if (nameInput) nameInput.value = '';
            if (iconInput) iconInput.value = '';
            await this.loadCustomPages();
            this.renderRoomList();
            this.refreshPanelSettingsUI();
            this.showToast(`Seite "${name}" erstellt.`, { level: 'success' });
        } catch (error) {
            this.showToast(`Seite konnte nicht erstellt werden: ${error.message}`, { level: 'error' });
        }
    }

    async editRoomPage(pageId) {
        const current = this.customPages?.[pageId];
        if (!current) return;
        const newName = prompt('Neuer Name für die Seite:', current.name || pageId);
        if (newName === null) return;
        const trimmedName = newName.trim();
        if (!trimmedName) {
            this.showToast('Name darf nicht leer sein.', { level: 'error' });
            return;
        }
        const newIcon = prompt('Lucide-Icon (z. B. home, building, panel-left):', current.icon || 'layout-grid');
        if (newIcon === null) return;
        const trimmedIcon = (newIcon || '').trim() || 'layout-grid';
        try {
            const response = await fetch(`/api/pages/${encodeURIComponent(pageId)}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name: trimmedName, icon: trimmedIcon })
            });
            const data = await response.json();
            if (!response.ok) {
                this.showToast(data.error || 'Seite konnte nicht bearbeitet werden.', { level: 'error' });
                return;
            }
            await this.loadCustomPages();
            this.renderRoomList();
            this.refreshPanelSettingsUI();
            this.showToast(`Seite "${trimmedName}" aktualisiert.`, { level: 'success' });
        } catch (error) {
            this.showToast(`Seite konnte nicht bearbeitet werden: ${error.message}`, { level: 'error' });
        }
    }

    async deleteRoomPage(pageId) {
        if (!confirm(`Seite "${pageId}" wirklich löschen? Widgets werden auf Dashboard verschoben.`)) return;
        try {
            const response = await fetch(`/api/pages/${encodeURIComponent(pageId)}`, { method: 'DELETE' });
            const data = await response.json();
            if (!response.ok) {
                this.showToast(data.error || 'Seite konnte nicht gelöscht werden.', { level: 'error' });
                return;
            }
            await this.loadCustomPages();
            this.renderRoomList();
            this.refreshPanelSettingsUI();
            const dynamicPage = document.getElementById(`${pageId}-page`);
            if (dynamicPage) dynamicPage.remove();
            if (this.currentPage === pageId) this.showPage('dashboard');
            this.showToast(`Seite "${pageId}" gelöscht.`, { level: 'success' });
        } catch (error) {
            this.showToast(`Seite konnte nicht gelöscht werden: ${error.message}`, { level: 'error' });
        }
    }

    async loadWidgetList() {
        try {
            const response = await fetch('/api/widgets');
            const data = await response.json();
            this._widgetStore = data.widgets || {};
            this.renderWidgetList(this._widgetStore);
        } catch (error) {
            console.error('❌ Fehler beim Laden der Widgets:', error);
        }
    }

    renderWidgetList(widgets) {
        const container = document.getElementById('widget-list');
        if (!container) return;

        const allWidgets = Object.entries(widgets || {}).map(([id, widget]) => ({ ...widget, id }));
        if (allWidgets.length === 0) {
            container.innerHTML = '<p class="text-gray-500 dark:text-gray-400">Keine Widgets konfiguriert. Erstelle ein neues Widget!</p>';
            return;
        }

        const byPage = {};
        allWidgets.forEach(widget => {
            const page = widget.page || 'dashboard';
            byPage[page] = byPage[page] || [];
            byPage[page].push(widget);
        });

        const pages = ['dashboard', 'lighting', 'climate', 'energy', 'cameras', 'monitor', 'widgets'];
        const extraPages = Object.keys(byPage).filter(page => !pages.includes(page)).sort();
        const orderedPages = [...pages, ...extraPages];
        const sortWidgets = (arr) => arr.sort((a, b) => {
            const orderA = Number(a.position?.order ?? 9999);
            const orderB = Number(b.position?.order ?? 9999);
            if (orderA !== orderB) return orderA - orderB;
            return (a.title || '').localeCompare(b.title || '');
        });

        container.innerHTML = orderedPages
            .filter(page => Array.isArray(byPage[page]) && byPage[page].length > 0)
            .map(page => {
                const pageWidgets = sortWidgets(byPage[page]);
                const itemsHtml = pageWidgets.map(widget => {
                    const bindingsHtml = Object.entries(widget.bindings || {})
                        .map(([key, binding]) => `<div class="text-xs text-gray-500 dark:text-gray-400">${this.escapeHtml(key)}: ${this.escapeHtml(binding.variable || '')} (${this.escapeHtml(binding.plc_type || '-')})</div>`)
                        .join('');
                    const locked = !!widget.config?.locked;
                    const icon = widget.config?.icon || 'box';
                    return `
                        <div class="widget-list-item p-3 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900"
                             data-widget-id="${this.escapeHtml(widget.id)}"
                             data-page="${this.escapeHtml(page)}"
                             draggable="${locked ? 'false' : 'true'}">
                            <div class="flex items-start justify-between gap-3">
                                <div class="flex items-start gap-3 min-w-0 flex-1">
                                    <button class="widget-drag-handle p-2 rounded bg-gray-100 dark:bg-gray-700 text-gray-500 ${locked ? 'opacity-40 cursor-not-allowed' : 'cursor-grab'}" title="${locked ? 'Fixiert' : 'Ziehen zum Sortieren'}">
                                        <i data-lucide="grip-vertical" class="w-4 h-4"></i>
                                    </button>
                                    <div class="w-9 h-9 rounded bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300 flex items-center justify-center">
                                        <i data-lucide="${this.escapeHtml(icon)}" class="w-4 h-4"></i>
                                    </div>
                                    <div class="min-w-0 flex-1">
                                        <div class="flex items-center flex-wrap gap-2 mb-1">
                                            <h3 class="text-sm font-semibold text-gray-900 dark:text-white truncate">${this.escapeHtml(widget.title || widget.id)}</h3>
                                            <span class="px-2 py-0.5 text-xs rounded bg-gray-200 dark:bg-gray-700">${this.escapeHtml(widget.type || '-')}</span>
                                            ${locked ? '<span class="px-2 py-0.5 text-xs rounded bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300">Fixiert</span>' : ''}
                                        </div>
                                        ${bindingsHtml || '<div class="text-xs text-gray-400">Keine Variablen verknüpft</div>'}
                                    </div>
                                </div>
                                <div class="flex items-center gap-1">
                                    <button class="widget-move-up-btn p-2 text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 rounded" data-widget-id="${this.escapeHtml(widget.id)}" title="Nach oben" ${locked ? 'disabled' : ''}>
                                        <i data-lucide="arrow-up" class="w-4 h-4"></i>
                                    </button>
                                    <button class="widget-move-down-btn p-2 text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 rounded" data-widget-id="${this.escapeHtml(widget.id)}" title="Nach unten" ${locked ? 'disabled' : ''}>
                                        <i data-lucide="arrow-down" class="w-4 h-4"></i>
                                    </button>
                                    <button class="widget-toggle-lock-btn p-2 text-amber-600 hover:bg-amber-100 dark:hover:bg-amber-900/30 rounded" data-widget-id="${this.escapeHtml(widget.id)}" title="${locked ? 'Fixierung lösen' : 'Fixieren'}">
                                        <i data-lucide="${locked ? 'lock' : 'unlock'}" class="w-4 h-4"></i>
                                    </button>
                                    <button class="widget-edit-btn p-2 text-blue-600 dark:text-blue-400 hover:bg-blue-100 dark:hover:bg-blue-900/30 rounded" data-widget-id="${this.escapeHtml(widget.id)}" title="Bearbeiten">
                                        <i data-lucide="edit" class="w-4 h-4"></i>
                                    </button>
                                    <button class="widget-delete-config-btn p-2 text-red-600 dark:text-red-400 hover:bg-red-100 dark:hover:bg-red-900/30 rounded" data-widget-id="${this.escapeHtml(widget.id)}" title="Löschen">
                                        <i data-lucide="trash-2" class="w-4 h-4"></i>
                                    </button>
                                </div>
                            </div>
                        </div>
                    `;
                }).join('');

                return `
                    <section class="widget-page-group mb-4" data-page="${this.escapeHtml(page)}">
                        <div class="flex items-center justify-between mb-2">
                            <h3 class="text-sm font-semibold text-gray-700 dark:text-gray-300 uppercase">${this.escapeHtml(page)}</h3>
                            <span class="text-xs text-gray-500">${pageWidgets.length} Widgets</span>
                        </div>
                        <div class="widget-page-list space-y-2" data-page="${this.escapeHtml(page)}">${itemsHtml}</div>
                    </section>
                `;
            }).join('');

        if (typeof lucide !== 'undefined') lucide.createIcons();
        this.setupWidgetListInteractions();
    }

    setupWidgetListInteractions() {
        const container = document.getElementById('widget-list');
        if (!container) return;

        let draggingId = null;

        container.querySelectorAll('.widget-list-item').forEach(item => {
            const widgetId = item.dataset.widgetId;
            const locked = item.getAttribute('draggable') !== 'true';
            if (!locked) {
                item.addEventListener('dragstart', (e) => {
                    draggingId = widgetId;
                    item.classList.add('opacity-40');
                    e.dataTransfer.effectAllowed = 'move';
                });
                item.addEventListener('dragend', () => {
                    draggingId = null;
                    item.classList.remove('opacity-40');
                });
            }
        });

        container.querySelectorAll('.widget-page-list').forEach(list => {
            list.addEventListener('dragover', (e) => {
                if (!draggingId) return;
                e.preventDefault();
            });
            list.addEventListener('drop', async (e) => {
                if (!draggingId) return;
                e.preventDefault();
                const targetItem = e.target.closest('.widget-list-item');
                const draggedItem = container.querySelector(`.widget-list-item[data-widget-id="${draggingId}"]`);
                if (!draggedItem || !targetItem || draggedItem === targetItem) return;
                if (targetItem.getAttribute('draggable') !== 'true') return;
                targetItem.parentNode.insertBefore(draggedItem, targetItem);
                await this.persistWidgetOrderForPage(list.dataset.page);
            });
        });

        container.querySelectorAll('.widget-edit-btn').forEach(btn => {
            btn.addEventListener('click', () => this.editWidget(btn.dataset.widgetId));
        });
        container.querySelectorAll('.widget-delete-config-btn').forEach(btn => {
            btn.addEventListener('click', () => this.deleteWidgetConfig(btn.dataset.widgetId));
        });
        container.querySelectorAll('.widget-move-up-btn').forEach(btn => {
            btn.addEventListener('click', async () => this.moveWidgetByStep(btn.dataset.widgetId, -1));
        });
        container.querySelectorAll('.widget-move-down-btn').forEach(btn => {
            btn.addEventListener('click', async () => this.moveWidgetByStep(btn.dataset.widgetId, 1));
        });
        container.querySelectorAll('.widget-toggle-lock-btn').forEach(btn => {
            btn.addEventListener('click', async () => this.toggleWidgetLock(btn.dataset.widgetId));
        });
    }

    async moveWidgetByStep(widgetId, delta) {
        const item = document.querySelector(`.widget-list-item[data-widget-id="${widgetId}"]`);
        if (!item) return;
        const list = item.closest('.widget-page-list');
        if (!list) return;

        const items = Array.from(list.querySelectorAll('.widget-list-item'));
        const index = items.indexOf(item);
        const targetIndex = index + delta;
        if (targetIndex < 0 || targetIndex >= items.length) return;
        const target = items[targetIndex];
        if (target.getAttribute('draggable') !== 'true') return;

        if (delta < 0) {
            list.insertBefore(item, target);
        } else {
            list.insertBefore(target, item);
        }
        await this.persistWidgetOrderForPage(list.dataset.page);
    }

    async persistWidgetOrderForPage(page) {
        const list = document.querySelector(`.widget-page-list[data-page="${page}"]`);
        if (!list) return;
        const items = Array.from(list.querySelectorAll('.widget-list-item'));
        try {
            const updates = items.map((item, index) => {
                const widgetId = item.dataset.widgetId;
                const current = this._widgetStore?.[widgetId] || {};
                const position = { ...(current.position || {}), order: index };
                return fetch(`/api/widgets/${widgetId}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ position })
                });
            });
            await Promise.all(updates);
            await this.loadWidgetList();
            await this.loadAndRenderWidgets(page);
        } catch (error) {
            console.error('Reihenfolge konnte nicht gespeichert werden:', error);
            this.showToast('Reihenfolge konnte nicht gespeichert werden.', { level: 'error' });
        }
    }

    async toggleWidgetLock(widgetId) {
        const widget = this._widgetStore?.[widgetId];
        if (!widget) return;
        const config = { ...(widget.config || {}), locked: !widget.config?.locked };
        await fetch(`/api/widgets/${widgetId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ config })
        });
        await this.loadWidgetList();
        await this.loadAndRenderWidgets(widget.page || this.currentPage);
    }

    openWidgetEditor(widgetId = null) {
        const modal = document.getElementById('widget-editor-modal');
        if (!modal) return;

        // Reset form
        document.getElementById('widget-form').reset();
        document.getElementById('widget-edit-id').value = widgetId || '';
        this.refreshWidgetPageOptions('dashboard');
        const iconInput = document.getElementById('widget-icon');
        if (iconInput) iconInput.value = 'box';
        const lockInput = document.getElementById('widget-locked');
        if (lockInput) lockInput.checked = false;
        this.updateWidgetIconPreview('box');

        if (widgetId) {
            // Load existing widget data
            this.loadWidgetForEdit(widgetId);
        } else {
            const switchConfigSection = document.getElementById('switch-config-section');
            const pulseDurationContainer = document.getElementById('pulse-duration-container');
            if (switchConfigSection) switchConfigSection.style.display = 'block';
            if (pulseDurationContainer) pulseDurationContainer.style.display = 'none';
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
                this.refreshWidgetPageOptions(widget.page || 'dashboard');
                document.getElementById('widget-page').value = widget.page;
                document.getElementById('widget-icon').value = widget.config?.icon || 'box';
                document.getElementById('widget-locked').checked = !!widget.config?.locked;
                this.updateWidgetIconPreview(widget.config?.icon || 'box');

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
        const icon = (document.getElementById('widget-icon')?.value || 'box').trim() || 'box';
        const locked = !!document.getElementById('widget-locked')?.checked;

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
        config.icon = icon;
        config.locked = locked;

        const widgetData = {
            title,
            type,
            page,
            bindings,
            config
        };

        if (widgetId) {
            const current = this._widgetStore?.[widgetId] || {};
            widgetData.position = current.position || {};
        }

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
                await this.loadAndRenderWidgets(page);
            } else {
                alert('Fehler beim Speichern');
            }
        } catch (error) {
            console.error('Fehler:', error);
            alert('Fehler beim Speichern');
        }
    }

    async savePanelSettings() {
        const select = document.getElementById('panel-start-page');
        const kioskCheckbox = document.getElementById('panel-kiosk-default');
        const defaultPage = select?.value || 'dashboard';
        const kioskDefault = !!kioskCheckbox?.checked;
        try {
            const response = await fetch('/api/ui-settings', {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ default_page: defaultPage, kiosk_default: kioskDefault })
            });
            const data = await response.json();
            if (!response.ok) {
                this.showToast(data.error || 'Panel-Einstellungen konnten nicht gespeichert werden.', { level: 'error' });
                return;
            }
            this.uiSettings = {
                default_page: data.default_page || defaultPage,
                kiosk_default: !!data.kiosk_default
            };
            this.applyKioskMode(this.uiSettings.kiosk_default);
            this.showToast('Panel-Einstellungen gespeichert.', { level: 'success' });
        } catch (error) {
            this.showToast(`Panel-Einstellungen konnten nicht gespeichert werden: ${error.message}`, { level: 'error' });
        }
    }

    async editWidget(widgetId) {
        this.openWidgetEditor(widgetId);
    }

    async deleteWidgetConfig(widgetId) {
        if (!confirm('Widget wirklich löschen?')) return;

        try {
            const response = await fetch(`/api/widgets/${widgetId}`, {
                method: 'DELETE'
            });

            if (response.ok) {
                await this.loadWidgetList();
                await this.loadAndRenderWidgets(this.currentPage);
            } else {
                alert('Fehler beim Löschen');
            }
        } catch (error) {
            console.error('Fehler:', error);
            alert('Fehler beim Löschen');
        }
    }

    renderWidgetIconQuickpick() {
        const container = document.getElementById('widget-icon-quickpick');
        if (!container) return;
        const icons = [
            'lightbulb', 'power', 'toggle-left', 'thermometer', 'droplets',
            'wind', 'zap', 'battery', 'gauge', 'activity',
            'camera', 'shield', 'home', 'settings', 'box'
        ];
        container.innerHTML = icons.map(icon => `
            <button type="button" class="widget-icon-pick-btn px-2 py-1 text-xs rounded border border-gray-300 dark:border-gray-600 hover:bg-gray-100 dark:hover:bg-gray-700" data-icon="${icon}">
                <i data-lucide="${icon}" class="w-4 h-4 inline mr-1"></i>${icon}
            </button>
        `).join('');
        container.querySelectorAll('.widget-icon-pick-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const icon = btn.dataset.icon || 'box';
                const input = document.getElementById('widget-icon');
                if (input) input.value = icon;
                this.updateWidgetIconPreview(icon);
            });
        });
        if (typeof lucide !== 'undefined') lucide.createIcons();
    }

    updateWidgetIconPreview(iconName) {
        const preview = document.getElementById('widget-icon-preview');
        if (!preview) return;
        const safeIcon = this.escapeHtml(iconName || 'box');
        preview.innerHTML = `<i data-lucide="${safeIcon}" class="w-5 h-5 text-gray-600 dark:text-gray-300"></i>`;
        if (typeof lucide !== 'undefined') lucide.createIcons();
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
        const scope = 'page:monitor';

        // ⭐ v4.6.0: Lade Widgets für diese Page
        await this.loadAndRenderWidgets('monitor');

        // Initial data load
        await this.loadMonitorData();

        // Setup event listeners
        this.setupMonitorEventListeners(scope);

        // Start auto-refresh if enabled
        const autoRefresh = document.getElementById('monitor-auto-refresh');
        if (autoRefresh && autoRefresh.checked) {
            this.startMonitorAutoRefresh();
        }
    }

    setupMonitorEventListeners(scope = 'page:monitor') {
        // Auto-Refresh Toggle
        const autoRefreshToggle = document.getElementById('monitor-auto-refresh');
        if (autoRefreshToggle) {
            this._bindScopedListener(autoRefreshToggle, 'change', (e) => {
                if (e.target.checked) {
                    this.startMonitorAutoRefresh();
                } else {
                    this.stopMonitorAutoRefresh();
                }
            }, { scope, key: 'monitor:auto-refresh-toggle' });
        }

        // Refresh Button
        const refreshBtn = document.getElementById('monitor-refresh-btn');
        if (refreshBtn) {
            this._bindScopedListener(refreshBtn, 'click', () => this.loadMonitorData(), { scope, key: 'monitor:refresh' });
        }

        // Measure Latency Button
        const latencyBtn = document.getElementById('measure-latency-btn');
        if (latencyBtn) {
            this._bindScopedListener(latencyBtn, 'click', () => this.measureLatency(), { scope, key: 'monitor:latency' });
        }

        // Export Buttons
        const exportJsonBtn = document.getElementById('export-json-btn');
        if (exportJsonBtn) {
            this._bindScopedListener(exportJsonBtn, 'click', () => this.exportMonitorData('json'), { scope, key: 'monitor:export-json' });
        }

        const exportCsvBtn = document.getElementById('export-csv-btn');
        if (exportCsvBtn) {
            this._bindScopedListener(exportCsvBtn, 'click', () => this.exportMonitorData('csv'), { scope, key: 'monitor:export-csv' });
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

        // Variable Subscriptions (client-spezifisch)
        const subsContainer = document.getElementById('monitor-subscriptions');
        if (subsContainer) {
            const subs = data.subscriptions || {};
            const items = Array.isArray(subs.items) ? subs.items : [];
            if (items.length === 0) {
                subsContainer.innerHTML = '<p class="text-gray-500">Keine aktiven Variable-Subscriptions</p>';
            } else {
                const bySid = subs.by_sid || {};
                const header = `
                    <div class="flex items-center justify-between mb-2">
                        <div class="font-medium">Aktiv: ${subs.total || items.length}</div>
                        <div class="text-xs text-gray-500">Clients: ${Object.keys(bySid).length}</div>
                    </div>
                `;
                const rows = items.slice(0, 80).map((item) => `
                    <div class="p-2 rounded bg-gray-50 dark:bg-gray-700/40 border border-gray-200 dark:border-gray-700">
                        <div><span class="font-mono text-xs">SID:</span> <span class="font-mono text-xs">${item.sid}</span></div>
                        <div><span class="font-mono text-xs">Widget:</span> <span class="font-mono text-xs">${item.widget_id}</span></div>
                        <div><span class="font-mono text-xs">PLC:</span> <span class="font-mono text-xs">${item.plc_id}</span></div>
                        <div><span class="font-mono text-xs">Var:</span> <span class="font-mono text-xs">${item.variable}</span></div>
                    </div>
                `).join('');
                const truncated = items.length > 80
                    ? `<p class="text-xs text-gray-500 mt-2">… ${items.length - 80} weitere Einträge ausgeblendet</p>`
                    : '';
                subsContainer.innerHTML = `${header}<div class="grid grid-cols-1 md:grid-cols-2 gap-2">${rows}</div>${truncated}`;
            }
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
        this.ensureDynamicPage(pageName);

        try {
            const response = await fetch('/api/widgets');
            if (!response.ok) {
                console.error('Fehler beim Laden der Widgets:', response.status);
                return;
            }

            const data = await response.json();
            let widgets = [];
            if (data.widgets) {
                if (Array.isArray(data.widgets)) {
                    widgets = data.widgets;
                } else if (typeof data.widgets === 'object') {
                    widgets = Object.values(data.widgets);
                }
            }

            const pageWidgets = widgets
                .filter(w => (w.page || 'dashboard') === pageName)
                .sort((a, b) => {
                    const orderA = Number(a.position?.order ?? 9999);
                    const orderB = Number(b.position?.order ?? 9999);
                    if (orderA !== orderB) return orderA - orderB;
                    return (a.title || '').localeCompare(b.title || '');
                });

            const container = this.getDynamicWidgetContainer(pageName);
            if (!container) {
                console.error(`Widget-Container für ${pageName} nicht gefunden`);
                return;
            }

            container.querySelectorAll('[data-widget-id]').forEach(w => w.remove());

            pageWidgets.forEach(widget => {
                this.renderWidget(widget, container);
            });

            this.setLegacyPageVisibility(pageName, pageWidgets.length === 0);
            console.log(`✅ ${pageWidgets.length} Widgets gerendert`);

        } catch (error) {
            console.error('Fehler beim Laden/Rendern der Widgets:', error);
        }
    }

    getDynamicWidgetContainer(pageName) {
        let container = document.getElementById(`${pageName}-widgets-dynamic`);
        if (container) return container;
        const page = document.getElementById(`${pageName}-page`);
        if (!page) return null;
        container = document.createElement('div');
        container.id = `${pageName}-widgets-dynamic`;
        container.className = 'grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4 mb-6';
        page.insertBefore(container, page.firstChild.nextSibling);
        return container;
    }

    setLegacyPageVisibility(pageName, showLegacy) {
        const page = document.getElementById(`${pageName}-page`);
        if (!page) return;
        page.querySelectorAll(`[data-legacy-page="${pageName}"]`).forEach(el => {
            if (showLegacy) {
                el.classList.remove('hidden');
            } else {
                el.classList.add('hidden');
            }
        });
    }

    renderWidget(widget, container) {
        const icon = widget.config?.icon || 'box';
        const locked = !!widget.config?.locked;
        const widgetEl = document.createElement('div');
        widgetEl.className = 'widget bg-white dark:bg-gray-800 p-4 rounded-lg shadow border border-gray-200 dark:border-gray-700';
        widgetEl.setAttribute('data-widget-id', widget.id);
        widgetEl.setAttribute('data-widget-type', widget.type || '');

        if (widget.bindings && widget.bindings.value && widget.bindings.value.variable && this.variableManager) {
            const plcId = widget.plc_id || 'plc_001';
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
        }

        const safeTitle = this.escapeHtml(widget.title || widget.id);
        const safeVar = this.escapeHtml(widget.bindings?.value?.variable || 'Keine Variable');
        const safeFeedback = this.escapeHtml(widget.bindings?.feedback?.variable || '');

        switch(widget.type) {
            case 'switch':
            case 'boolean':
                const switchValue = widget.value || false;
                const switchMode = widget.config?.mode || 'toggle';
                const pulseDuration = widget.config?.pulse_duration || 500;

                widgetEl.innerHTML = `
                    <div class="widget-header flex justify-between items-center mb-2">
                        <div class="flex items-center gap-2 min-w-0">
                            <i data-lucide="${this.escapeHtml(icon)}" class="w-4 h-4 text-blue-500"></i>
                            <h3 class="text-sm font-bold text-gray-900 dark:text-white truncate">${safeTitle}</h3>
                            ${locked ? '<i data-lucide="lock" class="w-3.5 h-3.5 text-amber-500"></i>' : ''}
                        </div>
                        <button class="text-xs text-red-500 hover:text-red-700" onclick="app.deleteWidgetConfig('${widget.id}')">✕</button>
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
                                    <div class="font-medium">Steuerung: ${safeVar}</div>
                                    ${safeFeedback ? `<div class="text-xs text-gray-500 mt-1">Feedback: ${safeFeedback}</div>` : ''}
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
                        <div class="flex items-center gap-2 min-w-0">
                            <i data-lucide="${this.escapeHtml(icon)}" class="w-4 h-4 text-blue-500"></i>
                            <h3 class="text-sm font-bold text-gray-900 dark:text-white truncate">${safeTitle}</h3>
                            ${locked ? '<i data-lucide="lock" class="w-3.5 h-3.5 text-amber-500"></i>' : ''}
                        </div>
                        <button class="text-xs text-red-500 hover:text-red-700" onclick="app.deleteWidgetConfig('${widget.id}')">✕</button>
                    </div>
                    <div class="widget-body">
                        <div class="text-3xl font-bold text-blue-600 dark:text-blue-400">
                            ${widget.value || 0}
                        </div>
                        <div class="text-xs text-gray-500 dark:text-gray-400 mt-1">
                            ${safeVar}
                        </div>
                    </div>
                `;
                break;

            case 'gauge':
                widgetEl.innerHTML = `
                    <div class="widget-header flex justify-between items-center mb-2">
                        <div class="flex items-center gap-2 min-w-0">
                            <i data-lucide="${this.escapeHtml(icon)}" class="w-4 h-4 text-blue-500"></i>
                            <h3 class="text-sm font-bold text-gray-900 dark:text-white truncate">${safeTitle}</h3>
                            ${locked ? '<i data-lucide="lock" class="w-3.5 h-3.5 text-amber-500"></i>' : ''}
                        </div>
                        <button class="text-xs text-red-500 hover:text-red-700" onclick="app.deleteWidgetConfig('${widget.id}')">✕</button>
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
                            ${safeVar}
                        </div>
                    </div>
                `;
                break;

            default:
                widgetEl.innerHTML = `
                    <div class="widget-header flex justify-between items-center mb-2">
                        <div class="flex items-center gap-2 min-w-0">
                            <i data-lucide="${this.escapeHtml(icon)}" class="w-4 h-4 text-blue-500"></i>
                            <h3 class="text-sm font-bold text-gray-900 dark:text-white truncate">${safeTitle}</h3>
                            ${locked ? '<i data-lucide="lock" class="w-3.5 h-3.5 text-amber-500"></i>' : ''}
                        </div>
                        <button class="text-xs text-red-500 hover:text-red-700" onclick="app.deleteWidgetConfig('${widget.id}')">✕</button>
                    </div>
                    <div class="widget-body">
                        <div class="text-xs text-gray-500">
                            Typ: ${this.escapeHtml(widget.type || '-')}<br>
                            Variable: ${safeVar}
                        </div>
                    </div>
                `;
        }

        container.appendChild(widgetEl);
        if (typeof lucide !== 'undefined') lucide.createIcons();
    }

    async deleteWidget(widgetId) {
        if (!confirm('Widget wirklich löschen?')) return;

        try {
            // ⭐ v4.6.0: Unsubscribe before delete
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
    // ⭐ v4.6.0: VARIABLE MANAGER WIDGET METHODS
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
                toggleBtn.classList.remove('bg-gray-300', 'bg-gray-400', 'dark:bg-gray-600');
                toggleBtn.classList.add('bg-green-500');
            } else {
                toggleBtn.classList.remove('bg-green-500');
                toggleBtn.classList.add('bg-gray-400', 'dark:bg-gray-600');
            }

            // Update Label
            const spans = toggleBtn.querySelectorAll('span');
            if (spans[0]) spans[0].textContent = boolValue ? '●' : '○';
            if (spans[1]) {
                spans[1].textContent = boolValue ? 'ON' : 'OFF';
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

    // ========================================================================
    // PTZ STEUERUNG
    // ========================================================================

    async _initPTZControls(camId) {
        const ptzControls = document.getElementById('ptz-controls');
        if (!ptzControls) return;

        // PTZ-Status von Kamera abfragen
        try {
            const resp = await fetch(`/api/cameras/${camId}/ptz/status`);
            const data = await resp.json();

            if (!data.has_ptz) {
                ptzControls.classList.add('hidden');
                return;
            }

            // PTZ verfuegbar -> Controls anzeigen
            ptzControls.classList.remove('hidden');
            this._ptzCamId = camId;

            // Presets laden
            this._loadPTZPresets(camId);

            // Event-Listener fuer D-Pad Buttons
            this._setupPTZButtonListeners();

        } catch (e) {
            console.warn('PTZ Status-Abfrage fehlgeschlagen:', e);
            ptzControls.classList.add('hidden');
        }
    }

    _setupPTZButtonListeners() {
        // Alte Listener entfernen (falls vorhanden)
        this._cleanupPTZListeners();

        this._ptzListeners = [];

        const speedMap = {
            'up':       { pan: 0.0, tilt: 0.18, zoom: 0.0 },
            'down':     { pan: 0.0, tilt: -0.18, zoom: 0.0 },
            'left':     { pan: -0.18, tilt: 0.0, zoom: 0.0 },
            'right':    { pan: 0.18, tilt: 0.0, zoom: 0.0 },
            'zoom-in':  { pan: 0.0, tilt: 0.0, zoom: 0.16 },
            'zoom-out': { pan: 0.0, tilt: 0.0, zoom: -0.16 }
        };

        // D-Pad + Zoom Buttons: mousedown/touchstart -> move, mouseup/touchend -> stop
        document.querySelectorAll('.ptz-btn[data-ptz]').forEach(btn => {
            const action = btn.getAttribute('data-ptz');

            if (action === 'home') {
                // Home-Button: einfacher Click
                const handler = (e) => {
                    e.preventDefault();
                    this._ptzHome();
                };
                btn.addEventListener('click', handler);
                this._ptzListeners.push({ el: btn, event: 'click', handler });
                return;
            }

            const speed = speedMap[action];
            if (!speed) return;

            // Move starten
            const startHandler = (e) => {
                e.preventDefault();
                this._ptzMove(speed.pan, speed.tilt, speed.zoom);
            };
            // Move stoppen
            const stopHandler = (e) => {
                e.preventDefault();
                this._ptzStop();
            };

            // Mouse events
            btn.addEventListener('mousedown', startHandler);
            btn.addEventListener('mouseup', stopHandler);
            btn.addEventListener('mouseleave', stopHandler);
            this._ptzListeners.push({ el: btn, event: 'mousedown', handler: startHandler });
            this._ptzListeners.push({ el: btn, event: 'mouseup', handler: stopHandler });
            this._ptzListeners.push({ el: btn, event: 'mouseleave', handler: stopHandler });

            // Touch events (Mobile)
            btn.addEventListener('touchstart', startHandler, { passive: false });
            btn.addEventListener('touchend', stopHandler, { passive: false });
            btn.addEventListener('touchcancel', stopHandler, { passive: false });
            this._ptzListeners.push({ el: btn, event: 'touchstart', handler: startHandler });
            this._ptzListeners.push({ el: btn, event: 'touchend', handler: stopHandler });
            this._ptzListeners.push({ el: btn, event: 'touchcancel', handler: stopHandler });
        });

        // Preset Go-Button
        const goBtn = document.getElementById('ptz-preset-go');
        if (goBtn) {
            const goHandler = () => this._ptzGotoPreset();
            goBtn.addEventListener('click', goHandler);
            this._ptzListeners.push({ el: goBtn, event: 'click', handler: goHandler });
        }

        // Preset Save-Button
        const saveBtn = document.getElementById('ptz-preset-save');
        if (saveBtn) {
            const saveHandler = () => this._ptzSavePreset();
            saveBtn.addEventListener('click', saveHandler);
            this._ptzListeners.push({ el: saveBtn, event: 'click', handler: saveHandler });
        }
    }

    _cleanupPTZListeners() {
        if (this._ptzListeners) {
            this._ptzListeners.forEach(({ el, event, handler }) => {
                el.removeEventListener(event, handler);
            });
            this._ptzListeners = [];
        }
    }

    _cleanupPTZControls() {
        this._cleanupPTZListeners();
        const ptzControls = document.getElementById('ptz-controls');
        if (ptzControls) ptzControls.classList.add('hidden');
        this._ptzCamId = null;
    }

    async _ptzMove(pan, tilt, zoom) {
        if (!this._ptzCamId) return;
        try {
            await fetch(`/api/cameras/${this._ptzCamId}/ptz/move`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ pan, tilt, zoom, timeout_ms: 250 })
            });
        } catch (e) {
            console.error('PTZ move Fehler:', e);
        }
    }

    async _ptzStop() {
        if (!this._ptzCamId) return;
        try {
            await fetch(`/api/cameras/${this._ptzCamId}/ptz/stop`, {
                method: 'POST'
            });
        } catch (e) {
            console.error('PTZ stop Fehler:', e);
        }
    }

    async _ptzHome() {
        if (!this._ptzCamId) return;
        try {
            await fetch(`/api/cameras/${this._ptzCamId}/ptz/home`, {
                method: 'POST'
            });
        } catch (e) {
            console.error('PTZ home Fehler:', e);
        }
    }

    async _loadPTZPresets(camId) {
        const select = document.getElementById('ptz-preset-select');
        if (!select) return;

        select.innerHTML = '<option value="">Presets...</option>';

        try {
            const resp = await fetch(`/api/cameras/${camId}/ptz/presets`);
            const data = await resp.json();

            if (data.presets && data.presets.length > 0) {
                data.presets.forEach(p => {
                    const opt = document.createElement('option');
                    opt.value = p.token;
                    opt.textContent = p.name;
                    select.appendChild(opt);
                });
            }
        } catch (e) {
            console.warn('PTZ Presets laden fehlgeschlagen:', e);
        }
    }

    async _ptzGotoPreset() {
        if (!this._ptzCamId) return;
        const select = document.getElementById('ptz-preset-select');
        const token = select ? select.value : '';
        if (!token) return;

        try {
            await fetch(`/api/cameras/${this._ptzCamId}/ptz/preset`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ token })
            });
        } catch (e) {
            console.error('PTZ goto preset Fehler:', e);
        }
    }

    async _ptzSavePreset() {
        if (!this._ptzCamId) return;
        const name = prompt('Preset-Name:');
        if (!name) return;

        try {
            const resp = await fetch(`/api/cameras/${this._ptzCamId}/ptz/preset/save`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name })
            });
            const data = await resp.json();
            if (data.success) {
                // Presets neu laden
                this._loadPTZPresets(this._ptzCamId);
            }
        } catch (e) {
            console.error('PTZ save preset Fehler:', e);
        }
    }

    // ========================================================================
    // WIDGET PTZ (Inline-Controls in der Kamera-Card)
    // ========================================================================

    async _checkWidgetPTZ(camId) {
        // Prueft ob Kamera PTZ hat und blendet Toggle-Button ein
        try {
            const resp = await fetch(`/api/cameras/${camId}/ptz/status`);
            const data = await resp.json();
            if (data.has_ptz) {
                const btn = document.querySelector(`.cam-ptz-toggle-btn[data-cam-id="${camId}"]`);
                if (btn) btn.style.display = '';
            }
        } catch (e) {
            // Kein PTZ oder ONVIF nicht konfiguriert - Button bleibt hidden
        }
    }

    _toggleWidgetPTZ(camId) {
        const panel = document.getElementById(`widget-ptz-${camId}`);
        if (!panel) return;

        if (panel.classList.contains('hidden')) {
            // Panel oeffnen und Controls rendern
            panel.classList.remove('hidden');
            this._renderWidgetPTZ(camId, panel);
        } else {
            // Panel schliessen und Listener aufraeumen
            panel.classList.add('hidden');
            panel.innerHTML = '';
            this._cleanupWidgetPTZListeners(camId);
        }

        // Toggle-Button Styling
        const btn = document.querySelector(`.cam-ptz-toggle-btn[data-cam-id="${camId}"]`);
        if (btn) {
            if (panel.classList.contains('hidden')) {
                btn.classList.remove('bg-red-600', 'hover:bg-red-500');
                btn.classList.add('bg-blue-600', 'hover:bg-blue-500');
                btn.querySelector('span').textContent = 'PTZ';
            } else {
                btn.classList.remove('bg-blue-600', 'hover:bg-blue-500');
                btn.classList.add('bg-red-600', 'hover:bg-red-500');
                btn.querySelector('span').textContent = 'PTZ aus';
            }
        }
    }

    _renderWidgetPTZ(camId, panel) {
        panel.innerHTML = `
            <div class="flex items-start space-x-3">
                <!-- D-Pad -->
                <div class="grid grid-cols-3 gap-0.5" style="width:100px;">
                    <div></div>
                    <button data-wptz="${camId}" data-dir="up" class="wptz-btn w-8 h-8 bg-gray-300 dark:bg-gray-600 text-gray-800 dark:text-white rounded flex items-center justify-center hover:bg-blue-500 hover:text-white active:bg-blue-600 text-xs font-bold">&#9650;</button>
                    <div></div>
                    <button data-wptz="${camId}" data-dir="left" class="wptz-btn w-8 h-8 bg-gray-300 dark:bg-gray-600 text-gray-800 dark:text-white rounded flex items-center justify-center hover:bg-blue-500 hover:text-white active:bg-blue-600 text-xs font-bold">&#9664;</button>
                    <button data-wptz="${camId}" data-dir="home" class="wptz-btn w-8 h-8 bg-gray-300 dark:bg-gray-600 text-gray-800 dark:text-white rounded flex items-center justify-center hover:bg-blue-500 hover:text-white active:bg-blue-600 text-xs">&#8962;</button>
                    <button data-wptz="${camId}" data-dir="right" class="wptz-btn w-8 h-8 bg-gray-300 dark:bg-gray-600 text-gray-800 dark:text-white rounded flex items-center justify-center hover:bg-blue-500 hover:text-white active:bg-blue-600 text-xs font-bold">&#9654;</button>
                    <div></div>
                    <button data-wptz="${camId}" data-dir="down" class="wptz-btn w-8 h-8 bg-gray-300 dark:bg-gray-600 text-gray-800 dark:text-white rounded flex items-center justify-center hover:bg-blue-500 hover:text-white active:bg-blue-600 text-xs font-bold">&#9660;</button>
                    <div></div>
                </div>
                <!-- Zoom + Presets -->
                <div class="flex flex-col space-y-1">
                    <div class="flex space-x-0.5">
                        <button data-wptz="${camId}" data-dir="zoom-in" class="wptz-btn flex-1 h-8 px-3 bg-gray-300 dark:bg-gray-600 text-gray-800 dark:text-white rounded flex items-center justify-center hover:bg-blue-500 hover:text-white active:bg-blue-600 text-sm font-bold">+</button>
                        <button data-wptz="${camId}" data-dir="zoom-out" class="wptz-btn flex-1 h-8 px-3 bg-gray-300 dark:bg-gray-600 text-gray-800 dark:text-white rounded flex items-center justify-center hover:bg-blue-500 hover:text-white active:bg-blue-600 text-sm font-bold">&minus;</button>
                    </div>
                    <div class="flex space-x-0.5">
                        <select id="wptz-presets-${camId}" class="flex-1 h-7 text-xs bg-white dark:bg-gray-800 text-gray-900 dark:text-white rounded border border-gray-300 dark:border-gray-600 px-1">
                            <option value="">Presets...</option>
                        </select>
                        <button data-wptz-go="${camId}" class="h-7 px-2 bg-gray-300 dark:bg-gray-600 text-gray-800 dark:text-white rounded text-xs hover:bg-blue-500 hover:text-white">Go</button>
                        <button data-wptz-save="${camId}" class="h-7 px-2 bg-gray-300 dark:bg-gray-600 text-gray-800 dark:text-white rounded text-xs hover:bg-green-500 hover:text-white">Save</button>
                    </div>
                </div>
            </div>
        `;

        // Presets laden
        this._loadWidgetPTZPresets(camId);

        // Event-Listener binden
        this._setupWidgetPTZListeners(camId);
    }

    _setupWidgetPTZListeners(camId) {
        if (!this._widgetPtzListeners) this._widgetPtzListeners = {};
        this._widgetPtzListeners[camId] = [];

        const speedMap = {
            'up':       { pan: 0.0, tilt: 0.18, zoom: 0.0 },
            'down':     { pan: 0.0, tilt: -0.18, zoom: 0.0 },
            'left':     { pan: -0.18, tilt: 0.0, zoom: 0.0 },
            'right':    { pan: 0.18, tilt: 0.0, zoom: 0.0 },
            'zoom-in':  { pan: 0.0, tilt: 0.0, zoom: 0.16 },
            'zoom-out': { pan: 0.0, tilt: 0.0, zoom: -0.16 }
        };

        const addListener = (el, event, handler, opts) => {
            el.addEventListener(event, handler, opts);
            this._widgetPtzListeners[camId].push({ el, event, handler });
        };

        document.querySelectorAll(`[data-wptz="${camId}"]`).forEach(btn => {
            const dir = btn.getAttribute('data-dir');

            if (dir === 'home') {
                addListener(btn, 'click', (e) => {
                    e.preventDefault();
                    fetch(`/api/cameras/${camId}/ptz/home`, { method: 'POST' }).catch(() => {});
                });
                return;
            }

            const speed = speedMap[dir];
            if (!speed) return;

            const startMove = (e) => {
                e.preventDefault();
                fetch(`/api/cameras/${camId}/ptz/move`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ ...speed, timeout_ms: 250 })
                }).catch(() => {});
            };
            const stopMove = (e) => {
                e.preventDefault();
                fetch(`/api/cameras/${camId}/ptz/stop`, { method: 'POST' }).catch(() => {});
            };

            addListener(btn, 'mousedown', startMove);
            addListener(btn, 'mouseup', stopMove);
            addListener(btn, 'mouseleave', stopMove);
            addListener(btn, 'touchstart', startMove, { passive: false });
            addListener(btn, 'touchend', stopMove, { passive: false });
            addListener(btn, 'touchcancel', stopMove, { passive: false });
        });

        // Go-Button
        const goBtn = document.querySelector(`[data-wptz-go="${camId}"]`);
        if (goBtn) {
            addListener(goBtn, 'click', () => {
                const select = document.getElementById(`wptz-presets-${camId}`);
                const token = select ? select.value : '';
                if (!token) return;
                fetch(`/api/cameras/${camId}/ptz/preset`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ token })
                }).catch(() => {});
            });
        }

        // Save-Button
        const saveBtn = document.querySelector(`[data-wptz-save="${camId}"]`);
        if (saveBtn) {
            addListener(saveBtn, 'click', async () => {
                const name = prompt('Preset-Name:');
                if (!name) return;
                try {
                    const resp = await fetch(`/api/cameras/${camId}/ptz/preset/save`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ name })
                    });
                    const data = await resp.json();
                    if (data.success) {
                        this._loadWidgetPTZPresets(camId);
                    }
                } catch (e) {}
            });
        }
    }

    _cleanupWidgetPTZListeners(camId) {
        if (this._widgetPtzListeners && this._widgetPtzListeners[camId]) {
            this._widgetPtzListeners[camId].forEach(({ el, event, handler }) => {
                el.removeEventListener(event, handler);
            });
            delete this._widgetPtzListeners[camId];
        }
    }

    async _loadWidgetPTZPresets(camId) {
        const select = document.getElementById(`wptz-presets-${camId}`);
        if (!select) return;

        try {
            const resp = await fetch(`/api/cameras/${camId}/ptz/presets`);
            const data = await resp.json();
            if (data.presets && data.presets.length > 0) {
                data.presets.forEach(p => {
                    const opt = document.createElement('option');
                    opt.value = p.token;
                    opt.textContent = p.name;
                    select.appendChild(opt);
                });
            }
        } catch (e) {}
    }
}

// ========================================================================
// APP START
// ========================================================================

document.addEventListener('DOMContentLoaded', () => {
    window.app = new SmartHomeApp();
});
