/* v6.0.29 hotfix: canonical navigation with a single Games owner and runtime-safe recovery telemetry. */
(function () {
  'use strict';
  const frontend = window.MGCFrontend;
  if (!frontend) throw new Error('MGCFrontend runtime is missing');
  if (frontend.has('navigation')) return;

  function legacy() { return frontend.get('legacy-app'); }

  // game_lab_v618.js recovery paths call reportError(). Keep one global,
  // dependency-safe reporter so a render failure cannot trigger a second
  // ReferenceError and leave the Games view stuck on its loading state.
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

  function setView(view) {
    const target = String(view || 'home');

    // Games has exactly one canonical owner. practice-games retains its legacy
    // implementation only as a compatibility module for other owned views.
    if (target === 'games' && frontend.has('game-lab-v618')) {
      return frontend.get('game-lab-v618').navigate('games');
    }
    if (frontend.has('pilot-home') && frontend.get('pilot-home').owns(target)) {
      return frontend.get('pilot-home').navigate(target);
    }
    if (frontend.has('learning') && frontend.get('learning').owns(target)) {
      return frontend.get('learning').navigate(target);
    }
    if (frontend.has('game-lab-v618') && frontend.get('game-lab-v618').owns(target)) {
      return frontend.get('game-lab-v618').navigate(target);
    }
    if (frontend.has('practice-games') && frontend.get('practice-games').owns(target)) {
      return frontend.get('practice-games').navigate(target);
    }
    if (frontend.has('support-notifications') && frontend.get('support-notifications').owns(target)) {
      return frontend.get('support-notifications').navigate(target);
    }
    if (frontend.has('assistant-knowledge') && frontend.get('assistant-knowledge').owns(target)) {
      return frontend.get('assistant-knowledge').navigate(target);
    }
    if (frontend.has('final-assessment') && frontend.get('final-assessment').owns(target)) {
      return frontend.get('final-assessment').navigate(target);
    }
    if (frontend.has('chinese-reference') && frontend.get('chinese-reference').owns(target)) {
      return frontend.get('chinese-reference').navigate(target);
    }
    if (frontend.has('manager-admin') && frontend.get('manager-admin').owns(target)) {
      return frontend.get('manager-admin').navigate(target);
    }
    return legacy().setView(target);
  }

  function interceptGamesNavigation(event) {
    const button = event.target && event.target.closest
      ? event.target.closest('[data-view="games"]')
      : null;
    if (!button) return;

    // Run at window capture phase, before the older document-level listeners in
    // game-lab/practice-games. This prevents two modules from racing to render
    // the same route.
    event.preventDefault();
    event.stopImmediatePropagation();
    Promise.resolve(setView('games')).catch(function (error) {
      window.reportError('games-navigation-owner', error);
      const main = document.getElementById('main');
      if (main) {
        const message = String(error && error.message ? error.message : error || 'Неизвестная ошибка')
          .replace(/[&<>"']/g, function (char) {
            return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[char];
          });
        main.innerHTML = '<div class="empty"><h2>Не удалось открыть игры</h2><p>' + message +
          '</p><button class="primary" data-games-nav-retry>Повторить</button></div>';
        const retry = main.querySelector('[data-games-nav-retry]');
        if (retry) retry.addEventListener('click', function () { void setView('games'); });
      }
    });
  }

  // Window is earlier than document in the capture path, so this becomes the
  // authoritative click route even though legacy modules still register their
  // own document-level listeners for backwards compatibility.
  window.addEventListener('click', interceptGamesNavigation, true);

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
