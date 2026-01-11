/**
 * Variable Explorer v1.0.0
 * Explorer für PLC-Symbole und MQTT-Topics mit TreeView
 *
 * Features:
 * - Hierarchische Ansicht
 * - Drag & Drop zu Widgets
 * - Variable kopieren
 * - Live-Werte anzeigen (optional)
 */

class VariableExplorer {
    constructor(app) {
        this.app = app;
        this.plcTreeView = null;
        this.mqttTreeView = null;
        this.activeTab = 'plc'; // 'plc' oder 'mqtt'
    }

    /**
     * Initialisiert den Variable Explorer
     */
    async init() {
        console.log('📁 Initialisiere Variable Explorer...');

        // PLC TreeView
        this.plcTreeView = new TreeView('plc-variable-tree', {
            draggable: true,
            searchable: true,
            expandLevel: 1,
            onNodeClick: (node) => this.onVariableClick(node, 'plc'),
            onNodeDragStart: (node, e) => {
                console.log('Drag Start:', node.full_path);
            }
        });

        // MQTT TreeView
        this.mqttTreeView = new TreeView('mqtt-topic-tree', {
            draggable: true,
            searchable: true,
            expandLevel: 2,
            onNodeClick: (node) => this.onVariableClick(node, 'mqtt'),
        });

        // Tab-Switching
        this.setupTabs();

        // Initial Load
        await this.loadPLCSymbols();
        await this.loadMQTTTopics();
    }

    setupTabs() {
        const plcTab = document.getElementById('explorer-tab-plc');
        const mqttTab = document.getElementById('explorer-tab-mqtt');

        if (plcTab) {
            plcTab.addEventListener('click', () => this.switchTab('plc'));
        }

        if (mqttTab) {
            mqttTab.addEventListener('click', () => this.switchTab('mqtt'));
        }
    }

    switchTab(tab) {
        this.activeTab = tab;

        // Update Tab UI
        const plcTab = document.getElementById('explorer-tab-plc');
        const mqttTab = document.getElementById('explorer-tab-mqtt');
        const plcContent = document.getElementById('explorer-content-plc');
        const mqttContent = document.getElementById('explorer-content-mqtt');

        if (tab === 'plc') {
            plcTab?.classList.add('border-blue-500', 'text-blue-600');
            plcTab?.classList.remove('border-transparent', 'text-gray-500');
            mqttTab?.classList.remove('border-blue-500', 'text-blue-600');
            mqttTab?.classList.add('border-transparent', 'text-gray-500');

            plcContent?.classList.remove('hidden');
            mqttContent?.classList.add('hidden');
        } else {
            mqttTab?.classList.add('border-blue-500', 'text-blue-600');
            mqttTab?.classList.remove('border-transparent', 'text-gray-500');
            plcTab?.classList.remove('border-blue-500', 'text-blue-600');
            plcTab?.classList.add('border-transparent', 'text-gray-500');

            mqttContent?.classList.remove('hidden');
            plcContent?.classList.add('hidden');
        }
    }

    /**
     * Lädt PLC-Symbole vom Server
     */
    async loadPLCSymbols() {
        console.log('📥 Lade PLC-Symbole...');

        try {
            const response = await fetch('/api/plc/symbols/tree');
            if (!response.ok) {
                throw new Error('Failed to load PLC symbols');
            }

            const treeData = await response.json();

            if (this.plcTreeView) {
                this.plcTreeView.render(treeData);
                console.log(`✅ ${this.countNodes(treeData)} PLC-Symbole geladen`);
            }

        } catch (error) {
            console.error('❌ Fehler beim Laden der PLC-Symbole:', error);

            // Zeige Fehlermeldung im Tree
            if (this.plcTreeView) {
                this.plcTreeView.treeContainer.innerHTML = `
                    <div class="p-4 text-center text-red-500">
                        <i data-lucide="alert-circle" class="w-8 h-8 mx-auto mb-2"></i>
                        <p>Fehler beim Laden der Symbole</p>
                        <p class="text-sm text-gray-500">${error.message}</p>
                    </div>
                `;
                lucide.createIcons();
            }
        }
    }

    /**
     * Lädt MQTT-Topics vom Server
     */
    async loadMQTTTopics() {
        console.log('📥 Lade MQTT-Topics...');

        try {
            const response = await fetch('/api/mqtt/topics/tree');
            if (!response.ok) {
                throw new Error('Failed to load MQTT topics');
            }

            const treeData = await response.json();

            if (this.mqttTreeView) {
                this.mqttTreeView.render(treeData);
                console.log(`✅ ${this.countNodes(treeData)} MQTT-Topics geladen`);
            }

        } catch (error) {
            console.error('❌ Fehler beim Laden der MQTT-Topics:', error);

            // Zeige Fehlermeldung
            if (this.mqttTreeView) {
                this.mqttTreeView.treeContainer.innerHTML = `
                    <div class="p-4 text-center text-orange-500">
                        <i data-lucide="wifi-off" class="w-8 h-8 mx-auto mb-2"></i>
                        <p>MQTT nicht verbunden</p>
                        <p class="text-sm text-gray-500">Verbinde dich mit einem MQTT-Broker</p>
                    </div>
                `;
                lucide.createIcons();
            }
        }
    }

