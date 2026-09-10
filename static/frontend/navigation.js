/* v6.0.31: simplified pilot navigation.
 * Games have one canonical owner: practice-games.
 * Home prefers the premium editorial workspace and falls back to pilot-home.
 */
(function () {
  'use strict';
  const frontend = window.MGCFrontend;
  if (!frontend) throw new Error('MGCFrontend runtime is missing');
  if (frontend.has('navigation')) return;

  function legacy() { return frontend.get('legacy-app'); }

  if (typeof window.reportError !== 'function') {
    window.reportError = function (scope, error) {
      if (!frontend.has('error-boundary')) return;
      frontend.get('error-boundary').record(
        String(scope || 'frontend'),
        error && error.message ? error.message : error,
        '', 0, 0
      );
    };
  }

  function syncHomeChrome(view) {
    if (!document.body) return;
    document.body.classList.toggle('v631-premium-home-active', String(view || 'home') === 'home');
  }

  function setView(view) {
    view = String(view || 'home');
    syncHomeChrome(view);

    if (frontend.has('premium-home') && frontend.get('premium-home').owns(view)) {
      return frontend.get('premium-home').navigate(view);
    }
    if (frontend.has('pilot-home') && frontend.get('pilot-home').owns(view)) {
      return frontend.get('pilot-home').navigate(view);
    }
    if (frontend.has('learning') && frontend.get('learning').owns(view)) {
      return frontend.get('learning').navigate(view);
    }
    if (frontend.has('practice-games') && frontend.get('practice-games').owns(view)) {
      return frontend.get('practice-games').navigate(view);
    }
    if (frontend.has('support-notifications') && frontend.get('support-notifications').owns(view)) {
      return frontend.get('support-notifications').navigate(view);
    }
    if (frontend.has('final-assessment') && frontend.get('final-assessment').owns(view)) {
      return frontend.get('final-assessment').navigate(view);
    }
    if (frontend.has('chinese-reference') && frontend.get('chinese-reference').owns(view)) {
      return frontend.get('chinese-reference').navigate(view);
    }
    if (frontend.has('manager-admin') && frontend.get('manager-admin').owns(view)) {
      return frontend.get('manager-admin').navigate(view);
    }
    return legacy().setView(view);
  }

  function interceptGamesNavigation(event) {
    const button = event.target && event.target.closest
      ? event.target.closest('[data-view="games"], [data-go="games"], [data-pilot-target="games"]')
      : null;
    if (!button) return;

    event.preventDefault();
    event.stopImmediatePropagation();
    Promise.resolve(setView('games')).catch(function (error) {
      window.reportError('games-navigation-owner', error);
      const main = document.getElementById('main');
      if (!main) return;
      const message = String(error && error.message ? error.message : error || 'Неизвестная ошибка')
        .replace(/[&<>"']/g, function (char) {
          return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[char];
        });
      main.innerHTML = '<div class="empty"><h2>Не удалось открыть игры</h2><p>' + message +
        '</p><button class="primary" data-games-nav-retry>Повторить</button></div>';
      const retry = main.querySelector('[data-games-nav-retry]');
      if (retry) retry.addEventListener('click', function () { void setView('games'); });
    });
  }

  window.addEventListener('click', interceptGamesNavigation, true);

  frontend.register('navigation', {
    setView: setView,
    loadLanguage: function () { return legacy().loadLanguage(); },
    showApp: function () { return legacy().showApp(); },
    showAuth: function () {
      syncHomeChrome('auth');
      return legacy().showAuth();
    },
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
      syncHomeChrome('auth');
      frontend.get('app-state').set('user', null);
      legacy().showAuth();
    }
  });
})();
