/* v6.0.30 — Chinese learning content policy.
 * UI chrome stays Russian. Only the material being learned is Chinese + pinyin.
 * Presentation only: no answer, XP, scoring or API ownership.
 */
(function (root) {
  'use strict';

  const main = root.document.getElementById('main');
  if (!main) return;
  let queued = false;

  function snapshot() {
    try {
      const frontend = root.MGCFrontend;
      return frontend && frontend.has && frontend.has('app-state') ? frontend.get('app-state').current() : {};
    } catch (_) { return {}; }
  }

  function chinese() { return snapshot().language === 'chinese'; }

  function optionPinyin(question, selector) {
    main.querySelectorAll(selector).forEach(function (button, index) {
      let node = button.querySelector('.v630-option-pinyin');
      const value = chinese() && question && Array.isArray(question.option_pronunciations)
        ? String(question.option_pronunciations[index] || '') : '';
      if (!value) {
        if (node) node.remove();
        return;
      }
      if (!node) {
        node = root.document.createElement('span');
        node.className = 'pinyin-line v630-option-pinyin';
        button.appendChild(node);
      }
      node.textContent = value;
    });
  }

  function gameItemPinyin() {
    const state = snapshot();
    if (!chinese() || String(state.view || '') !== 'games') return;
    const session = state.gameSessionV618 || state.gameSession || null;
    const index = Number(state.gameIndexV618 || 0);
    const item = session && Array.isArray(session.items) ? session.items[index] : null;
    if (!item) return;

    const value = String(item.prompt_pronunciation || item.pronunciation || item.pinyin || '');
    if (!value) return;
    if (main.querySelector('.game-stage > .v630-game-learning-pinyin, .game-stage h2 + .v630-game-learning-pinyin')) return;

    const anchor = main.querySelector('.game-stage h2, .hotspot-target b, .game-prompt-block h2, .game-term-display b');
    if (!anchor) return;
    const node = root.document.createElement('div');
    node.className = 'question-pinyin v630-game-learning-pinyin';
    node.textContent = value;
    anchor.insertAdjacentElement('afterend', node);
  }

  function injectPinyin() {
    const state = snapshot();
    if (!chinese()) {
      main.querySelectorAll('.v630-option-pinyin,.v630-game-learning-pinyin').forEach(function (node) { node.remove(); });
      return;
    }
    if (String(state.view || '') === 'quiz' && Array.isArray(state.quiz)) {
      optionPinyin(state.quiz[state.quizIndex], '[data-answer]');
    }
    if (String(state.view || '') === 'course30' && Array.isArray(state.dayQuiz)) {
      optionPinyin(state.dayQuiz[state.dayQuizIndex], '[data-day-answer]');
    }
    gameItemPinyin();
  }

  function mark() {
    main.classList.toggle('v630-chinese-learning-content', chinese());
    main.setAttribute('data-learning-ui-language', 'ru');
    main.setAttribute('data-learning-content-language', chinese() ? 'zh-pinyin' : 'en');
  }

  function apply() { mark(); injectPinyin(); }
  function schedule() {
    if (queued) return;
    queued = true;
    root.requestAnimationFrame(function () { queued = false; apply(); });
  }

  new MutationObserver(schedule).observe(main, {childList:true, subtree:true, characterData:true});
  root.document.addEventListener('click', function (event) {
    if (!event.target || !event.target.closest) return;
    if (event.target.closest('[data-language],[data-view],[data-answer],[data-day-answer],[data-start-v618-game],[data-start-game]')) {
      root.setTimeout(schedule, 0);
      root.setTimeout(schedule, 100);
    }
  }, true);
  root.addEventListener('popstate', schedule);
  schedule();
})(window);
