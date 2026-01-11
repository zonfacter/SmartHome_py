# Multi-PLC Management API

## Backend-Integration in web_manager.py

### 1. Initialisierung (in `initialize()` Methode einfügen):

```python
# PLC Config Manager initialisieren
from modules.gateway.plc_config_manager import PLCConfigManager

config_mgr = self.app_context.module_manager.get_module('config_manager')
if config_mgr:
    plc_data_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        'plc_data'
    )
    self.plc_config_manager = PLCConfigManager(
        config_dir=config_mgr.config_dir,
        plc_data_dir=plc_data_dir
    )
    print(f"  ✓ PLC Config Manager initialisiert")
```

### 2. API-Endpoints (in `_setup_routes()` einfügen):

```python
# ====================================================================
# MULTI-PLC MANAGEMENT API
# ====================================================================

@self.app.route('/api/admin/plcs')
def get_all_plcs():
    """Alle PLC-Konfigurationen"""
    if not self.plc_config_manager:
        return jsonify({'error': 'PLC Config Manager nicht verfügbar'}), 503

    plcs = self.plc_config_manager.get_all_plcs()
    stats = self.plc_config_manager.get_statistics()

    return jsonify({
        'plcs': plcs,
        'statistics': stats,
        'active_plc': self.plc_config_manager.configs['active_plc']
    })

@self.app.route('/api/admin/plcs/<plc_id>')
def get_plc(plc_id):
    """Einzelne PLC-Konfiguration"""
    if not self.plc_config_manager:
        return jsonify({'error': 'PLC Config Manager nicht verfügbar'}), 503

    plc = self.plc_config_manager.get_plc(plc_id)
    if not plc:
        return jsonify({'error': 'PLC nicht gefunden'}), 404

    return jsonify(plc)

@self.app.route('/api/admin/plcs', methods=['POST'])
def create_plc():
    """Neue PLC-Konfiguration erstellen"""
    if not self.plc_config_manager:
        return jsonify({'error': 'PLC Config Manager nicht verfügbar'}), 503

    data = request.json
    required = ['name', 'ams_net_id']

    for field in required:
        if field not in data:
            return jsonify({'error': f'Feld {field} erforderlich'}), 400

    plc_id = self.plc_config_manager.add_plc(
        name=data['name'],
        ams_net_id=data['ams_net_id'],
        ams_port=data.get('ams_port', 851),
        ip_address=data.get('ip_address'),
        description=data.get('description', '')
    )

    return jsonify({
        'success': True,
        'plc_id': plc_id,
        'plc': self.plc_config_manager.get_plc(plc_id)
    })

@self.app.route('/api/admin/plcs/<plc_id>', methods=['PUT'])
def update_plc(plc_id):
    """PLC-Konfiguration aktualisieren"""
    if not self.plc_config_manager:
        return jsonify({'error': 'PLC Config Manager nicht verfügbar'}), 503

    data = request.json
    success = self.plc_config_manager.update_plc(plc_id, **data)

    if success:
        return jsonify({
            'success': True,
            'plc': self.plc_config_manager.get_plc(plc_id)
        })
    else:
        return jsonify({'error': 'PLC nicht gefunden'}), 404

@self.app.route('/api/admin/plcs/<plc_id>', methods=['DELETE'])
def delete_plc(plc_id):
    """PLC-Konfiguration löschen"""
    if not self.plc_config_manager:
        return jsonify({'error': 'PLC Config Manager nicht verfügbar'}), 503

    delete_tpy = request.args.get('delete_tpy', 'false').lower() == 'true'
    success = self.plc_config_manager.delete_plc(plc_id, delete_tpy=delete_tpy)

    if success:
        return jsonify({'success': True})
    else:
        return jsonify({'error': 'PLC nicht gefunden'}), 404

@self.app.route('/api/admin/plcs/<plc_id>/set-active', methods=['POST'])
def set_active_plc(plc_id):
    """Aktive PLC setzen"""
    if not self.plc_config_manager:
        return jsonify({'error': 'PLC Config Manager nicht verfügbar'}), 503

    success = self.plc_config_manager.set_active_plc(plc_id)

    if success:
        return jsonify({'success': True, 'active_plc': plc_id})
    else:
        return jsonify({'error': 'PLC nicht gefunden'}), 404

@self.app.route('/api/admin/plcs/<plc_id>/upload-tpy', methods=['POST'])
def upload_plc_tpy(plc_id):
    """TPY-Datei für PLC hochladen"""
    if not self.plc_config_manager:
        return jsonify({'error': 'PLC Config Manager nicht verfügbar'}), 503

    if 'file' not in request.files:
        return jsonify({'error': 'Keine Datei'}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({'error': 'Kein Dateiname'}), 400

    if not file.filename.endswith('.tpy'):
        return jsonify({'error': 'Nur .tpy Dateien'}), 400

    # Upload
    file_data = file.read()
    success = self.plc_config_manager.upload_tpy(plc_id, file_data, file.filename)

    if success:
        # Invalidiere Parser-Cache für diese PLC
        self.symbol_parser = None

        return jsonify({
            'success': True,
            'filename': f"{plc_id}_{file.filename}",
            'size': len(file_data)
        })
    else:
        return jsonify({'error': 'Upload fehlgeschlagen'}), 500

@self.app.route('/api/admin/plcs/cleanup-tpy', methods=['POST'])
def cleanup_unused_tpy():
    """Unbenutzte TPY-Dateien löschen"""
    if not self.plc_config_manager:
        return jsonify({'error': 'PLC Config Manager nicht verfügbar'}), 503

    deleted_files = self.plc_config_manager.cleanup_unused_tpy_files()

    return jsonify({
        'success': True,
        'deleted_files': deleted_files,
        'count': len(deleted_files)
    })
```

