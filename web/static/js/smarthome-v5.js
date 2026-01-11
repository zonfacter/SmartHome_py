/**
 * SmartHome Edge OS v5.0
 * Zentrale Integration aller v5.0 Features
 *
 * Neue Features:
 * - Symbol Browser v5.0 (PLC-Symbole mit korrekter Type-Detection)
 * - Widget Manager v5.0 (Erweiterte CRUD-Operationen)
 * - Plugin Manager v5.0 (ioBroker-Style Plugin-Verwaltung)
 */

class SmartHomeV5 {
    constructor() {
        this.symbolBrowser = null;
        this.widgetManager = null;
        this.pluginManager = null;
        this.instanceManager = null;
        this.socket = null;

        this.init();
    }

    init() {
        console.log('🚀 SmartHome Edge OS v5.0 - Initialisierung...');

        // Socket.IO Connection
        this.initSocketIO();

        // Initialize components when DOM is ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.initComponents());
        } else {
            this.initComponents();
        }
    }

    initSocketIO() {
        if (typeof io === 'undefined') {
            console.warn('⚠️  Socket.IO nicht geladen');
            return;
        }

        this.socket = io();

        this.socket.on('connect', () => {
            console.log('✅ Socket.IO verbunden');
        });

        this.socket.on('disconnect', () => {
            console.log('❌ Socket.IO getrennt');
        });

        // PLC Data Updates
        this.socket.on('plc_data_update', (data) => {
            this.handlePLCDataUpdate(data);
        });

        // Widget Value Updates
        this.socket.on('widget_value_update', (data) => {
            this.handleWidgetValueUpdate(data);
        });
    }

    initComponents() {
        console.log('🔧 Initialisiere v5.0 Komponenten...');

        // Symbol Browser (if container exists)
        const symbolContainer = document.getElementById('symbol-tree');
        if (symbolContainer && typeof SymbolBrowserV5 !== 'undefined') {
            this.symbolBrowser = new SymbolBrowserV5({
                container: symbolContainer,
                connectionId: 'plc_001',
                onSelect: (symbol) => this.onSymbolSelected(symbol)
            });
            console.log('✅ Symbol Browser v5.0 geladen');
        }

        // Widget Manager (if container exists)
        const widgetContainer = document.getElementById('widget-manager');
        if (widgetContainer && typeof WidgetManagerV5 !== 'undefined') {
            this.widgetManager = new WidgetManagerV5({
                container: widgetContainer,
                onWidgetCreated: (widget) => this.onWidgetCreated(widget),
                onWidgetUpdated: (id, widget) => this.onWidgetUpdated(id, widget),
                onWidgetDeleted: (id) => this.onWidgetDeleted(id)
            });
            console.log('✅ Widget Manager v5.0 geladen');
        }

        // Plugin Manager (if container exists)
        const pluginContainer = document.getElementById('plugin-manager');
        if (pluginContainer && typeof PluginManagerV5 !== 'undefined') {
            this.pluginManager = new PluginManagerV5({
                container: pluginContainer
            });
            console.log('✅ Plugin Manager v5.0 geladen');
        }

        // Instance Manager (if container exists)
        const instanceContainer = document.getElementById('instance-manager');
        if (instanceContainer && typeof InstanceManagerV5 !== 'undefined') {
            this.instanceManager = new InstanceManagerV5({
                container: instanceContainer
            });
            console.log('✅ Instance Manager v5.0 geladen');
        }

        console.log('🎉 SmartHome v5.0 bereit!');
    }

    // ========================================================================
    // EVENT HANDLERS
    // ========================================================================

    onSymbolSelected(symbol) {
        console.log('Symbol ausgewählt:', symbol);

        // Emit custom event
        window.dispatchEvent(new CustomEvent('symbol-selected', {
            detail: symbol
        }));

        // Show toast notification
        this.showToast(`Symbol: ${symbol.name} (${symbol.type})`, 'info');
    }

    onWidgetCreated(widget) {
        console.log('Widget erstellt:', widget);
        this.showToast(`Widget "${widget.title}" erstellt`, 'success');

        // Trigger widget sync
        this.syncWidgets();
    }

    onWidgetUpdated(id, widget) {
        console.log('Widget aktualisiert:', id, widget);
        this.showToast(`Widget "${widget.title}" aktualisiert`, 'success');

        // Trigger widget sync
        this.syncWidgets();
    }

    onWidgetDeleted(id) {
        console.log('Widget gelöscht:', id);
        this.showToast('Widget gelöscht', 'info');

        // Trigger widget sync
        this.syncWidgets();
    }

    handlePLCDataUpdate(data) {
        // Update widgets mit neuen PLC-Daten
        console.log('PLC Data Update:', data);
    }

    handleWidgetValueUpdate(data) {
        // Update widget values in UI
        console.log('Widget Value Update:', data);
    }

    // ========================================================================
    // API CALLS
    // ========================================================================

    async syncWidgets() {
        try {
            const response = await fetch('/api/plc/sync-widgets', {
                method: 'POST'
            });

            if (response.ok) {
                console.log('✅ Widgets synchronisiert');
            }
        } catch (error) {
            console.error('Widget Sync Error:', error);
        }
    }

    async getWidgetDebugInfo() {
        try {
            const response = await fetch('/api/widgets/debug');
            const data = await response.json();

            console.table(data);
            return data;
        } catch (error) {
            console.error('Debug Info Error:', error);
        }
    }

    async refreshSymbols(connectionId = 'plc_001') {
        if (this.symbolBrowser) {
            await this.symbolBrowser.loadSymbols(true);
        }
    }

    // ========================================================================
    // UTILITIES
    // ========================================================================

    showToast(message, type = 'info') {
        // Simple toast notification
        const toast = document.createElement('div');
        toast.className = `fixed bottom-4 right-4 px-4 py-3 rounded-lg shadow-lg z-50 ${
            type === 'success' ? 'bg-green-500' :
            type === 'error' ? 'bg-red-500' :
            type === 'warning' ? 'bg-orange-500' :
            'bg-blue-500'
        } text-white`;
        toast.textContent = message;

        document.body.appendChild(toast);

        setTimeout(() => {
            toast.classList.add('opacity-0', 'transition-opacity');
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }

    // ========================================================================
    // PUBLIC API
    // ========================================================================

    getSymbolBrowser() {
        return this.symbolBrowser;
    }

    getWidgetManager() {
        return this.widgetManager;
    }

    getPluginManager() {
        return this.pluginManager;
    }

    getInstanceManager() {
        return this.instanceManager;
    }
}

// Auto-initialize on load
let smarthome;

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        smarthome = new SmartHomeV5();
        window.smarthome = smarthome;
    });
} else {
    smarthome = new SmartHomeV5();
    window.smarthome = smarthome;
}

// Export
window.SmartHomeV5 = SmartHomeV5;
