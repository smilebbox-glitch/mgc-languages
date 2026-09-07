/* v6.0.9: canonical content-governance helpers for admin/editor surfaces. */
(function (root) {
  'use strict';

  const frontend = root.MGCFrontend;
  if (!frontend) throw new Error('MGCFrontend runtime is missing');
  if (frontend.has('content-governance')) return;

  const original = {
    adminContentHTML: typeof root.adminContentHTML === 'function' ? root.adminContentHTML : null,
    bindAdminContent: typeof root.bindAdminContent === 'function' ? root.bindAdminContent : null,
    adminTermCard: typeof root.adminTermCard === 'function' ? root.adminTermCard : null,
    questionQualityHTML: typeof root.questionQualityHTML === 'function' ? root.questionQualityHTML : null
  };

  function legacy() { return frontend.get('legacy-app'); }
  function state() { return frontend.get('app-state'); }
  function api() { return frontend.get('api-client'); }
  function current() { return state().current(); }

  function assertAccess() {
    const user = current().user || {};
    if (!['admin', 'editor'].includes(user.role)) throw new Error('Недостаточно прав');
  }

  function reportError(scope, error) {
    if (!frontend.has('error-boundary')) return;
    frontend.get('error-boundary').record(
      String(scope || 'content-governance'),
      error && error.message ? error.message : error,
      '', 0, 0
    );
  }

  function esc(value) { return legacy().escapeHtml(value); }
  function query(selector) { return legacy().query(selector); }
  function queryAll(selector) { return legacy().queryAll(selector); }
  function toast(message) { legacy().toast(message); }

  function questionQualityHTML(data) {
    if (!data) return '';
    const flagged = (data.items || []).filter(function (item) { return item.flag; }).slice(0, 8);
    return '<div class="section-title"><h2>Качество заданий</h2><span>adaptive telemetry</span></div>' +
      '<section class="card"><p class="muted">Сигнал для проверки контента, а не HR-оценка сотрудника.</p>' +
      (flagged.length ? '<div class="weak-topic-grid">' + flagged.map(function (item) {
        return '<div><b>' + esc(item.question_id) + '</b><span>' + Number(item.accuracy_percent || 0).toFixed(1) +
          '% · ' + Number(item.attempts || 0) + ' попыток</span><small>' + esc(item.topic || item.kind) + ' · ' +
          esc(item.flag) + '</small></div>';
      }).join('') + '</div>' : '<p>Пока нет вопросов, требующих проверки.</p>') + '</section>';
  }

  function adminTermCard(item) {
    const actions = [];
    const role = ((current().user || {}).role || '');
    if (item.status !== 'published') {
      actions.push('<button class="secondary mini" data-term-submit="' + esc(item.db_id) + '">На проверку</button>');
    }
    if (role === 'admin' && item.status === 'review') {
      actions.push('<button class="primary mini" data-term-approve="' + esc(item.db_id) + '">Утвердить</button>');
      actions.push('<button class="secondary mini" data-term-reject="' + esc(item.db_id) + '">Вернуть</button>');
    }
    actions.push('<button class="secondary mini" data-term-history="' + esc(item.db_id) + '">Версии</button>');
    return '<article class="term-card admin-governed-term"><div class="meta">' +
      esc(String(item.level || '') + ' · ' + String(item.topic || '') + ' · ' + String(item.status || '')) +
      '</div><div class="target">' + esc(item.term) + '</div><div class="translation">' + esc(item.translation) +
      '</div><div class="reading-line">Источник: ' + esc(item.source_type || 'manual') +
      (item.source_ref ? ' · ' + esc(item.source_ref) : '') + '</div><div class="pronunciation-actions">' +
      actions.join('') + '</div><div class="term-history-slot" data-term-history-slot="' + esc(item.db_id) + '"></div></article>';
  }

  function adminContentHTML() {
    assertAccess();
    const currentState = current();
    const taxonomy = currentState.adminTaxonomy || {levels: [], shops: [], topics: []};
    const terms = Array.isArray(currentState.adminTerms) ? currentState.adminTerms : [];
    return '<div class="section-title"><h2>Добавить термин</h2><span>English / 中文 · тема · цех</span></div>' +
      '<section class="card admin-term-form"><div class="grid three"><label>Язык<select id="termLanguage">' +
      '<option value="chinese">中文</option><option value="english">English</option></select></label>' +
      '<label>Уровень<select id="termLevel">' + (taxonomy.levels || []).map(function (x) { return '<option>' + esc(x) + '</option>'; }).join('') +
      '</select></label><label>Цех / функция<input id="termShop" list="shopList"></label></div>' +
      '<datalist id="shopList">' + (taxonomy.shops || []).map(function (x) { return '<option value="' + esc(x) + '">'; }).join('') + '</datalist>' +
      '<datalist id="topicList">' + (taxonomy.topics || []).map(function (x) { return '<option value="' + esc(x) + '">'; }).join('') + '</datalist>' +
      '<div class="grid two"><label>Тема<input id="termTopic" list="topicList" required></label><label>Подтема<input id="termSubtopic"></label></div>' +
      '<div class="grid two"><label>Термин<input id="termValue" required></label><label>Перевод<input id="termTranslation" required></label></div>' +
      '<div class="grid three"><label>Pinyin / IPA<input id="termPronunciation"></label><label>Как читать (приблизительно)<input id="termReading"></label><label>Tags<input id="termTags"></label></div>' +
      '<div class="grid two"><label>Источник<select id="termSourceType"><option value="manual">Ручной ввод</option>' +
      '<option value="company_standard">Стандарт компании</option><option value="supplier">Поставщик</option>' +
      '<option value="work_instruction">Рабочая инструкция</option><option value="engineering_document">Инженерный документ</option>' +
      '<option value="language_expert">Language Expert</option><option value="public_dictionary">Словарь</option>' +
      '<option value="ai_suggestion">AI suggestion</option></select></label><label>Ссылка / номер документа<input id="termSourceRef"></label></div>' +
      '<div class="grid two"><label>Пример<textarea id="termExample"></textarea></label><label>Перевод примера<textarea id="termExampleTranslation"></textarea></label></div>' +
      '<button id="createTerm" class="primary">Опубликовать термин</button></section>' +
      '<div class="section-title"><h2>Массовый импорт</h2><span>XLSX / CSV</span></div><section class="card">' +
      '<input id="termImport" type="file" accept=".xlsx,.csv"><button id="importTerms" class="secondary">Импортировать</button>' +
      '<p class="muted">Колонки: language, shop, topic, subtopic, level, term, pronunciation/pinyin, reading, translation, example, example_translation, tags, source_type, source_ref, status.</p></section>' +
      '<div class="section-title"><h2>Кастомные термины</h2><span>' + terms.length + '</span></div>' +
      '<div class="term-list compact">' + terms.slice(0, 30).map(adminTermCard).join('') + '</div>';
  }

  function value(selector) {
    const node = query(selector);
    return node ? node.value : '';
  }

  async function refreshLanguageAndAdmin() {
    if (frontend.has('navigation')) await frontend.get('navigation').loadLanguage();
    if (frontend.has('manager-admin')) await frontend.get('manager-admin').renderAdmin();
  }

  function bindAdminContent() {
    assertAccess();
    const create = query('#createTerm');
    if (create) create.addEventListener('click', async function () {
      try {
        const payload = {
          language: value('#termLanguage'), level: value('#termLevel'), shop: value('#termShop'),
          topic: value('#termTopic'), subtopic: value('#termSubtopic'), term: value('#termValue'),
          pronunciation: value('#termPronunciation'), reading: value('#termReading'), translation: value('#termTranslation'),
          example: value('#termExample'), example_translation: value('#termExampleTranslation'), tags: value('#termTags'),
          source_type: value('#termSourceType'), source_ref: value('#termSourceRef'), status: 'published'
        };
        await api().request('/api/admin/terms', {method: 'POST', body: JSON.stringify(payload)});
        toast('Термин опубликован');
        await refreshLanguageAndAdmin();
      } catch (error) {
        reportError('content-create-term', error);
        toast(error && error.message ? error.message : error);
      }
    });

    const importer = query('#importTerms');
    if (importer) importer.addEventListener('click', async function () {
      const input = query('#termImport');
      const file = input && input.files ? input.files[0] : null;
      if (!file) { toast('Выберите XLSX или CSV'); return; }
      const data = new FormData();
      data.append('file', file);
      try {
        const result = await api().request('/api/admin/terms/import?default_language=' + encodeURIComponent(current().language), {
          method: 'POST', body: data
        });
        toast('Импортировано: ' + Number(result.created || 0) + (result.error_count ? ' · ошибок: ' + result.error_count : ''));
        await refreshLanguageAndAdmin();
      } catch (error) {
        reportError('content-import-terms', error);
        toast(error && error.message ? error.message : error);
      }
    });

    queryAll('[data-term-submit]').forEach(function (button) {
      button.addEventListener('click', async function () {
        try {
          await api().request('/api/admin/terms/' + encodeURIComponent(button.dataset.termSubmit) + '/submit-review', {method: 'POST'});
          toast('Отправлено на проверку');
          await frontend.get('manager-admin').renderAdmin();
        } catch (error) { reportError('content-submit-review', error); toast(error.message || error); }
      });
    });

    queryAll('[data-term-approve]').forEach(function (button) {
      button.addEventListener('click', async function () {
        try {
          await api().request('/api/admin/terms/' + encodeURIComponent(button.dataset.termApprove) + '/approve', {
            method: 'POST', body: JSON.stringify({note: 'Approved in Content Governance'})
          });
          toast('Термин утверждён');
          await refreshLanguageAndAdmin();
        } catch (error) { reportError('content-approve', error); toast(error.message || error); }
      });
    });

    queryAll('[data-term-reject]').forEach(function (button) {
      button.addEventListener('click', async function () {
        try {
          await api().request('/api/admin/terms/' + encodeURIComponent(button.dataset.termReject) + '/reject', {
            method: 'POST', body: JSON.stringify({note: 'Returned for correction'})
          });
          toast('Возвращено на доработку');
          await frontend.get('manager-admin').renderAdmin();
        } catch (error) { reportError('content-reject', error); toast(error.message || error); }
      });
    });

    queryAll('[data-term-history]').forEach(function (button) {
      button.addEventListener('click', async function () {
        try {
          const history = await api().request('/api/admin/terms/' + encodeURIComponent(button.dataset.termHistory) + '/revisions');
          const slot = query('[data-term-history-slot="' + String(button.dataset.termHistory).replace(/["\\]/g, '\\$&') + '"]');
          if (slot) slot.innerHTML = '<small>Версий: ' + Number((history.revisions || []).length) + ' · проверок: ' + Number((history.reviews || []).length) + '</small>';
        } catch (error) { reportError('content-history', error); toast(error.message || error); }
      });
    });
  }

  async function loadContentState() {
    assertAccess();
    const values = await Promise.all([
      api().request('/api/admin/taxonomy'),
      api().request('/api/admin/terms'),
      api().request('/api/admin/learning/question-quality')
    ]);
    state().patch({adminTaxonomy: values[0], adminTerms: values[1] || [], questionQuality: values[2]});
    return state().current();
  }

  async function renderEditor() {
    assertAccess();
    const currentState = await loadContentState();
    const main = query('#main');
    if (!main) throw new Error('Content governance view missing #main');
    main.innerHTML = '<div class="page-head"><div><div class="kicker">Content control</div>' +
      '<h1>Language Expert / Editor</h1><p>Управление корпоративной терминологией. Пользовательская аналитика доступна только Admin.</p></div></div>' +
      questionQualityHTML(currentState.questionQuality) + adminContentHTML();
    bindAdminContent();
  }

  function installLegacyAdapters() {
    root.adminContentHTML = adminContentHTML;
    root.bindAdminContent = bindAdminContent;
    root.adminTermCard = adminTermCard;
    root.questionQualityHTML = questionQualityHTML;
  }

  frontend.register('content-governance', {
    load: loadContentState,
    renderEditor: renderEditor,
    adminContentHTML: adminContentHTML,
    bindAdminContent: bindAdminContent,
    adminTermCard: adminTermCard,
    questionQualityHTML: questionQualityHTML,
    installLegacyAdapters: installLegacyAdapters,
    legacyFallbacks: original
  });

  installLegacyAdapters();
})(typeof window !== 'undefined' ? window : globalThis);