### 3. Symbole-API anpassen (aktive PLC verwenden):

Ersetze in `get_plc_symbols()` die TPY-Auswahl durch:

```python
# Verwende aktive PLC's TPY-Datei
if self.plc_config_manager:
    tpy_file = self.plc_config_manager.get_tpy_path(
        self.plc_config_manager.configs['active_plc']
    )
else:
    # Fallback
    tpy_file = os.path.join(project_root, 'plc_data', 'TwinCAT_Project.tpy')
```

## Frontend-Integration

### Admin-Seite HTML (index.html hinzufügen):

```html
<!-- Admin Page (nach Setup-Page einfügen) -->
<div id="admin-page" class="page page-container p-6">
    <h1 class="text-2xl font-bold text-gray-900 dark:text-white mb-6">Admin-Bereich</h1>

    <!-- PLC-Verwaltung -->
    <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-6 mb-6">
        <div class="flex items-center justify-between mb-4">
            <h2 class="text-lg font-semibold text-gray-900 dark:text-white">PLC-Verwaltung</h2>
            <button id="add-plc-btn" class="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600">
                <i data-lucide="plus" class="w-4 h-4 inline mr-1"></i> Neue PLC
            </button>
        </div>

        <!-- Statistiken -->
        <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
            <div class="p-4 bg-gray-50 dark:bg-gray-900 rounded-lg">
                <div class="text-sm text-gray-600 dark:text-gray-400">Gesamt PLCs</div>
                <div id="stat-total-plcs" class="text-2xl font-bold">0</div>
            </div>
            <div class="p-4 bg-gray-50 dark:bg-gray-900 rounded-lg">
                <div class="text-sm text-gray-600 dark:text-gray-400">Aktive PLCs</div>
                <div id="stat-active-plcs" class="text-2xl font-bold">0</div>
            </div>
            <div class="p-4 bg-gray-50 dark:bg-gray-900 rounded-lg">
                <div class="text-sm text-gray-600 dark:text-gray-400">Mit TPY</div>
                <div id="stat-plcs-with-tpy" class="text-2xl font-bold">0</div>
            </div>
            <div class="p-4 bg-gray-50 dark:bg-gray-900 rounded-lg">
                <div class="text-sm text-gray-600 dark:text-gray-400">TPY-Größe</div>
                <div id="stat-tpy-size" class="text-2xl font-bold">0 MB</div>
            </div>
        </div>

        <!-- PLC-Liste -->
        <div id="plc-list" class="space-y-3">
            <!-- Wird dynamisch gefüllt -->
        </div>

        <!-- Cleanup-Button -->
        <div class="mt-6 pt-6 border-t border-gray-200 dark:border-gray-700">
            <button id="cleanup-tpy-btn" class="px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600">
                <i data-lucide="trash-2" class="w-4 h-4 inline mr-1"></i> Ungenutzte TPY-Dateien löschen
            </button>
        </div>
    </div>
</div>
```

