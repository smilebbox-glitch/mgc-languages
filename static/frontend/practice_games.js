/* v6.0.15: canonical practice, games and XP implementation. */
(function (root) {
  'use strict';

  const frontend = root.MGCFrontend;
  if (!frontend) throw new Error('MGCFrontend runtime is missing');
  if (frontend.has('practice-games')) return;

  const OWNED_VIEWS = Object.freeze(['roleplay', 'games', 'xp']);
  const owned = new Set(OWNED_VIEWS);
  const GAME_LABELS = Object.freeze({
    match: ['Word Match', 'Сопоставьте термин и перевод'],
    listening: ['Listening Sprint', 'Прослушайте термин и выберите значение'],
    phrase: ['Phrase Builder', 'Соберите рабочую фразу в правильном порядке'],
    mistake: ['Find the Mistake', 'Найдите точное значение среди похожих вариантов']
  });
  const INLINE_HELP = new Set([
    'hint_small', 'show_pinyin', 'slow_audio', 'eliminate_option',
    'sentence_start', 'explain_word', 'pronunciation_breakdown',
    'work_example', 'mistake_explain'
  ]);
  let installed = false;

  function legacy() { return frontend.get('legacy-app'); }
  function state() { return frontend.get('app-state'); }
  function api() { return frontend.get('api-client'); }
  function current() { return state().current(); }
  function esc(value) { return legacy().escapeHtml(value); }
  function query(selector, scope) { return legacy().query(selector, scope); }
  function queryAll(selector, scope) { return legacy().queryAll(selector, scope); }
  function toast(message) { legacy().toast(String(message || '')); }

  function owns(view) {
    return owned.has(String(view || ''));
  }

  function reportError(scope, error) {
    if (!frontend.has('error-boundary')) return;
    frontend.get('error-boundary').record(
      String(scope || 'practice-games'),
      error && error.message ? error.message : error,
      '', 0, 0
    );
  }

  function featureEnabled(key) {
    const flags = (current().pilot && current().pilot.features) || {};
    return flags[key] !== false;
  }

  function assertFeature(view) {
    const key = view === 'games' ? 'games' : view === 'xp' ? 'xp_economy' : null;
    if (key && !featureEnabled(key)) {
      throw new Error('Эта функция пока не включена для вашей волны пилота');
    }
  }

  function pageHead(kicker, title, subtitle) {
    return '<div class="page-head"><div><div class="kicker">' + esc(kicker) +
      '</div><h1>' + esc(title) + '</h1><p>' + esc(subtitle) + '</p></div></div>';
  }

  function updateXpProfile(profile) {
    if (!profile) return;
    state().set('gamification', profile);
    const pill = query('#xpPill');
    if (pill) pill.textContent = Number(profile.spendable_xp || 0) + ' XP';
  }

  function xpPanelHTML() {
    const g = current().gamification || {
      level: 1, title: 'Новичок I', lifetime_xp: 0, spendable_xp: 0,
      weekly_xp: 0, progress_xp: 0, level_xp: 500
    };
    const pct = Math.min(100, Math.round((Number(g.progress_xp || 0) * 100) /
      Math.max(1, Number(g.level_xp || 500))));
    return '<section class="xp-overview card"><div><div class="kicker">УРОВЕНЬ ' +
      Number(g.level || 1) + '</div><h2>' + esc(g.title) + '</h2><p>Lifetime: <b>' +
      Number(g.lifetime_xp || 0) + ' XP</b> · доступно для помощи: <b>' +
      Number(g.spendable_xp || 0) + ' XP</b> · неделя: ' + Number(g.weekly_xp || 0) +
      ' XP</p></div><div class="xp-levelbar"><i style="width:' + pct +
      '%"></i></div><button class="ghost" data-go="xp">Использовать XP →</button></section>';
  }

  function termCard(item) {
    const lang = item.language || current().language;
    const pronunciationClass = lang === 'chinese' ? 'pinyin' : 'ipa-line';
    const examplePronClass = lang === 'chinese' ? 'pinyin-line' : 'ipa-line';
    const meta = String(item.level || '') + ' · ' + String(item.topic || '') +
      (item.shop ? ' · ' + item.shop : '');
    return '<article class="term-card"><div class="meta">' + esc(meta) + '</div>' +
      '<div class="target">' + esc(item.term) + '</div>' +
      (item.pronunciation ? '<div class="' + pronunciationClass + '">' +
        esc(item.pronunciation) + '</div>' : '') +
      (item.reading ? '<div class="reading-line">≈ ' + esc(item.reading) +
        ' <small>как читать</small></div>' : '') +
      '<div class="pronunciation-actions"><button class="listen-button" data-speak-text="' +
      esc(item.term) + '" data-speak-language="' + esc(lang) +
      '" data-speak-rate="0.9">▶ Послушать</button><button class="listen-button subtle" data-speak-text="' +
      esc(item.term) + '" data-speak-language="' + esc(lang) +
      '" data-speak-rate="0.68">0.7×</button></div><div class="translation">' +
      esc(item.translation) + '</div>' +
      (item.example && item.example !== item.term ? '<div class="term-example"><div class="example-head"><span>' +
        esc(item.example) + '</span><button class="mini-listen" data-speak-text="' +
        esc(item.example) + '" data-speak-language="' + esc(lang) +
        '" data-speak-rate="0.86">▶</button></div>' +
        (item.example_pronunciation ? '<div class="' + examplePronClass + '">' +
          esc(item.example_pronunciation) + '</div>' : '') +
        '<span>' + esc(item.example_translation) + '</span></div>' : '') + '</article>';
  }

  function scenarioProgressKey() {
    const snapshot = current();
    return 'mgc-scenarios-' + (snapshot.user ? snapshot.user.id : 'guest') + '-' + snapshot.language;
  }

  function getScenarioProgress() {
    try {
      return JSON.parse(root.localStorage.getItem(scenarioProgressKey()) || '{}');
    } catch (_) {
      return {};
    }
  }

  function saveScenarioProgress(id, correct) {
    const progress = getScenarioProgress();
    const value = progress[id] || {attempts: 0, correct: 0};
    value.attempts += 1;
    if (correct) value.correct += 1;
    progress[id] = value;
    root.localStorage.setItem(scenarioProgressKey(), JSON.stringify(progress));
  }

  async function renderRoleplay() {
    let snapshot = current();
    let items = Array.isArray(snapshot.scenarioItems) ? snapshot.scenarioItems : [];
    if (!items.length) {
      items = await api().request('/api/language/' + encodeURIComponent(snapshot.language) + '/roleplays');
      if (!Array.isArray(items)) items = [];
      state().set('scenarioItems', items);
    }
    snapshot = current();

    const topics = ['Все'].concat(Array.from(new Set(items.map(function (item) { return item.topic; }))));
    let activeTopic = snapshot.scenarioTopic || 'Все';
    if (!topics.includes(activeTopic)) {
      activeTopic = 'Все';
      state().set('scenarioTopic', activeTopic);
    }
    const filtered = activeTopic === 'Все' ? items : items.filter(function (item) {
      return item.topic === activeTopic;
    });
    if (snapshot.scenarioIndex >= filtered.length) {
      state().set('scenarioIndex', 0);
      snapshot = current();
    }
    const item = filtered[snapshot.scenarioIndex];
    const completed = Object.keys(getScenarioProgress()).length;
    const main = query('#main');
    if (!main) throw new Error('Roleplay view missing #main');

    if (!item) {
      main.innerHTML = pageHead('Практика', 'Сценарии', 'Для выбранной темы сценариев пока нет.') +
        '<button class="ghost" data-go="topics">Выбрать другую тему</button>';
      return;
    }

    main.innerHTML = pageHead(
      'Коммуникационный тренажёр',
      'Рабочие сценарии',
      'Ситуации, MGC-сценарии и Role Play объединены в одну мини-игру.'
    ) + '<div class="scenario-toolbar"><div class="chip-row">' +
      topics.map(function (topic) {
        return '<button class="topic-chip ' + (topic === activeTopic ? 'active' : '') +
          '" data-scenario-topic="' + esc(topic) + '">' + esc(topic) + '</button>';
      }).join('') + '</div><div class="scenario-stats"><b>' +
      Number(snapshot.scenarioScore || 0) + ' XP</b><span>' + completed +
      ' сценариев попробовано</span></div></div><div class="scenario-stage">' +
      '<div class="quiz-progress"><i style="width:' +
      (((snapshot.scenarioIndex + 1) / filtered.length) * 100) +
      '%"></i></div><div class="scenario-meta"><span>' +
      (snapshot.scenarioIndex + 1) + ' / ' + filtered.length + '</span><span>' +
      esc(item.topic) + '</span></div><div class="card scenario-question"><div class="kicker">' +
      esc(item.title) + '</div><h2>' + esc(item.question) + '</h2>' +
      (item.question_pronunciation ? '<div class="' +
        (snapshot.language === 'chinese' ? 'question-pinyin' : 'ipa-line') + '">' +
        esc(item.question_pronunciation) + '</div>' : '') +
      (item.question_reading ? '<div class="reading-line">≈ ' +
        esc(item.question_reading) + '</div>' : '') +
      '<div class="pronunciation-actions"><button class="listen-button" data-speak-text="' +
      esc(item.question) + '" data-speak-language="' + esc(snapshot.language) +
      '">▶ Вопрос</button></div><p class="scenario-translation">' +
      esc(item.question_translation) + '</p><div class="roles">' +
      (item.roles || []).map(function (role) { return '<span>' + esc(role) + '</span>'; }).join('') +
      '</div><div class="scenario-options">' + (item.options || []).map(function (option, index) {
        return '<div class="scenario-option-wrap"><button class="scenario-option" data-scenario-answer="' +
          index + '"><b>' + esc(option.text) + '</b>' +
          (option.pronunciation ? '<span class="' +
            (snapshot.language === 'chinese' ? 'pinyin-line' : 'ipa-line') + '">' +
            esc(option.pronunciation) + '</span>' : '') +
          (option.reading ? '<span class="reading-line">≈ ' + esc(option.reading) + '</span>' : '') +
          '<span class="answer-translation hidden">' + esc(option.translation) +
          '</span></button><button class="mini-listen scenario-listen" data-speak-text="' +
          esc(option.text) + '" data-speak-language="' + esc(snapshot.language) +
          '">▶</button></div>';
      }).join('') + '</div><div id="scenarioFeedback"></div></div></div>';

    queryAll('[data-scenario-topic]').forEach(function (button) {
      button.addEventListener('click', function () {
        state().patch({
          scenarioTopic: button.dataset.scenarioTopic,
          scenarioIndex: 0,
          scenarioScore: 0,
          scenarioAnswered: false
        });
        void renderRoleplay();
      });
    });
    queryAll('[data-scenario-answer]').forEach(function (button) {
      button.addEventListener('click', function () {
        void answerScenario(item, Number(button.dataset.scenarioAnswer), filtered.length);
      });
    });
  }

  async function answerScenario(item, selectedIndex, total) {
    const snapshot = current();
    if (snapshot.scenarioAnswered) return;
    state().set('scenarioAnswered', true);
    const options = item.options || [];
    const selected = options[selectedIndex];
    const correct = Boolean(selected && selected.correct);
    saveScenarioProgress(item.id, correct);

    queryAll('[data-scenario-answer]').forEach(function (button) {
      const index = Number(button.dataset.scenarioAnswer);
      button.disabled = true;
      button.classList.toggle('correct', Boolean(options[index] && options[index].correct));
      button.classList.toggle('wrong', index === selectedIndex && !correct);
      const translation = query('.answer-translation', button);
      if (translation) translation.classList.remove('hidden');
    });

    const practice = await legacy().submitPractice(
      'scenario',
      legacy().newSessionId('scenario-' + item.id),
      correct ? 1 : 0,
      1,
      item.topic
    );
    const earned = practice && practice.awarded ? practice.awarded : 0;
    if (earned) state().set('scenarioScore', Number(current().scenarioScore || 0) + earned);

    const feedback = query('#scenarioFeedback');
    if (!feedback) return;
    feedback.innerHTML = '<div class="answer-feedback"><b>' +
      (correct ? ('+' + earned + ' XP · точный ответ') :
        (earned ? ('+' + earned + ' XP за попытку') : 'Посмотрите профессиональную формулировку')) +
      '</b><p><strong>Цель:</strong> ' + esc(item.goal) + '</p><ol class="checklist">' +
      (item.prompts || []).map(function (prompt) { return '<li>' + esc(prompt) + '</li>'; }).join('') +
      '</ol></div><button id="nextScenario" class="primary wide">' +
      (current().scenarioIndex + 1 >= total ? 'Начать круг заново' : 'Следующая ситуация') +
      '</button>';
    const next = query('#nextScenario');
    if (next) next.addEventListener('click', function () {
      state().patch({
        scenarioIndex: (current().scenarioIndex + 1) % total,
        scenarioAnswered: false
      });
      void renderRoleplay();
    });
  }

  async function startGame(type) {
    const gameType = String(type || '');
    if (!Object.prototype.hasOwnProperty.call(GAME_LABELS, gameType)) {
      throw new Error('Неизвестный тип игры');
    }
    try {
      const snapshot = current();
      const url = '/api/games/' + encodeURIComponent(gameType) +
        '/start?language=' + encodeURIComponent(snapshot.language) +
        '&topic=' + encodeURIComponent(snapshot.topic || '');
      const session = await api().request(url, {method: 'POST'});
      state().patch({
        gameSession: session,
        gameAnswers: [],
        gameIndex: 0,
        phraseSelected: []
      });
      await renderGames();
    } catch (error) {
      toast(error && error.message ? error.message : error);
      reportError('practice-game-start', error);
    }
  }

  async function finishGame(session) {
    const result = await api().request('/api/games/' + encodeURIComponent(session.session_id) + '/finish', {
      method: 'POST',
      body: JSON.stringify({answers: current().gameAnswers || []})
    });
    if (result.profile) updateXpProfile(result.profile);
    state().patch({gameSession: null, gameAnswers: [], gameIndex: 0, phraseSelected: []});
    const main = query('#main');
    if (!main) return;
    main.innerHTML = pageHead(
      'Игра завершена',
      'Результат ' + Number(result.score || 0) + '/' + Number(result.total || 0),
      'Короткая практика закончена. Можно остановиться здесь — ежедневной обязанности нет.'
    ) + '<div class="card exam-intro"><div class="result-score">' +
      Number(result.score || 0) + '/' + Number(result.total || 0) + '</div><p>+' +
      Number(result.awarded || 0) + ' XP · баланс ' +
      Number((current().gamification || {}).spendable_xp || 0) +
      ' XP</p><button class="primary" data-go="games">Ещё одна игра</button></div>';
  }

  async function renderGames() {
    assertFeature('games');
    const snapshot = current();
    const main = query('#main');
    if (!main) throw new Error('Games view missing #main');

    if (!snapshot.gameSession) {
      main.innerHTML = pageHead(
        '3–5 минут',
        'Игры',
        'Короткие упражнения без давления. XP начисляется сервером, повторное фармление одной и той же активности ограничивается.'
      ) + '<div class="game-grid">' + Object.keys(GAME_LABELS).map(function (key) {
        const labels = GAME_LABELS[key];
        const symbol = key === 'match' ? '↔' : key === 'listening' ? '◖' : key === 'phrase' ? '≡' : '✓';
        return '<button class="game-card" data-start-game="' + key + '"><div class="game-symbol">' +
          symbol + '</div><h3>' + labels[0] + '</h3><p>' + labels[1] +
          '</p><span>Начать →</span></button>';
      }).join('') + '</div>' + xpPanelHTML();
      queryAll('[data-start-game]').forEach(function (button) {
        button.addEventListener('click', function () { void startGame(button.dataset.startGame); });
      });
      return;
    }

    if (snapshot.gameIndex >= (snapshot.gameSession.items || []).length) {
      await finishGame(snapshot.gameSession);
      return;
    }

    const item = snapshot.gameSession.items[snapshot.gameIndex];
    const type = snapshot.gameSession.game_type;
    let body = '';

    if (type === 'match') {
      const options = snapshot.gameSession.items.slice().sort(function () { return Math.random() - 0.5; });
      body = '<h2>' + esc(item.term) + '</h2>' +
        (item.pronunciation ? '<div class="' +
          (snapshot.language === 'chinese' ? 'question-pinyin' : 'ipa-line') + '">' +
          esc(item.pronunciation) + '</div>' : '') +
        (item.reading ? '<div class="reading-line">≈ ' + esc(item.reading) + '</div>' : '') +
        '<div class="pronunciation-actions"><button class="listen-button" data-speak-text="' +
        esc(item.term) + '" data-speak-language="' + esc(snapshot.language) +
        '">▶ Послушать</button></div><div class="options">' +
        options.map(function (value) {
          return '<button class="option" data-game-answer="' + esc(value.id) + '">' +
            esc(value.translation) + '</button>';
        }).join('') + '</div>';
    } else if (type === 'listening') {
      body = '<button id="playGameAudio" class="audio-button">▶ Прослушать</button>' +
        (item.pronunciation ? '<div class="' +
          (snapshot.language === 'chinese' ? 'question-pinyin' : 'ipa-line') + '">' +
          esc(item.pronunciation) + '</div>' : '') +
        (item.reading ? '<div class="reading-line">≈ ' + esc(item.reading) + '</div>' : '') +
        '<div class="options">' + (item.options || []).map(function (value, index) {
          return '<button class="option" data-game-answer="' + index + '">' + esc(value) + '</button>';
        }).join('') + '</div>';
    } else if (type === 'mistake') {
      body = '<h2>' + esc(item.term) + '</h2>' +
        (item.pronunciation ? '<div class="' +
          (snapshot.language === 'chinese' ? 'question-pinyin' : 'ipa-line') + '">' +
          esc(item.pronunciation) + '</div>' : '') +
        (item.reading ? '<div class="reading-line">≈ ' + esc(item.reading) + '</div>' : '') +
        '<div class="pronunciation-actions"><button class="listen-button" data-speak-text="' +
        esc(item.term) + '" data-speak-language="' + esc(snapshot.language) +
        '">▶ Послушать</button></div><p>Какое значение точное?</p><div class="options">' +
        (item.options || []).map(function (value, index) {
          return '<button class="option" data-game-answer="' + index + '">' + esc(value) + '</button>';
        }).join('') + '</div>';
    } else {
      const selected = Array.isArray(snapshot.phraseSelected) ? snapshot.phraseSelected : [];
      body = '<p class="translation-line">' + esc(item.translation) +
        '</p><div id="phraseBuilt" class="phrase-built">' + selected.map(esc).join(' ') +
        '</div><div class="token-bank">' + (item.tokens || []).map(function (value, index) {
          return '<button class="token" data-token-index="' + index + '">' + esc(value) + '</button>';
        }).join('') + '</div><div class="actions"><button id="phraseReset" class="ghost">Сбросить</button>' +
        '<button id="phraseDone" class="primary">Готово</button></div>';
    }

    main.innerHTML = pageHead(
      GAME_LABELS[type][0],
      GAME_LABELS[type][1],
      (snapshot.gameIndex + 1) + ' из ' + snapshot.gameSession.items.length
    ) + '<div class="quiz-stage"><div class="quiz-progress"><i style="width:' +
      (((snapshot.gameIndex + 1) / snapshot.gameSession.items.length) * 100) +
      '%"></i></div><div class="card question-card">' + body + '</div></div>';

    const play = query('#playGameAudio');
    if (play) play.addEventListener('click', function () {
      void legacy().playPronunciation(item.audio_text, 0.82, current().language);
    });

    queryAll('[data-game-answer]').forEach(function (button) {
      button.addEventListener('click', function () {
        const answers = (current().gameAnswers || []).slice();
        const raw = button.dataset.gameAnswer;
        answers.push(type === 'match' ? raw : Number(raw));
        state().patch({gameAnswers: answers, gameIndex: current().gameIndex + 1});
        void renderGames();
      });
    });

    queryAll('[data-token-index]').forEach(function (button) {
      button.addEventListener('click', function () {
        if (button.disabled) return;
        button.disabled = true;
        const selected = (current().phraseSelected || []).slice();
        selected.push(item.tokens[Number(button.dataset.tokenIndex)]);
        state().set('phraseSelected', selected);
        const built = query('#phraseBuilt');
        if (built) built.textContent = selected.join(' ');
      });
    });

    const reset = query('#phraseReset');
    if (reset) reset.addEventListener('click', function () {
      state().set('phraseSelected', []);
      void renderGames();
    });
    const done = query('#phraseDone');
    if (done) done.addEventListener('click', function () {
      const answers = (current().gameAnswers || []).slice();
      answers.push((current().phraseSelected || []).slice());
      state().patch({
        gameAnswers: answers,
        phraseSelected: [],
        gameIndex: current().gameIndex + 1
      });
      void renderGames();
    });
  }

  function renderXpPack(pack) {
    if (!pack) return '';
    if (Array.isArray(pack.items) && pack.items.length && pack.items[0].term) {
      return '<div class="section-title"><h2>' + esc(pack.title || 'Персональная тренировка') +
        '</h2></div><div class="term-list">' + pack.items.map(termCard).join('') + '</div>';
    }
    if (Array.isArray(pack.items) && pack.items.length) {
      return '<div class="section-title"><h2>Открытая практика</h2></div><div class="knowledge-grid">' +
        pack.items.map(function (item) {
          return '<article class="card"><div class="kicker">' + esc(item.topic || 'Scenario') +
            '</div><h3>' + esc(item.title || '') + '</h3><p>' +
            esc(item.question_translation || item.goal || '') + '</p></article>';
        }).join('') + '</div>';
    }
    return '';
  }

  async function buyReward(id) {
    try {
      const snapshot = current();
      const result = await api().request('/api/gamification/spend', {
        method: 'POST',
        body: JSON.stringify({
          reward_id: id,
          language: snapshot.language,
          context: {topic: snapshot.topic || ''}
        })
      });
      if (result.profile) updateXpProfile(result.profile);
      state().set('xpPack', result.result || null);
      toast('−' + Number(result.spent || 0) + ' XP · ' +
        String((result.reward && result.reward.title) || 'Помощь активирована'));
      await renderXP();
    } catch (error) {
      toast(error && error.message ? error.message : error);
      reportError('practice-xp-spend', error);
    }
  }

  async function renderXP() {
    assertFeature('xp');
    const values = await Promise.all([
      api().request('/api/gamification/me'),
      api().request('/api/gamification/rewards')
    ]);
    updateXpProfile(values[0]);
    state().set('rewards', values[1] || {items: []});
    const snapshot = current();
    const rewards = snapshot.rewards && Array.isArray(snapshot.rewards.items) ? snapshot.rewards.items : [];
    const packHtml = snapshot.xpPack ? renderXpPack(snapshot.xpPack) : '';
    const main = query('#main');
    if (!main) throw new Error('XP view missing #main');

    main.innerHTML = pageHead(
      'XP economy',
      'Опыт, который помогает учиться',
      'Уровень не уменьшается. Тратится только доступный баланс XP; основные рабочие функции сервиса всегда бесплатны.'
    ) + xpPanelHTML() + '<div class="section-title"><h2>Практическая помощь</h2><span>Баланс: ' +
      Number((snapshot.gamification || {}).spendable_xp || 0) + ' XP</span></div><div class="reward-grid">' +
      rewards.map(function (item) {
        const inlineOnly = INLINE_HELP.has(item.id);
        return '<article class="reward-card"><div><div class="reward-price">' +
          Number(item.price || 0) + ' XP</div><h3>' + esc(item.title) + '</h3><p>' +
          esc(item.description) + '</p></div>' +
          (inlineOnly ? '<small>Используется прямо внутри задания</small>' :
            '<button class="primary" data-buy-reward="' + esc(item.id) + '">Активировать</button>') +
          '</article>';
      }).join('') + '</div>' + packHtml;

    queryAll('[data-buy-reward]').forEach(function (button) {
      button.addEventListener('click', function () { void buyReward(button.dataset.buyReward); });
    });
  }

  function prepareGo(element) {
    if (!element || !element.dataset || !element.dataset.topic) return;
    const values = {
      topic: element.dataset.topic,
      scenarioTopic: element.dataset.topic
    };
    if (element.dataset.go === 'roleplay') {
      Object.assign(values, {scenarioIndex: 0, scenarioAnswered: false});
    }
    state().patch(values);
  }

  async function render(view) {
    const target = String(view || state().get('view') || 'roleplay');
    if (!owns(target)) throw new Error('Practice module does not own view: ' + target);
    assertFeature(target);
    if (target === 'roleplay') await renderRoleplay();
    else if (target === 'games') await renderGames();
    else await renderXP();
    legacy().ensureChineseStandardBanner();
  }

  async function navigate(view) {
    const target = String(view || 'roleplay');
    if (!owns(target)) return legacy().setView(target);
    assertFeature(target);

    state().set('view', target);
    legacy().closeMenu();
    queryAll('[data-view]').forEach(function (button) {
      button.classList.toggle('active', button.dataset.view === target);
    });

    const main = query('#main');
    if (main) main.innerHTML = '<div class="loading-card"><span class="spinner"></span><p>Загрузка</p></div>';

    try {
      await render(target);
    } catch (error) {
      if (main) {
        main.innerHTML = '<div class="empty"><h2>Не удалось открыть раздел</h2><p>' +
          esc(error && error.message ? error.message : error) +
          '</p><button class="primary" data-go="home">На главную</button></div>';
      }
      reportError('practice-navigation', error);
      throw error;
    }
  }

  function install() {
    if (installed) return;
    installed = true;

    document.addEventListener('click', function (event) {
      const button = event.target && event.target.closest ? event.target.closest('[data-view]') : null;
      if (!button || !owns(button.dataset.view)) return;
      event.preventDefault();
      event.stopImmediatePropagation();
      navigate(button.dataset.view).catch(function () {});
    }, true);

    const main = query('#main');
    if (main) {
      main.addEventListener('click', function (event) {
        const go = event.target && event.target.closest ? event.target.closest('[data-go]') : null;
        if (!go || !owns(go.dataset.go)) return;
        event.preventDefault();
        event.stopImmediatePropagation();
        prepareGo(go);
        navigate(go.dataset.go).catch(function () {});
      }, true);
    }
  }

  frontend.register('practice-games', {
    views: OWNED_VIEWS,
    owns: owns,
    render: render,
    navigate: navigate,
    renderRoleplay: renderRoleplay,
    answerScenario: answerScenario,
    renderGames: renderGames,
    startGame: startGame,
    renderXP: renderXP,
    buyReward: buyReward,
    install: install
  });

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', install, {once: true});
  } else {
    install();
  }
})(typeof window !== 'undefined' ? window : globalThis);
