/* v6.0.6: canonical ownership for AI assistant and practical knowledge views. */
(function (root) {
  'use strict';

  const frontend = root.MGCFrontend;
  if (!frontend) throw new Error('MGCFrontend runtime is missing');
  if (frontend.has('assistant-knowledge')) return;

  const OWNED_VIEWS = Object.freeze(['assistant', 'knowledge']);
  const owned = new Set(OWNED_VIEWS);
  let installed = false;

  function legacy() { return frontend.get('legacy-app'); }
  function state() { return frontend.get('app-state'); }
  function api() { return frontend.get('api-client'); }

  function owns(view) {
    return owned.has(String(view || ''));
  }

  function featureEnabled(view) {
    if (String(view || '') !== 'assistant') return true;
    const current = state().current();
    const flags = (current.pilot && current.pilot.features) || {};
    return flags.ai_assistant !== false;
  }

  function assertFeature(view) {
    if (!featureEnabled(view)) {
      throw new Error('Эта функция пока не включена для вашей волны пилота');
    }
  }

  function reportError(scope, error) {
    if (!frontend.has('error-boundary')) return;
    frontend.get('error-boundary').record(
      String(scope || 'assistant-knowledge'),
      error && error.message ? error.message : error,
      '', 0, 0
    );
  }

  function pageHead(kicker, title, subtitle) {
    const esc = legacy().escapeHtml;
    return '<div class="page-head"><div><div class="kicker">' + esc(kicker) +
      '</div><h1>' + esc(title) + '</h1><p>' + esc(subtitle) + '</p></div></div>';
  }

  function termCard(item) {
    const esc = legacy().escapeHtml;
    const current = state().current();
    const lang = item.language || current.language;
    const pronunciationClass = lang === 'chinese' ? 'pinyin' : 'ipa-line';
    const examplePronClass = lang === 'chinese' ? 'pinyin-line' : 'ipa-line';
    const meta = String(item.level || '') + ' · ' + String(item.topic || '') + (item.shop ? ' · ' + item.shop : '');
    return '<article class="term-card"><div class="meta">' + esc(meta) + '</div>' +
      '<div class="target">' + esc(item.term) + '</div>' +
      (item.pronunciation ? '<div class="' + pronunciationClass + '">' + esc(item.pronunciation) + '</div>' : '') +
      (item.reading ? '<div class="reading-line">≈ ' + esc(item.reading) + ' <small>как читать</small></div>' : '') +
      '<div class="pronunciation-actions"><button class="listen-button" data-speak-text="' + esc(item.term) +
      '" data-speak-language="' + esc(lang) + '" data-speak-rate="0.9">▶ Послушать</button>' +
      '<button class="listen-button subtle" data-speak-text="' + esc(item.term) + '" data-speak-language="' + esc(lang) +
      '" data-speak-rate="0.68">0.7×</button></div>' +
      '<div class="translation">' + esc(item.translation) + '</div>' +
      (item.example && item.example !== item.term ? '<div class="term-example"><div class="example-head"><span>' +
        esc(item.example) + '</span><button class="mini-listen" data-speak-text="' + esc(item.example) +
        '" data-speak-language="' + esc(lang) + '" data-speak-rate="0.86">▶</button></div>' +
        (item.example_pronunciation ? '<div class="' + examplePronClass + '">' + esc(item.example_pronunciation) + '</div>' : '') +
        '<span>' + esc(item.example_translation) + '</span></div>' : '') + '</article>';
  }

  function renderAssistant() {
    const current = state().current();
    const esc = legacy().escapeHtml;
    const examples = current.language === 'english'
      ? ['How do I discuss a welding defect?', 'Phrase for escalating an SOP risk', 'How do I request a cost breakdown?']
      : ['如何讨论焊接缺陷？', '如何升级量产风险？', '如何要求提供成本明细？'];
    const main = legacy().query('#main');
    if (!main) throw new Error('Assistant view missing #main');

    main.innerHTML = pageHead(
      'Помощник по базе',
      'ИИ-помощник',
      'Находит подходящие термины и проверенные рабочие формулировки на выбранном языке.'
    ) + '<div class="tool-layout"><div class="card"><label>Вопрос<textarea id="assistantQuestion" placeholder="Опишите рабочую ситуацию"></textarea></label>' +
      '<div class="chip-row examples-row">' + examples.map(function (item) {
        return '<button class="topic-chip" data-ai-example="' + esc(item) + '">' + esc(item) + '</button>';
      }).join('') + '</div><button id="askAssistant" class="primary wide">Найти формулировку</button></div>' +
      '<div id="assistantResult" class="answer-box"><b>Как пользоваться</b><p>Опишите задачу своими словами: дефект, переговоры, запуск, финансы или производство.</p></div></div>';

    legacy().queryAll('[data-ai-example]').forEach(function (button) {
      button.addEventListener('click', function () {
        const input = legacy().query('#assistantQuestion');
        if (input) input.value = button.dataset.aiExample;
      });
    });
    const ask = legacy().query('#askAssistant');
    if (ask) ask.addEventListener('click', function () { void askAssistant(); });
  }

  async function askAssistant() {
    const current = state().current();
    const input = legacy().query('#assistantQuestion');
    const resultBox = legacy().query('#assistantResult');
    const question = input ? input.value.trim() : '';
    if (!question) {
      legacy().toast('Введите вопрос');
      return;
    }
    if (!resultBox) throw new Error('Assistant result container is missing');
    resultBox.innerHTML = '<span class="spinner"></span>';
    try {
      const data = await api().request('/api/assistant', {
        method: 'POST',
        body: JSON.stringify({language: current.language, question: question})
      });
      const evidence = Array.isArray(data.evidence) ? data.evidence : [];
      resultBox.innerHTML = '<b>' + legacy().escapeHtml(data.answer) + '</b><div class="result-list">' +
        evidence.map(termCard).join('') + '</div><p class="muted">' + legacy().escapeHtml(data.note) + '</p>';
    } catch (error) {
      resultBox.innerHTML = '<b>Ошибка</b><p>' + legacy().escapeHtml(error && error.message ? error.message : error) + '</p>';
      reportError('assistant-request', error);
    }
  }

  function renderKnowledgeDetail(item) {
    const current = state().current();
    const esc = legacy().escapeHtml;
    const main = legacy().query('#main');
    if (!main) throw new Error('Knowledge view missing #main');

    main.innerHTML = '<button id="backKnowledge" class="ghost">← База знаний</button>' +
      pageHead(item.topic, item.title, item.situation) +
      '<div class="knowledge-detail"><section class="card"><div class="kicker">Что делать</div><ol class="knowledge-steps">' +
      (Array.isArray(item.steps) ? item.steps : []).map(function (step) { return '<li>' + esc(step) + '</li>'; }).join('') +
      '</ol><div class="avoid-box"><b>Не делайте так</b><p>' + esc(item.avoid) + '</p></div></section>' +
      '<section class="card phrase-panel"><div class="kicker">Рабочая формулировка</div><div class="target-line">' + esc(item.target) + '</div>' +
      (item.pronunciation ? '<div class="pinyin-line">' + esc(item.pronunciation) + '</div>' : '') +
      '<div class="translation-line">' + esc(item.translation) + '</div><div class="pronunciation-actions">' +
      '<button class="listen-button" data-speak-text="' + esc(item.target) + '" data-speak-language="' + esc(current.language) + '">▶ Послушать</button></div>' +
      '<button class="primary wide" data-go="roleplay" data-topic="' + esc(item.topic) + '">Отработать похожий сценарий</button></section></div>';

    const back = legacy().query('#backKnowledge');
    if (back) {
      back.addEventListener('click', function () {
        state().set('knowledgeId', null);
        void renderKnowledge();
      });
    }
  }

  function renderKnowledgeList(items) {
    const current = state().current();
    const esc = legacy().escapeHtml;
    const main = legacy().query('#main');
    if (!main) throw new Error('Knowledge view missing #main');
    const activeTopic = current.knowledgeTopic || 'Все';
    const topics = ['Все'].concat(Array.from(new Set(items.map(function (item) { return item.topic; }))));
    const filtered = activeTopic === 'Все' ? items : items.filter(function (item) { return item.topic === activeTopic; });

    main.innerHTML = pageHead(
      'Практические инструкции',
      'База знаний',
      'Реальные рабочие ситуации: что проверить, чего избегать и какую фразу использовать.'
    ) + '<div class="chip-row knowledge-filter">' + topics.map(function (topic) {
      return '<button class="topic-chip ' + (topic === activeTopic ? 'active' : '') + '" data-knowledge-topic="' +
        esc(topic) + '">' + esc(topic) + '</button>';
    }).join('') + '</div><div class="knowledge-grid">' + filtered.map(function (item, index) {
      return '<button class="knowledge-card" data-knowledge="' + esc(item.id) + '"><div class="kicker">Ситуация ' +
        String(index + 1).padStart(2, '0') + ' · ' + esc(item.topic) + '</div><h3>' + esc(item.title) + '</h3><p>' +
        esc(item.situation) + '</p><span>Открыть инструкцию →</span></button>';
    }).join('') + '</div>';

    legacy().queryAll('[data-knowledge-topic]').forEach(function (button) {
      button.addEventListener('click', function () {
        state().set('knowledgeTopic', button.dataset.knowledgeTopic);
        void renderKnowledge();
      });
    });
    legacy().queryAll('[data-knowledge]').forEach(function (button) {
      button.addEventListener('click', function () {
        state().set('knowledgeId', button.dataset.knowledge);
        void renderKnowledge();
      });
    });
  }

  async function renderKnowledge() {
    const current = state().current();
    let items = Array.isArray(current.knowledgeItems) ? current.knowledgeItems : [];
    if (!items.length) {
      items = await api().request('/api/knowledge?language=' + encodeURIComponent(current.language));
      if (!Array.isArray(items)) items = [];
      state().set('knowledgeItems', items);
    }

    const selectedId = state().get('knowledgeId');
    if (selectedId) {
      const item = items.find(function (row) { return String(row.id) === String(selectedId); });
      if (item) {
        renderKnowledgeDetail(item);
        return;
      }
      state().set('knowledgeId', null);
    }
    renderKnowledgeList(items);
  }

  async function render(view) {
    const target = String(view || state().get('view') || 'assistant');
    if (!owns(target)) throw new Error('Assistant/knowledge module does not own view: ' + target);
    assertFeature(target);
    if (target === 'assistant') {
      renderAssistant();
      return;
    }
    await renderKnowledge();
  }

  async function navigate(view) {
    const target = String(view || 'assistant');
    if (!owns(target)) return legacy().setView(target);
    assertFeature(target);

    state().set('view', target);
    legacy().closeMenu();
    legacy().queryAll('[data-view]').forEach(function (button) {
      button.classList.toggle('active', button.dataset.view === target);
    });

    const main = legacy().query('#main');
    if (main) main.innerHTML = '<div class="loading-card"><span class="spinner"></span><p>Загрузка</p></div>';

    try {
      await render(target);
    } catch (error) {
      if (main) {
        main.innerHTML = '<div class="empty"><h2>Не удалось открыть раздел</h2><p>' +
          legacy().escapeHtml(error && error.message ? error.message : error) +
          '</p><button class="primary" data-go="home">На главную</button></div>';
      }
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
      navigate(button.dataset.view).catch(function (error) {
        reportError('assistant-knowledge-navigation', error);
      });
    }, true);
  }

  frontend.register('assistant-knowledge', {
    views: OWNED_VIEWS,
    owns: owns,
    render: render,
    navigate: navigate,
    askAssistant: askAssistant,
    renderKnowledge: renderKnowledge,
    install: install
  });

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', install, {once: true});
  } else {
    install();
  }
})(typeof window !== 'undefined' ? window : globalThis);