### JavaScript (app.js ergänzen):

```javascript
// In loadAdminPage():
async loadAdminPage() {
    console.log('👑 Lade Admin...');

    await this.loadPLCConfigs();
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
        container.innerHTML = '<p class="text-gray-500">Keine PLCs konfiguriert</p>';
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
                        <h3 class="text-lg font-semibold">${plc.name}</h3>
                        ${isActive ? '<span class="px-2 py-1 text-xs bg-blue-500 text-white rounded">Aktiv</span>' : ''}
                        ${plc.tpy_file ? '<i data-lucide="file-check" class="w-4 h-4 text-green-500"></i>' : ''}
                    </div>
                    <div class="text-sm space-y-1">
                        <div><span class="text-gray-600 dark:text-gray-400">AMS NetID:</span> ${plc.ams_net_id}</div>
                        <div><span class="text-gray-600 dark:text-gray-400">Port:</span> ${plc.ams_port}</div>
                        ${plc.description ? `<div class="text-gray-500">${plc.description}</div>` : ''}
                        ${plc.tpy_file ? `<div class="text-xs text-gray-500">TPY: ${plc.tpy_file}</div>` : ''}
                    </div>
                </div>
                <div class="flex items-center space-x-2">
                    ${!isActive ? `<button onclick="app.setActivePLC('${plc_id}')" class="p-2 text-blue-600 hover:bg-blue-100 dark:hover:bg-blue-900/30 rounded">
                        <i data-lucide="check-circle" class="w-4 h-4"></i>
                    </button>` : ''}
                    <button onclick="app.uploadTPYForPLC('${plc_id}')" class="p-2 text-green-600 hover:bg-green-100 dark:hover:bg-green-900/30 rounded">
                        <i data-lucide="upload" class="w-4 h-4"></i>
                    </button>
                    <button onclick="app.deletePLC('${plc_id}')" class="p-2 text-red-600 hover:bg-red-100 dark:hover:bg-red-900/30 rounded">
                        <i data-lucide="trash-2" class="w-4 h-4"></i>
                    </button>
                </div>
            </div>
        `;

        container.appendChild(card);
    }

    lucide.createIcons();
}

async setActivePLC(plc_id) {
    const response = await fetch(`/api/admin/plcs/${plc_id}/set-active`, { method: 'POST' });
    if (response.ok) {
        this.loadPLCConfigs();
    }
}

async deletePLC(plc_id) {
    if (!confirm('PLC-Konfiguration wirklich löschen?')) return;

    const deleteTpy = confirm('Auch zugehörige TPY-Datei löschen?');
    const response = await fetch(`/api/admin/plcs/${plc_id}?delete_tpy=${deleteTpy}`, { method: 'DELETE' });

    if (response.ok) {
        this.loadPLCConfigs();
    }
}
```

## Navigation erweitern

Füge in der Sidebar hinzu:

```html
<a href="#" data-page="admin" class="nav-link flex items-center space-x-3 px-4 py-3 rounded-lg">
    <i data-lucide="shield" class="w-5 h-5"></i>
    <span>Admin</span>
</a>
```

## Nächste Schritte

1. Backend-Code aus dieser Datei in `web_manager.py` einfügen
2. Frontend-HTML in `index.html` einfügen
3. Frontend-JS in `app.js` einfügen
4. Server neu starten
5. Admin-Seite testen
