/* v6.0.9: canonical ownership for manager and admin views. */
(function (root) {
  'use strict';

  const frontend = root.MGCFrontend;
  if (!frontend) throw new Error('MGCFrontend runtime is missing');
  if (frontend.has('manager-admin')) return;

  const OWNED_VIEWS = Object.freeze(['manager', 'admin']);
  const owned = new Set(OWNED_VIEWS);
  let installed = false;

  function legacy() { return frontend.get('legacy-app'); }
  function state() { return frontend.get('app-state'); }
  function api() { return frontend.get('api-client'); }

  function owns(view) {
    return owned.has(String(view || ''));
  }

  function currentUser() {
    const current = state().current();
    return current && current.user ? current.user : null;
  }

  function assertAccess(view) {
    const user = currentUser();
    const role = user && user.role ? user.role : '';
    if (view === 'manager' && role !== 'manager') {
      throw new Error('Раздел доступен руководителю подразделения');
    }
    if (view === 'admin' && !['admin', 'editor'].includes(role)) {
      throw new Error('Недостаточно прав');
    }
  }

  function reportError(scope, error) {
    if (!frontend.has('error-boundary')) return;
    frontend.get('error-boundary').record(
      String(scope || 'manager-admin'),
      error && error.message ? error.message : error,
      '', 0, 0
    );
  }

  function pageHead(kicker, title, subtitle) {
    const esc = legacy().escapeHtml;
    return '<div class="page-head"><div><div class="kicker">' + esc(kicker) +
      '</div><h1>' + esc(title) + '</h1><p>' + esc(subtitle) + '</p></div></div>';
  }

  async function renderManager() {
    assertAccess('manager');
    const team = await api().request('/api/manager/team');
    state().set('managerTeam', team);
    const users = Array.isArray(team && team.users) ? team.users : [];
    const esc = legacy().escapeHtml;
    const main = legacy().query('#main');
    if (!main) throw new Error('Manager view missing #main');

    main.innerHTML = pageHead(
      'Department scope',
      'Моя команда · ' + String((team && team.department) || ''),
      'Только сотрудники вашего подразделения. XP показан как мотивационная активность и не является оценкой профессиональной пригодности.'
    ) + '<div class="table-wrap"><table class="admin-table"><thead><tr>' +
      '<th>Сотрудник</th><th>Уровень</th><th>XP</th><th>Освоено</th><th>Активность</th>' +
      '</tr></thead><tbody>' + users.map(function (user) {
        const lastActivity = user.last_activity_at ? new Date(user.last_activity_at).toLocaleDateString() : '—';
        return '<tr data-manager-user="' + esc(user.id) + '"><td><b>' + esc(user.display_name) + '</b><small>' +
          esc(user.username) + '</small></td><td>' + esc(user.level) + ' · ' + esc(user.level_title) + '</td><td>' +
          esc(user.lifetime_xp) + '</td><td>' + esc(user.terms_known) + '/' + esc(user.terms_touched) + '</td><td>' +
          esc(lastActivity) + '</td></tr>';
      }).join('') + '</tbody></table></div><div id="managerUserDetail"></div>';

    legacy().queryAll('[data-manager-user]').forEach(function (row) {
      row.addEventListener('click', function () {
        void openManagerUser(row.dataset.managerUser);
      });
    });
  }

  async function openManagerUser(id) {
    assertAccess('manager');
    try {
      const user = await api().request('/api/manager/team/' + encodeURIComponent(id) + '/learning-stats');
      const target = legacy().query('#managerUserDetail');
      if (!target) return;
      const esc = legacy().escapeHtml;
      const languages = user && user.languages ? user.languages : {};
      target.innerHTML = '<section class="card admin-user-detail"><div class="section-title"><h2>' +
        esc(user.display_name) + '</h2><span>' + esc(user.department) + '</span></div>' +
        Object.keys(languages).map(function (lang) {
          const details = languages[lang] || {};
          const topics = Array.isArray(details.topics) ? details.topics : [];
          return '<h3>' + (lang === 'english' ? 'English' : '中文') + ' · ' + esc(details.known) + '/' +
            esc(details.touched) + '</h3><div class="chip-row">' + topics.map(function (topic) {
              return '<span class="topic-chip static">' + esc(topic.topic) + ' · ' + esc(topic.mastery_percent) + '%</span>';
            }).join('') + '</div>';
        }).join('') + '</section>';
    } catch (error) {
      reportError('manager-user-detail', error);
      legacy().toast(error && error.message ? error.message : error);
    }
  }

  async function renderAdmin() {
    assertAccess('admin');
    const user = currentUser() || {};
    if (user.role === 'editor') {
      if (!frontend.has('content-governance')) throw new Error('Content governance module is missing');
      return frontend.get('content-governance').renderEditor();
    }
    return legacy().renderAdmin();
  }

  async function render(view) {
    const target = String(view || state().get('view') || 'manager');
    if (!owns(target)) throw new Error('Manager/admin module does not own view: ' + target);
    assertAccess(target);
    if (target === 'manager') return renderManager();
    return renderAdmin();
  }

  async function navigate(view) {
    const target = String(view || 'manager');
    if (!owns(target)) return legacy().setView(target);
    assertAccess(target);
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
      reportError('manager-admin-navigation', error);
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
        reportError('manager-admin-click', error);
      });
    }, true);
  }

  frontend.register('manager-admin', {
    views: OWNED_VIEWS,
    owns: owns,
    render: render,
    navigate: navigate,
    renderManager: renderManager,
    openManagerUser: openManagerUser,
    renderAdmin: renderAdmin,
    install: install
  });

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', install, {once: true});
  } else {
    install();
  }
})(typeof window !== 'undefined' ? window : globalThis);
