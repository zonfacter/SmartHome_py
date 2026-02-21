/**
 * Variable Manager v1.0.0
 * Frontend-Verwaltung von PLC-Variable Subscriptions
 *
 * Aufgaben:
 * - Widget → Variable Zuordnung verwalten
 * - WebSocket Subscriptions steuern
 * - Value-Updates an Widgets verteilen
 * - Multi-PLC Support
 *
 * Architektur: Frontend ↔ WebSocket ↔ Backend Variable Manager ↔ Data Gateway ↔ PLC
 */

class VariableManager {
    constructor(socket) {
        this.socket = socket;

        // Widget-Subscriptions: widget_id → { variable, plc_id, callback }
        this.subscriptions = new Map();

        // Value-Cache: `${plc_id}/${variable}` → { value, timestamp, type }
        this.valueCache = new Map();

        // Event-Callbacks: event_name → Set(callbacks)
        this.eventCallbacks = new Map();

        // Statistics
        this.stats = {
            subscriptions: 0,
            updates_received: 0,
            writes_sent: 0
        };

        this._setupSocketHandlers();
        console.log('✅ Variable Manager initialisiert');
    }

    /**
     * Setup WebSocket Event Handlers
     */
    _setupSocketHandlers() {
        // Variable Updates vom Backend
        this.socket.on('variable_updates', (data) => {
            this._handleVariableUpdates(data);
        });
        // Kompatibilität: einzelnes Update-Format
        this.socket.on('variable_update', (data) => {
            this._handleSingleVariableUpdate(data);
        });

        // Reconnect-Safety: subscriptions erneut beim Connect senden.
        this.socket.on('connect', () => {
            this._resubscribeAll();
        });

        // Subscribe Success
        this.socket.on('subscribe_success', (data) => {
            console.log(`✅ Subscribe erfolgreich: ${data.widget_id} → ${data.variable}`);
            this._triggerEvent('subscribe_success', data);
        });

        // Unsubscribe Success
        this.socket.on('unsubscribe_success', (data) => {
            console.log(`✅ Unsubscribe erfolgreich: ${data.widget_id}`);
            this._triggerEvent('unsubscribe_success', data);
        });

        // Error Handling
        this.socket.on('error', (data) => {
            console.error('❌ Variable Manager Error:', data.message);
            this._triggerEvent('error', data);
        });
    }

    /**
     * Widget abonniert eine Variable
     *
     * @param {string} widgetId - Eindeutige Widget-ID
     * @param {string} variable - Variable-Name (z.B. "Light.Light_EG_WZ.bOn")
     * @param {function} callback - Callback für Value-Updates: (value, timestamp, type) => {}
     * @param {string} plcId - PLC-ID (Standard: 'plc_001')
     */
    subscribe(widgetId, variable, callback, plcId = 'plc_001') {
        if (!widgetId || !variable || !callback) {
            console.error('❌ subscribe(): widgetId, variable und callback erforderlich');
            return;
        }

        const hadSubscription = this.subscriptions.has(widgetId);

        // Speichere Subscription lokal
        this.subscriptions.set(widgetId, {
            variable: variable,
            plc_id: plcId,
            callback: callback
        });

        // Sende Subscribe-Request an Backend
        this.socket.emit('subscribe_variable', {
            widget_id: widgetId,
            variable: variable,
            plc_id: plcId
        });

        if (!hadSubscription) {
            this.stats.subscriptions++;
        }
        console.log(`📌 Widget ${widgetId} subscribes to ${plcId}/${variable}`);
    }

    /**
     * Widget beendet Subscription
     *
     * @param {string} widgetId - Widget-ID
     */
    unsubscribe(widgetId) {
        if (!widgetId) {
            console.error('❌ unsubscribe(): widgetId erforderlich');
            return;
        }

        // Entferne aus lokaler Map
        const subscription = this.subscriptions.get(widgetId);
        if (!subscription) {
            console.warn(`⚠️  Widget ${widgetId} hat keine aktive Subscription`);
            return;
        }

        this.subscriptions.delete(widgetId);

        // Sende Unsubscribe-Request an Backend
        this.socket.emit('unsubscribe_variable', {
            widget_id: widgetId
        });

        this.stats.subscriptions--;
        console.log(`📌 Widget ${widgetId} unsubscribed`);
    }

