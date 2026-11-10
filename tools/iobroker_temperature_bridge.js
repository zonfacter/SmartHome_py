'use strict';

// Telemetry only. Supply explicit MQTT -> user-temperature mappings at installation.
// No discovery, timers, actuator APIs, or writes back to the source device.
function startTemperatureBridge(api, mappings) {
  if (!Array.isArray(mappings) || !mappings.length || mappings.length > 7) throw Error('Expected 1–7 temperature mappings');
  const sources = new Set(), targets = new Set();
  for (const m of mappings) {
    if (!m || typeof m.source !== 'string' || !/^mqtt\.\d+\.[\w.-]+$/.test(m.source) ||
        typeof m.target !== 'string' || !/^0_userdata\.0\.Heizung\.Temp\.Temp_[\w-]+$/.test(m.target) ||
        sources.has(m.source) || targets.has(m.target)) throw Error('Invalid or duplicate temperature mapping');
    sources.add(m.source); targets.add(m.target);
  }
  const pending = new Map(), newest = new Map();
  function forward(m, state) {
    const previous = pending.get(m.target) || Promise.resolve();
    const next = previous.then(async () => {
      const stamped = state && Number.isFinite(state.ts) && state.ts > 0;
      if (stamped && state.ts < (newest.get(m.target) || 0)) return;
      const numeric = state && typeof state.val === 'number' && Number.isFinite(state.val) && state.val >= -55 && state.val <= 125;
      const q = state && Number.isInteger(state.q) && state.q >= 0 ? state.q : 0;
      // A restart must not give an old source sample a fresh measurement time.
      await api.setStateAsync(m.target, {
        val: numeric ? state.val : null,
        ack: state ? state.ack === true : true,
        q: stamped && numeric ? q : (q | 0x40),
        ts: stamped ? state.ts : Date.now()
      });
      if (stamped) newest.set(m.target, state.ts);
    });
    pending.set(m.target, next.catch(error => api.log('Temperature forwarding failed: ' + error.message, 'warn')));
    return next;
  }
  // Subscribe before the initial read; late initial responses cannot overwrite newer samples.
  for (const m of mappings) api.on({ id: m.source, change: 'any', q: '*' }, event => {
    forward(m, event && event.state).catch(() => {});
  });
  return Promise.all(mappings.map(async m => {
    const state = await api.getStateAsync(m.source);
    await forward(m, state);
  }));
}

if (typeof module !== 'undefined') module.exports = { startTemperatureBridge };
