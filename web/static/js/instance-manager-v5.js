/**
 * Instance Manager v4.6.0
 * Connection-Instanzen Verwaltung mit Live-Monitoring
 */

class InstanceManagerV5 {
    constructor(options = {}) {
        this.container = options.container || document.getElementById('instance-manager');
        this.connections = [];
        this.selectedConnection = null;
        this.refreshInterval = null;

        this.init();
    }

    init() {
        this.render();
        this.attachEvents();
        this.loadConnections();
        this.startAutoRefresh();
    }

    render() {
        this.container.innerHTML = `
            <div class="instance-manager-v5">
                <!-- Header -->
                <div class="flex items-center justify-between mb-6">
                    <h2 class="text-2xl font-bold text-gray-900 dark:text-white">
                        <i data-lucide="network" class="inline w-6 h-6 mr-2"></i>
                        Connection Manager
                    </h2>
                    <div class="flex gap-2">
                        <button id="refresh-connections-btn" class="px-4 py-2 bg-gray-200 dark:bg-gray-700 rounded-lg hover:bg-gray-300 dark:hover:bg-gray-600">
                            <i data-lucide="refresh-cw" class="inline w-5 h-5"></i>
                        </button>
                        <button id="add-connection-btn" class="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 flex items-center space-x-2">
                            <i data-lucide="plus" class="w-5 h-5"></i>
                            <span>Connection hinzufügen</span>
                        </button>
                    </div>
                </div>

                <!-- Stats -->
                <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
                    <div class="bg-white dark:bg-gray-800 rounded-lg p-4 shadow">
                        <div class="text-sm text-gray-500 dark:text-gray-400">Total</div>
                        <div id="total-connections" class="text-2xl font-bold text-gray-900 dark:text-white">0</div>
                    </div>
                    <div class="bg-white dark:bg-gray-800 rounded-lg p-4 shadow">
                        <div class="text-sm text-gray-500 dark:text-gray-400">Verbunden</div>
                        <div id="connected-count" class="text-2xl font-bold text-green-500">0</div>
                    </div>
                    <div class="bg-white dark:bg-gray-800 rounded-lg p-4 shadow">
                        <div class="text-sm text-gray-500 dark:text-gray-400">Getrennt</div>
                        <div id="disconnected-count" class="text-2xl font-bold text-orange-500">0</div>
                    </div>
                    <div class="bg-white dark:bg-gray-800 rounded-lg p-4 shadow">
                        <div class="text-sm text-gray-500 dark:text-gray-400">Fehler</div>
                        <div id="error-count" class="text-2xl font-bold text-red-500">0</div>
                    </div>
                </div>

                <!-- Connection List -->
                <div id="connection-list" class="grid grid-cols-1 gap-4">
                    <!-- Connections werden hier eingefügt -->
                </div>

                <!-- Add Connection Modal -->
                <div id="connection-modal" class="fixed inset-0 bg-black bg-opacity-50 hidden flex items-center justify-center z-50">
                    <div class="bg-white dark:bg-gray-800 rounded-lg p-6 max-w-md w-full mx-4">
                        <h3 class="text-xl font-bold mb-4 text-gray-900 dark:text-white">Neue Connection</h3>

                        <form id="connection-form" class="space-y-4">
                            <div>
                                <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Connection ID</label>
                                <input type="text" id="connection-id" class="w-full px-3 py-2 border rounded-lg dark:bg-gray-700 dark:border-gray-600" placeholder="z.B. plc_002" required>
                            </div>

                            <div>
                                <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Type</label>
                                <select id="connection-type" class="w-full px-3 py-2 border rounded-lg dark:bg-gray-700 dark:border-gray-600">
                                    <option value="plc">PLC (TwinCAT/ADS)</option>
                                    <option value="bluetooth">Bluetooth (BLE)</option>
                                    <option value="mqtt">MQTT (TODO)</option>
                                </select>
                            </div>

                            <!-- PLC Config -->
                            <div id="plc-config" class="space-y-4">
                                <div>
                                    <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">AMS Net ID</label>
                                    <input type="text" id="ams-net-id" class="w-full px-3 py-2 border rounded-lg dark:bg-gray-700 dark:border-gray-600" placeholder="192.168.2.162.1.1">
                                </div>
                                <div>
                                    <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">AMS Port</label>
                                    <input type="number" id="ams-port" class="w-full px-3 py-2 border rounded-lg dark:bg-gray-700 dark:border-gray-600" value="851">
                                </div>
                                <div>
                                    <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">IP Address</label>
                                    <input type="text" id="ip-address" class="w-full px-3 py-2 border rounded-lg dark:bg-gray-700 dark:border-gray-600" placeholder="192.168.2.162">
                                </div>
                            </div>

                            <!-- Bluetooth Config -->
                            <div id="bluetooth-config" class="space-y-4 hidden">
                                <div>
                                    <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Device Address</label>
                                    <input type="text" id="device-address" class="w-full px-3 py-2 border rounded-lg dark:bg-gray-700 dark:border-gray-600" placeholder="AA:BB:CC:DD:EE:FF">
                                </div>
                            </div>

                            <div class="flex justify-end space-x-2 pt-4">
                                <button type="button" id="cancel-modal-btn" class="px-4 py-2 border rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700">
                                    Abbrechen
                                </button>
                                <button type="submit" class="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600">
                                    Erstellen
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            </div>
        `;

        if (typeof lucide !== 'undefined') {
            lucide.createIcons();
        }
    }