    /**
     * Schreibt einen Wert in eine PLC-Variable
     *
     * @param {string} variable - Variable-Name
     * @param {any} value - Wert zum Schreiben
     * @param {string} plcId - PLC-ID (Standard: 'plc_001')
     * @returns {Promise<boolean>} Success/Failure
     */
    async writeVariable(variable, value, plcId = 'plc_001') {
        try {
            const response = await fetch('/api/variables/write', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    plc_id: plcId,
                    variable: variable,
                    value: value
                })
            });

            const data = await response.json();

            if (data.status === 'success') {
                console.log(`✍️  Variable geschrieben: ${plcId}/${variable} = ${value}`);
                this.stats.writes_sent++;
                return true;
            } else {
                console.error(`❌ Schreiben fehlgeschlagen: ${data.message}`);
                return false;
            }

        } catch (error) {
            console.error('❌ writeVariable() error:', error);
            return false;
        }
    }

    /**
     * Liest eine Variable (aus Cache oder direkt von PLC)
     *
     * @param {string} variable - Variable-Name
     * @param {boolean} useCache - Aus Cache lesen? (Standard: true)
     * @param {string} plcId - PLC-ID (Standard: 'plc_001')
     * @returns {Promise<object|null>} { value, timestamp, type, source } oder null
     */
    async readVariable(variable, useCache = true, plcId = 'plc_001') {
        try {
            const response = await fetch('/api/variables/read', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    plc_id: plcId,
                    variable: variable,
                    use_cache: useCache
                })
            });

            const data = await response.json();

            if (data.status === 'success') {
                console.log(`📖 Variable gelesen: ${plcId}/${variable} = ${data.value} (${data.source})`);

                // Cache aktualisieren
                const key = `${plcId}/${variable}`;
                this.valueCache.set(key, {
                    value: data.value,
                    timestamp: data.timestamp,
                    type: data.type || 'UNKNOWN'
                });

                return {
                    value: data.value,
                    timestamp: data.timestamp,
                    type: data.type,
                    source: data.source
                };
            } else {
                console.error(`❌ Lesen fehlgeschlagen: ${data.message}`);
                return null;
            }

        } catch (error) {
            console.error('❌ readVariable() error:', error);
            return null;
        }
    }

    /**
     * Holt gecachten Wert (ohne Backend-Request)
     *
     * @param {string} variable - Variable-Name
     * @param {string} plcId - PLC-ID
     * @returns {object|null} { value, timestamp, type } oder null
     */
    getCachedValue(variable, plcId = 'plc_001') {
        const key = `${plcId}/${variable}`;
        return this.valueCache.get(key) || null;
    }

    /**
     * Registriert Event-Callback
     *
     * @param {string} eventName - Event-Name ('subscribe_success', 'unsubscribe_success', 'error')
     * @param {function} callback - Callback-Funktion
     */
    on(eventName, callback) {
        if (!this.eventCallbacks.has(eventName)) {
            this.eventCallbacks.set(eventName, new Set());
        }
        this.eventCallbacks.get(eventName).add(callback);
    }

    /**
     * Entfernt Event-Callback
     *
     * @param {string} eventName - Event-Name
     * @param {function} callback - Callback-Funktion
     */
    off(eventName, callback) {
        if (this.eventCallbacks.has(eventName)) {
            this.eventCallbacks.get(eventName).delete(callback);
        }
    }

    /**
     * Triggert Event-Callbacks
     *
     * @private
     */
    _triggerEvent(eventName, data) {
        if (this.eventCallbacks.has(eventName)) {
            this.eventCallbacks.get(eventName).forEach(callback => {
                try {
                    callback(data);
                } catch (error) {
                    console.error(`❌ Event callback error (${eventName}):`, error);
                }
            });
        }
    }

    /**
     * Verarbeitet Variable-Updates vom Backend
     *
     * @private
     */
    _handleVariableUpdates(data) {
        // Data Format: { plc_id: { variable: { value, timestamp, type } } }
        for (const [plcId, variables] of Object.entries(data)) {
            for (const [variable, update] of Object.entries(variables)) {

                // Cache aktualisieren
                const key = `${plcId}/${variable}`;
                this.valueCache.set(key, {
                    value: update.value,
                    timestamp: update.timestamp,
                    type: update.type
                });

                // Finde Widgets die diese Variable abonniert haben
                for (const [widgetId, subscription] of this.subscriptions.entries()) {
                    if (subscription.variable === variable && subscription.plc_id === plcId) {

                        // Rufe Widget-Callback auf
                        try {
                            subscription.callback(update.value, update.timestamp, update.type);
                        } catch (error) {
                            console.error(`❌ Widget callback error (${widgetId}):`, error);
                        }
                    }
                }

                this.stats.updates_received++;
            }
        }
    }

    /**
     * Verarbeitet Einzel-Update-Format
     *
     * @private
     */
    _handleSingleVariableUpdate(data) {
        if (!data || !data.variable) return;
        const plcId = data.plc_id || 'plc_001';
        const variable = data.variable;
        const update = {
            value: data.value,
            timestamp: data.timestamp || Date.now() / 1000,
            type: data.type || 'UNKNOWN'
        };
        this._handleVariableUpdates({
            [plcId]: {
                [variable]: update
            }
        });
    }

    /**
     * Sendet alle aktiven Subscriptions erneut (z.B. nach Reconnect)
     *
     * @private
     */
    _resubscribeAll() {
        if (!this.socket || this.subscriptions.size === 0) return;

        for (const [widgetId, subscription] of this.subscriptions.entries()) {
            this.socket.emit('subscribe_variable', {
                widget_id: widgetId,
                variable: subscription.variable,
                plc_id: subscription.plc_id
            });
        }
        console.log(`📌 Re-Subscribe ausgeführt: ${this.subscriptions.size} Widgets`);
    }

    /**
     * Gibt Statistiken zurück
     *
     * @returns {object} Statistiken
     */
    getStatistics() {
        return {
            active_subscriptions: this.subscriptions.size,
            cached_values: this.valueCache.size,
            ...this.stats
        };
    }

    /**
     * Gibt alle aktiven Subscriptions zurück (Debug)
     *
     * @returns {Array} Liste von Subscriptions
     */
    getActiveSubscriptions() {
        const result = [];
        for (const [widgetId, subscription] of this.subscriptions.entries()) {
            result.push({
                widget_id: widgetId,
                variable: subscription.variable,
                plc_id: subscription.plc_id
            });
        }
        return result;
    }

    /**
     * Lädt Backend-Statistiken
     *
     * @returns {Promise<object|null>} Backend-Statistiken
     */
    async getBackendStatistics() {
        try {
            const response = await fetch('/api/variables/statistics');
            const data = await response.json();

            if (data.status === 'success') {
                return data.statistics;
            } else {
                console.error('❌ Backend-Statistiken nicht verfügbar:', data.message);
                return null;
            }

        } catch (error) {
            console.error('❌ getBackendStatistics() error:', error);
            return null;
        }
    }

    /**
     * Cleanup - Entfernt alle Subscriptions
     */
    cleanup() {
        // Unsubscribe alle Widgets
        for (const widgetId of this.subscriptions.keys()) {
            this.unsubscribe(widgetId);
        }

        // Clear Caches
        this.valueCache.clear();
        this.eventCallbacks.clear();

        console.log('✅ Variable Manager cleanup abgeschlossen');
    }
}

// Export für globalen Zugriff
window.VariableManager = VariableManager;
