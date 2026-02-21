/**
 * Widget Manager v4.6.0
 * Erweiterte CRUD-Operationen für Widgets
 */

class WidgetManagerV5 {
    constructor(options = {}) {
        this.container = options.container || document.getElementById('widget-manager');
        this.onWidgetCreated = options.onWidgetCreated || (() => {});
        this.onWidgetUpdated = options.onWidgetUpdated || (() => {});
        this.onWidgetDeleted = options.onWidgetDeleted || (() => {});

        this.widgets = {};
        this.currentPage = 'dashboard';

        this.init();
    }

    init() {
        this.render();
        this.loadWidgets();
    }

    render() {
        this.container.innerHTML = `
            <div class="widget-manager-v5">
                <!-- Header -->
                <div class="flex items-center justify-between mb-6">
                    <h2 class="text-2xl font-bold text-gray-900 dark:text-white">
                        <i data-lucide="layout-dashboard" class="inline w-6 h-6 mr-2"></i>
                        Widget Manager
                    </h2>
                    <button id="create-widget-btn" class="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 flex items-center space-x-2">
                        <i data-lucide="plus" class="w-5 h-5"></i>
                        <span>Neues Widget</span>
                    </button>
                </div>

                <!-- Stats -->
                <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
                    <div class="bg-white dark:bg-gray-800 rounded-lg p-4 shadow">
                        <div class="text-sm text-gray-500 dark:text-gray-400">Gesamt</div>
                        <div id="total-widgets" class="text-2xl font-bold text-gray-900 dark:text-white">0</div>
                    </div>
                    <div class="bg-white dark:bg-gray-800 rounded-lg p-4 shadow">
                        <div class="text-sm text-gray-500 dark:text-gray-400">Aktive Seite</div>
                        <div id="current-page-name" class="text-2xl font-bold text-blue-500">Dashboard</div>
                    </div>
                    <div class="bg-white dark:bg-gray-800 rounded-lg p-4 shadow">
                        <div class="text-sm text-gray-500 dark:text-gray-400">Typen</div>
                        <div id="widget-types-count" class="text-2xl font-bold text-gray-900 dark:text-white">0</div>
                    </div>
                    <div class="bg-white dark:bg-gray-800 rounded-lg p-4 shadow">
                        <div class="text-sm text-gray-500 dark:text-gray-400">Bindings</div>
                        <div id="total-bindings" class="text-2xl font-bold text-gray-900 dark:text-white">0</div>
                    </div>
                </div>

                <!-- Filter -->
                <div class="mb-4 flex gap-2">
                    <select id="page-filter" class="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white">
                        <option value="">Alle Seiten</option>
                        <option value="dashboard">Dashboard</option>
                        <option value="lighting">Beleuchtung</option>
                        <option value="climate">Klima</option>
                        <option value="energy">Energie</option>
                    </select>

                    <select id="type-filter" class="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white">
                        <option value="">Alle Typen</option>
                        <option value="switch">Switch</option>
                        <option value="slider">Slider</option>
                        <option value="gauge">Gauge</option>
                        <option value="chart">Chart</option>
                        <option value="status">Status</option>
                    </select>

                    <input
                        type="text"
                        id="widget-search"
                        placeholder="Suche..."
                        class="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                    >
                </div>

                <!-- Widget List -->
                <div id="widget-list" class="space-y-2">
                    <div class="text-center py-8 text-gray-500">Lade Widgets...</div>
                </div>

                <!-- Create/Edit Modal -->
                <div id="widget-modal" class="fixed inset-0 bg-black bg-opacity-50 hidden z-50 flex items-center justify-center">
                    <div class="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto m-4">
                        <div class="p-6">
                            <h3 id="modal-title" class="text-xl font-bold text-gray-900 dark:text-white mb-4">Neues Widget erstellen</h3>

                            <form id="widget-form" class="space-y-4">
                                <!-- Typ -->
                                <div>
                                    <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                                        Typ *
                                    </label>
                                    <select id="widget-type" required class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white">
                                        <option value="switch">Switch (Ein/Aus)</option>
                                        <option value="slider">Slider (Regler)</option>
                                        <option value="gauge">Gauge (Anzeige)</option>
                                        <option value="chart">Chart (Diagram)</option>
                                        <option value="status">Status (Indikator)</option>
                                        <option value="button">Button (Taster)</option>
                                    </select>
                                </div>

                                <!-- Titel -->
                                <div>
                                    <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                                        Titel *
                                    </label>
                                    <input
                                        type="text"
                                        id="widget-title"
                                        required
                                        placeholder="z.B. Wohnzimmer Licht"
                                        class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                                    >
                                </div>

                                <!-- Seite -->
                                <div>
                                    <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                                        Seite
                                    </label>
                                    <select id="widget-page" class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white">
                                        <option value="dashboard">Dashboard</option>
                                        <option value="lighting">Beleuchtung</option>
                                        <option value="climate">Klima</option>
                                        <option value="energy">Energie</option>
                                    </select>
                                </div>

                                <!-- Variable Binding -->
                                <div>
                                    <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                                        PLC Variable
                                    </label>
                                    <div class="flex gap-2">
                                        <input
                                            type="text"
                                            id="widget-variable"
                                            placeholder="z.B. MAIN.bLight1"
                                            class="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                                        >
                                        <button type="button" id="browse-symbol-btn" class="px-3 py-2 bg-gray-200 dark:bg-gray-600 rounded-lg hover:bg-gray-300 dark:hover:bg-gray-500">
                                            <i data-lucide="folder-search" class="w-5 h-5"></i>
                                        </button>
                                    </div>
                                </div>

                                <!-- PLC Type -->
                                <div>
                                    <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                                        PLC Typ
                                    </label>
                                    <select id="widget-plc-type" class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white">
                                        <option value="BOOL">BOOL</option>
                                        <option value="INT">INT</option>
                                        <option value="DINT">DINT</option>
                                        <option value="REAL">REAL</option>
                                        <option value="LREAL">LREAL</option>
                                        <option value="STRING">STRING</option>
                                    </select>
                                </div>

                                <!-- Icon -->
                                <div>
                                    <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                                        Icon (Lucide)
                                    </label>
                                    <input
                                        type="text"
                                        id="widget-icon"
                                        placeholder="z.B. lightbulb, thermometer, battery"
                                        class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                                    >
                                    <div class="text-xs text-gray-500 mt-1">
                                        <a href="https://lucide.dev/icons" target="_blank" class="text-blue-500 hover:underline">
                                            Icon-Liste ansehen
                                        </a>
                                    </div>
                                </div>

                                <!-- Buttons -->
                                <div class="flex justify-end space-x-2 pt-4">
                                    <button type="button" id="cancel-modal-btn" class="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700">
                                        Abbrechen
                                    </button>
                                    <button type="submit" class="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600">
                                        Speichern
                                    </button>
                                </div>
                            </form>
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
        // Create Widget Button
        document.getElementById('create-widget-btn')?.addEventListener('click', () => {
            this.openCreateModal();
        });

        // Cancel Modal
        document.getElementById('cancel-modal-btn')?.addEventListener('click', () => {
            this.closeModal();
        });

        // Form Submit
        document.getElementById('widget-form')?.addEventListener('submit', (e) => {
            e.preventDefault();
            this.saveWidget();
        });

        // Browse Symbol
        document.getElementById('browse-symbol-btn')?.addEventListener('click', () => {
            this.openSymbolBrowser();
        });

        // Filters
        document.getElementById('page-filter')?.addEventListener('change', () => {
            this.applyFilters();
        });

        document.getElementById('type-filter')?.addEventListener('change', () => {
            this.applyFilters();
        });

        document.getElementById('widget-search')?.addEventListener('input', () => {
            this.applyFilters();
        });
    }

    async loadWidgets() {
        try {
            const response = await fetch('/api/widgets');
            const data = await response.json();

            this.widgets = data.widgets || {};
            this.renderWidgetList();
            this.updateStats();

        } catch (error) {
            console.error('Load Widgets Error:', error);
        }
    }

    renderWidgetList() {
        const container = document.getElementById('widget-list');
        if (!container) return;

        const widgets = Object.values(this.widgets);

        if (widgets.length === 0) {
            container.innerHTML = '<div class="text-center py-8 text-gray-500">Keine Widgets vorhanden</div>';
            return;
        }

        container.innerHTML = widgets.map(widget => this.renderWidgetCard(widget)).join('');

        if (typeof lucide !== 'undefined') {
            lucide.createIcons();
        }

        // Attach event listeners to dynamically created buttons
        container.querySelectorAll('.edit-widget-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.openEditModal(btn.dataset.id);
            });
        });

        container.querySelectorAll('.delete-widget-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.deleteWidget(btn.dataset.id);
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

    renderWidgetCard(widget) {
        const bindings = widget.bindings || {};
        const valueBinding = bindings.value || {};

        return `
            <div class="bg-white dark:bg-gray-800 rounded-lg p-4 shadow hover:shadow-md transition-shadow">
                <div class="flex items-start justify-between">
                    <div class="flex items-start space-x-3 flex-1">
                        <div class="w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
                            <i data-lucide="${this.escapeHtml(widget.config?.icon || 'box')}" class="w-5 h-5 text-white"></i>
                        </div>
                        <div class="flex-1">
                            <h3 class="font-semibold text-gray-900 dark:text-white">${this.escapeHtml(widget.title)}</h3>
                            <div class="flex items-center space-x-2 mt-1">
                                <span class="text-xs px-2 py-0.5 rounded bg-gray-200 dark:bg-gray-700">${this.escapeHtml(widget.type)}</span>
                                <span class="text-xs text-gray-500">${this.escapeHtml(widget.page || 'dashboard')}</span>
                            </div>
                            ${valueBinding.variable ? `
                                <div class="mt-2 text-sm text-gray-600 dark:text-gray-400">
                                    <i data-lucide="link" class="inline w-3 h-3"></i>
                                    ${this.escapeHtml(valueBinding.variable)} (${this.escapeHtml(valueBinding.plc_type || 'BOOL')})
                                </div>
                            ` : ''}
                        </div>
                    </div>
                    <div class="flex items-center space-x-2">
                        <button class="edit-widget-btn p-2 text-blue-500 hover:bg-blue-50 dark:hover:bg-blue-900 rounded" data-id="${this.escapeHtml(widget.id)}">
                            <i data-lucide="edit" class="w-4 h-4"></i>
                        </button>
                        <button class="delete-widget-btn p-2 text-red-500 hover:bg-red-50 dark:hover:bg-red-900 rounded" data-id="${this.escapeHtml(widget.id)}">
                            <i data-lucide="trash-2" class="w-4 h-4"></i>
                        </button>
                    </div>
                </div>
            </div>
        `;
    }

    applyFilters() {
        const pageFilter = document.getElementById('page-filter')?.value || '';
        const typeFilter = document.getElementById('type-filter')?.value || '';
        const searchQuery = (document.getElementById('widget-search')?.value || '').toLowerCase();

        const filtered = Object.values(this.widgets).filter(widget => {
            if (pageFilter && widget.page !== pageFilter) return false;
            if (typeFilter && widget.type !== typeFilter) return false;
            if (searchQuery && !widget.title.toLowerCase().includes(searchQuery)) return false;
            return true;
        });

        const container = document.getElementById('widget-list');
        if (container) {
            if (filtered.length === 0) {
                container.innerHTML = '<div class="text-center py-8 text-gray-500">Keine Widgets gefunden</div>';
            } else {
                container.innerHTML = filtered.map(w => this.renderWidgetCard(w)).join('');
            }

            if (typeof lucide !== 'undefined') {
                lucide.createIcons();
            }

            // Reattach event listeners after filtering
            container.querySelectorAll('.edit-widget-btn').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    this.openEditModal(btn.dataset.id);
                });
            });

            container.querySelectorAll('.delete-widget-btn').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    this.deleteWidget(btn.dataset.id);
                });
            });
        }
    }

    updateStats() {
        const totalEl = document.getElementById('total-widgets');
        const typesEl = document.getElementById('widget-types-count');
        const bindingsEl = document.getElementById('total-bindings');

        if (totalEl) totalEl.textContent = Object.keys(this.widgets).length;

        const types = new Set(Object.values(this.widgets).map(w => w.type));
        if (typesEl) typesEl.textContent = types.size;

        let totalBindings = 0;
        Object.values(this.widgets).forEach(w => {
            totalBindings += Object.keys(w.bindings || {}).length;
        });
        if (bindingsEl) bindingsEl.textContent = totalBindings;
    }

    openCreateModal() {
        const modal = document.getElementById('widget-modal');
        const titleEl = document.getElementById('modal-title');

        if (titleEl) titleEl.textContent = 'Neues Widget erstellen';
        document.getElementById('widget-form')?.reset();

        modal?.classList.remove('hidden');
    }

    openEditModal(widgetId) {
        const widget = this.widgets[widgetId];
        if (!widget) return;

        const modal = document.getElementById('widget-modal');
        const titleEl = document.getElementById('modal-title');

        if (titleEl) titleEl.textContent = 'Widget bearbeiten';

        // Fill form
        document.getElementById('widget-type').value = widget.type;
        document.getElementById('widget-title').value = widget.title;
        document.getElementById('widget-page').value = widget.page || 'dashboard';

        const valueBinding = widget.bindings?.value || {};
        document.getElementById('widget-variable').value = valueBinding.variable || '';
        document.getElementById('widget-plc-type').value = valueBinding.plc_type || 'BOOL';
        document.getElementById('widget-icon').value = widget.config?.icon || '';

        if (modal) {
            modal.classList.remove('hidden');
            modal.dataset.editId = widgetId;
        }
    }

    closeModal() {
        const modal = document.getElementById('widget-modal');
        if (!modal) return;
        modal.classList.add('hidden');
        delete modal.dataset.editId;
    }

    async saveWidget() {
        const modal = document.getElementById('widget-modal');
        const editId = modal?.dataset.editId;

        const widgetData = {
            type: document.getElementById('widget-type').value,
            title: document.getElementById('widget-title').value,
            page: document.getElementById('widget-page').value,
            bindings: {
                value: {
                    variable: document.getElementById('widget-variable').value,
                    plc_type: document.getElementById('widget-plc-type').value
                }
            },
            config: {
                icon: document.getElementById('widget-icon').value
            }
        };

        try {
            let response;
            if (editId) {
                // Update
                response = await fetch(`/api/widgets/${editId}`, {
                    method: 'PUT',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(widgetData)
                });
                this.onWidgetUpdated(editId, widgetData);
            } else {
                // Create
                response = await fetch('/api/widgets', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(widgetData)
                });
                this.onWidgetCreated(widgetData);
            }

            if (response.ok) {
                this.closeModal();
                this.loadWidgets();
            } else {
                alert('Fehler beim Speichern');
            }

        } catch (error) {
            console.error('Save Error:', error);
            alert('Fehler beim Speichern');
        }
    }

    async deleteWidget(widgetId) {
        if (!confirm('Widget wirklich löschen?')) return;

        try {
            const response = await fetch(`/api/widgets/${widgetId}`, {
                method: 'DELETE'
            });

            if (response.ok) {
                this.loadWidgets();
                this.onWidgetDeleted(widgetId);
            }

        } catch (error) {
            console.error('Delete Error:', error);
        }
    }

    openSymbolBrowser() {
        // TODO: Integrate with SymbolBrowserV5
        alert('Symbol Browser öffnen (Integration mit SymbolBrowserV5)');
    }
}

window.WidgetManagerV5 = WidgetManagerV5;