    attachEvents() {
        // Refresh Button
        document.getElementById('refresh-connections-btn')?.addEventListener('click', () => {
            this.loadConnections();
        });

        // Add Connection Button
        document.getElementById('add-connection-btn')?.addEventListener('click', () => {
            this.openModal();
        });

        // Cancel Modal
        document.getElementById('cancel-modal-btn')?.addEventListener('click', () => {
            this.closeModal();
        });

        // Form Submit
        document.getElementById('connection-form')?.addEventListener('submit', (e) => {
            e.preventDefault();
            this.createConnection();
        });

        // Type Change
        document.getElementById('connection-type')?.addEventListener('change', (e) => {
            this.toggleConfigFields(e.target.value);
        });
    }

    async loadConnections() {
        try {
            const response = await fetch('/api/connections');
            const data = await response.json();

            if (data.success) {
                this.connections = data.connections || [];
                this.renderConnectionList();
                this.updateStats();
            }

        } catch (error) {
            console.error('Load Connections Error:', error);
        }
    }

    renderConnectionList() {
        const container = document.getElementById('connection-list');

        if (this.connections.length === 0) {
            container.innerHTML = '<div class="text-center py-8 text-gray-500">Keine Connections vorhanden</div>';
            return;
        }

        container.innerHTML = this.connections.map(conn => this.renderConnectionCard(conn)).join('');

        if (typeof lucide !== 'undefined') {
            lucide.createIcons();
        }

        // Attach event listeners
        this.attachConnectionEvents();
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

    renderConnectionCard(conn) {
        const statusColors = {
            'connected': 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300',
            'disconnected': 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300',
            'connecting': 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900 dark:text-yellow-300',
            'error': 'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300'
        };

        const statusIcons = {
            'connected': '●',
            'disconnected': '○',
            'connecting': '◐',
            'error': '✗'
        };

        const statusColor = statusColors[conn.status] || statusColors['disconnected'];
        const statusIcon = statusIcons[conn.status] || '○';

        const typeIcons = {
            'plc': 'cpu',
            'bluetooth': 'bluetooth',
            'mqtt': 'rss'
        };

        return `
            <div class="bg-white dark:bg-gray-800 rounded-lg p-4 shadow hover:shadow-md transition-shadow">
                <div class="flex items-start justify-between">
                    <div class="flex items-start space-x-3 flex-1">
                        <div class="w-12 h-12 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
                            <i data-lucide="${this.escapeHtml(typeIcons[conn.type] || 'network')}" class="w-6 h-6 text-white"></i>
                        </div>
                        <div class="flex-1">
                            <h3 class="font-semibold text-gray-900 dark:text-white">${this.escapeHtml(conn.id)}</h3>
                            <div class="flex items-center space-x-2 mt-1">
                                <span class="text-xs px-2 py-0.5 rounded ${statusColor}">
                                    ${statusIcon} ${this.escapeHtml(conn.status)}
                                </span>
                                <span class="text-xs text-gray-500">${this.escapeHtml(conn.type)}</span>
                            </div>

                            ${conn.config.ams_net_id ? `
                                <div class="mt-2 text-sm text-gray-600 dark:text-gray-400">
                                    <i data-lucide="server" class="inline w-3 h-3"></i>
                                    ${this.escapeHtml(conn.config.ams_net_id)}:${this.escapeHtml(conn.config.ams_port || 851)}
                                </div>
                            ` : ''}

                            ${conn.config.device_address ? `
                                <div class="mt-2 text-sm text-gray-600 dark:text-gray-400">
                                    <i data-lucide="bluetooth" class="inline w-3 h-3"></i>
                                    ${this.escapeHtml(conn.config.device_address)}
                                </div>
                            ` : ''}

                            ${conn.status === 'connected' && conn.stats ? `
                                <div class="mt-3 grid grid-cols-2 gap-2 text-xs text-gray-600 dark:text-gray-400">
                                    <div>
                                        <span class="text-green-600">↑</span> ${this.escapeHtml(conn.stats.packets_sent || 0)} pkt
                                    </div>
                                    <div>
                                        <span class="text-blue-600">↓</span> ${this.escapeHtml(conn.stats.packets_received || 0)} pkt
                                    </div>
                                </div>
                            ` : ''}

                            ${conn.last_error ? `
                                <div class="mt-2 text-xs text-red-500">
                                    <i data-lucide="alert-circle" class="inline w-3 h-3"></i>
                                    ${this.escapeHtml(conn.last_error)}
                                </div>
                            ` : ''}
                        </div>
                    </div>
                    <div class="flex flex-col space-y-2">
                        ${conn.status === 'connected' ? `
                            <button class="disconnect-btn p-2 text-orange-500 hover:bg-orange-50 dark:hover:bg-orange-900 rounded" data-id="${this.escapeHtml(conn.id)}">
                                <i data-lucide="power" class="w-4 h-4"></i>
                            </button>
                        ` : `
                            <button class="connect-btn p-2 text-green-500 hover:bg-green-50 dark:hover:bg-green-900 rounded" data-id="${this.escapeHtml(conn.id)}">
                                <i data-lucide="power" class="w-4 h-4"></i>
                            </button>
                        `}
                        <button class="stats-btn p-2 text-blue-500 hover:bg-blue-50 dark:hover:bg-blue-900 rounded" data-id="${this.escapeHtml(conn.id)}">
                            <i data-lucide="bar-chart-2" class="w-4 h-4"></i>
                        </button>
                        <button class="delete-btn p-2 text-red-500 hover:bg-red-50 dark:hover:bg-red-900 rounded" data-id="${this.escapeHtml(conn.id)}">
                            <i data-lucide="trash-2" class="w-4 h-4"></i>
                        </button>
                    </div>
                </div>
            </div>
        `;
    }

    attachConnectionEvents() {
        // Connect Buttons
        document.querySelectorAll('.connect-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.connectConnection(btn.dataset.id);
            });
        });

        // Disconnect Buttons
        document.querySelectorAll('.disconnect-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.disconnectConnection(btn.dataset.id);
            });
        });

        // Stats Buttons
        document.querySelectorAll('.stats-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.showStats(btn.dataset.id);
            });
        });

        // Delete Buttons
        document.querySelectorAll('.delete-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.deleteConnection(btn.dataset.id);
            });
        });
    }

    updateStats() {
        const connected = this.connections.filter(c => c.status === 'connected').length;
        const disconnected = this.connections.filter(c => c.status === 'disconnected').length;
        const error = this.connections.filter(c => c.status === 'error').length;

        document.getElementById('total-connections').textContent = this.connections.length;
        document.getElementById('connected-count').textContent = connected;
        document.getElementById('disconnected-count').textContent = disconnected;
        document.getElementById('error-count').textContent = error;
    }

    // ========================================================================
    // MODAL
    // ========================================================================

    openModal() {
        const modal = document.getElementById('connection-modal');
        modal.classList.remove('hidden');
        document.getElementById('connection-id').value = '';
        document.getElementById('ams-net-id').value = '';
        document.getElementById('ip-address').value = '';
        document.getElementById('device-address').value = '';
        this.toggleConfigFields('plc');
    }

    closeModal() {
        const modal = document.getElementById('connection-modal');
        modal.classList.add('hidden');
    }

    toggleConfigFields(type) {
        const plcConfig = document.getElementById('plc-config');
        const bluetoothConfig = document.getElementById('bluetooth-config');

        if (type === 'plc') {
            plcConfig.classList.remove('hidden');
            bluetoothConfig.classList.add('hidden');
        } else if (type === 'bluetooth') {
            plcConfig.classList.add('hidden');
            bluetoothConfig.classList.remove('hidden');
        }
    }

    // ========================================================================
    // API CALLS
    // ========================================================================

    async createConnection() {
        const connectionId = document.getElementById('connection-id').value;
        const connectionType = document.getElementById('connection-type').value;

        let config = {};

        if (connectionType === 'plc') {
            config = {
                ams_net_id: document.getElementById('ams-net-id').value,
                ams_port: parseInt(document.getElementById('ams-port').value) || 851,
                ip_address: document.getElementById('ip-address').value,
                timeout: 5000
            };
        } else if (connectionType === 'bluetooth') {
            config = {
                device_address: document.getElementById('device-address').value,
                timeout: 10000
            };
        }

        try {
            const response = await fetch('/api/connections', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    id: connectionId,
                    type: connectionType,
                    config: config
                })
            });

            if (response.ok) {
                this.closeModal();
                this.loadConnections();
                this.showToast('Connection erstellt', 'success');
            } else {
                const data = await response.json();
                alert(`Fehler: ${data.error}`);
            }

        } catch (error) {
            console.error('Create Connection Error:', error);
            alert('Fehler beim Erstellen der Connection');
        }
    }

    async connectConnection(connectionId) {
        try {
            const response = await fetch(`/api/connections/${connectionId}/connect`, {
                method: 'POST'
            });

            if (response.ok) {
                this.loadConnections();
                this.showToast(`${connectionId} verbunden`, 'success');
            }

        } catch (error) {
            console.error('Connect Error:', error);
        }
    }

    async disconnectConnection(connectionId) {
        try {
            const response = await fetch(`/api/connections/${connectionId}/disconnect`, {
                method: 'POST'
            });

            if (response.ok) {
                this.loadConnections();
                this.showToast(`${connectionId} getrennt`, 'info');
            }

        } catch (error) {
            console.error('Disconnect Error:', error);
        }
    }

    async deleteConnection(connectionId) {
        if (!confirm(`Connection "${connectionId}" wirklich löschen?`)) return;

        try {
            const response = await fetch(`/api/connections/${connectionId}`, {
                method: 'DELETE'
            });

            if (response.ok) {
                this.loadConnections();
                this.showToast(`${connectionId} gelöscht`, 'info');
            }

        } catch (error) {
            console.error('Delete Error:', error);
        }
    }

    async showStats(connectionId) {
        try {
            const response = await fetch(`/api/connections/${connectionId}/stats`);
            const data = await response.json();

            if (data.success) {
                const stats = data.stats;
                const message = `
Statistiken für ${connectionId}:

Packets: ↑ ${stats.packets_sent || 0} | ↓ ${stats.packets_received || 0}
Bytes: ↑ ${this.formatBytes(stats.bytes_sent || 0)} | ↓ ${this.formatBytes(stats.bytes_received || 0)}
Errors: ${stats.errors || 0}
${stats.uptime_seconds ? `Uptime: ${this.formatUptime(stats.uptime_seconds)}` : ''}
                `.trim();

                alert(message);
            }

        } catch (error) {
            console.error('Stats Error:', error);
        }
    }

    // ========================================================================
    // AUTO REFRESH
    // ========================================================================

    startAutoRefresh() {
        this.refreshInterval = setInterval(() => {
            this.loadConnections();
        }, 5000); // Refresh alle 5 Sekunden
    }

    stopAutoRefresh() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
            this.refreshInterval = null;
        }
    }

    // ========================================================================
    // UTILITIES
    // ========================================================================

    formatBytes(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
    }

    formatUptime(seconds) {
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        const secs = Math.floor(seconds % 60);
        return `${hours}h ${minutes}m ${secs}s`;
    }

    showToast(message, type = 'info') {
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
    // SHUTDOWN
    // ========================================================================

    destroy() {
        this.stopAutoRefresh();
    }
}

// Export
window.InstanceManagerV5 = InstanceManagerV5;
