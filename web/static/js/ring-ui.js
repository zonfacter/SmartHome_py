(function () {
    const ringUiMethods = {
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
        },

        _clearRingEventsRefreshTimer() {
            if (this._ringEventsRefreshTimer) {
                clearTimeout(this._ringEventsRefreshTimer);
                this._ringEventsRefreshTimer = null;
            }
        },

        _scheduleRingEventsRefresh(delayMs = 30000) {
            this._clearRingEventsRefreshTimer();
            if (this.currentPage !== 'cameras') return;
            this._ringEventsRefreshTimer = setTimeout(() => {
                this.loadRingEvents().catch((error) => {
                    console.error('Fehler beim Aktualisieren der Ring-Ereignisse:', error);
                });
            }, Math.max(5000, Number(delayMs) || 30000));
        },

        _formatRingEventTimestamp(event) {
            const epochSeconds = Number(event?.ding_ts || 0);
            if (Number.isFinite(epochSeconds) && epochSeconds > 0) {
                try {
                    return new Date(epochSeconds * 1000).toLocaleString('de-DE');
                } catch (e) {}
            }
            if (event?.created_at) {
                try {
                    return new Date(event.created_at).toLocaleString('de-DE');
                } catch (e) {}
            }
            return event?.created_at_local || '-';
        },

        _renderRingEvents(events) {
            const panel = document.getElementById('ring-events-panel');
            if (!panel) return;

            const items = Array.isArray(events) ? events : [];
            if (items.length === 0) {
                panel.innerHTML = `
                    <div class="p-4 text-sm text-gray-500 dark:text-gray-400 bg-gray-50 dark:bg-gray-700">
                        Keine Ring-Ereignisse gefunden.
                    </div>
                `;
                return;
            }

            panel.innerHTML = `
                <div class="overflow-x-auto">
                    <table class="min-w-full text-sm">
                        <thead class="bg-gray-50 dark:bg-gray-700/60 text-gray-600 dark:text-gray-300">
                            <tr>
                                <th class="px-4 py-3 text-left font-semibold">Zeit</th>
                                <th class="px-4 py-3 text-left font-semibold">Kamera</th>
                                <th class="px-4 py-3 text-left font-semibold">Trigger</th>
                                <th class="px-4 py-3 text-left font-semibold">Event-ID</th>
                            </tr>
                        </thead>
                        <tbody class="divide-y divide-gray-200 dark:divide-gray-700 bg-white dark:bg-gray-800">
                            ${items.map((event) => {
                                const trigger = this.escapeHtml(event.trigger || event.kind || 'unknown');
                                const timeLabel = this.escapeHtml(this._formatRingEventTimestamp(event));
                                const cameraName = this.escapeHtml(event.camera_name || event.cam_id || '-');
                                const eventId = this.escapeHtml(event.id || '-');
                                return `
                                    <tr>
                                        <td class="px-4 py-3 whitespace-nowrap text-gray-900 dark:text-gray-100">${timeLabel}</td>
                                        <td class="px-4 py-3 text-gray-700 dark:text-gray-200">${cameraName}</td>
                                        <td class="px-4 py-3">
                                            <span class="inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium bg-orange-100 text-orange-800 dark:bg-orange-900/40 dark:text-orange-200">${trigger}</span>
                                        </td>
                                        <td class="px-4 py-3 font-mono text-xs text-gray-500 dark:text-gray-400">${eventId}</td>
                                    </tr>
                                `;
                            }).join('')}
                        </tbody>
                    </table>
                </div>
            `;
        },

        async loadRingEvents() {
            const panel = document.getElementById('ring-events-panel');
            const statusEl = document.getElementById('ring-events-status');
            if (!panel || !statusEl) return;

            statusEl.textContent = 'Ring-Ereignisse werden geladen...';

            try {
                const response = await fetch('/api/ring/events?limit=25');
                const payload = await response.json();
                if (!response.ok || !payload.success) {
                    throw new Error(payload.error || 'Ring-Ereignisse konnten nicht geladen werden');
                }

                const events = Array.isArray(payload.events) ? payload.events : [];
                this._renderRingEvents(events);
                statusEl.textContent = `${events.length} Ereignisse geladen`;
            } catch (error) {
                panel.innerHTML = `
                    <div class="p-4 text-sm text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-950/20">
                        Fehler beim Laden der Ring-Ereignisse: ${this.escapeHtml(error.message || String(error))}
                    </div>
                `;
                statusEl.textContent = 'Ring-Ereignisse konnten nicht geladen werden';
            } finally {
                this._scheduleRingEventsRefresh(30000);
            }
        },

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

            const otpInput = document.getElementById('ring-otp');
            if (otpInput) otpInput.value = '';

            await this._refreshRingStatus();
            await this.loadRingEvents();
            return true;
        },

        async _ringEnsureAuthenticated() {
            const status = await this._refreshRingStatus();
            if (!status.available) {
                alert('Ring-Integration ist nicht verfügbar. Bitte ring_doorbell installieren.');
                return false;
            }
            if (status.configured) return true;

            return await this._ringAuthenticateFromForm();
        },

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
                await this.loadRingEvents();
            } catch (e) {
                panel.innerHTML = `<p class=\"text-red-500\">Fehler: ${e.message}</p>`;
            }
        },

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
        },

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
    };

    window.extendSmartHomeAppWithRingUI = function (SmartHomeApp) {
        Object.assign(SmartHomeApp.prototype, ringUiMethods);
    };
})();
