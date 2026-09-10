/* v6.0.31: focused games UI compatibility fix.
 * Keeps the approved pilot design unchanged while repairing Word Match
 * answer rendering/scoring and adding an in-game return path to the game catalog.
 */
(function (root) {
  'use strict';

  let observer = null;
  let fetchNormalized = false;

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

  function normalizeMatchFinishPayload() {
    if (fetchNormalized || typeof root.fetch !== 'function') return;
    const nativeFetch = root.fetch.bind(root);

    root.fetch = function (input, init) {
      const snapshot = current();
      const session = snapshot.gameSession;
      const url = typeof input === 'string' ? input : (input && input.url ? String(input.url) : '');
      const isMatchFinish = session && session.game_type === 'match' && /\/api\/games\/[^/]+\/finish(?:\?|$)/.test(url);

      if (!isMatchFinish || !init || typeof init.body !== 'string') {
        return nativeFetch(input, init);
      }

      try {
        const payload = JSON.parse(init.body);
        if (Array.isArray(payload.answers)) {
          payload.answers = payload.answers.map(function (value) {
            return typeof value === 'string' && /^\d+$/.test(value) ? Number(value) : value;
          });
          init = Object.assign({}, init, {body: JSON.stringify(payload)});
        }
      } catch (_) {}

      return nativeFetch(input, init);
    };
    fetchNormalized = true;
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
        if (!button.hidden) button.hidden = true;
        if (!button.disabled) button.disabled = true;
        if (button.hasAttribute('data-game-answer')) button.removeAttribute('data-game-answer');
        return;
      }

      const answerIndex = String(index);
      const answerText = String(options[index]);

      if (button.hidden) button.hidden = false;
      if (button.disabled) button.disabled = false;
      if (button.dataset.gameAnswer !== answerIndex) button.dataset.gameAnswer = answerIndex;
      if (button.textContent !== answerText) button.textContent = answerText;
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
    button.style.marginBottom = '16px';
    button.style.alignSelf = 'flex-start';
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
    normalizeMatchFinishPayload();
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
