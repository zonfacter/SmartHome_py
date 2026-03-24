(function () {
    const RING_EVENTS_CARD_ID = '__ring_events__';

    const cameraPageUiMethods = {
        async loadCamerasPage() {
            console.log('📹 Lade Kameras...');
            const scope = 'page:cameras';

            await this.loadAndRenderWidgets('cameras');
            this._applyGridLayout();
            this._setupGridLayoutToggle();

            const addCameraBtn = document.getElementById('add-camera-btn');
            if (addCameraBtn) this._bindScopedListener(addCameraBtn, 'click', () => this.addCamera(), { scope, key: 'cameras:add-camera' });

            const diagnoseBtn = document.getElementById('diagnose-btn');
            if (diagnoseBtn) this._bindScopedListener(diagnoseBtn, 'click', () => this._runCameraDiagnose(), { scope, key: 'cameras:diagnose' });

            const scanBtn = document.getElementById('network-scan-btn');
            if (scanBtn) this._bindScopedListener(scanBtn, 'click', () => this._runNetworkScan(), { scope, key: 'cameras:scan' });

            const ringImportBtn = document.getElementById('import-ring-btn');
            if (ringImportBtn) this._bindScopedListener(ringImportBtn, 'click', () => this._openRingImport(), { scope, key: 'cameras:ring-import' });

            const ringAuthBtn = document.getElementById('ring-auth-btn');
            if (ringAuthBtn) this._bindScopedListener(ringAuthBtn, 'click', () => this._ringAuthenticateFromForm(), { scope, key: 'cameras:ring-auth' });

            const ringAuthHelpBtn = document.getElementById('ring-auth-help-btn');
            if (ringAuthHelpBtn) this._bindScopedListener(ringAuthHelpBtn, 'click', () => this.openRingHelpModal(), { scope, key: 'cameras:ring-auth-help' });

            const ringHelpCloseBtn = document.getElementById('ring-help-close-btn');
            if (ringHelpCloseBtn) this._bindScopedListener(ringHelpCloseBtn, 'click', () => this.closeRingHelpModal(), { scope, key: 'cameras:ring-help-close' });

            const ringWebrtcPreferred = document.getElementById('ring-webrtc-preferred');
            if (ringWebrtcPreferred) {
                const stored = localStorage.getItem('ringWebrtcPreferred');
                ringWebrtcPreferred.checked = stored !== '0';
                this._bindScopedListener(ringWebrtcPreferred, 'change', () => {
                    localStorage.setItem('ringWebrtcPreferred', ringWebrtcPreferred.checked ? '1' : '0');
                }, { scope, key: 'cameras:ring-webrtc-preferred' });
            }

            this._refreshRingStatus();
            await this.loadSavedCameras();

            const refreshRingEventsBtn = document.getElementById('refresh-ring-events-btn');
            if (refreshRingEventsBtn) {
                this._bindScopedListener(refreshRingEventsBtn, 'click', () => this.loadRingEvents(), { scope, key: 'cameras:ring-events-refresh' });
            }

            const ringEventsHelpBtn = document.getElementById('ring-events-help-btn');
            if (ringEventsHelpBtn) {
                this._bindScopedListener(ringEventsHelpBtn, 'click', () => this.openRingHelpModal(), { scope, key: 'cameras:ring-events-help' });
            }

            this.loadRingEvents();
        },

        _getScanOptions() {
            const ports = [];
            document.querySelectorAll('.scan-port-cb:checked').forEach(cb => {
                ports.push(parseInt(cb.value));
            });

            const customPorts = document.getElementById('scan-custom-ports')?.value?.trim();
            if (customPorts) {
                customPorts.split(/[,\s]+/).forEach(p => {
                    const num = parseInt(p);
                    if (num > 0 && num <= 65535 && !ports.includes(num)) ports.push(num);
                });
            }

            const user = document.getElementById('scan-user')?.value?.trim() || 'admin';
            const password = document.getElementById('scan-password')?.value?.trim() || 'admin';
            return { ports, user, password };
        },

        _getCameraGridOrder() {
            try {
                const raw = localStorage.getItem('cameraGridOrder');
                const parsed = raw ? JSON.parse(raw) : [];
                return Array.isArray(parsed) ? parsed.filter(id => typeof id === 'string' && id) : [];
            } catch (e) {
                return [];
            }
        },

        _setCameraGridOrder(order) {
            if (!Array.isArray(order)) return;
            localStorage.setItem('cameraGridOrder', JSON.stringify(order.filter(id => typeof id === 'string' && id)));
        },

        _sortCameraGridIds(camIds) {
            const preferred = this._getCameraGridOrder();
            const available = [RING_EVENTS_CARD_ID, ...camIds];
            const known = preferred.filter(id => available.includes(id));
            const rest = available.filter(id => !known.includes(id));
            return [...known, ...rest];
        },

        _setupCameraGridDragAndDrop() {
            const grid = document.getElementById('cameras-grid');
            if (!grid) return;

            let draggingId = null;

            const persistOrder = () => {
                const order = Array.from(grid.querySelectorAll('.camera-card[data-card-id]'))
                    .map(card => card.getAttribute('data-card-id'))
                    .filter(Boolean);
                this._setCameraGridOrder(order);
            };

            grid.querySelectorAll('.camera-card[data-card-id]').forEach(card => {
                const cardId = card.getAttribute('data-card-id');
                card.setAttribute('draggable', 'true');

                card.addEventListener('dragstart', (e) => {
                    draggingId = cardId;
                    card.classList.add('opacity-60', 'scale-[0.98]');
                    if (e.dataTransfer) {
                        e.dataTransfer.effectAllowed = 'move';
                        e.dataTransfer.setData('text/plain', cardId);
                    }
                });

                card.addEventListener('dragend', () => {
                    draggingId = null;
                    card.classList.remove('opacity-60', 'scale-[0.98]');
                    grid.querySelectorAll('.camera-card').forEach(item => {
                        item.classList.remove('ring-2', 'ring-blue-400', 'ring-offset-2', 'dark:ring-offset-gray-900');
                    });
                });

                card.addEventListener('dragover', (e) => {
                    if (!draggingId || draggingId === cardId) return;
                    e.preventDefault();
                    card.classList.add('ring-2', 'ring-blue-400', 'ring-offset-2', 'dark:ring-offset-gray-900');
                });

                card.addEventListener('dragleave', () => {
                    card.classList.remove('ring-2', 'ring-blue-400', 'ring-offset-2', 'dark:ring-offset-gray-900');
                });

                card.addEventListener('drop', (e) => {
                    if (!draggingId || draggingId === cardId) return;
                    e.preventDefault();
                    const dragged = grid.querySelector(`.camera-card[data-card-id="${draggingId}"]`);
                    if (!dragged || dragged === card) return;

                    const rect = card.getBoundingClientRect();
                    const before = e.clientY < rect.top + rect.height / 2;
                    card.parentNode.insertBefore(dragged, before ? card : card.nextSibling);
                    persistOrder();
                    card.classList.remove('ring-2', 'ring-blue-400', 'ring-offset-2', 'dark:ring-offset-gray-900');
                });
            });
        },

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
                        const portsLabel = (dev.ports || []).map(p => `<span class="px-1.5 py-0.5 rounded text-xs bg-gray-200 dark:bg-gray-600 text-gray-700 dark:text-gray-300">${p}</span>`).join(' ');

                        html += `
                            <div class="theme-subpanel flex items-center justify-between p-2 rounded-xl">
                                <div class="flex items-center space-x-3">
                                    <span class="font-mono text-sm font-semibold text-gray-900 dark:text-white">${dev.host}</span>
                                    <span class="px-1.5 py-0.5 rounded text-xs ${typeColor}">${typeLabel}</span>
                                    ${discoveryBadge}
                                    <span class="text-xs text-gray-500">${dev.name || ''}</span>
                                </div>
                                <div class="flex items-center space-x-2">
                                    <span class="text-xs text-gray-400">Ports: ${portsLabel}</span>
                                    <button class="scan-diagnose-btn theme-accent-button px-3 py-1 text-xs rounded" data-host="${dev.host}">Diagnose</button>
                                </div>
                            </div>`;
                    });
                    html += '</div>';
                }

                resultPanel.innerHTML = html;

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
        },

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

                let html = '';
                html += `<div class="mb-3"><span class="font-semibold text-gray-900 dark:text-white">Offene Ports:</span> `;
                if (data.ports && data.ports.length > 0) {
                    html += data.ports.map(p => `<span class="inline-block px-2 py-0.5 bg-green-100 text-green-800 dark:bg-green-800 dark:text-green-100 rounded text-xs mr-1">${p}</span>`).join('');
                } else {
                    html += '<span class="text-gray-500">Keine gefunden</span>';
                }
                html += '</div>';

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

                html += '<div class="mb-3"><span class="font-semibold text-gray-900 dark:text-white">Snapshot:</span> ';
                if (data.snapshot) {
                    html += `<span class="text-green-600 dark:text-green-400 font-mono text-xs">${data.snapshot.url}</span>`;
                } else {
                    html += '<span class="text-gray-500">Nicht gefunden</span>';
                }
                html += '</div>';

                if (data.streams && data.streams.length > 0) {
                    const mainstream = data.streams.find(s => s.stream_type === 'mainstream');
                    const substream = data.streams.find(s => s.stream_type === 'substream');
                    const mainUrl = mainstream ? mainstream.url : (data.streams[0] ? data.streams[0].url : '');
                    const subUrl = substream ? substream.url : '';

                    html += `<button id="diagnose-apply-btn" class="theme-accent-button mt-2 px-4 py-2 text-sm rounded-lg"
                        data-main-url="${mainUrl}"
                        data-sub-url="${subUrl}"
                        data-onvif-port="${data.onvif ? data.onvif.port : ''}"
                        data-host="${ip}">
                        Uebernehmen
                    </button>`;
                }

                resultPanel.innerHTML = html;

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
        },

        async addCamera() {
            const nameInput = document.getElementById('camera-name');
            const urlInput = document.getElementById('camera-rtsp-url');

            const name = nameInput?.value?.trim();
            const streamUrl = urlInput?.value?.trim();

            if (!name || !streamUrl) {
                alert('Bitte Name und Stream-URL eingeben!');
                return;
            }

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

            if (nameInput) nameInput.value = '';
            if (urlInput) urlInput.value = '';
            this.loadSavedCameras();
        },

        async loadSavedCameras() {
            const cameraListContainer = document.getElementById('camera-list');
            const camerasGridContainer = document.getElementById('cameras-grid');
            if (!cameraListContainer || !camerasGridContainer) return;

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
            console.log(`Kameras geladen: ${camIds.length}`, camIds);
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
                    <div class="theme-subpanel p-3 rounded-xl" id="cam-entry-${camId}">
                        <div class="cam-display flex items-center justify-between">
                            <div class="flex items-center space-x-3 min-w-0">
                                <i data-lucide="video" class="widget-accent-text w-5 h-5 flex-shrink-0"></i>
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
                                <button class="theme-outline-button px-3 py-1 text-sm rounded edit-camera-btn"
                                        data-camera-id="${camId}">
                                    <i data-lucide="pencil" class="w-4 h-4 inline"></i>
                                </button>
                                <button class="theme-outline-button px-3 py-1 text-sm rounded text-red-600 dark:text-red-400 remove-camera-btn"
                                        data-camera-id="${camId}">
                                    <i data-lucide="trash-2" class="w-4 h-4 inline"></i>
                                </button>
                            </div>
                        </div>
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
                                <button class="save-camera-btn theme-accent-button px-4 py-1.5 text-sm rounded" data-camera-id="${camId}">Speichern</button>
                                <button class="cancel-edit-btn theme-outline-button px-4 py-1.5 text-sm rounded" data-camera-id="${camId}">Abbrechen</button>
                            </div>
                        </div>
                    </div>
                `;
            });
            listHtml += '</div>';
            cameraListContainer.innerHTML = listHtml;

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

            const orderedIds = this._sortCameraGridIds(camIds);
            let gridHtml = '';
            orderedIds.forEach(cardId => {
                if (cardId === RING_EVENTS_CARD_ID) {
                    gridHtml += `
                <div class="camera-card theme-panel rounded-2xl p-4 transition-transform transition-shadow duration-200 hover:-translate-y-0.5 hover:shadow-lg" data-cam-type="ring-events" data-card-id="${RING_EVENTS_CARD_ID}">
                    <div class="flex items-start justify-between gap-3 mb-3">
                        <div>
                            <div class="flex items-center gap-2">
                                <button class="camera-card-drag-handle theme-subpanel p-1.5 rounded-full text-gray-500 cursor-grab" title="Kachel verschieben">
                                    <i data-lucide="grip" class="w-4 h-4"></i>
                                </button>
                                <h3 class="font-semibold text-gray-900 dark:text-white">Ring Ereignisse</h3>
                                <span id="ring-events-health-badge" class="inline-flex items-center rounded-full bg-slate-100 px-2 py-0.5 text-[11px] font-medium text-slate-700 dark:bg-slate-700 dark:text-slate-200">Prüfung…</span>
                            </div>
                            <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">Klingeln, Bewegung und weitere API-Historie</p>
                        </div>
                        <div class="flex items-center gap-2">
                            <button id="ring-events-help-btn" type="button" class="theme-outline-button px-2.5 py-1.5 text-xs rounded inline-flex items-center gap-1" title="Hinweise zu Ring-Diagnose">
                                <span class="inline-flex h-4 w-4 items-center justify-center rounded-full border border-current text-[10px] font-bold">i</span>
                                <span>Hilfe</span>
                            </button>
                            <button id="refresh-ring-events-btn" class="theme-accent-button px-3 py-1.5 text-xs rounded">
                                Aktualisieren
                            </button>
                        </div>
                    </div>
                    <div id="ring-events-status" class="text-xs text-gray-500 dark:text-gray-400 mb-3">Ereignisse werden geladen...</div>
                    <div id="ring-events-guidance" class="hidden mb-3"></div>
                    <div id="ring-events-panel" class="theme-subpanel rounded-xl overflow-hidden">
                        <div class="p-4 text-sm text-gray-500 dark:text-gray-400">
                            Noch keine Ring-Ereignisse geladen.
                        </div>
                    </div>
                </div>
            `;
                    return;
                }

                const camId = cardId;
                const cam = cameras[camId];
                const streamType = (cam.type || 'rtsp').toLowerCase();

                if (streamType === 'mjpeg') {
                    gridHtml += `
                        <div class="camera-card theme-panel rounded-2xl p-4 transition-transform transition-shadow duration-200 hover:-translate-y-0.5 hover:shadow-lg" data-cam-id="${camId}" data-cam-name="${cam.name}" data-cam-type="mjpeg" data-card-id="${camId}">
                            <div class="flex items-center gap-2 mb-2">
                                <button class="camera-card-drag-handle theme-subpanel p-1.5 rounded-full text-gray-500 cursor-grab" title="Kachel verschieben">
                                    <i data-lucide="grip" class="w-4 h-4"></i>
                                </button>
                                <h3 class="font-semibold text-gray-900 dark:text-white">${cam.name}</h3>
                            </div>
                            <div class="aspect-video bg-gray-900 rounded-xl overflow-hidden relative ring-1 ring-black/5">
                                <img id="cam-image-${camId}" src="${cam.url}" alt="${cam.name}" class="w-full h-full object-cover"
                                     onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';">
                                <div class="w-full h-full flex items-center justify-center text-white bg-gray-900" style="display:none;">
                                    <div class="text-center">
                                        <i data-lucide="alert-circle" class="w-12 h-12 mx-auto mb-2 text-red-500"></i>
                                        <p class="text-sm">Stream nicht erreichbar</p>
                                    </div>
                                </div>
                            </div>
                            <div class="flex items-center space-x-2 mt-2">
                                <button class="cam-fullscreen-btn theme-outline-button px-3 py-1.5 text-xs rounded flex items-center space-x-1"
                                        data-cam-id="${camId}" data-cam-name="${cam.name}" data-cam-type="mjpeg">
                                    <i data-lucide="maximize-2" class="w-3.5 h-3.5"></i><span>Vollbild</span>
                                </button>
                                <button class="cam-ptz-toggle-btn theme-accent-button px-3 py-1.5 text-xs rounded flex items-center space-x-1"
                                        data-cam-id="${camId}" style="display:none;">
                                    <i data-lucide="move" class="w-3.5 h-3.5"></i><span>PTZ</span>
                                </button>
                                <span class="text-xs px-2 py-0.5 rounded bg-green-100 text-green-800">MJPEG</span>
                            </div>
                            <div id="widget-ptz-${camId}" class="widget-ptz-panel theme-subpanel hidden mt-2 p-2 rounded-lg select-none"></div>
                        </div>
                    `;
                } else if (streamType === 'ring') {
                    gridHtml += `
                        <div class="camera-card theme-panel rounded-2xl p-4 transition-transform transition-shadow duration-200 hover:-translate-y-0.5 hover:shadow-lg" data-cam-id="${camId}" data-cam-name="${cam.name}" data-cam-type="ring" data-card-id="${camId}">
                            <div class="flex items-center gap-2 mb-2">
                                <button class="camera-card-drag-handle theme-subpanel p-1.5 rounded-full text-gray-500 cursor-grab" title="Kachel verschieben">
                                    <i data-lucide="grip" class="w-4 h-4"></i>
                                </button>
                                <h3 class="font-semibold text-gray-900 dark:text-white">${cam.name}</h3>
                            </div>
                            <div class="aspect-video bg-gray-900 rounded-xl overflow-hidden relative ring-1 ring-black/5">
                                <video id="ring-video-${camId}" class="w-full h-full object-cover" muted autoplay playsinline style="display:none;"></video>
                                <img id="cam-image-${camId}" src="" alt="${cam.name}" class="w-full h-full object-cover">
                                <div id="ring-snapshot-ts-${camId}" class="absolute bottom-2 right-2 text-[11px] text-white bg-black/70 px-2 py-1 rounded pointer-events-none z-10 hidden">
                                    Snapshot: -
                                </div>
                                <div id="ring-loading-${camId}" class="absolute inset-0 flex items-center justify-center text-white bg-gray-900 bg-opacity-60">
                                    <div class="text-center">
                                        <i data-lucide="loader" class="w-8 h-8 mx-auto mb-2 animate-spin"></i>
                                        <p class="text-sm">Ring Stream wird geladen...</p>
                                    </div>
                                </div>
                            </div>
                            <div class="flex items-center space-x-2 mt-2">
                                <button class="cam-fullscreen-btn theme-outline-button px-3 py-1.5 text-xs rounded flex items-center space-x-1"
                                        data-cam-id="${camId}" data-cam-name="${cam.name}" data-cam-type="ring">
                                    <i data-lucide="maximize-2" class="w-3.5 h-3.5"></i><span>Vollbild</span>
                                </button>
                                <button class="ring-widget-mode-btn theme-accent-button px-3 py-1.5 text-xs rounded flex items-center space-x-1"
                                        data-cam-id="${camId}" data-mode="snapshot">
                                    <i data-lucide="refresh-cw" class="w-3.5 h-3.5"></i><span id="ring-mode-label-${camId}">Snapshot</span>
                                </button>
                                <span class="text-xs px-2 py-0.5 rounded bg-orange-100 text-orange-800">RING</span>
                            </div>
                            <div id="ring-live-note-${camId}" class="mt-2 hidden text-[11px] text-amber-600 dark:text-amber-300"></div>
                            <div id="widget-ptz-${camId}" class="widget-ptz-panel theme-subpanel hidden mt-2 p-2 rounded-lg select-none"></div>
                        </div>
                    `;
                } else {
                    gridHtml += `
                        <div class="camera-card theme-panel rounded-2xl p-4 transition-transform transition-shadow duration-200 hover:-translate-y-0.5 hover:shadow-lg" data-cam-id="${camId}" data-cam-name="${cam.name}" data-cam-type="rtsp" data-card-id="${camId}">
                            <div class="flex items-center gap-2 mb-2">
                                <button class="camera-card-drag-handle theme-subpanel p-1.5 rounded-full text-gray-500 cursor-grab" title="Kachel verschieben">
                                    <i data-lucide="grip" class="w-4 h-4"></i>
                                </button>
                                <h3 class="font-semibold text-gray-900 dark:text-white">${cam.name}</h3>
                            </div>
                            <div class="aspect-video bg-gray-900 rounded-xl overflow-hidden relative ring-1 ring-black/5">
                                <img id="cam-image-${camId}" src="" alt="${cam.name}" class="w-full h-full object-cover">
                                <video id="hls-video-${camId}" class="w-full h-full object-cover" muted autoplay playsinline style="display:none;"></video>
                                <div id="hls-loading-${camId}" class="absolute inset-0 flex items-center justify-center text-white bg-gray-900">
                                    <div class="text-center">
                                        <i data-lucide="loader" class="w-8 h-8 mx-auto mb-2 animate-spin"></i>
                                        <p class="text-sm">Stream wird geladen...</p>
                                    </div>
                                </div>
                            </div>
                            <div class="flex items-center space-x-2 mt-2">
                                <button class="cam-fullscreen-btn theme-outline-button px-3 py-1.5 text-xs rounded flex items-center space-x-1"
                                        data-cam-id="${camId}" data-cam-name="${cam.name}" data-cam-type="rtsp">
                                    <i data-lucide="maximize-2" class="w-3.5 h-3.5"></i><span>Vollbild</span>
                                </button>
                                <button class="cam-ptz-toggle-btn theme-accent-button px-3 py-1.5 text-xs rounded flex items-center space-x-1"
                                        data-cam-id="${camId}" style="display:none;">
                                    <i data-lucide="move" class="w-3.5 h-3.5"></i><span>PTZ</span>
                                </button>
                                <span class="text-xs px-2 py-0.5 rounded bg-blue-100 text-blue-800">HLS</span>
                            </div>
                            <div id="widget-ptz-${camId}" class="widget-ptz-panel theme-subpanel hidden mt-2 p-2 rounded-lg select-none"></div>
                        </div>
                    `;
                }
            });
            camerasGridContainer.innerHTML = gridHtml;

            if (typeof lucide !== 'undefined') {
                lucide.createIcons();
            }

            this._setupCameraGridDragAndDrop();

            rtspCams.forEach(camId => {
                this._loadRtspSnapshot(camId, `cam-image-${camId}`, 4500);
                this._startRtspSnapshotRefresh(camId, `cam-image-${camId}`, 3500);
            });

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

            document.querySelectorAll('.remove-camera-btn').forEach(btn => {
                btn.addEventListener('click', () => {
                    const cameraId = btn.getAttribute('data-camera-id');
                    if (confirm(`Kamera "${cameras[cameraId]?.name || cameraId}" wirklich loeschen?`)) {
                        this.removeCamera(cameraId);
                    }
                });
            });

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

            document.querySelectorAll('.cam-fullscreen-btn').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    const camId = btn.getAttribute('data-cam-id');
                    const camName = btn.getAttribute('data-cam-name');
                    const camType = btn.getAttribute('data-cam-type');
                    this.openCameraFullscreen(camId, camName, camType);
                });
            });

            camIds.forEach(camId => {
                this._checkWidgetPTZ(camId);
            });

            document.querySelectorAll('.cam-ptz-toggle-btn').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    const camId = btn.getAttribute('data-cam-id');
                    this._toggleWidgetPTZ(camId);
                });
            });
        },

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
                this.loadSavedCameras();
            } catch (e) {
                console.error('Fehler beim Speichern:', e);
                alert('Server nicht erreichbar');
            }
        },

        async removeCamera(cameraId) {
            try {
                await fetch(`/api/cameras/${cameraId}`, { method: 'DELETE' });
                console.log(`Kamera entfernt: ${cameraId}`);
            } catch (e) {
                console.error('Fehler beim Entfernen der Kamera:', e);
            }
            this.loadSavedCameras();
        }
    };

    window.extendSmartHomeAppWithCameraPageUI = function (SmartHomeApp) {
        Object.assign(SmartHomeApp.prototype, cameraPageUiMethods);
    };
})();
