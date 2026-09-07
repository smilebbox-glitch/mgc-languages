/* v5.9.9: bridge the legacy frontend bundle into the modular registry. */
(function () {
  'use strict';

  const frontend = window.MGCFrontend;
  if (!frontend) throw new Error('MGCFrontend runtime is missing');

  function requireFunction(name, value) {
    if (typeof value !== 'function') throw new Error('Frontend contract missing function: ' + name);
    return value;
  }

  try {
    if (typeof state === 'undefined' || !state) {
      throw new Error('Frontend contract missing state');
    }

    const legacy = {
      api: requireFunction('api', api),
      getState: function () { return state; },
      setView: requireFunction('setView', setView),
      loadLanguage: requireFunction('loadLanguage', loadLanguage),
      showApp: requireFunction('showApp', showApp),
      showAuth: requireFunction('showAuth', showAuth),
      toast: requireFunction('toast', toast),
      escapeHtml: requireFunction('esc', esc),
      query: requireFunction('$', $),
      queryAll: requireFunction('$$', $$)
    };

    if (!frontend.has('legacy-app')) frontend.register('legacy-app', legacy);

    const requiredDomIds = [
      'authView', 'authForm', 'username', 'department', 'password',
      'appView', 'main', 'sidebar', 'logoutButton', 'toast'
    ];
    const missing = requiredDomIds.filter(function (id) { return !document.getElementById(id); });
    if (missing.length) throw new Error('Frontend DOM contract missing: ' + missing.join(', '));

    frontend.markReady();
    document.dispatchEvent(new CustomEvent('mgc:frontend-ready', {
      detail: {version: frontend.version, modules: frontend.list()}
    }));
  } catch (error) {
    const message = frontend.fail(error);
    const main = document.getElementById('main');
    if (main) {
      main.innerHTML = '<div class="card"><h2>Не удалось загрузить интерфейс</h2><p>' +
        String(message).replace(/[&<>"']/g, function (char) {
          return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[char];
        }) + '</p></div>';
    }
    throw error;
  }
})();
