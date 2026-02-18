/**
 * SmartHome OS v4.5 - Socket Handler
 * WebSocket-Kommunikation mit dem DataGateway
 *
 * Features:
 * - Echtzeit Value-Updates
 * - Blob-Updates (Bilder)
 * - System-Capabilities
 * - PLC-Befehle
 * - Reconnect-Handling
 */

class SocketHandler {
    constructor() {
        this.socket = null;
        this.connected = false;
        this.telemetryCache = {};
        this.systemCapabilities = {};
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 10;

        this.init();
    }

    /**
     * Initialisiert Socket.IO Verbindung
     */
    init() {
        console.log('[SocketHandler] Initialisiere WebSocket...');

        this.socket = io({
            reconnection: true,
            reconnectionDelay: 1000,
            reconnectionDelayMax: 5000,
            reconnectionAttempts: this.maxReconnectAttempts
        });

        this.setupEventHandlers();
    }

    /**
     * Setup Socket.IO Event-Handler
     */
    setupEventHandlers() {
        // Connection Events
        this.socket.on('connect', () => {
            console.log('[SocketHandler] ✓ Verbunden');
            this.connected = true;
            this.reconnectAttempts = 0;

            if (window.updateConnectionStatus) {
                window.updateConnectionStatus(true);
            }
        });

        this.socket.on('disconnect', () => {
            console.log('[SocketHandler] ✗ Verbindung getrennt');
            this.connected = false;

            if (window.updateConnectionStatus) {
                window.updateConnectionStatus(false);
            }
        });

        this.socket.on('connect_error', (error) => {
            console.error('[SocketHandler] Verbindungsfehler:', error);
            this.reconnectAttempts++;
        });

        // Data Events
        this.socket.on('initial_telemetry', (data) => {
            console.log('[SocketHandler] Initial Telemetrie empfangen:', Object.keys(data).length, 'Werte');
            this.telemetryCache = data;

            if (window.updateTelemetryList) {
                window.updateTelemetryList(data);
            }
        });

        this.socket.on('telemetry_update', (data) => {
            const { key, value, timestamp } = data;
            console.log('[SocketHandler] Telemetrie-Update:', key, '=', value);

            // Update Cache
            this.telemetryCache[key] = value;

            // Update UI
            if (window.updateTelemetryList) {
                window.updateTelemetryList(this.telemetryCache);
            }

            // Callback für spezifische Keys
            this.triggerCallback('telemetry:' + key, value);
        });

        this.socket.on('blob_update', (data) => {
            const { key, timestamp } = data;
            console.log('[SocketHandler] Blob-Update:', key);

            // Callback
            this.triggerCallback('blob:' + key, { key, timestamp });
        });

        this.socket.on('system_capabilities', (data) => {
            console.log('[SocketHandler] System-Capabilities:', data);
            this.systemCapabilities = data;

            // Callback
            this.triggerCallback('system_capabilities', data);
        });

        this.socket.on('plc_write_result', (data) => {
            console.log('[SocketHandler] PLC Write Result:', data);

            // Callback
            this.triggerCallback('plc_write_result', data);
        });

        this.socket.on('mqtt_message', (data) => {
            console.log('[SocketHandler] MQTT Message:', data);

            // Update MQTT-Werte im Frontend
            if (window.app && window.app.loadMQTTValues) {
                window.app.loadMQTTValues();
            }

            // Callback
            this.triggerCallback('mqtt_message', data);
        });

        this.socket.on('camera_alert', (data) => {
            console.log('[SocketHandler] Camera Alert:', data);
            this.triggerCallback('camera_alert', data);
        });
    }

    /**
     * Fordert Telemetrie-Wert an
     *
     * @param {string} key - Telemetrie-Key (z.B. 'PLC.MAIN.temperature')
     * @param {function} callback - Callback mit Wert
     */
    requestTelemetry(key, callback) {
        // Prüfe Cache zuerst
        if (key in this.telemetryCache) {
            console.log('[SocketHandler] Telemetrie aus Cache:', key);
            callback(this.telemetryCache[key]);
            return;
        }

        // Request vom Server
        console.log('[SocketHandler] Request Telemetrie:', key);

        const callbackId = 'telemetry:' + key;
        this.registerCallback(callbackId, (value) => {
            callback(value);
            this.unregisterCallback(callbackId);
        });

        this.socket.emit('request_telemetry', { key });
    }

    /**
     * Schreibt PLC-Variable
     *
     * @param {string} symbol - PLC-Symbol (z.B. 'MAIN.temperature')
     * @param {any} value - Wert
     * @param {function} callback - Callback mit Ergebnis
     */
    writePLC(symbol, value, callback) {
        console.log('[SocketHandler] PLC Write:', symbol, '=', value);

        // Register Callback
        const callbackId = 'plc_write_result';
        this.registerCallback(callbackId, (result) => {
            callback(result);
            this.unregisterCallback(callbackId);
        });

        this.socket.emit('plc_write', { symbol, value });
    }

    /**
     * Holt Telemetrie-Wert aus Cache
     *
     * @param {string} key - Telemetrie-Key
     * @returns {any} Wert oder undefined
     */
    getTelemetryValue(key) {
        return this.telemetryCache[key];
    }

    /**
     * Holt alle Telemetrie-Werte
     *
     * @returns {object} Alle Werte
     */
    getAllTelemetry() {
        return { ...this.telemetryCache };
    }

    /**
     * Holt System-Capabilities
     *
     * @returns {object} Capabilities
     */
    getCapabilities() {
        return { ...this.systemCapabilities };
    }

    /**
     * Prüft ob verbunden
     *
     * @returns {boolean} Verbunden
     */
    isConnected() {
        return this.connected;
    }

    // ========================================================================
    // CALLBACK SYSTEM
    // ========================================================================

    /**
     * Registriert Callback für Event
     *
     * @param {string} eventId - Event-ID
     * @param {function} callback - Callback-Funktion
     */
    registerCallback(eventId, callback) {
        if (!this._callbacks) {
            this._callbacks = {};
        }

        if (!this._callbacks[eventId]) {
            this._callbacks[eventId] = [];
        }

        this._callbacks[eventId].push(callback);
    }

    /**
     * Entfernt Callback
     *
     * @param {string} eventId - Event-ID
     */
    unregisterCallback(eventId) {
        if (this._callbacks && this._callbacks[eventId]) {
            delete this._callbacks[eventId];
        }
    }

    /**
     * Triggert Callbacks
     *
     * @param {string} eventId - Event-ID
     * @param {any} data - Event-Daten
     */
    triggerCallback(eventId, data) {
        if (!this._callbacks || !this._callbacks[eventId]) {
            return;
        }

        for (const callback of this._callbacks[eventId]) {
            try {
                callback(data);
            } catch (e) {
                console.error('[SocketHandler] Callback-Fehler:', e);
            }
        }
    }
}
