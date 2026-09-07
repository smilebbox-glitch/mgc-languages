/* v6.0.14: canonical core learning UI, language switch and learning preferences. */
(function (root) {
  'use strict';

  const frontend = root.MGCFrontend;
  if (!frontend) throw new Error('MGCFrontend runtime is missing');
  if (frontend.has('learning')) return;

  const OWNED_VIEWS = Object.freeze(['home', 'topics', 'quiz', 'course30']);
  const owned = new Set(OWNED_VIEWS);
  let installed = false;

  function legacy() { return frontend.get('legacy-app'); }
  function state() { return frontend.get('app-state'); }
  function api() { return frontend.get('api-client'); }
  function current() { return state().current(); }
  function esc(value) { return legacy().escapeHtml(value); }
  function query(selector, scope) { return legacy().query(selector, scope); }
  function queryAll(selector, scope) { return legacy().queryAll(selector, scope); }
  function toast(message) { legacy().toast(String(message || '')); }
  function navigation() { return frontend.get('navigation'); }

  function owns(view) {
    return owned.has(String(view || ''));
  }

  function reportError(scope, error) {
    if (!frontend.has('error-boundary')) return;
    frontend.get('error-boundary').record(
      String(scope || 'learning'),
      error && error.message ? error.message : error,
      '', 0, 0
    );
  }

  function featureEnabled(key) {
    const flags = (current().pilot && current().pilot.features) || {};
    return flags[key] !== false;
  }

  function languageName() {
    return current().language === 'english' ? 'английский' : 'китайский';
  }

  function targetLabel() {
    return current().language === 'english' ? 'English' : '中文 · 普通话';
  }

  function pageHead(kicker, title, subtitle) {
    return '<div class="page-head"><div><div class="kicker">' + esc(kicker) +
      '</div><h1>' + esc(title) + '</h1><p>' + esc(subtitle) + '</p></div></div>';
  }

  function levelChips(active) {
    return ['A1', 'A2', 'B1', 'B2', 'C1'].map(function (level) {
      return '<button class="level-chip ' + (level === active ? 'active' : '') +
        '" data-level="' + level + '">' + level + '</button>';
    }).join('');
  }

  function topicCards(limit) {
    const snapshot = current();
    const all = Array.isArray(snapshot.topics) ? snapshot.topics : [];
    const topics = typeof limit === 'number' ? all.slice(0, limit) : all;
    return topics.map(function (topic, index) {
      const examples = (topic.examples || []).map(function (item) {
        return '<span>' + esc(item) + '</span>';
      }).join('');
      return '<button class="topic-card" data-open-topic="' + esc(topic.label) + '">' +
        '<span class="topic-icon">' + String(index + 1).padStart(2, '0') + '</span>' +
        '<h3>' + esc(topic.label) + '</h3><p>' + esc(topic.description) + '</p>' +
        '<div class="topic-examples">' + examples + '</div><small>' + Number(topic.count || 0) +
        ' терминов · открыть →</small></button>';
    }).join('');
  }

  function bindTopicCards() {
    queryAll('[data-open-topic]').forEach(function (button) {
      button.addEventListener('click', function () {
        state().patch({topic: button.dataset.openTopic, topicDetail: button.dataset.openTopic});
        void navigate('topics');
      });
    });
  }

  function bindLevelSelection(rerender) {
    const main = query('#main');
    queryAll('[data-level]', main).forEach(function (button) {
      button.addEventListener('click', function () {
        state().set('level', button.dataset.level);
        if (rerender) {
          void render(current().view);
          return;
        }
        queryAll('[data-level]', main).forEach(function (item) {
          item.classList.toggle('active', item.dataset.level === current().level);
        });
        const description = query('#levelDescription');
        if (description && current().summary && current().summary.level_labels) {
          description.textContent = current().summary.level_labels[current().level] || '';
        }
      });
    });
  }

  function topicOptions(selected) {
    return (current().topics || []).map(function (topic) {
      return '<option value="' + esc(topic.label) + '" ' +
        (topic.label === selected ? 'selected' : '') + '>' + esc(topic.label) + '</option>';
    }).join('');
  }

  function termCard(item) {
    const lang = item.language || current().language;
    const pronunciationClass = lang === 'chinese' ? 'pinyin' : 'ipa-line';
    const examplePronClass = lang === 'chinese' ? 'pinyin-line' : 'ipa-line';
    const meta = String(item.level || '') + ' · ' + String(item.topic || '') +
      (item.shop ? ' · ' + item.shop : '');
    return '<article class="term-card"><div class="meta">' + esc(meta) + '</div>' +
      '<div class="target">' + esc(item.term) + '</div>' +
      (item.pronunciation ? '<div class="' + pronunciationClass + '">' + esc(item.pronunciation) + '</div>' : '') +
      (item.reading ? '<div class="reading-line">≈ ' + esc(item.reading) + ' <small>как читать</small></div>' : '') +
      '<div class="pronunciation-actions"><button class="listen-button" data-speak-text="' + esc(item.term) +
      '" data-speak-language="' + esc(lang) + '" data-speak-rate="0.9">▶ Послушать</button>' +
      '<button class="listen-button subtle" data-speak-text="' + esc(item.term) + '" data-speak-language="' +
      esc(lang) + '" data-speak-rate="0.68">0.7×</button></div>' +
      '<div class="translation">' + esc(item.translation) + '</div>' +
      (item.example && item.example !== item.term ? '<div class="term-example"><div class="example-head"><span>' +
        esc(item.example) + '</span><button class="mini-listen" data-speak-text="' + esc(item.example) +
        '" data-speak-language="' + esc(lang) + '" data-speak-rate="0.86">▶</button></div>' +
        (item.example_pronunciation ? '<div class="' + examplePronClass + '">' + esc(item.example_pronunciation) + '</div>' : '') +
        '<span>' + esc(item.example_translation) + '</span></div>' : '') + '</article>';
  }

  function xpPanelHTML() {
    const g = current().gamification || {
      level: 1, title: 'Новичок I', lifetime_xp: 0, spendable_xp: 0,
      weekly_xp: 0, progress_xp: 0, level_xp: 500
    };
    const pct = Math.min(100, Math.round((g.progress_xp || 0) * 100 / Math.max(1, g.level_xp || 500)));
    return '<section class="xp-overview card"><div><div class="kicker">УРОВЕНЬ ' + Number(g.level || 1) +
      '</div><h2>' + esc(g.title) + '</h2><p>Lifetime: <b>' + Number(g.lifetime_xp || 0) +
      ' XP</b> · доступно для помощи: <b>' + Number(g.spendable_xp || 0) + ' XP</b> · неделя: ' +
      Number(g.weekly_xp || 0) + ' XP</p></div><div class="xp-levelbar"><i style="width:' + pct +
      '%"></i></div><button class="ghost" data-go="xp">Использовать XP →</button></section>';
  }

  function nudgeHTML() {
    const nudges = current().nudges || [];
    if (!nudges.length) return '';
    const item = nudges[0];
    return '<section class="nudge-card"><div><div class="kicker">НЕНАВЯЗЧИВОЕ НАПОМИНАНИЕ</div><h3>' +
      esc(item.title) + '</h3><p>' + esc(item.body) + '</p></div><div class="actions">' +
      '<button class="primary" data-nudge-open="' + esc(item.id) + '" data-target="' +
      esc(item.target_view || 'home') + '">Открыть</button><button class="ghost" data-nudge-dismiss="' +
      esc(item.id) + '">Не сейчас</button></div></section>';
  }

  function pilotCohortHTML() {
    const pilot = current().pilot || {};
    const groups = (pilot.groups || []).filter(function (group) { return group.active; });
    if (!groups.length) return '';
    const wave = pilot.wave == null ? '—' : pilot.wave;
    return '<section class="pilot-cohort-strip"><div><b>Пилот · Wave ' + esc(wave) + '</b><span>' +
      groups.map(function (group) { return esc(group.name); }).join(' · ') +
      '</span></div><small>Функции могут включаться поэтапно для вашей группы.</small></section>';
  }

  async function renderHome() {
    const snapshot = current();
    const summary = snapshot.summary || {progress: {}, level_labels: {}};
    const progress = summary.progress || {};
    const pilot = snapshot.pilot || {};
    const assignments = pilot.assignments || [];
    const title = snapshot.language === 'english' ? 'Английский для автопрома' : 'Путунхуа для автопрома';
    const accent = snapshot.language === 'english' ? 'ENGLISH' : '中文';
    const main = query('#main');
    if (!main) throw new Error('Learning home missing #main');

    main.innerHTML = '<section class="hero"><div class="kicker">MGC LANGUAGE LAB · ' + esc(targetLabel()) +
      '</div><h1>' + esc(title) + '<br><span>' + accent + '</span></h1>' +
      '<p>Термины, реальные рабочие ситуации и тренировка коммуникации в Автопромышленности.</p>' +
      '<div class="hero-actions"><button class="primary" data-go="topics">Выбрать тему</button>' +
      '<button class="ghost" data-go="roleplay">Начать сценарий</button></div></section>' +
      pilotCohortHTML() +
      (assignments.length ? '<section class="card pilot-assignments"><div class="kicker">МОЙ ПИЛОТНЫЙ ТРЕК</div>' +
        '<h3>Назначено вашей группе</h3>' + assignments.map(function (assignment) {
          return '<div class="pilot-assignment"><b>' + esc(assignment.track_name) + '</b><span>' +
            (assignment.language === 'chinese' ? 'Путунхуа / 中文' : 'English') +
            (assignment.topic ? ' · ' + esc(assignment.topic) : '') + ' · цель ' + esc(assignment.target_level) +
            (assignment.due_date ? ' · до ' + esc(assignment.due_date) : '') + '</span></div>';
        }).join('') + '</section>' : '') +
      nudgeHTML() + (featureEnabled('xp_economy') ? xpPanelHTML() : '') +
      '<div class="grid three"><button class="card action-card" data-go="topics"><span class="number">01</span>' +
      '<h3>Темы</h3><p>Слова и рабочие фразы по цехам и функциям.</p></button>' +
      '<button class="card action-card" data-go="quiz"><span class="number">02</span><h3>Тест</h3>' +
      '<p>Короткая проверка по выбранной теме и уровню.</p></button>' +
      '<button class="card action-card" data-go="roleplay"><span class="number">03</span><h3>Сценарии</h3>' +
      '<p>Мини-игра с решениями для реальных рабочих разговоров.</p></button></div>' +
      '<div class="section-title"><h2>Уровень обучения</h2></div><div class="card"><div class="level-strip">' +
      levelChips(snapshot.level) + '</div><p class="muted" id="levelDescription">' +
      esc((summary.level_labels || {})[snapshot.level] || '') + '</p></div>' +
      '<div class="section-title"><h2>Профессиональные темы</h2><button class="ghost" data-go="topics">Все ' +
      (snapshot.topics || []).length + '</button></div><div class="topic-grid">' + topicCards(9) + '</div>' +
      '<div class="section-title"><h2>Ваш прогресс</h2></div><div class="progress-dashboard">' +
      '<button class="progress-tile" data-go="topics"><b>' + Number(progress.percent || 0) +
      '%</b><span>терминов изучено</span></button><button class="progress-tile" data-go="course30"><b>' +
      Number(progress.completed_days || 0) + '/30</b><span>дней курса завершено</span></button>' +
      '<button class="progress-tile" data-go="exam"><b>' + Number(progress.best_exam || 0) +
      '/50</b><span>' + (progress.exam_passed ? 'экзамен сдан' : 'лучший результат') + '</span></button></div>';

    bindLevelSelection(false);
    bindTopicCards();
    queryAll('[data-nudge-open]').forEach(function (button) {
      button.addEventListener('click', async function () {
        await api().request('/api/notifications/' + encodeURIComponent(button.dataset.nudgeOpen) + '/read', {method: 'POST'});
        state().set('nudges', (current().nudges || []).filter(function (item) {
          return String(item.id) !== String(button.dataset.nudgeOpen);
        }));
        await navigation().setView(button.dataset.target || 'home');
      });
    });
    queryAll('[data-nudge-dismiss]').forEach(function (button) {
      button.addEventListener('click', async function () {
        await api().request('/api/notifications/' + encodeURIComponent(button.dataset.nudgeDismiss) + '/read', {method: 'POST'});
        state().set('nudges', (current().nudges || []).filter(function (item) {
          return String(item.id) !== String(button.dataset.nudgeDismiss);
        }));
        await renderHome();
      });
    });
  }

  async function renderTopics() {
    const snapshot = current();
    const main = query('#main');
    if (!main) throw new Error('Topics view missing #main');
    if (!snapshot.topicDetail) {
      main.innerHTML = pageHead(
        'Отраслевой словарь',
        'Темы',
        'Выберите конкретный процесс или функцию — слова не смешиваются в одну длинную ленту.'
      ) + '<div class="topic-grid">' + topicCards() + '</div>';
      bindTopicCards();
      return;
    }

    state().set('topic', snapshot.topicDetail);
    const result = await api().request('/api/language/' + encodeURIComponent(snapshot.language) +
      '/terms?topic=' + encodeURIComponent(snapshot.topicDetail) + '&limit=500');
    const items = Array.isArray(result.items) ? result.items : [];
    main.innerHTML = '<div class="topic-detail-head"><button id="allTopics" class="ghost">← Все темы</button>' +
      '<div><div class="kicker">Словарь темы</div><h1>' + esc(snapshot.topicDetail) + '</h1><p>' +
      Number(result.total || items.length) + ' терминов по уровням A1–C1.</p></div></div>' +
      '<div class="topic-actions"><button class="primary" data-go="quiz" data-topic="' + esc(snapshot.topicDetail) +
      '">Пройти тест</button><button class="secondary" data-go="roleplay" data-topic="' + esc(snapshot.topicDetail) +
      '">Открыть сценарии</button></div><div class="filter-bar"><div class="level-strip">' +
      '<button class="level-chip active" data-topic-level="ALL">Все</button>' +
      ['A1', 'A2', 'B1', 'B2', 'C1'].map(function (level) {
        return '<button class="level-chip" data-topic-level="' + level + '">' + level + '</button>';
      }).join('') + '</div></div><div id="topicTerms" class="term-list">' + items.map(termCard).join('') + '</div>';

    const allTopics = query('#allTopics');
    if (allTopics) allTopics.addEventListener('click', function () {
      state().set('topicDetail', null);
      void renderTopics();
    });
    queryAll('[data-topic-level]').forEach(function (button) {
      button.addEventListener('click', function () {
        queryAll('[data-topic-level]').forEach(function (item) {
          item.classList.toggle('active', item === button);
        });
        const level = button.dataset.topicLevel;
        const filtered = level === 'ALL' ? items : items.filter(function (item) { return item.level === level; });
        const target = query('#topicTerms');
        if (target) target.innerHTML = filtered.length ? filtered.map(termCard).join('') :
          '<div class="empty">На этом уровне пока нет терминов.</div>';
      });
    });
  }

  async function buyQuizHelp(rewardId, question) {
    try {
      const snapshot = current();
      const result = await api().request('/api/gamification/spend', {
        method: 'POST',
        body: JSON.stringify({
          reward_id: rewardId,
          language: snapshot.language,
          context: {term_id: question.id, options: question.options}
        })
      });
      if (result.profile) state().set('gamification', result.profile);
      const pill = query('#xpPill');
      if (pill && current().gamification) pill.textContent = Number(current().gamification.spendable_xp || 0) + ' XP';
      const box = query('#quizHintBox');
      const value = result.result || {};
      if (value.type === 'eliminate') {
        queryAll('[data-answer]').forEach(function (button) {
          if (button.textContent === value.option) {
            button.disabled = true;
            button.classList.add('eliminated');
          }
        });
        if (box) box.innerHTML = '<div class="hint-result">Один неверный вариант убран · −' +
          Number(result.spent || 0) + ' XP</div>';
      } else if (value.type === 'audio') {
        await legacy().playPronunciation(value.text, value.rate || 0.7, snapshot.language);
        if (box) box.innerHTML = '<div class="hint-result">Фраза произнесена медленнее · −' +
          Number(result.spent || 0) + ' XP</div>';
      } else {
        const text = value.text || value.target || 'Подсказка активирована';
        if (box) box.innerHTML = '<div class="hint-result">' + esc(text) + ' · −' +
          Number(result.spent || 0) + ' XP</div>';
      }
    } catch (error) {
      toast(error && error.message ? error.message : error);
      reportError('learning-quiz-help', error);
    }
  }

  async function renderQuiz() {
    const snapshot = current();
    const main = query('#main');
    if (!main) throw new Error('Quiz view missing #main');
    if (!snapshot.quiz) {
      main.innerHTML = pageHead(
        'Проверка знаний',
        'Тест по теме',
        'До 10 вопросов. Pinyin можно включать и выключать; произношение доступно отдельной кнопкой.'
      ) + '<div class="card quiz-setup"><label>Тема<select id="quizTopic">' + topicOptions(snapshot.topic) +
      '</select></label><div><div class="field-label">Уровень</div><div class="level-strip">' +
      levelChips(snapshot.level) + '</div></div><button id="startQuiz" class="primary">Начать тест</button></div>';
      const select = query('#quizTopic');
      if (select) select.addEventListener('change', function (event) { state().set('topic', event.target.value); });
      bindLevelSelection(false);
      const start = query('#startQuiz');
      if (start) start.addEventListener('click', function () { void startQuiz(); });
      return;
    }

    if (snapshot.quizIndex >= snapshot.quiz.length) {
      if (snapshot.practiceSessionId) {
        await legacy().submitPractice('quiz', snapshot.practiceSessionId, snapshot.quizScore, snapshot.quiz.length, snapshot.topic);
        state().set('practiceSessionId', null);
      }
      main.innerHTML = pageHead(
        'Тест завершён',
        'Результат',
        'Вы можете повторить тему или перейти к рабочим сценариям.'
      ) + '<div class="card exam-intro"><div class="result-score">' + Number(snapshot.quizScore || 0) + '/' +
      snapshot.quiz.length + '</div><p>Правильных ответов</p><div class="actions centered">' +
      '<button id="retryQuiz" class="primary">Пройти ещё раз</button><button data-go="roleplay" data-topic="' +
      esc(snapshot.topic) + '" class="secondary">Сценарии по теме</button></div></div>';
      const retry = query('#retryQuiz');
      if (retry) retry.addEventListener('click', function () {
        state().patch({quiz: null, quizIndex: 0, quizScore: 0, quizAnswered: false});
        void renderQuiz();
      });
      return;
    }

    const question = snapshot.quiz[snapshot.quizIndex];
    main.innerHTML = '<div class="quiz-stage"><div class="quiz-progress"><i style="width:' +
      (((snapshot.quizIndex + 1) / snapshot.quiz.length) * 100) + '%"></i></div><div class="card question-card">' +
      '<div class="kicker">' + esc(question.level + ' · ' + question.topic + ' · ' +
      (snapshot.quizIndex + 1) + '/' + snapshot.quiz.length) + '</div><h2>' + esc(question.prompt) + '</h2>' +
      (question.pronunciation ? '<div class="' + (snapshot.language === 'chinese' ? 'question-pinyin' : 'ipa-line') +
        '">' + esc(question.pronunciation) + '</div>' : '') +
      (question.reading ? '<div class="reading-line">≈ ' + esc(question.reading) + ' <small>как читать</small></div>' : '') +
      (question.audio_text ? '<div class="pronunciation-actions"><button class="listen-button" data-speak-text="' +
        esc(question.audio_text) + '" data-speak-language="' + esc(snapshot.language) +
        '" data-speak-rate="0.88">▶ Послушать</button><button class="listen-button subtle" data-speak-text="' +
        esc(question.audio_text) + '" data-speak-language="' + esc(snapshot.language) +
        '" data-speak-rate="0.65">медленно</button></div>' : '') +
      '<div class="options">' + question.options.map(function (option, index) {
        return '<button class="option" data-answer="' + index + '">' + esc(option) + '</button>';
      }).join('') + '</div><div class="quiz-help"><button class="micro-action" data-buy-hint="hint_small">' +
      'Подсказка · 10 XP</button><button class="micro-action" data-buy-hint="eliminate_option">Убрать вариант · 20 XP</button>' +
      (snapshot.language === 'chinese' ? '<button class="micro-action" data-buy-hint="show_pinyin">Pinyin · 10 XP</button>' : '') +
      '</div><div id="quizHintBox"></div><div id="quizNextWrap"></div></div></div>';

    queryAll('[data-answer]').forEach(function (button) {
      button.addEventListener('click', function () { answerQuiz(Number(button.dataset.answer)); });
    });
    queryAll('[data-buy-hint]').forEach(function (button) {
      button.addEventListener('click', function () { void buyQuizHelp(button.dataset.buyHint, question); });
    });
  }

  async function startQuiz() {
    const snapshot = current();
    const data = await api().request('/api/language/' + encodeURIComponent(snapshot.language) + '/quiz?topic=' +
      encodeURIComponent(snapshot.topic) + '&level=' + encodeURIComponent(snapshot.level) + '&count=10');
    state().patch({
      quiz: Array.isArray(data.questions) ? data.questions : [],
      practiceSessionId: legacy().newSessionId('quiz'),
      quizIndex: 0,
      quizScore: 0,
      quizAnswered: false
    });
    await renderQuiz();
  }

  function answerQuiz(index) {
    const snapshot = current();
    if (snapshot.quizAnswered) return;
    const question = snapshot.quiz[snapshot.quizIndex];
    state().set('quizAnswered', true);
    if (index === question.correct_index) state().set('quizScore', Number(snapshot.quizScore || 0) + 1);
    queryAll('[data-answer]').forEach(function (button) {
      const value = Number(button.dataset.answer);
      if (value === question.correct_index) button.classList.add('correct');
      else if (value === index) button.classList.add('wrong');
      button.disabled = true;
    });
    const wrap = query('#quizNextWrap');
    if (!wrap) return;
    wrap.innerHTML = '<div class="answer-feedback"><b>' +
      (index === question.correct_index ? 'Верно' : 'Правильный ответ: ' + esc(question.options[question.correct_index])) +
      '</b><p>' + esc(question.explanation || '') + '</p></div><button id="quizNext" class="primary wide">' +
      (snapshot.quizIndex === snapshot.quiz.length - 1 ? 'Показать результат' : 'Следующий вопрос') + '</button>';
    const next = query('#quizNext');
    if (next) next.addEventListener('click', function () {
      state().patch({quizIndex: current().quizIndex + 1, quizAnswered: false});
      void renderQuiz();
    });
  }

  function makePairOptions(day, termIndex) {
    const correct = day.terms[termIndex];
    const others = day.terms.filter(function (_, index) { return index !== termIndex; }).slice(0, 2);
    return [correct].concat(others).map(function (item) {
      return {translation: item.translation, correct: item.id === correct.id};
    }).sort(function (a, b) { return a.translation.localeCompare(b.translation); });
  }

  async function renderCourse30() {
    const snapshot = current();
    const data = await api().request('/api/language/' + encodeURIComponent(snapshot.language) + '/course30');
    state().set('courseData', data);
    const latest = current();
    const days = Array.isArray(data.days) ? data.days : [];
    const day = days.find(function (item) { return item.day === latest.courseDay; }) || days[0];
    const main = query('#main');
    if (!main) throw new Error('Course30 view missing #main');
    if (!day) {
      main.innerHTML = pageHead('Учебная программа', '30 дней', 'Программа пока недоступна.');
      return;
    }
    if (latest.dayQuiz) {
      renderDayQuiz(day);
      return;
    }

    const pairTerm = day.terms[latest.pairIndex % day.terms.length];
    const pairOptions = makePairOptions(day, latest.pairIndex % day.terms.length);
    main.innerHTML = pageHead(
      'Учебная программа',
      '30 дней · ' + (latest.language === 'english' ? 'English' : '中文'),
      'Каждый день: новые термины, короткая активность, рабочий кейс и обязательный тест.'
    ) + '<div class="course-overview"><div><b>' + Number(data.completed_days || 0) +
      ' / 30 дней</b><span>завершено</span></div><div class="course-progress"><i style="width:' +
      (Number(data.completed_days || 0) / 30 * 100) + '%"></i></div><strong>' +
      Math.round(Number(data.completed_days || 0) / 30 * 100) + '%</strong></div>' +
      '<div class="day-grid">' + days.map(function (item) {
        return '<button class="day-card ' + (item.day === day.day ? 'active' : '') + ' ' +
          (item.completed ? 'completed' : '') + '" data-day="' + item.day + '"><b>' +
          (item.completed ? '✓' : item.day) + '</b><span>' + esc(item.level + ' · ' + item.topic) + '</span></button>';
      }).join('') + '</div><div class="section-title"><h2>' + esc(day.title) + '</h2><span class="day-score">' +
      (day.completed ? 'Лучший тест: ' + day.best_score + '/5' : 'Зачёт: 4/5') + '</span></div>' +
      '<div class="activity-steps">' + day.activities.map(function (activity, index) {
        return '<span class="' + (index === 0 || day.completed ? 'done' : '') + '"><b>' + (index + 1) +
          '</b>' + esc(activity) + '</span>';
      }).join('') + '</div><div class="grid two course-content"><section class="card"><div class="kicker">' +
      esc(day.level + ' · ' + languageName()) + '</div><h3>Термины дня</h3><p>' + esc(day.task) +
      '</p><div class="term-list compact">' + day.terms.map(termCard).join('') + '</div></section>' +
      '<section class="card pair-game"><div class="kicker">Активность</div><h3>Соберите пару</h3>' +
      '<p>Выберите перевод для термина.</p><div class="pair-target">' + esc(pairTerm.term) + '</div>' +
      (pairTerm.pronunciation ? '<div class="question-pinyin">' + esc(pairTerm.pronunciation) + '</div>' : '') +
      '<div class="options">' + pairOptions.map(function (option, index) {
        return '<button class="option" data-pair-answer="' + index + '" data-correct="' + option.correct + '">' +
          esc(option.translation) + '</button>';
      }).join('') + '</div><div id="pairFeedback"></div></section></div><div class="course-actions">' +
      '<button class="secondary" data-go="roleplay" data-topic="' + esc(day.topic) + '">Мини-кейс по теме</button>' +
      '<button id="startDayQuiz" class="primary">Пройти тест дня · 5 вопросов</button></div>';

    queryAll('[data-day]').forEach(function (button) {
      button.addEventListener('click', function () {
        state().patch({
          courseDay: Number(button.dataset.day), pairIndex: 0, pairAnswered: false,
          dayQuiz: null, dayQuizIndex: 0, dayQuizScore: 0, dayQuizAnswered: false
        });
        void renderCourse30();
      });
    });
    queryAll('[data-pair-answer]').forEach(function (button) {
      button.addEventListener('click', function () { void answerPair(button, day); });
    });
    const start = query('#startDayQuiz');
    if (start) start.addEventListener('click', function () {
      state().patch({dayQuiz: day.quiz, dayQuizIndex: 0, dayQuizScore: 0, dayQuizAnswered: false});
      void renderCourse30();
    });
  }

  async function answerPair(button, day) {
    const snapshot = current();
    if (snapshot.pairAnswered) return;
    state().set('pairAnswered', true);
    const correct = button.dataset.correct === 'true';
    queryAll('[data-pair-answer]').forEach(function (item) {
      item.disabled = true;
      if (item.dataset.correct === 'true') item.classList.add('correct');
    });
    if (!correct) button.classList.add('wrong');
    const practice = await legacy().submitPractice(
      'pair', legacy().newSessionId('pair-' + day.day + '-' + snapshot.pairIndex), correct ? 1 : 0, 1, day.topic
    );
    const earned = practice && practice.awarded ? practice.awarded : 0;
    const feedback = query('#pairFeedback');
    if (feedback) feedback.innerHTML = '<div class="answer-feedback"><b>' +
      (correct ? ('Верно · +' + earned + ' XP') : ('Пара показана выше' +
        (earned ? ' · +' + earned + ' XP за попытку' : ''))) +
      '</b></div><button id="nextPair" class="ghost wide">Следующий термин</button>';
    const next = query('#nextPair');
    if (next) next.addEventListener('click', function () {
      state().patch({pairIndex: (current().pairIndex + 1) % day.terms.length, pairAnswered: false});
      void renderCourse30();
    });
  }

  function renderDayQuiz(day) {
    const snapshot = current();
    const main = query('#main');
    if (!main || !snapshot.dayQuiz) return;
    if (snapshot.dayQuizIndex >= snapshot.dayQuiz.length) {
      const passed = snapshot.dayQuizScore >= 4;
      main.innerHTML = pageHead(
        'Тест дня завершён',
        passed ? 'День ' + day.day + ' пройден' : 'Нужно ещё одно повторение',
        passed ? 'Результат сохранён в вашем прогрессе.' : 'Для зачёта нужно минимум 4 правильных ответа из 5.'
      ) + '<div class="card exam-intro"><div class="result-score">' + snapshot.dayQuizScore +
      '/5</div><p>' + (passed ? 'Отлично — следующий день открыт.' : 'Повторите термины и попробуйте снова.') +
      '</p><button id="finishDayQuiz" class="primary">' + (passed ? 'Вернуться к курсу' : 'Повторить материал') +
      '</button></div>';
      const finish = query('#finishDayQuiz');
      if (finish) finish.addEventListener('click', async function () {
        if (passed) {
          const latest = current();
          await api().request('/api/course-day/result', {
            method: 'POST',
            body: JSON.stringify({language: latest.language, day: day.day, score: latest.dayQuizScore, total: 5})
          });
          await legacy().submitPractice(
            'course_day', legacy().newSessionId('course-' + latest.language + '-' + day.day),
            latest.dayQuizScore, 5, day.topic
          );
          state().set('summary', await api().request('/api/language/' + encodeURIComponent(latest.language) + '/summary'));
        }
        state().patch({dayQuiz: null, dayQuizIndex: 0, dayQuizScore: 0, dayQuizAnswered: false});
        await renderCourse30();
      });
      return;
    }

    const question = snapshot.dayQuiz[snapshot.dayQuizIndex];
    main.innerHTML = '<div class="quiz-stage"><button id="leaveDayQuiz" class="ghost">← К материалу дня</button>' +
      '<div class="quiz-progress"><i style="width:' + ((snapshot.dayQuizIndex + 1) * 20) + '%"></i></div>' +
      '<div class="card question-card"><div class="kicker">День ' + day.day + ' · вопрос ' +
      (snapshot.dayQuizIndex + 1) + ' из 5</div><h2>' + esc(question.prompt) + '</h2>' +
      (question.pronunciation ? '<div class="question-pinyin">' + esc(question.pronunciation) + '</div>' : '') +
      '<div class="options">' + question.options.map(function (option, index) {
        return '<button class="option" data-day-answer="' + index + '">' + esc(option) + '</button>';
      }).join('') + '</div><div id="dayQuizNext"></div></div></div>';
    const leave = query('#leaveDayQuiz');
    if (leave) leave.addEventListener('click', function () {
      state().patch({dayQuiz: null, dayQuizIndex: 0, dayQuizAnswered: false});
      void renderCourse30();
    });
    queryAll('[data-day-answer]').forEach(function (button) {
      button.addEventListener('click', function () { answerDayQuiz(question, Number(button.dataset.dayAnswer)); });
    });
  }

  function answerDayQuiz(question, index) {
    const snapshot = current();
    if (snapshot.dayQuizAnswered) return;
    state().set('dayQuizAnswered', true);
    if (index === question.correct_index) state().set('dayQuizScore', Number(snapshot.dayQuizScore || 0) + 1);
    queryAll('[data-day-answer]').forEach(function (button) {
      const value = Number(button.dataset.dayAnswer);
      if (value === question.correct_index) button.classList.add('correct');
      else if (value === index) button.classList.add('wrong');
      button.disabled = true;
    });
    const target = query('#dayQuizNext');
    if (!target) return;
    target.innerHTML = '<div class="answer-feedback"><b>' +
      (index === question.correct_index ? 'Верно' : 'Правильный ответ: ' + esc(question.options[question.correct_index])) +
      '</b><p>' + esc(question.explanation || '') + '</p></div><button id="nextDayQuestion" class="primary wide">' +
      (snapshot.dayQuizIndex === 4 ? 'Завершить тест' : 'Следующий вопрос') + '</button>';
    const next = query('#nextDayQuestion');
    if (next) next.addEventListener('click', function () {
      state().patch({dayQuizIndex: current().dayQuizIndex + 1, dayQuizAnswered: false});
      void renderCourse30();
    });
  }

  function applyLearningControls() {
    const snapshot = current();
    const chinese = snapshot.language === 'chinese';
    const flags = (snapshot.pilot && snapshot.pilot.features) || {};
    const basics = query('#chineseBasicsNav');
    if (basics) basics.classList.toggle('hidden', !chinese || flags.chinese_reference === false);
    const toggle = query('#pinyinToggle');
    if (toggle) {
      toggle.classList.toggle('hidden', !chinese);
      toggle.textContent = '拼 Pinyin: ' + (snapshot.learningPrefs.show_pinyin ? 'вкл' : 'выкл');
      toggle.classList.toggle('off', !snapshot.learningPrefs.show_pinyin);
    }
    document.body.classList.toggle('pinyin-off', chinese && !snapshot.learningPrefs.show_pinyin);
    document.body.classList.toggle('reading-off', !snapshot.learningPrefs.show_reading);
  }

  function resetLanguageState() {
    state().patch({
      topic: null,
      topicDetail: null,
      quiz: null,
      quizIndex: 0,
      quizScore: 0,
      quizAnswered: false,
      scenarioItems: [],
      scenarioTopic: 'Все',
      scenarioIndex: 0,
      scenarioScore: 0,
      scenarioAnswered: false,
      courseData: null,
      courseDay: 1,
      pairIndex: 0,
      pairAnswered: false,
      dayQuiz: null,
      dayQuizIndex: 0,
      dayQuizScore: 0,
      dayQuizAnswered: false,
      exam: null,
      examIndex: 0,
      examScore: 0,
      examAnswered: false,
      knowledgeItems: [],
      knowledgeId: null,
      knowledgeTopic: 'Все',
      level: 'A1',
      gameSession: null,
      gameAnswers: [],
      xpPack: null,
      practiceSessionId: null
    });
  }

  async function switchLanguage(language) {
    const target = String(language || '');
    if (!['english', 'chinese'].includes(target) || target === current().language) return;
    state().set('language', target);
    resetLanguageState();
    await api().request('/api/me/language', {
      method: 'POST',
      body: JSON.stringify({language: target})
    });
    await legacy().loadLanguage();
    applyLearningControls();
    await navigation().setView('home');
  }

  async function togglePinyin() {
    const snapshot = current();
    if (snapshot.language !== 'chinese') return;
    try {
      const next = Object.assign({}, snapshot.learningPrefs || {}, {
        show_pinyin: !(snapshot.learningPrefs && snapshot.learningPrefs.show_pinyin)
      });
      const saved = await api().request('/api/learning/preferences', {
        method: 'PUT',
        body: JSON.stringify(next)
      });
      state().set('learningPrefs', saved || next);
      applyLearningControls();
      toast(current().learningPrefs.show_pinyin ? 'Pinyin включён' : 'Pinyin скрыт');
      await navigation().setView(current().view || 'home');
    } catch (error) {
      toast(error && error.message ? error.message : error);
      reportError('learning-pinyin-toggle', error);
    }
  }

  async function render(view) {
    const target = String(view || current().view || 'home');
    if (!owns(target)) throw new Error('Learning module does not own view: ' + target);
    if (target === 'home') await renderHome();
    else if (target === 'topics') await renderTopics();
    else if (target === 'quiz') await renderQuiz();
    else await renderCourse30();
    legacy().ensureChineseStandardBanner();
  }

  function selectTopicFromElement(element) {
    if (!element || !element.dataset || !element.dataset.topic) return;
    const values = {topic: element.dataset.topic, scenarioTopic: element.dataset.topic};
    if (element.dataset.go === 'quiz') {
      Object.assign(values, {quiz: null, quizIndex: 0, quizScore: 0, quizAnswered: false});
    }
    state().patch(values);
  }

  async function navigate(view) {
    const target = String(view || 'home');
    if (!owns(target)) return legacy().setView(target);
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
      reportError('learning-navigation', error);
      throw error;
    }
  }

  function install() {
    if (installed) return;
    installed = true;

    document.addEventListener('click', function (event) {
      const language = event.target && event.target.closest ? event.target.closest('[data-language]') : null;
      if (language) {
        event.preventDefault();
        event.stopImmediatePropagation();
        switchLanguage(language.dataset.language).catch(function (error) {
          reportError('learning-language-switch', error);
        });
        return;
      }

      const pinyin = event.target && event.target.closest ? event.target.closest('#pinyinToggle') : null;
      if (pinyin) {
        event.preventDefault();
        event.stopImmediatePropagation();
        togglePinyin().catch(function () {});
        return;
      }

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
        selectTopicFromElement(go);
        navigate(go.dataset.go).catch(function () {});
      }, true);
    }
  }

  frontend.register('learning', {
    views: OWNED_VIEWS,
    owns: owns,
    render: render,
    navigate: navigate,
    renderHome: renderHome,
    renderTopics: renderTopics,
    renderQuiz: renderQuiz,
    renderCourse30: renderCourse30,
    startQuiz: startQuiz,
    answerQuiz: answerQuiz,
    switchLanguage: switchLanguage,
    togglePinyin: togglePinyin,
    install: install
  });

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', install, {once: true});
  } else {
    install();
  }
})(typeof window !== 'undefined' ? window : globalThis);
