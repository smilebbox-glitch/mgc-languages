/* v6.0.29 hotfix: canonical navigation with a single Games owner and deadlock-free catalog entry. */
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

  function normalizeGamesState() {
    if (!frontend.has('app-state')) return;
    const state = frontend.get('app-state');
    const snapshot = state.current() || {};
    const session = snapshot.gameSessionV618;
    if (!session) return;

    const items = Array.isArray(session.items) ? session.items : [];
    const index = Number(snapshot.gameIndexV618 || 0);
    if (!items.length || index >= items.length) {
      state.patch({
        gameSessionV618: null,
        gameAnswersV618: [],
        gameIndexV618: 0,
        gameSelectionV618: []
      });
      window.reportError('games-stale-session-reset', 'Completed or empty cached session was cleared before catalog render');
    }
  }

  function setView(view) {
    view = String(view || 'home');

    if (view === 'games' && frontend.has('game-lab-v618')) {
      normalizeGamesState();
      return frontend.get('game-lab-v618').navigate('games');
    }
    if (frontend.has('pilot-home') && frontend.get('pilot-home').owns(view)) {
      return frontend.get('pilot-home').navigate(view);
    }
    if (frontend.has('learning') && frontend.get('learning').owns(view)) {
      return frontend.get('learning').navigate(view);
    }
    if (frontend.has('game-lab-v618') && frontend.get('game-lab-v618').owns(view)) {
      return frontend.get('game-lab-v618').navigate(view);
    }
    if (frontend.has('practice-games') && frontend.get('practice-games').owns(view)) {
      return frontend.get('practice-games').navigate(view);
    }
    if (frontend.has('support-notifications') && frontend.get('support-notifications').owns(view)) {
      return frontend.get('support-notifications').navigate(view);
    }
    if (frontend.has('assistant-knowledge') && frontend.get('assistant-knowledge').owns(view)) {
      return frontend.get('assistant-knowledge').navigate(view);
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
      ? event.target.closest('[data-view="games"]')
      : null;
    if (!button) return;

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
