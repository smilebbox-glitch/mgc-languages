/* v6.0.12: canonical Chinese reference, Putonghua foundations and Tone Lab. */
(function (root) {
  'use strict';

  const frontend = root.MGCFrontend;
  if (!frontend) throw new Error('MGCFrontend runtime is missing');
  if (frontend.has('chinese-reference')) return;

  const OWNED_VIEWS = Object.freeze(['chinese-basics']);
  const owned = new Set(OWNED_VIEWS);
  let installed = false;

  function legacy() { return frontend.get('legacy-app'); }
  function state() { return frontend.get('app-state'); }
  function api() { return frontend.get('api-client'); }
  function current() { return state().current(); }
  function esc(value) { return legacy().escapeHtml(value); }
  function query(selector) { return legacy().query(selector); }
  function queryAll(selector) { return legacy().queryAll(selector); }
  function list(value) { return Array.isArray(value) ? value : []; }

  function owns(view) {
    return owned.has(String(view || ''));
  }

  function featureEnabled() {
    const pilot = current().pilot || {};
    const flags = pilot.features || {};
    return flags.chinese_reference !== false;
  }

  function assertAvailable() {
    if (current().language !== 'chinese') throw new Error('Раздел доступен только для китайского языка');
    if (!featureEnabled()) throw new Error('Эта функция пока не включена для вашей волны пилота');
  }

  function reportError(scope, error) {
    if (!frontend.has('error-boundary')) return;
    frontend.get('error-boundary').record(
      String(scope || 'chinese-reference'),
      error && error.message ? error.message : error,
      '', 0, 0
    );
  }

  function pageHead(kicker, title, subtitle) {
    return '<div class="page-head"><div><div class="kicker">' + esc(kicker) + '</div><h1>' + esc(title) +
      '</h1><p>' + esc(subtitle) + '</p></div></div>';
  }

  function toneCardsHTML(data) {
    return '<div class="tone-grid">' + list(data.tones).map(function (tone) {
      return '<article class="tone-card tone-' + esc(tone.number) + '"><div class="tone-number">' +
        esc(tone.number || '·') + '</div><div><b>' + esc(tone.name) + ' тон · ' + esc(tone.gesture) +
        '</b><div class="tone-word">' + esc(tone.hanzi) + ' <span class="pinyin-line">' + esc(tone.pinyin) +
        '</span></div><p>' + esc(tone.ru) + ' · ' + esc(tone.hint) + '</p></div><button class="mini-listen" ' +
        'data-speak-text="' + esc(tone.hanzi) + '" data-speak-language="chinese" data-speak-rate="0.72">▶</button></article>';
    }).join('') + '</div>';
  }

  function soundGroupsHTML(groups, kind) {
    return list(groups).map(function (group) {
      const items = list(group.items).map(function (item) {
        const hanzi = item.example_hanzi || item.sample || '';
        const pinyin = item.example_pinyin || item.sample_pinyin || '';
        if (kind === 'final') {
          return '<div class="final-chip"><div><div class="sound-chip-head"><b>' + esc(item.pinyin) +
            '</b><button class="mini-listen" data-speak-text="' + esc(hanzi) + '" data-speak-language="chinese" ' +
            'data-speak-rate="0.72">▶</button></div><div><strong>' + esc(hanzi) + '</strong> <span class="pinyin-line">' +
            esc(pinyin) + '</span></div><small>≈ ' + esc(item.example_reading || '') + ' · ' +
            esc(item.hint || item.ru || '') + '</small></div></div>';
        }
        return '<div class="sound-chip"><div class="sound-chip-head"><b>' + esc(item.pinyin) +
          '</b><button class="mini-listen" data-speak-text="' + esc(hanzi) + '" data-speak-language="chinese" ' +
          'data-speak-rate="0.72">▶</button></div><span>≈ ' + esc(item.ru) + '</span><div class="sound-example"><strong>' +
          esc(hanzi) + '</strong><em class="pinyin-line">' + esc(pinyin) + '</em><small>≈ ' +
          esc(item.example_reading || '') + ' · ' + esc(item.example_ru || '') + '</small></div><small>' +
          esc(item.hint) + '</small></div>';
      }).join('');
      return '<section class="sound-group"><h3>' + esc(group.group) + '</h3><div class="' +
        (kind === 'final' ? 'final-grid' : 'sound-grid') + '">' + items + '</div></section>';
    }).join('');
  }

  function starterTermsHTML(data) {
    return list(data.starter_terms).map(function (item) {
      return '<article class="starter-word"><div><div class="target">' + esc(item.hanzi) +
        '</div><div class="pinyin-line">' + esc(item.pinyin) + '</div><div class="reading-line">≈ ' +
        esc(item.reading) + '</div><div class="translation">' + esc(item.ru) +
        '</div></div><div class="pronunciation-actions"><button class="listen-button" data-speak-text="' +
        esc(item.hanzi) + '" data-speak-language="chinese">▶</button><button class="listen-button subtle" ' +
        'data-speak-text="' + esc(item.hanzi) + '" data-speak-language="chinese" data-speak-rate="0.62">медленно</button></div></article>';
    }).join('');
  }

  function contextHTML(data) {
    const context = data.context || {};
    const example = context.example || {};
    const a = example.a || {};
    const b = example.b || {};
    return '<div class="section-title"><h2>' + esc(context.title || 'Контекст помогает понимать речь') +
      '</h2><span>но не отменяет тоны</span></div><section class="card"><p class="lead">' +
      esc(context.simple || '') + '</p><div class="friendly-steps compact">' + list(context.clues).map(function (clue, index) {
        return '<div><b>' + (index + 1) + '</b><p><strong>' + esc(clue.title) + '.</strong> ' + esc(clue.text) +
          '</p></div>';
      }).join('') + '</div><div class="warning-soft">' + esc(context.but || '') + '</div>' +
      (a.hanzi && b.hanzi ? '<div class="grid two"><div class="factory-phrase"><div><strong>' + esc(a.hanzi) +
        '</strong><span class="pinyin-line">' + esc(a.pinyin) + '</span><small>' + esc(a.ru) +
        '</small></div><button class="listen-button" data-speak-text="' + esc(a.hanzi) +
        '" data-speak-language="chinese">▶</button></div><div class="factory-phrase"><div><strong>' + esc(b.hanzi) +
        '</strong><span class="pinyin-line">' + esc(b.pinyin) + '</span><small>' + esc(b.ru) +
        '</small></div><button class="listen-button" data-speak-text="' + esc(b.hanzi) +
        '" data-speak-language="chinese">▶</button></div></div><p class="muted">' + esc(example.lesson || '') + '</p>' : '') +
      '</section>';
  }

  function putonghuaHTML(data) {
    const pt = data.putonghua || {};
    if (!pt.title) return '';
    const standard = data.learning_standard || {};
    const comparisons = list(pt.comparison_examples).map(function (item) {
      const base = item.standard || {};
      const variants = list(item.variants).map(function (variant) {
        return '<div class="dialect-variant"><div class="dialect-variant-head"><b>' + esc(variant.label) +
          '</b><small>' + esc(variant.place || '') + '</small></div><div class="dialect-phrase">' +
          esc(variant.text || '') + '</div><div class="dialect-roman">' + esc(variant.romanization || '') +
          ' <span>' + esc(variant.system || '') + '</span></div><div class="dialect-reading">' +
          esc(variant.reading_ru || '') + '</div><p>' + esc(variant.note || '') + '</p></div>';
      }).join('');
      return '<article class="dialect-compare-card"><div class="dialect-compare-title"><div><div class="kicker">' +
        'ОДИН СМЫСЛ · РАЗНЫЙ ЗВУК</div><h3>' + esc(item.meaning || '') + '</h3><p>' + esc(item.lesson || '') +
        '</p></div></div><div class="dialect-standard"><div><b>Путунхуа</b><div class="dialect-phrase">' +
        esc(base.text || '') + '</div><div class="pinyin-line">' + esc(base.romanization || '') +
        '</div><small>≈ ' + esc(base.reading_ru || '') + '</small></div>' +
        (base.audio ? '<button class="listen-button" data-speak-text="' + esc(base.text || '') +
          '" data-speak-language="chinese" data-speak-rate="0.78">▶ Путунхуа</button>' : '') +
        '</div><div class="dialect-variants">' + variants + '</div></article>';
    }).join('');
    const comparisonIntro = pt.comparison_intro || {};
    const accent = pt.accent_vs_dialect || {};
    const howMany = pt.how_many || {};

    return '<div class="section-title"><h2>Справка: Путунхуа и диалекты</h2><span>не отдельный учебный трек</span></div>' +
      '<section class="reference-only-strip"><b>Это справочная информация.</b><span>' +
      esc(standard.reference_message || 'Учить диалекты не нужно. Все уроки, тесты, XP и итоговый экзамен относятся к Путунхуа.') +
      '</span></section><section class="card putonghua-hero"><div class="putonghua-mark">普</div><div><div class="kicker">' +
      '普通话 · PǓTŌNGHUÀ</div><h2>' + esc(pt.title) + '</h2><p class="lead">' + esc(pt.simple) +
      '</p><div class="friendly-steps compact">' + list(pt.official_basis).map(function (line, index) {
        return '<div><b>' + (index + 1) + '</b><p>' + esc(line) + '</p></div>';
      }).join('') + '</div><div class="warning-soft">' + esc(pt.not_beijing_dialect || '') + '</div></div></section>' +
      '<section class="card workplace-language"><div><div class="kicker">НА ЗАВОДЕ</div><h2>Что вы услышите в реальной работе</h2><p>' +
      esc(pt.workplace || '') + '</p><div class="factory-phrase"><div><strong>请说普通话，可以吗？</strong>' +
      '<span class="pinyin-line">qǐng shuō pǔtōnghuà, kěyǐ ma?</span><small>Можно, пожалуйста, говорить на Путунхуа?</small></div>' +
      '<button class="listen-button" data-speak-text="请说普通话，可以吗？" data-speak-language="chinese" data-speak-rate="0.78">▶ Послушать</button></div></div></section>' +
      '<section class="card dialect-count"><div class="big-ten">10<span>крупных групп</span></div><div><h2>' +
      esc(howMany.headline || 'Так сколько в Китае диалектов?') + '</h2><p>' + esc(howMany.simple || '') +
      '</p><div class="warning-soft">' + esc(howMany.important || '') + '</div></div></section>' +
      '<div class="dialect-grid">' + list(pt.groups).map(function (group, index) {
        return '<details class="dialect-card"><summary><span class="dialect-number">' + (index + 1) +
          '</span><div><b>' + esc(group.zh) + ' · ' + esc(group.name) + '</b><small>' + esc(group.where) +
          '</small></div><span class="chevron">⌄</span></summary><div class="dialect-body"><p><b>Пример:</b> ' +
          esc(group.examples) + '</p><p>' + esc(group.friendly) + '</p></div></details>';
      }).join('') + '</div>' +
      (accent.title ? '<section class="card"><h2>' + esc(accent.title) + '</h2><div class="grid two"><div><b>Акцент</b><p>' +
        esc(accent.accent) + '</p></div><div><b>Диалект / местная разновидность</b><p>' + esc(accent.dialect) +
        '</p></div></div><div class="warning-soft">' + esc(accent.factory_tip || '') + '</div></section>' : '') +
      (comparisons ? '<section class="card dialect-comparison-intro"><div class="kicker">СРАВНИТЕ ГЛАЗАМИ И УШАМИ</div><h2>' +
        esc(comparisonIntro.title || 'Как один смысл звучит по-разному') + '</h2><p class="lead">' +
        esc(comparisonIntro.simple || '') + '</p><div class="warning-soft">' + esc(comparisonIntro.tone_note || '') +
        '</div><p class="muted">' + esc(comparisonIntro.audio_note || '') + '</p></section><div class="dialect-comparisons">' +
        comparisons + '</div><p class="muted dialect-safety">' + esc(pt.comparison_safety || '') + '</p>' : '') +
      (list(pt.mini_facts).length ? '<div class="section-title"><h2>Короткие ответы</h2></div><div class="knowledge-grid">' +
        list(pt.mini_facts).map(function (fact) { return '<article class="card"><h3>' + esc(fact.q) + '</h3><p>' +
          esc(fact.a) + '</p></article>'; }).join('') + '</div>' : '') +
      '<section class="reference-only-strip"><b>Главное</b><span>' + esc(pt.safe_message || '') +
      '</span></section><p class="muted">' + esc(pt.sources_note || '') + '</p>';
  }

  function referenceHTML(data) {
    const standard = data.learning_standard || {};
    const pinyin = data.pinyin || {};
    const pinyinExample = pinyin.example || {};
    const soundAdvice = data.sound_advice || {};
    const miniPath = list(data.mini_path);
    const toneChanges = data.tone_changes || {};

    return pageHead(
      standard.short_badge || 'УЧИМ: ПУТУНХУА 普通话',
      data.title || 'Информация о китайском',
      data.subtitle || 'Произношение, Pinyin и справка о региональных вариантах.'
    ) + '<section class="putonghua-learning-banner"><div class="putonghua-learning-icon">普</div><div><b>' +
      esc(standard.name || 'Путунхуа (普通话)') + '</b><span>' +
      esc(standard.primary_message || 'Основной китайский курс — стандартный Путунхуа.') +
      '</span></div><small>' + esc(standard.reference_message || 'Диалекты ниже — только справка, их не нужно учить.') +
      '</small></section><section class="card"><div class="kicker">СНАЧАЛА 4 ФАКТА</div><div class="friendly-steps">' +
      list(data.truths).map(function (truth, index) { return '<div><b>' + (index + 1) + '</b><p>' + esc(truth) +
        '</p></div>'; }).join('') + '</div></section><div class="section-title"><h2>' +
      esc(pinyin.title || 'Что такое Pinyin') + '</h2><span>карта произношения</span></div><section class="card"><p class="lead">' +
      esc(pinyin.simple || '') + '</p><div class="formula-box"><b>' + esc(pinyin.formula || '') +
      '</b></div>' + (pinyinExample.hanzi ? '<div class="factory-phrase"><div><strong>' + esc(pinyinExample.hanzi) +
        '</strong><span class="pinyin-line">' + esc(pinyinExample.pinyin) + '</span><small>≈ ' +
        esc(pinyinExample.reading) + ' · ' + esc(pinyinExample.ru) + '</small></div><button class="listen-button" ' +
        'data-speak-text="' + esc(pinyinExample.hanzi) + '" data-speak-language="chinese">▶ Послушать</button></div>' : '') +
      '<div class="warning-soft">' + esc(pinyin.warning || '') + '</div></section><div class="section-title"><h2>Пять тонов</h2>' +
      '<span>сначала направление голоса</span></div>' + toneCardsHTML(data) +
      '<section class="card tone-lab-card"><div class="section-title"><div><h2>Tone Lab · 5 звуков</h2><span>короткая практика без давления</span></div>' +
      '<button id="toneLabStart" class="primary">Начать</button></div><div id="toneLabBody"><p class="muted">Слушайте слог и выбирайте направление тона. Цель — научиться различать движение голоса.</p></div></section>' +
      (soundAdvice.title ? '<section class="card"><h2>' + esc(soundAdvice.title) + '</h2><ol class="checklist">' +
        list(soundAdvice.items).map(function (item) { return '<li>' + esc(item) + '</li>'; }).join('') + '</ol></section>' : '') +
      '<div class="section-title"><h2>Инициали</h2><span>звук, а не название латинской буквы</span></div>' +
      soundGroupsHTML(data.initials, 'initial') + '<div class="section-title"><h2>Финали</h2><span>слушайте целый слог</span></div>' +
      soundGroupsHTML(data.finals, 'final') + (data.sound_map_note ? '<p class="muted">' + esc(data.sound_map_note) + '</p>' : '') +
      '<div class="section-title"><h2>10 стартовых слов</h2><span>Путунхуа · рабочая база</span></div><div class="starter-word-grid">' +
      starterTermsHTML(data) + '</div>' + contextHTML(data) +
      (toneChanges.title ? '<section class="card"><h2>' + esc(toneChanges.title) + '</h2><ol class="checklist">' +
        list(toneChanges.items).map(function (item) { return '<li>' + esc(item) + '</li>'; }).join('') + '</ol></section>' : '') +
      (miniPath.length ? '<div class="section-title"><h2>Как проходить этот раздел</h2></div><div class="friendly-steps">' +
        miniPath.map(function (step) { return '<div><b>' + esc(step.step) + '</b><p><strong>' + esc(step.title) +
          '.</strong> ' + esc(step.text) + '</p></div>'; }).join('') + '</div>' : '') + putonghuaHTML(data);
  }

  async function loadFoundations() {
    assertAvailable();
    let data = current().chineseFoundations;
    if (!data) {
      data = await api().request('/api/chinese/foundations');
      state().set('chineseFoundations', data);
    }
    return data;
  }

  async function render() {
    assertAvailable();
    const data = await loadFoundations();
    const main = query('#main');
    if (!main) throw new Error('Chinese reference view missing #main');
    main.innerHTML = referenceHTML(data);
    const start = query('#toneLabStart');
    if (start) start.addEventListener('click', function () { startToneLab(data); });
    if (current().toneLab) renderToneLabRound();
  }

  function startToneLab(data) {
    assertAvailable();
    const rounds = list(data && data.tones).filter(function (tone) {
      return Number(tone.number) >= 1 && Number(tone.number) <= 4;
    });
    const deck = rounds.concat(rounds).sort(function () { return Math.random() - 0.5; }).slice(0, 5);
    state().set('toneLab', {
      deck: deck,
      index: 0,
      score: 0,
      answered: false,
      submitted: false,
      sessionId: legacy().newSessionId('tone-lab')
    });
    renderToneLabRound();
  }

  function submitToneLab(lab) {
    if (!lab || lab.submitted) return;
    lab.submitted = true;
    legacy().submitPractice('tone_lab', lab.sessionId, lab.score, lab.deck.length, 'Pinyin · тоны').then(function (result) {
      if (result && result.awarded) legacy().toast('Tone Lab: +' + result.awarded + ' XP');
    }).catch(function (error) {
      lab.submitted = false;
      reportError('tone-lab-submit', error);
    });
  }

  function renderToneLabRound() {
    const box = query('#toneLabBody');
    const lab = current().toneLab;
    if (!box || !lab) return;
    if (lab.index >= lab.deck.length) {
      box.innerHTML = '<div class="tone-lab-finish"><b>' + lab.score + ' / ' + lab.deck.length +
        '</b><p>Готово. Здесь цель — начать слышать направление тона, а не получить идеальный результат.</p>' +
        '<button id="toneLabAgain" class="secondary">Ещё 5 звуков</button></div>';
      submitToneLab(lab);
      const again = query('#toneLabAgain');
      if (again) again.addEventListener('click', function () { startToneLab(current().chineseFoundations); });
      return;
    }

    const tone = lab.deck[lab.index];
    const data = current().chineseFoundations || {};
    box.innerHTML = '<div class="tone-lab-question"><div class="kicker">ЗВУК ' + (lab.index + 1) + ' / ' +
      lab.deck.length + '</div><h3>Как движется голос?</h3><button class="audio-button" data-speak-text="' +
      esc(tone.hanzi) + '" data-speak-language="chinese" data-speak-rate="0.70">▶ Послушать слог</button>' +
      '<div class="tone-choice-grid">' + [1, 2, 3, 4].map(function (number) {
        const item = list(data.tones).find(function (candidate) { return Number(candidate.number) === number; }) || {};
        return '<button class="tone-choice" data-tone-choice="' + number + '"><b>' + number + '</b><span>' +
          esc(item.gesture || '') + '</span></button>';
      }).join('') + '</div><div id="toneLabFeedback"></div></div>';

    queryAll('[data-tone-choice]').forEach(function (button) {
      button.addEventListener('click', function () {
        if (lab.answered) return;
        lab.answered = true;
        const picked = Number(button.dataset.toneChoice);
        const correct = picked === Number(tone.number);
        if (correct) lab.score += 1;
        queryAll('[data-tone-choice]').forEach(function (choice) {
          choice.disabled = true;
          if (Number(choice.dataset.toneChoice) === Number(tone.number)) choice.classList.add('correct');
          else if (choice === button && !correct) choice.classList.add('wrong');
        });
        const feedback = query('#toneLabFeedback');
        if (feedback) feedback.innerHTML = '<div class="tone-lab-feedback ' + (correct ? 'ok' : 'no') + '"><b>' +
          (correct ? 'Верно' : 'Почти') + ': ' + esc(tone.number) + '-й тон — ' + esc(tone.gesture) +
          '</b><p>' + esc(tone.hanzi) + ' · <span class="pinyin-line">' + esc(tone.pinyin) + '</span> · ' +
          esc(tone.ru) + '. ' + esc(tone.hint) + '</p><button id="toneLabNext" class="primary">Дальше</button></div>';
        const next = query('#toneLabNext');
        if (next) next.addEventListener('click', function () {
          lab.index += 1;
          lab.answered = false;
          renderToneLabRound();
        });
      });
    });
  }

  async function navigate(view) {
    const target = String(view || 'chinese-basics');
    if (!owns(target)) return legacy().setView(target);
    if (current().language !== 'chinese') {
      if (frontend.has('navigation')) return frontend.get('navigation').setView('home');
      return legacy().setView('home');
    }
    assertAvailable();
    state().set('view', target);
    legacy().closeMenu();
    queryAll('[data-view]').forEach(function (button) {
      button.classList.toggle('active', button.dataset.view === target);
    });
    const main = query('#main');
    if (main) main.innerHTML = '<div class="loading-card"><span class="spinner"></span><p>Загрузка</p></div>';
    try {
      await render();
    } catch (error) {
      if (main) main.innerHTML = '<div class="empty"><h2>Не удалось открыть раздел</h2><p>' +
        esc(error && error.message ? error.message : error) + '</p><button class="primary" data-go="home">На главную</button></div>';
      reportError('chinese-reference-navigation', error);
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
      navigate(button.dataset.view).catch(function (error) { reportError('chinese-reference-click', error); });
    }, true);
  }

  frontend.register('chinese-reference', {
    views: OWNED_VIEWS,
    owns: owns,
    render: render,
    navigate: navigate,
    loadFoundations: loadFoundations,
    startToneLab: startToneLab,
    renderToneLabRound: renderToneLabRound,
    install: install
  });

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', install, {once: true});
  else install();
})(typeof window !== 'undefined' ? window : globalThis);
