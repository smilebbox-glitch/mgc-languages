/* v6.0.1: isolate the historical app.js globals behind one compatibility adapter. */
(function () {
  'use strict';

  const frontend = window.MGCFrontend;
  if (!frontend) throw new Error('MGCFrontend runtime is missing');

  function requireFunction(name, value) {
    if (typeof value !== 'function') throw new Error('Frontend contract missing function: ' + name);
    return value;
  }

  if (typeof state === 'undefined' || !state) {
    throw new Error('Frontend contract missing state');
  }

  if (!frontend.has('legacy-app')) {
    frontend.register('legacy-app', {
      getState: function () { return state; },
      boot: requireFunction('boot', boot),
      bindStaticEvents: requireFunction('bindStaticEvents', bindStaticEvents),
      configureAuthUi: requireFunction('configureAuthUi', configureAuthUi),
      setView: requireFunction('setView', setView),
      loadLanguage: requireFunction('loadLanguage', loadLanguage),
      showApp: requireFunction('showApp', showApp),
      showAuth: requireFunction('showAuth', showAuth),
      setServiceStatus: requireFunction('setServiceStatus', setServiceStatus),
      toast: requireFunction('toast', toast),
      escapeHtml: requireFunction('esc', esc),
      query: requireFunction('$', $),
      queryAll: requireFunction('$$', $$)
    });
  }
})();
