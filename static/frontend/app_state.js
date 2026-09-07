/* v6.0.0: canonical facade for shared frontend state. */
(function () {
  'use strict';
  const frontend = window.MGCFrontend;
  if (!frontend) throw new Error('MGCFrontend runtime is missing');
  if (frontend.has('app-state')) return;

  function current() {
    return frontend.get('legacy-app').getState();
  }

  function get(key) {
    return current()[key];
  }

  function set(key, value) {
    current()[key] = value;
    document.dispatchEvent(new CustomEvent('mgc:state-change', {
      detail: {key: key, value: value}
    }));
    return value;
  }

  function patch(values) {
    Object.keys(values || {}).forEach(function (key) { current()[key] = values[key]; });
    document.dispatchEvent(new CustomEvent('mgc:state-change', {
      detail: {patch: Object.assign({}, values || {})}
    }));
    return current();
  }

  frontend.register('app-state', {
    current: current,
    get: get,
    set: set,
    patch: patch
  });
})();
