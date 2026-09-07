/* v6.0.0: stable frontend module registry and runtime diagnostics. */
(function (global) {
  'use strict';

  if (global.MGCFrontend) return;

  const modules = new Map();
  const diagnostics = {
    version: '6.0.0',
    startedAt: new Date().toISOString(),
    ready: false,
    failures: []
  };

  function register(name, api) {
    const key = String(name || '').trim();
    if (!key) throw new Error('Frontend module name is required');
    if (modules.has(key)) throw new Error('Frontend module already registered: ' + key);
    modules.set(key, Object.freeze(api || {}));
    return modules.get(key);
  }

  function has(name) {
    return modules.has(String(name));
  }

  function get(name) {
    const key = String(name);
    if (!modules.has(key)) throw new Error('Frontend module is not registered: ' + key);
    return modules.get(key);
  }

  function list() {
    return Array.from(modules.keys()).sort();
  }

  function fail(error) {
    const message = error instanceof Error ? error.message : String(error);
    diagnostics.failures.push({at: new Date().toISOString(), message: message});
    diagnostics.ready = false;
    if (global.document && global.document.documentElement) {
      global.document.documentElement.dataset.mgcFrontend = 'failed';
    }
    return message;
  }

  function markReady() {
    diagnostics.ready = true;
    if (global.document && global.document.documentElement) {
      global.document.documentElement.dataset.mgcFrontend = 'ready';
    }
  }

  global.MGCFrontend = Object.freeze({
    version: diagnostics.version,
    diagnostics: diagnostics,
    register: register,
    has: has,
    get: get,
    list: list,
    fail: fail,
    markReady: markReady
  });
})(typeof window !== 'undefined' ? window : globalThis);
