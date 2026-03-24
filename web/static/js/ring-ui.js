(function () {
    const RING_HELP_LINKS = {
        login_url: 'https://account.ring.com/account/login',
        help_url: 'https://support.help.ring.com/',
    };

    const ringUiMethods = {
        _getRingHelpLinks(source = null) {
            const candidate = source && typeof source === 'object' ? source : {};
            return {
                login_url: candidate.login_url || RING_HELP_LINKS.login_url,
                help_url: candidate.help_url || RING_HELP_LINKS.help_url,
            };
        },

        _escapeAttr(value) {
            return this.escapeHtml(value).replace(/"/g, '&quot;');
        },

        _normalizeRingHint(hint) {
            if (!hint || typeof hint !== 'object') return null;
            const title = String(hint.title || '').trim();
            const message = String(hint.message || '').trim();
            if (!title && !message) return null;
            return {
                level: String(hint.level || 'info').trim().toLowerCase() || 'info',
                title,
                message,
            };
        },

        _collectRingDiagnosticsHints(payload) {
            const collected = [];
            const seen = new Set();
            const addHint = (hint) => {
                const normalized = this._normalizeRingHint(hint);
                if (!normalized) return;
                const key = `${normalized.title}|${normalized.message}`;
                if (seen.has(key)) return;
                seen.add(key);
                collected.push(normalized);
            };

            if (payload?.guidance?.hints && Array.isArray(payload.guidance.hints)) {
                payload.guidance.hints.forEach(addHint);
            }

            const diagnostics = Array.isArray(payload?.diagnostics) ? payload.diagnostics : [];
            diagnostics.forEach((item) => {
                const checks = item?.checks && typeof item.checks === 'object' ? item.checks : {};
                Object.values(checks).forEach((check) => {
                    if (!check || typeof check !== 'object') return;
                    const hints = Array.isArray(check.hints) ? check.hints : [];
                    hints.forEach(addHint);
                });
            });

            return collected;
        },

        _getRingHintClasses(level) {
            const normalized = String(level || 'info').toLowerCase();
            if (normalized === 'warning') {
                return 'border-amber-300/70 bg-amber-50 text-amber-900 dark:border-amber-700/60 dark:bg-amber-950/25 dark:text-amber-100';
            }
            if (normalized === 'error') {
                return 'border-red-300/70 bg-red-50 text-red-900 dark:border-red-700/60 dark:bg-red-950/25 dark:text-red-100';
            }
            return 'border-sky-300/70 bg-sky-50 text-sky-900 dark:border-sky-700/60 dark:bg-sky-950/25 dark:text-sky-100';
        },

        _renderRingHintCards(hints) {
            const items = Array.isArray(hints) ? hints : [];
            if (!items.length) return '';
            return items.map((hint) => {
                const classes = this._getRingHintClasses(hint.level);
                const title = this.escapeHtml(hint.title || 'Hinweis');
                const message = this.escapeHtml(hint.message || '');
                return `
                    <div class="rounded-xl border px-3 py-2 ${classes}">
                        <div class="font-medium">${title}</div>
                        ${message ? `<div class="mt-1 text-xs opacity-90">${message}</div>` : ''}
                    </div>
                `;
            }).join('');
        },

        _renderRingHelpInline(hints, links) {
            const panel = document.getElementById('ring-auth-help-inline');
            if (!panel) return;
            const items = Array.isArray(hints) ? hints : [];
            const helpLinks = this._getRingHelpLinks(links);
            if (!items.length) {
                panel.classList.add('hidden');
                panel.innerHTML = '';
                return;
            }

            panel.classList.remove('hidden');
            panel.innerHTML = `
                <div class="flex items-start justify-between gap-3">
                    <div class="space-y-2">${this._renderRingHintCards(items.slice(0, 2))}</div>
                    <div class="flex shrink-0 flex-col gap-2">
                        <a href="${this._escapeAttr(helpLinks.login_url)}" target="_blank" rel="noopener noreferrer" class="theme-outline-button px-3 py-2 rounded-lg text-xs text-center">Ring Login</a>
                        <a href="${this._escapeAttr(helpLinks.help_url)}" target="_blank" rel="noopener noreferrer" class="theme-outline-button px-3 py-2 rounded-lg text-xs text-center">Ring Hilfe</a>
                    </div>
                </div>
            `;
        },

        _setRingHealthBadge(state = 'unknown', label = 'Prüfung…') {
            const badge = document.getElementById('ring-events-health-badge');
            if (!badge) return;
            const stateClasses = {
                healthy: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-200',
                warning: 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-200',
                error: 'bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-200',
                unknown: 'bg-slate-100 text-slate-700 dark:bg-slate-700 dark:text-slate-200',
            };
            badge.className = `inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium ${stateClasses[state] || stateClasses.unknown}`;
            badge.textContent = label;
        },

        _deriveRingHealthState(payload) {
            const diagnostics = Array.isArray(payload?.diagnostics) ? payload.diagnostics : [];
            let anyFailure = false;
            let anyWarning = false;
            let successCount = 0;
            diagnostics.forEach((item) => {
                const checks = item?.checks && typeof item.checks === 'object' ? item.checks : {};
                Object.values(checks).forEach((check) => {
                    if (!check || typeof check !== 'object') return;
                    if (check.success) {
                        successCount += 1;
                        return;
                    }
                    const errorText = String(check.error || '').toLowerCase();
                    anyFailure = true;
                    if (errorText.includes('406') || errorText.includes('timeout') || errorText.includes('auth') || errorText.includes('verification') || errorText.includes('2fa') || errorText.includes('otp')) {
                        anyWarning = true;
                    }
                });
            });
            if (anyFailure) {
                return anyWarning
                    ? { state: 'warning', label: 'Re-Auth prüfen' }
                    : { state: 'error', label: 'Fehler' };
            }
            if (successCount > 0) {
                return { state: 'healthy', label: 'OK' };
            }
            return { state: 'unknown', label: 'Prüfung…' };
        },

        _renderRingGuidanceNotice(hints, links) {
            const panel = document.getElementById('ring-events-guidance');
            if (!panel) return;
            const items = Array.isArray(hints) ? hints : [];
            const helpLinks = this._getRingHelpLinks(links);
            if (!items.length) {
                panel.classList.add('hidden');
                panel.innerHTML = '';
                return;
            }

            panel.classList.remove('hidden');
            panel.innerHTML = `
                <div class="rounded-xl border border-amber-300/70 bg-amber-50 px-3 py-3 text-xs text-amber-950 dark:border-amber-700/60 dark:bg-amber-950/25 dark:text-amber-100">
                    <div class="flex items-start justify-between gap-3">
                        <div class="space-y-2">
                            <div class="font-semibold">Ring benötigt Aufmerksamkeit</div>
                            ${this._renderRingHintCards(items.slice(0, 2))}
                        </div>
                        <div class="flex shrink-0 flex-col gap-2">
                            <button type="button" id="ring-guidance-help-open-btn" class="theme-outline-button px-3 py-2 rounded-lg text-xs">Mehr Infos</button>
                            <a href="${this._escapeAttr(helpLinks.login_url)}" target="_blank" rel="noopener noreferrer" class="theme-outline-button px-3 py-2 rounded-lg text-xs text-center">Ring Login</a>
                        </div>
                    </div>
                </div>
            `;

            const openBtn = document.getElementById('ring-guidance-help-open-btn');
            if (openBtn) {
                openBtn.addEventListener('click', () => this.openRingHelpModal(), { once: true });
            }
        },

        _buildRingHelpModalBody({ hints = [], links = null, diagnostics = [] } = {}) {
            const helpLinks = this._getRingHelpLinks(links);
            const items = Array.isArray(hints) ? hints : [];
            const diagItems = Array.isArray(diagnostics) ? diagnostics : [];
            const firstFailures = [];
            diagItems.forEach((item) => {
                const checks = item?.checks && typeof item.checks === 'object' ? item.checks : {};
                Object.entries(checks).forEach(([kind, check]) => {
                    if (firstFailures.length >= 3) return;
                    if (!check || typeof check !== 'object' || !check.error) return;
                    firstFailures.push({
                        camera_name: item.camera_name || item.cam_id || 'Ring Kamera',
                        kind,
                        error: String(check.error || '').trim(),
                    });
                });
            });
            const lastEvent = Array.isArray(this._lastRingEvents) && this._lastRingEvents.length ? this._lastRingEvents[0] : null;
            const health = this._lastRingHealth && typeof this._lastRingHealth === 'object' ? this._lastRingHealth : {};
            const lastEventText = lastEvent
                ? `${this._formatRingEventTimestamp(lastEvent)} · ${this.escapeHtml(lastEvent.camera_name || lastEvent.cam_id || 'Ring Kamera')} · ${this.escapeHtml(lastEvent.trigger || lastEvent.kind || 'unknown')}`
                : '-';
            const lastSuccessText = this._formatRingHealthTimestamp(health.last_successful_pull_at);
            const lastErrorText = health.last_error_message
                ? `${this._formatRingHealthTimestamp(health.last_error_at)} · ${this.escapeHtml(health.last_error_message)}`
                : '-';
            const disturbedSinceText = health.last_error_at
                ? this._formatRingHealthTimestamp(health.last_error_at)
                : '-';
            const reauthEstimateText = (typeof health.days_until_estimated_reauth === 'number' && Number.isFinite(health.days_until_estimated_reauth))
                ? `${this.escapeHtml(String(health.days_until_estimated_reauth))} Tage`
                : '-';

            return `
                <div class="theme-subpanel rounded-xl p-4">
                    <div class="font-semibold text-gray-900 dark:text-white mb-2">So stellst du Ring wieder her</div>
                    <ol class="list-decimal ml-5 space-y-1 text-sm text-gray-700 dark:text-gray-200">
                        <li>Ring Login oder Hilfe in neuem Tab öffnen.</li>
                        <li>Offene Sicherheitsabfragen, Gerätefreigaben oder Konto-Bestätigungen im Ring-Konto abschließen.</li>
                        <li>Zurück auf die Kameraseite gehen und Ring verbinden erneut ausführen.</li>
                        <li>Falls Ring einen Code verlangt, den 2FA-Code in das Feld 2FA Code (optional) eintragen.</li>
                    </ol>
                    <div class="mt-3 flex flex-wrap gap-2">
                        <a href="${this._escapeAttr(helpLinks.login_url)}" target="_blank" rel="noopener noreferrer" class="theme-accent-button px-3 py-2 rounded-lg text-sm">Ring Login öffnen</a>
                        <a href="${this._escapeAttr(helpLinks.help_url)}" target="_blank" rel="noopener noreferrer" class="theme-outline-button px-3 py-2 rounded-lg text-sm">Ring Hilfe öffnen</a>
                    </div>
                </div>
                ${items.length ? `<div class="space-y-2">${this._renderRingHintCards(items)}</div>` : ''}
                <div class="theme-subpanel rounded-xl p-4">
                    <div class="font-semibold text-gray-900 dark:text-white mb-2">Timeline</div>
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
                        <div class="rounded-lg border border-gray-200/70 dark:border-gray-700 px-3 py-2">
                            <div class="text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400">Letztes Event</div>
                            <div class="mt-1 text-gray-900 dark:text-white">${lastEventText}</div>
                        </div>
                        <div class="rounded-lg border border-gray-200/70 dark:border-gray-700 px-3 py-2">
                            <div class="text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400">Letzter erfolgreicher API-Abruf</div>
                            <div class="mt-1 text-gray-900 dark:text-white">${this.escapeHtml(lastSuccessText)}</div>
                        </div>
                        <div class="rounded-lg border border-gray-200/70 dark:border-gray-700 px-3 py-2">
                            <div class="text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400">Letzter Fehler</div>
                            <div class="mt-1 text-gray-900 dark:text-white">${lastErrorText}</div>
                        </div>
                        <div class="rounded-lg border border-gray-200/70 dark:border-gray-700 px-3 py-2">
                            <div class="text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400">Seit wann gestört</div>
                            <div class="mt-1 text-gray-900 dark:text-white">${this.escapeHtml(disturbedSinceText)}</div>
                            <div class="mt-1 text-[11px] text-gray-500 dark:text-gray-400">Geschätztes Re-Auth-Fenster: ${reauthEstimateText}</div>
                        </div>
                    </div>
                </div>
                ${firstFailures.length ? `
                    <div class="theme-subpanel rounded-xl p-4">
                        <div class="font-semibold text-gray-900 dark:text-white mb-2">Aktuelle Diagnose</div>
                        <div class="space-y-2">
                            ${firstFailures.map((failure) => `
                                <div class="rounded-lg border border-gray-200/70 dark:border-gray-700 px-3 py-2">
                                    <div class="text-sm font-medium text-gray-900 dark:text-white">${this.escapeHtml(failure.camera_name)} · ${this.escapeHtml(failure.kind)}</div>
                                    <div class="mt-1 font-mono text-[11px] text-gray-500 dark:text-gray-400">${this.escapeHtml(failure.error)}</div>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                ` : ''}
            `;
        },

        openRingHelpModal() {
            const modal = document.getElementById('ring-help-modal');
            const body = document.getElementById('ring-help-modal-body');
            if (!modal || !body) return;
            body.innerHTML = this._buildRingHelpModalBody({
                hints: this._lastRingDiagnosticsHints || [],
                links: this._lastRingHelpLinks || null,
                diagnostics: this._lastRingDiagnostics || [],
            });
            modal.classList.remove('hidden');
            modal.classList.add('flex');
        },

        closeRingHelpModal() {
            const modal = document.getElementById('ring-help-modal');
            if (!modal) return;
            modal.classList.add('hidden');
            modal.classList.remove('flex');
        },

        async loadRingDiagnostics() {
            try {
                const response = await fetch('/api/ring/diagnostics?limit=5');
                const payload = await response.json();
                this._lastRingHelpLinks = this._getRingHelpLinks(payload?.help_links);
                this._lastRingDiagnostics = Array.isArray(payload?.diagnostics) ? payload.diagnostics : [];
                this._lastRingDiagnosticsHints = this._collectRingDiagnosticsHints(payload);
                this._lastRingHealth = payload?.health && typeof payload.health === 'object' ? payload.health : null;
                const health = this._deriveRingHealthState(payload);
                this._setRingHealthBadge(health.state, health.label);
                this._renderRingGuidanceNotice(this._lastRingDiagnosticsHints, this._lastRingHelpLinks);
                this._renderRingHelpInline(this._lastRingDiagnosticsHints, this._lastRingHelpLinks);
                return payload;
            } catch (error) {
                this._setRingHealthBadge('error', 'Diagnosefehler');
                return { success: false, error: error.message || String(error), diagnostics: [] };
            }
        },

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
                this._lastRingHelpLinks = this._getRingHelpLinks(data.help_links);
                this._lastRingSavedCredentials = !!data.saved_credentials;
                const usernameInput = document.getElementById('ring-username');
                if (usernameInput && data.saved_username && !usernameInput.value) {
                    usernameInput.value = data.saved_username;
                }

                if (!data.available) {
                    statusEl.textContent = 'Ring Status: Modul nicht installiert (ring_doorbell fehlt)';
                } else if (data.configured) {
                    statusEl.textContent = `Ring Status: verbunden (User-Agent: ${data.user_agent || 'n/a'}${data.saved_credentials ? ', Zugangsdaten verschlüsselt gespeichert' : ''})`;
                } else {
                    statusEl.textContent = data.saved_credentials
                        ? 'Ring Status: nicht verbunden, aber verschlüsselte Zugangsdaten sind gespeichert'
                        : 'Ring Status: nicht verbunden';
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

        _formatRingHealthTimestamp(value) {
            const ts = Number(value || 0);
            if (!Number.isFinite(ts) || ts <= 0) return '-';
            try {
                return new Date(ts * 1000).toLocaleString('de-DE');
            } catch (e) {
                return '-';
            }
        },

        _renderRingHealthSummary(health, statusEl, baseLabel) {
            if (!statusEl) return;
            const summary = health && typeof health === 'object' ? health : {};
            const parts = [this.escapeHtml(baseLabel || 'Status unbekannt')];
            const lastSuccess = this._formatRingHealthTimestamp(summary.last_successful_pull_at);
            const lastErrorAt = this._formatRingHealthTimestamp(summary.last_error_at);
            const lastErrorMessage = this.escapeHtml(summary.last_error_message || '');
            const daysUntil = summary.days_until_estimated_reauth;
            if (lastSuccess !== '-') {
                parts.push(`Letzter Erfolg: ${this.escapeHtml(lastSuccess)}`);
            }
            if (typeof daysUntil === 'number' && Number.isFinite(daysUntil)) {
                parts.push(`Re-Auth grob in: ${this.escapeHtml(String(daysUntil))} Tagen`);
            }
            if (lastErrorMessage) {
                parts.push(`Letzter Fehler (${this.escapeHtml(lastErrorAt)}): ${lastErrorMessage}`);
            }
            statusEl.innerHTML = parts.map((part, index) => (
                index === 0
                    ? `<div>${part}</div>`
                    : `<div class="mt-1 text-[11px] text-gray-500 dark:text-gray-400">${part}</div>`
            )).join('');
        },

        _getRingEventTriggerMeta(event) {
            const rawTrigger = String(event?.trigger || event?.kind || 'unknown').trim().toLowerCase();
            const metaByTrigger = {
                ding: {
                    label: 'Klingeln',
                    classes: 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-200',
                },
                motion: {
                    label: 'Bewegung',
                    classes: 'bg-sky-100 text-sky-800 dark:bg-sky-900/40 dark:text-sky-200',
                },
                package: {
                    label: 'Paket',
                    classes: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-200',
                },
                on_demand: {
                    label: 'Live / On-Demand',
                    classes: 'bg-violet-100 text-violet-800 dark:bg-violet-900/40 dark:text-violet-200',
                },
            };
            return metaByTrigger[rawTrigger] || {
                label: rawTrigger || 'Unbekannt',
                classes: 'bg-slate-100 text-slate-700 dark:bg-slate-700 dark:text-slate-200',
            };
        },

        _getRingEventDetailLabel(event) {
            const candidates = [
                event?.event_subtype,
                event?.subtype,
                event?.event_type,
                event?.detection_type,
                event?.object_type,
                event?.cv_detection_type,
                event?.label,
                event?.category,
            ];
            for (const value of candidates) {
                const text = String(value || '').trim();
                if (!text) continue;
                const normalized = text.toLowerCase();
                if (normalized === String(event?.trigger || '').trim().toLowerCase()) continue;
                if (normalized === String(event?.kind || '').trim().toLowerCase()) continue;
                return text.replace(/[_-]+/g, ' ');
            }
            return '';
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
                                const triggerMeta = this._getRingEventTriggerMeta(event);
                                const triggerLabel = this.escapeHtml(triggerMeta.label);
                                const detailLabel = this.escapeHtml(this._getRingEventDetailLabel(event));
                                const timeLabel = this.escapeHtml(this._formatRingEventTimestamp(event));
                                const cameraName = this.escapeHtml(event.camera_name || event.cam_id || '-');
                                const eventId = this.escapeHtml(event.id || '-');
                                return `
                                    <tr>
                                        <td class="px-4 py-3 whitespace-nowrap text-gray-900 dark:text-gray-100">${timeLabel}</td>
                                        <td class="px-4 py-3 text-gray-700 dark:text-gray-200">${cameraName}</td>
                                        <td class="px-4 py-3">
                                            <div class="flex flex-col gap-1">
                                                <span class="inline-flex w-fit items-center rounded-full px-2.5 py-1 text-xs font-medium ${triggerMeta.classes}">${triggerLabel}</span>
                                                ${detailLabel ? `<span class="text-[11px] text-gray-500 dark:text-gray-400">${detailLabel}</span>` : ''}
                                            </div>
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
                const [response, diagnosticsResponse] = await Promise.all([
                    fetch('/api/ring/events?limit=25'),
                    fetch('/api/ring/diagnostics?limit=5').catch(() => null),
                ]);
                const payload = await response.json();
                let diagnosticsPayload = null;
                if (diagnosticsResponse) {
                    try {
                        diagnosticsPayload = await diagnosticsResponse.json();
                    } catch (e) {}
                }
                if (diagnosticsPayload) {
                    this._lastRingHelpLinks = this._getRingHelpLinks(diagnosticsPayload.help_links);
                    this._lastRingDiagnostics = Array.isArray(diagnosticsPayload.diagnostics) ? diagnosticsPayload.diagnostics : [];
                    this._lastRingDiagnosticsHints = this._collectRingDiagnosticsHints(diagnosticsPayload);
                    this._lastRingHealth = diagnosticsPayload?.health && typeof diagnosticsPayload.health === 'object'
                        ? diagnosticsPayload.health
                        : this._lastRingHealth;
                }
                if (!response.ok || !payload.success) {
                    throw new Error(payload.error || 'Ring-Ereignisse konnten nicht geladen werden');
                }

                const events = Array.isArray(payload.events) ? payload.events : [];
                this._lastRingEvents = events;
                this._lastRingHealth = payload?.health && typeof payload.health === 'object' ? payload.health : this._lastRingHealth;
                this._renderRingEvents(events);
                this._renderRingGuidanceNotice(this._lastRingDiagnosticsHints || [], this._lastRingHelpLinks);
                this._renderRingHelpInline(this._lastRingDiagnosticsHints || [], this._lastRingHelpLinks);
                if (!(this._lastRingDiagnostics && this._lastRingDiagnostics.length)) {
                    this._setRingHealthBadge('healthy', 'OK');
                }
                const storage = payload.storage && typeof payload.storage === 'object' ? payload.storage : null;
                const activeBackend = storage?.active_backend ? `, Speicher: ${storage.active_backend}` : '';
                this._renderRingHealthSummary(payload.health, statusEl, `${events.length} Ereignisse geladen${activeBackend}`);
            } catch (error) {
                panel.innerHTML = `
                    <div class="p-4 text-sm text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-950/20">
                        Fehler beim Laden der Ring-Ereignisse: ${this.escapeHtml(error.message || String(error))}
                    </div>
                `;
                this._renderRingHealthSummary(this._lastRingHealth || null, statusEl, 'Ring-Ereignisse konnten nicht geladen werden');
                this._setRingHealthBadge('error', 'Ladefehler');
                await this.loadRingDiagnostics();
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

            if ((!username || !password) && !this._lastRingSavedCredentials) {
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
                await this.loadRingDiagnostics();
                return false;
            }

            const otpInput = document.getElementById('ring-otp');
            if (otpInput) otpInput.value = '';

            await this._refreshRingStatus();
            await this.loadRingDiagnostics();
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
