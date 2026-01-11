/**
 * Plugin Manager v5.0
 * ioBroker-Style Plugin-Verwaltung
 */

class PluginManagerV5 {
    constructor(options = {}) {
        this.container = options.container || document.getElementById('plugin-manager');
        this.plugins = [];
        this.selectedPlugin = null;

        this.init();
    }

    init() {
        this.render();
        this.loadPlugins();
    }

    render() {
        this.container.innerHTML = `
            <div class="plugin-manager-v5">
                <!-- Header -->
                <div class="flex items-center justify-between mb-6">
                    <h2 class="text-2xl font-bold text-gray-900 dark:text-white">
                        <i data-lucide="puzzle" class="inline w-6 h-6 mr-2"></i>
                        Plugin Manager
                    </h2>
                    <div class="flex gap-2">
                        <button id="refresh-plugins-btn" class="px-4 py-2 bg-gray-200 dark:bg-gray-700 rounded-lg hover:bg-gray-300 dark:hover:bg-gray-600">
                            <i data-lucide="refresh-cw" class="inline w-5 h-5"></i>
                        </button>
                        <button id="install-plugin-btn" class="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 flex items-center space-x-2">
                            <i data-lucide="download" class="w-5 h-5"></i>
                            <span>Plugin installieren</span>
                        </button>
                    </div>
                </div>

                <!-- Stats -->
                <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
                    <div class="bg-white dark:bg-gray-800 rounded-lg p-4 shadow">
                        <div class="text-sm text-gray-500 dark:text-gray-400">Installiert</div>
                        <div id="installed-count" class="text-2xl font-bold text-gray-900 dark:text-white">0</div>
                    </div>
                    <div class="bg-white dark:bg-gray-800 rounded-lg p-4 shadow">
                        <div class="text-sm text-gray-500 dark:text-gray-400">Aktiv</div>
                        <div id="active-count" class="text-2xl font-bold text-green-500">0</div>
                    </div>
                    <div class="bg-white dark:bg-gray-800 rounded-lg p-4 shadow">
                        <div class="text-sm text-gray-500 dark:text-gray-400">Verfügbar</div>
                        <div id="available-count" class="text-2xl font-bold text-blue-500">0</div>
                    </div>
                    <div class="bg-white dark:bg-gray-800 rounded-lg p-4 shadow">
                        <div class="text-sm text-gray-500 dark:text-gray-400">Updates</div>
                        <div id="updates-count" class="text-2xl font-bold text-orange-500">0</div>
                    </div>
                </div>

                <!-- Tabs -->
                <div class="mb-4 border-b border-gray-200 dark:border-gray-700">
                    <nav class="flex space-x-4">
                        <button class="tab-btn px-4 py-2 border-b-2 border-blue-500 text-blue-500 font-medium" data-tab="installed">
                            Installiert
                        </button>
                        <button class="tab-btn px-4 py-2 border-b-2 border-transparent text-gray-500 hover:text-gray-700" data-tab="available">
                            Verfügbar
                        </button>
                        <button class="tab-btn px-4 py-2 border-b-2 border-transparent text-gray-500 hover:text-gray-700" data-tab="running">
                            Laufend
                        </button>
                    </nav>
                </div>

                <!-- Plugin List -->
                <div id="plugin-list" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    <div class="col-span-full text-center py-8 text-gray-500">Lade Plugins...</div>
                </div>

                <!-- Plugin Detail Modal -->
                <div id="plugin-detail-modal" class="fixed inset-0 bg-black bg-opacity-50 hidden z-50 flex items-center justify-center">
                    <div class="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-y-auto m-4">
                        <div class="p-6">
                            <div class="flex items-start justify-between mb-4">
                                <div>
                                    <h3 id="plugin-detail-name" class="text-2xl font-bold text-gray-900 dark:text-white mb-2"></h3>
                                    <div class="flex items-center space-x-2">
                                        <span id="plugin-detail-version" class="text-sm px-2 py-1 rounded bg-gray-200 dark:bg-gray-700"></span>
                                        <span id="plugin-detail-status" class="text-sm px-2 py-1 rounded"></span>
                                    </div>
                                </div>
                                <button id="close-detail-btn" class="text-gray-400 hover:text-gray-600">
                                    <i data-lucide="x" class="w-6 h-6"></i>
                                </button>
                            </div>

                            <div id="plugin-detail-content" class="space-y-4">
                                <!-- Dynamic Content -->
                            </div>

                            <div class="flex justify-end space-x-2 pt-4 mt-4 border-t border-gray-200 dark:border-gray-700">
                                <button id="plugin-configure-btn" class="px-4 py-2 bg-gray-200 dark:bg-gray-700 rounded-lg hover:bg-gray-300 dark:hover:bg-gray-600">
                                    <i data-lucide="settings" class="inline w-4 h-4 mr-2"></i>
                                    Konfigurieren
                                </button>
                                <button id="plugin-start-btn" class="px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600">
                                    <i data-lucide="play" class="inline w-4 h-4 mr-2"></i>
                                    Starten
                                </button>
                                <button id="plugin-stop-btn" class="px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600">
                                    <i data-lucide="stop-circle" class="inline w-4 h-4 mr-2"></i>
                                    Stoppen
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;

        if (typeof lucide !== 'undefined') {
            lucide.createIcons();
        }

        this.attachEvents();
    }

    attachEvents() {
        // Refresh
        document.getElementById('refresh-plugins-btn')?.addEventListener('click', () => {
            this.loadPlugins();
        });

        // Install
        document.getElementById('install-plugin-btn')?.addEventListener('click', () => {
            this.openInstallDialog();
        });

        // Tabs
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                // Update active tab
                document.querySelectorAll('.tab-btn').forEach(b => {
                    b.classList.remove('border-blue-500', 'text-blue-500');
                    b.classList.add('border-transparent', 'text-gray-500');
                });
                btn.classList.add('border-blue-500', 'text-blue-500');
                btn.classList.remove('border-transparent', 'text-gray-500');

                // Filter plugins
                this.filterPlugins(btn.dataset.tab);
            });
        });

        // Close Detail
        document.getElementById('close-detail-btn')?.addEventListener('click', () => {
            this.closeDetailModal();
        });
    }

    async loadPlugins() {
        try {
            // Load installed plugins
            const installedResponse = await fetch('/api/plugins/installed');
            const installedData = await installedResponse.json();

            // Load available plugins
            const availableResponse = await fetch('/api/plugins/available');
            const availableData = await availableResponse.json();

            this.plugins = [
                ...(installedData.plugins || []).map(p => ({...p, installed: true})),
                ...(availableData.plugins || []).map(p => ({...p, installed: false}))
            ];

            this.renderPluginList();
            this.updateStats();

        } catch (error) {
            console.error('Load Plugins Error:', error);
            this.showMockPlugins();
        }
    }

    showMockPlugins() {
        // Mock data for demonstration
        this.plugins = [
            {
                id: 'bms_monitor',
                name: 'BMS Monitor',
                version: '1.0.0',
                description: 'Battery Management System Monitoring über Bluetooth',
                author: 'TwinCAT Team',
                status: 'running',
                installed: true,
                icon: 'battery',
                category: 'Hardware',
                cpu: 2.5,
                memory: 45
            },
            {
                id: 'multi_plc',
                name: 'Multi-PLC Manager',
                version: '1.0.0',
                description: 'Verwaltet mehrere PLC-Verbindungen parallel',
                author: 'TwinCAT Team',
                status: 'stopped',
                installed: true,
                icon: 'server',
                category: 'Industrial',
                cpu: 0,
                memory: 0
            },
            {
                id: 'mqtt_bridge',
                name: 'MQTT Bridge',
                version: '2.1.0',
                description: 'MQTT Broker Integration für IoT-Geräte',
                author: 'Community',
                status: 'running',
                installed: true,
                icon: 'radio',
                category: 'Communication',
                cpu: 1.2,
                memory: 32
            },
            {
                id: 'modbus_adapter',
                name: 'Modbus TCP Adapter',
                version: '1.5.0',
                description: 'Modbus TCP/RTU Geräte-Integration',
                author: 'Community',
                status: null,
                installed: false,
                icon: 'plug',
                category: 'Industrial'
            },
            {
                id: 'weather_api',
                name: 'Weather API',
                version: '1.2.0',
                description: 'Wetterdaten von OpenWeatherMap',
                author: 'Community',
                status: null,
                installed: false,
                icon: 'cloud',
                category: 'Data'
            }
        ];

        this.renderPluginList();
        this.updateStats();
    }

    renderPluginList() {
        const container = document.getElementById('plugin-list');
        if (!container) return;

        if (this.plugins.length === 0) {
            container.innerHTML = '<div class="col-span-full text-center py-8 text-gray-500">Keine Plugins verfügbar</div>';
            return;
        }

        container.innerHTML = this.plugins.map(plugin => this.renderPluginCard(plugin)).join('');

        if (typeof lucide !== 'undefined') {
            lucide.createIcons();
        }

        // Attach click events
        container.querySelectorAll('.plugin-card').forEach(card => {
            card.addEventListener('click', () => {
                const pluginId = card.dataset.id;
                const plugin = this.plugins.find(p => p.id === pluginId);
                if (plugin) {
                    this.showPluginDetail(plugin);
                }
            });
        });
    }

    escapeHtml(unsafe) {
        if (!unsafe) return '';
        return unsafe
            .toString()
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    renderPluginCard(plugin) {
        const statusColors = {
            'running': 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300',
            'stopped': 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300',
            'error': 'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300'
        };

        const statusColor = statusColors[plugin.status] || 'bg-gray-100 text-gray-700';

        return `
            <div class="plugin-card bg-white dark:bg-gray-800 rounded-lg p-4 shadow hover:shadow-lg transition-all cursor-pointer" data-id="${this.escapeHtml(plugin.id)}">
                <div class="flex items-start space-x-3">
                    <div class="w-12 h-12 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center flex-shrink-0">
                        <i data-lucide="${this.escapeHtml(plugin.icon || 'package')}" class="w-6 h-6 text-white"></i>
                    </div>
                    <div class="flex-1 min-w-0">
                        <h3 class="font-semibold text-gray-900 dark:text-white truncate">${this.escapeHtml(plugin.name)}</h3>
                        <div class="flex items-center space-x-2 mt-1">
                            <span class="text-xs text-gray-500">${this.escapeHtml(plugin.version)}</span>
                            ${plugin.status ? `
                                <span class="text-xs px-2 py-0.5 rounded ${statusColor}">
                                    ${plugin.status === 'running' ? '● Läuft' : '○ Gestoppt'}
                                </span>
                            ` : `
                                <span class="text-xs px-2 py-0.5 rounded bg-blue-100 text-blue-700">
                                    Verfügbar
                                </span>
                            `}
                        </div>
                        <p class="text-xs text-gray-500 dark:text-gray-400 mt-2 line-clamp-2">${this.escapeHtml(plugin.description)}</p>

                        ${plugin.status === 'running' && plugin.cpu !== undefined ? `
                            <div class="mt-3 space-y-1">
                                <div class="flex justify-between text-xs text-gray-500">
                                    <span>CPU</span>
                                    <span>${this.escapeHtml(plugin.cpu)}%</span>
                                </div>
                                <div class="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-1.5">
                                    <div class="bg-blue-500 h-1.5 rounded-full" style="width: ${Math.min(parseFloat(plugin.cpu) || 0, 100)}%"></div>
                                </div>
                                <div class="flex justify-between text-xs text-gray-500">
                                    <span>RAM</span>
                                    <span>${this.escapeHtml(plugin.memory)} MB</span>
                                </div>
                                <div class="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-1.5">
                                    <div class="bg-green-500 h-1.5 rounded-full" style="width: ${Math.min((parseFloat(plugin.memory) || 0 / 100) * 100, 100)}%"></div>
                                </div>
                            </div>
                        ` : ''}
                    </div>
                </div>

                <div class="mt-3 pt-3 border-t border-gray-200 dark:border-gray-700 flex items-center justify-between">
                    <span class="text-xs text-gray-500">
                        <i data-lucide="user" class="inline w-3 h-3"></i>
                        ${this.escapeHtml(plugin.author)}
                    </span>
                    ${plugin.installed ? `
                        <span class="text-xs text-green-500">
                            <i data-lucide="check-circle" class="inline w-3 h-3"></i>
                            Installiert
                        </span>
                    ` : ''}
                </div>
            </div>
        `;
    }

    filterPlugins(tab) {
        let filtered = [];

        switch(tab) {
            case 'installed':
                filtered = this.plugins.filter(p => p.installed);
                break;
            case 'available':
                filtered = this.plugins.filter(p => !p.installed);
                break;
            case 'running':
                filtered = this.plugins.filter(p => p.status === 'running');
                break;
            default:
                filtered = this.plugins;
        }

        const container = document.getElementById('plugin-list');
        if (container) {
            if (filtered.length === 0) {
                container.innerHTML = '<div class="col-span-full text-center py-8 text-gray-500">Keine Plugins gefunden</div>';
            } else {
                container.innerHTML = filtered.map(p => this.renderPluginCard(p)).join('');

                if (typeof lucide !== 'undefined') {
                    lucide.createIcons();
                }

                // Reattach events
                container.querySelectorAll('.plugin-card').forEach(card => {
                    card.addEventListener('click', () => {
                        const pluginId = card.dataset.id;
                        const plugin = this.plugins.find(p => p.id === pluginId);
                        if (plugin) {
                            this.showPluginDetail(plugin);
                        }
                    });
                });
            }
        }
    }

    updateStats() {
        const installed = this.plugins.filter(p => p.installed).length;
        const active = this.plugins.filter(p => p.status === 'running').length;
        const available = this.plugins.filter(p => !p.installed).length;

        document.getElementById('installed-count').textContent = installed;
        document.getElementById('active-count').textContent = active;
        document.getElementById('available-count').textContent = available;
        document.getElementById('updates-count').textContent = 0;
    }

    showPluginDetail(plugin) {
        const modal = document.getElementById('plugin-detail-modal');

        document.getElementById('plugin-detail-name').textContent = plugin.name;
        document.getElementById('plugin-detail-version').textContent = `v${plugin.version}`;

        const statusEl = document.getElementById('plugin-detail-status');
        if (plugin.status === 'running') {
            statusEl.textContent = '● Läuft';
            statusEl.className = 'text-sm px-2 py-1 rounded bg-green-100 text-green-700';
        } else if (plugin.status === 'stopped') {
            statusEl.textContent = '○ Gestoppt';
            statusEl.className = 'text-sm px-2 py-1 rounded bg-gray-100 text-gray-700';
        } else {
            statusEl.textContent = 'Nicht installiert';
            statusEl.className = 'text-sm px-2 py-1 rounded bg-blue-100 text-blue-700';
        }

        const content = document.getElementById('plugin-detail-content');
        content.innerHTML = `
            <div>
                <h4 class="font-semibold text-gray-900 dark:text-white mb-2">Beschreibung</h4>
                <p class="text-gray-600 dark:text-gray-400">${plugin.description}</p>
            </div>

            <div class="grid grid-cols-2 gap-4">
                <div>
                    <h4 class="font-semibold text-gray-900 dark:text-white mb-2">Autor</h4>
                    <p class="text-gray-600 dark:text-gray-400">${plugin.author}</p>
                </div>
                <div>
                    <h4 class="font-semibold text-gray-900 dark:text-white mb-2">Kategorie</h4>
                    <p class="text-gray-600 dark:text-gray-400">${plugin.category || 'Allgemein'}</p>
                </div>
            </div>

            ${plugin.status === 'running' ? `
                <div>
                    <h4 class="font-semibold text-gray-900 dark:text-white mb-2">Ressourcen</h4>
                    <div class="space-y-2">
                        <div>
                            <div class="flex justify-between text-sm mb-1">
                                <span class="text-gray-600 dark:text-gray-400">CPU-Auslastung</span>
                                <span class="text-gray-900 dark:text-white">${plugin.cpu}%</span>
                            </div>
                            <div class="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                                <div class="bg-blue-500 h-2 rounded-full" style="width: ${plugin.cpu}%"></div>
                            </div>
                        </div>
                        <div>
                            <div class="flex justify-between text-sm mb-1">
                                <span class="text-gray-600 dark:text-gray-400">RAM-Verwendung</span>
                                <span class="text-gray-900 dark:text-white">${plugin.memory} MB</span>
                            </div>
                            <div class="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                                <div class="bg-green-500 h-2 rounded-full" style="width: ${Math.min((plugin.memory / 100) * 100, 100)}%"></div>
                            </div>
                        </div>
                    </div>
                </div>
            ` : ''}
        `;

        modal?.classList.remove('hidden');
        this.selectedPlugin = plugin;

        if (typeof lucide !== 'undefined') {
            lucide.createIcons();
        }
    }

    closeDetailModal() {
        document.getElementById('plugin-detail-modal')?.classList.add('hidden');
        this.selectedPlugin = null;
    }

    openInstallDialog() {
        alert('Plugin Installation (TODO: Upload oder URL eingeben)');
    }
}

window.PluginManagerV5 = PluginManagerV5;