    /**
     * Handler für Variable-Click
     */
    onVariableClick(node, source) {
        console.log(`📌 Variable angeklickt:`, node);

        // Kopiere Variable-Path in Zwischenablage
        const path = node.full_path || node.name;

        if (navigator.clipboard) {
            navigator.clipboard.writeText(path).then(() => {
                this.showToast(`📋 Kopiert: ${path}`, 'success');
            }).catch(err => {
                console.error('Clipboard-Fehler:', err);
            });
        }

        // Zeige Variable-Details im Info-Panel
        this.showVariableInfo(node, source);
    }

    /**
     * Zeigt Variable-Informationen
     */
    showVariableInfo(node, source) {
        const infoPanel = document.getElementById('variable-info-panel');
        if (!infoPanel) return;

        let html = `
            <div class="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
                <h3 class="font-semibold text-lg mb-2">${node.name}</h3>
                <div class="space-y-1 text-sm">
                    <div><span class="text-gray-500">Pfad:</span> <span class="font-mono">${node.full_path || node.name}</span></div>
        `;

        if (source === 'plc') {
            html += `
                <div><span class="text-gray-500">Typ:</span> <span class="font-mono">${node.data_type || 'Unknown'}</span></div>
                <div><span class="text-gray-500">Kategorie:</span> ${node.category || '-'}</div>
            `;
        }

        html += `
                </div>
                <div class="mt-4 flex gap-2">
                    <button onclick="variableExplorer.copyToClipboard('${node.full_path || node.name}')"
                            class="px-3 py-1 bg-blue-500 text-white rounded hover:bg-blue-600 text-sm">
                        📋 Kopieren
                    </button>
                    <button onclick="variableExplorer.createWidget('${node.full_path || node.name}', '${node.data_type || 'BOOL'}')"
                            class="px-3 py-1 bg-green-500 text-white rounded hover:bg-green-600 text-sm">
                        ➕ Widget erstellen
                    </button>
                </div>
            </div>
        `;

        infoPanel.innerHTML = html;
    }

    /**
     * Kopiert Text in Zwischenablage
     */
    copyToClipboard(text) {
        if (navigator.clipboard) {
            navigator.clipboard.writeText(text).then(() => {
                this.showToast(`📋 Kopiert: ${text}`, 'success');
            });
        }
    }

    /**
     * Erstellt ein neues Widget aus einer Variable
     */
    async createWidget(variablePath, dataType) {
        console.log(`➕ Erstelle Widget für: ${variablePath}`);

        // Bestimme Widget-Typ basierend auf Datentyp
        let widgetType = 'light'; // Default
        if (dataType.includes('INT') || dataType.includes('REAL')) {
            widgetType = 'gauge';
        }

        // Erstelle Widget via API
        try {
            const response = await fetch('/api/widgets', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    type: widgetType,
                    title: variablePath.split('.').pop(), // Letzter Teil als Name
                    page: 'dashboard',
                    bindings: {
                        value: {
                            variable: variablePath,
                            plc_type: dataType
                        }
                    },
                    config: {}
                })
            });

            if (!response.ok) throw new Error('Failed to create widget');

            const data = await response.json();
            this.showToast(`✅ Widget erstellt: ${data.widget.title}`, 'success');

            // Reload Dashboard
            if (this.app.currentPage === 'dashboard') {
                this.app.loadDashboard();
            }

        } catch (error) {
            console.error('❌ Widget-Erstellung fehlgeschlagen:', error);
            this.showToast(`❌ Fehler: ${error.message}`, 'error');
        }
    }

    /**
     * Zählt Nodes im Tree (für Statistik)
     */
    countNodes(nodes) {
        let count = 0;
        const traverse = (n) => {
            count++;
            if (n.children) {
                n.children.forEach(traverse);
            }
        };
        nodes.forEach(traverse);
        return count;
    }

    /**
     * Zeigt Toast-Nachricht
     */
    showToast(message, type = 'info') {
        // Einfache Toast-Implementierung
        const toast = document.createElement('div');
        toast.className = `fixed bottom-4 right-4 px-4 py-2 rounded-lg shadow-lg text-white z-50 ${
            type === 'success' ? 'bg-green-500' :
            type === 'error' ? 'bg-red-500' :
            'bg-blue-500'
        }`;
        toast.textContent = message;

        document.body.appendChild(toast);

        setTimeout(() => {
            toast.remove();
        }, 3000);
    }

    /**
     * Refresh Trees
     */
    async refresh() {
        await this.loadPLCSymbols();
        await this.loadMQTTTopics();
    }
}

// Globale Instanz (wird von app.js initialisiert)
let variableExplorer = null;
