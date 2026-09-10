/* v6.0.31: focused games UI compatibility fix.
 * Keeps the approved pilot design unchanged while repairing Word Match
 * answer rendering and adding an in-game return path to the game catalog.
 */
(function (root) {
  'use strict';

  let observer = null;

  function runtime() { return root.MGCFrontend; }

  function gameModule() {
    const frontend = runtime();
    return frontend && frontend.has('practice-games') ? frontend.get('practice-games') : null;
  }

  function appState() {
    const frontend = runtime();
    return frontend && frontend.has('app-state') ? frontend.get('app-state') : null;
  }

  function current() {
    const state = appState();
    return state ? state.current() : {};
  }

  function repairWordMatchAnswers(main) {
    const snapshot = current();
    const session = snapshot.gameSession;
    if (!session || session.game_type !== 'match') return;

    const items = Array.isArray(session.items) ? session.items : [];
    const item = items[Number(snapshot.gameIndex || 0)];
    const options = item && Array.isArray(item.options) ? item.options : [];
    if (!options.length) return;

    const buttons = Array.from(main.querySelectorAll('.options [data-game-answer]'));
    if (!buttons.length) return;

    buttons.forEach(function (button, index) {
      if (index >= options.length) {
        button.hidden = true;
        button.disabled = true;
        button.removeAttribute('data-game-answer');
        return;
      }
      button.hidden = false;
      button.disabled = false;
      button.dataset.gameAnswer = String(index);
      button.textContent = String(options[index]);
    });
  }

  function installBackButton(main) {
    const snapshot = current();
    if (!snapshot.gameSession || snapshot.view !== 'games') return;
    if (main.querySelector('[data-back-to-games]')) return;

    const stage = main.querySelector('.quiz-stage');
    if (!stage) return;

    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'ghost game-back-to-catalog';
    button.dataset.backToGames = '1';
    button.textContent = '← К играм';
    button.setAttribute('aria-label', 'Вернуться к выбору игр');
    stage.insertBefore(button, stage.firstChild);

    button.addEventListener('click', function () {
      const state = appState();
      const games = gameModule();
      if (!state || !games) return;
      state.patch({
        gameSession: null,
        gameAnswers: [],
        gameIndex: 0,
        phraseSelected: []
      });
      Promise.resolve(games.renderGames()).catch(function (error) {
        const frontend = runtime();
        if (frontend && frontend.has('error-boundary')) {
          frontend.get('error-boundary').record(
            'games-back-to-catalog',
            error && error.message ? error.message : error,
            '', 0, 0
          );
        }
      });
    });
  }

  function repair() {
    const main = document.getElementById('main');
    if (!main) return;
    repairWordMatchAnswers(main);
    installBackButton(main);
  }

  function install() {
    const main = document.getElementById('main');
    if (!main || observer) return;
    repair();
    observer = new MutationObserver(function () { repair(); });
    observer.observe(main, {childList: true, subtree: true});
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', install, {once: true});
  } else {
    install();
  }
})(typeof window !== 'undefined' ? window : globalThis);
