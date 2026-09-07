/* v6.0.3: canonical navigation/session-view facade. */
(function () {
  'use strict';
  const frontend = window.MGCFrontend;
  if (!frontend) throw new Error('MGCFrontend runtime is missing');
  if (frontend.has('navigation')) return;

  function legacy() { return frontend.get('legacy-app'); }

  function setView(view) {
    if (frontend.has('learning') && frontend.get('learning').owns(view)) {
      return frontend.get('learning').navigate(view);
    }
    return legacy().setView(view);
  }

  frontend.register('navigation', {
    setView: setView,
    loadLanguage: function () { return legacy().loadLanguage(); },
    showApp: function () { return legacy().showApp(); },
    showAuth: function () { return legacy().showAuth(); },
    enterUserSession: async function (user) {
      const state = frontend.get('app-state');
      state.patch({
        user: user,
        language: user && user.preferred_language ? user.preferred_language : 'chinese'
      });
      legacy().showApp();
      await legacy().loadLanguage();
      await setView('home');
    },
    leaveUserSession: function () {
      frontend.get('app-state').set('user', null);
      legacy().showAuth();
    }
  });
})();
