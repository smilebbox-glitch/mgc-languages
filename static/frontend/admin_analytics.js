/* v6.0.11: canonical Admin / Analytics orchestration and IT dashboard presentation. */
(function (root) {
  'use strict';

  const frontend = root.MGCFrontend;
  if (!frontend) throw new Error('MGCFrontend runtime is missing');
  if (frontend.has('admin-analytics')) return;

  function legacy() { return frontend.get('legacy-app'); }
  function state() { return frontend.get('app-state'); }
  function api() { return frontend.get('api-client'); }
  function content() { return frontend.get('content-governance'); }
  function ops() { return frontend.get('admin-ops'); }
  function current() { return state().current(); }
  function esc(value) { return legacy().escapeHtml(value); }
  function query(selector) { return legacy().query(selector); }
  function queryAll(selector) { return legacy().queryAll(selector); }
  function toast(message) { legacy().toast(message); }

  function assertAdmin() {
    const user = current().user || {};
    if (user.role !== 'admin') throw new Error('Недостаточно прав');
  }

  function reportError(scope, error) {
    if (!frontend.has('error-boundary')) return;
    frontend.get('error-boundary').record(
      String(scope || 'admin-analytics'),
      error && error.message ? error.message : error,
      '', 0, 0
    );
  }

  function pageHead(kicker, title, subtitle) {
    return '<div class="page-head"><div><div class="kicker">' + esc(kicker) +
      '</div><h1>' + esc(title) + '</h1><p>' + esc(subtitle) + '</p></div></div>';
  }

  async function loadAdminData() {
    assertAdmin();
    const values = await Promise.all([
      api().request('/api/admin/analytics'),
      api().request('/api/admin/users'),
      api().request('/api/admin/taxonomy'),
      api().request('/api/admin/terms'),
      api().request('/api/admin/pilot-telemetry'),
      api().request('/api/admin/it-dashboard'),
      api().request('/api/admin/learning-error-telemetry'),
      api().request('/api/admin/pilot/governance-summary'),
      api().request('/api/admin/pilot/groups'),
      api().request('/api/admin/pilot/features'),
      api().request('/api/admin/learning/question-quality')
    ]);

    const snapshot = {
      analytics: values[0] || {},
      users: Array.isArray(values[1]) ? values[1] : [],
      taxonomy: values[2] || {levels: [], shops: [], topics: []},
      terms: Array.isArray(values[3]) ? values[3] : [],
      telemetry: values[4] || {},
      itDashboard: values[5] || null,
      learningErrorTelemetry: values[6] || null,
      pilotGovernance: values[7] || {},
      pilotGroups: Array.isArray(values[8]) ? values[8] : [],
      pilotFeatures: Array.isArray(values[9]) ? values[9] : [],
      questionQuality: values[10] || null
    };

    state().patch({
      adminUsers: snapshot.users,
      adminTaxonomy: snapshot.taxonomy,
      adminTerms: snapshot.terms,
      itDashboard: snapshot.itDashboard,
      learningErrorTelemetry: snapshot.learningErrorTelemetry,
      pilotGovernance: snapshot.pilotGovernance,
      pilotGroups: snapshot.pilotGroups,
      pilotFeatures: snapshot.pilotFeatures,
      questionQuality: snapshot.questionQuality
    });
    return snapshot;
  }

  function kpiHTML(analytics, telemetry) {
    const departments = Array.isArray(telemetry.departments) ? telemetry.departments : [];
    return '<div class="progress-dashboard admin-kpis"><div class="progress-tile"><b>' +
      Number(analytics.users || 0) + '</b><span>пользователей</span></div><div class="progress-tile"><b>' +
      Number(analytics.active_7d || 0) + '</b><span>активны 7 дней</span></div><div class="progress-tile"><b>' +
      Number(telemetry.practice_accuracy_7d || 0) + '%</b><span>точность практики 7д</span></div><div class="progress-tile"><b>' +
      Number(telemetry.games_completed_7d || 0) + '</b><span>игр завершено 7д</span></div></div>' +
      '<section class="card telemetry-strip"><b>Audio</b><span>' +
      (telemetry.server_tts_available ? ('offline · ' + esc(telemetry.tts_engine || 'TTS')) : 'browser fallback') +
      '</span><b>Подразделения</b><span>' + departments.length + '</span><b>Практика 7д</b><span>' +
      Number(telemetry.practice_sessions_7d || 0) + '</span></section>';
  }

  function learningErrorTelemetryHTML(data) {
    if (!data) return '';
    const weak = (data.weak_topics || []).slice(0, 6);
    return '<div class="section-title"><h2>Качество обучения · ошибки</h2><span>агрегировано · ' +
      Number(data.days || 7) + ' дней</span></div><section class="card learning-error-telemetry"><div class="grid four">' +
      '<div><b>' + Number(data.accuracy_percent || 0).toFixed(1) + '%</b><span>точность</span></div><div><b>' +
      Number(data.previous_accuracy_percent || 0).toFixed(1) + '%</b><span>предыдущий период</span></div><div><b>' +
      Number(data.errors || 0) + '</b><span>ошибок</span></div><div><b>' + Number(data.users_with_errors || 0) +
      '</b><span>пользователей с ошибками</span></div></div><div class="weak-topic-grid">' +
      (weak.length ? weak.map(function (item) {
        return '<div><b>' + esc(item.name) + '</b><span>' + Number(item.accuracy_percent || 0).toFixed(1) + '% · ' +
          Number(item.errors || 0) + ' ошибок</span><small>' + Number(item.sessions || 0) + ' сессий / ' +
          Number(item.questions || 0) + ' заданий</small></div>';
      }).join('') : '<p class="muted">Недостаточно данных для слабых тем.</p>') +
      '</div><p class="muted">' + esc(data.note || '') + '</p></section>';
  }

  function itDashboardHTML(data) {
    assertAdmin();
    if (!data) return '';
    const readiness = data.readiness || {};
    const checks = readiness.checks || {};
    const maintenance = data.maintenance || {};
    const dbLatency = checks.database_latency_ms == null ? '—' : checks.database_latency_ms + ' ms';
    const tts = data.tts || {};
    const slo = data.slo || {};
    const recovery = data.recovery || {};
    const alerts = (data.alerts || {}).items || [];
    const database = data.database || {};
    const pool = database.pool || {};
    const queryTelemetry = database.query_telemetry || {};
    const evidence = data.recovery_evidence || {};
    const backup = evidence.backup || {};
    const restore = evidence.restore_rehearsal || {};
    const objectives = evidence.objectives || {};
    const sloStatus = slo.status === 'met' ? 'SLO OK' :
      (slo.status === 'insufficient_data' ? 'мало данных' : 'SLO MISS');
    const backupLabel = backup.age_minutes == null ? 'нет evidence' : Number(backup.age_minutes).toFixed(0) + ' мин';
    const restoreLabel = restore.age_days == null ? 'нет evidence' : Number(restore.age_days).toFixed(1) + ' дн';
    const alertHtml = alerts.length ? '<div class="pilot-alert-list">' + alerts.map(function (alert) {
      return '<div class="pilot-alert alert-' + esc(alert.severity) + '"><div><b>' + esc(alert.title) +
        '</b><span>' + esc(alert.component) + ' · ' + esc(alert.status) + '</span><p>' + esc(alert.detail) +
        '</p></div>' + (alert.status === 'open' ? '<button class="secondary" data-alert-ack="' +
        esc(alert.id) + '">Принято</button>' : '') + '</div>';
    }).join('') + '</div>' : '<div class="ops-empty">Активных IT alerts нет.</div>';

    return '<div class="section-title"><h2>IT · Pilot Operations</h2><span>' + esc(recovery.state || 'unknown') +
      '</span></div><section class="card it-dashboard ' + (readiness.ready ? 'it-ok' : 'it-attention') +
      '"><div class="grid four"><div><b>' + (readiness.ready ? 'Готов' : 'Проверить') +
      '</b><span>readiness</span></div><div><b>' + esc(recovery.state || '—') +
      '</b><span>recovery state</span></div><div><b>' + esc(dbLatency) + '</b><span>DB latency</span></div><div><b>' +
      Number((data.alerts || {}).active_count || 0) + '</b><span>active alerts</span></div></div>' +
      '<div class="slo-grid"><div><b>' + Number(slo.availability_percent || 0).toFixed(2) +
      '%</b><span>availability · target ' + Number((slo.targets || {}).availability_percent || 0).toFixed(1) +
      '%</span></div><div><b>' + Number(slo.error_rate_percent || 0).toFixed(2) +
      '%</b><span>5xx rate</span></div><div><b>' + Number(slo.p95_ms || 0).toFixed(0) +
      ' ms</b><span>p95 · target ' + Number((slo.targets || {}).p95_ms || 0) +
      ' ms</span></div><div><b>' + esc(sloStatus) + '</b><span>' + Number(slo.samples || 0) + ' samples / ' +
      Number(slo.window_minutes || 0) + ' min</span></div></div>' +
      '<div class="slo-grid ops-detail-grid"><div><b>' + Number(queryTelemetry.p95_ms || 0).toFixed(1) +
      ' ms</b><span>DB query p95 · ' + Number(queryTelemetry.slow_queries || 0) + ' slow</span></div><div><b>' +
      Number(pool.saturation_percent || 0).toFixed(1) + '%</b><span>DB pool saturation</span></div><div><b>' +
      esc(backupLabel) + '</b><span>backup age · ' + esc(backup.status || 'unknown') + '</span></div><div><b>' +
      esc(restoreLabel) + '</b><span>restore evidence · ' + esc(restore.status || 'unknown') + '</span></div></div>' +
      '<div class="telemetry-strip compact"><b>Schema</b><span>' + esc((checks.schema_head || {}).current || '—') +
      '</span><b>TTS</b><span>' + (tts.circuit_open ? 'circuit OPEN' : (tts.server_available ? 'offline' : 'browser fallback')) +
      '</span><b>HTTP 5xx</b><span>' + Number((data.http || {}).server_errors_since_start || 0) +
      '</span><b>RPO/RTO</b><span>' + Number(objectives.rpo_target_minutes || 0) + 'm / ' +
      Number(objectives.rto_target_minutes || 0) + 'm</span></div>' +
      '<div class="ops-subtitle"><b>Alerts</b><span>acknowledge означает «IT увидел», а не «проблема устранена»</span></div>' +
      alertHtml + ((queryTelemetry.top_slow_fingerprints || []).length ?
        '<details><summary>Slow-query fingerprints · без SQL/параметров</summary><div class="event-list">' +
        queryTelemetry.top_slow_fingerprints.slice(0, 6).map(function (item) {
          return '<div><b>' + esc(item.operation) + ' · ' + esc(item.fingerprint) + '</b><span>' +
            Number(item.count || 0) + ' × · max ' + Number(item.max_ms || 0).toFixed(1) + ' ms</span></div>';
        }).join('') + '</div></details>' : '') +
      '<div class="maintenance-row"><span>К очистке: ' + Object.values(maintenance.counts || {}).reduce(function (sum, value) {
        return sum + Number(value || 0);
      }, 0) + '</span><button id="maintenancePreview" class="secondary">Проверить cleanup</button>' +
      '<button id="maintenanceRun" class="secondary">Запустить cleanup</button></div>' +
      (data.recent_events && data.recent_events.length ? '<details><summary>Последние operational events</summary>' +
        '<div class="event-list">' + data.recent_events.slice(0, 8).map(function (event) {
          return '<div><b>' + esc(event.component) + ' · ' + esc(event.event_type) + '</b><span>' +
            esc(event.severity) + ' · ' + esc(event.path || '') + '</span></div>';
        }).join('') + '</div></details>' : '') + '</section>';
  }

  function usersTableHTML(users) {
    const list = Array.isArray(users) ? users : [];
    return '<div class="section-title"><h2>Пользователи</h2></div><div class="table-wrap"><table class="admin-table">' +
      '<thead><tr><th>Сотрудник</th><th>Подразделение</th><th>Роль</th><th>Уровень</th><th>XP</th>' +
      '<th>Изучено</th><th>Последняя активность</th></tr></thead><tbody>' + list.map(function (user) {
        const last = user.last_activity_at ? new Date(user.last_activity_at).toLocaleDateString() : '—';
        return '<tr data-admin-user="' + esc(user.id) + '"><td><b>' + esc(user.display_name) + '</b><small>' +
          esc(user.username) + '</small></td><td>' + esc(user.department || 'General') + '</td><td>' + esc(user.role) +
          '</td><td>' + esc(user.level) + ' · ' + esc(user.level_title) + '</td><td>' + esc(user.lifetime_xp) +
          '</td><td>' + esc(user.terms_known) + '/' + esc(user.terms_touched) + '</td><td>' + esc(last) +
          '</td></tr>';
      }).join('') + '</tbody></table></div><div id="adminUserDetail"></div>';
  }

  async function openAdminUser(id) {
    assertAdmin();
    try {
      const user = await api().request('/api/admin/users/' + encodeURIComponent(id) + '/learning-stats');
      const target = query('#adminUserDetail');
      if (!target) return;
      const languages = user && user.languages ? user.languages : {};
      target.innerHTML = '<section class="card admin-user-detail"><div class="section-title"><h2>' +
        esc(user.display_name) + '</h2><span>' + esc(user.role) + '</span></div><div class="grid three"><div><b>' +
        esc(user.level) + '</b><span>уровень · ' + esc(user.level_title) + '</span></div><div><b>' +
        esc(user.lifetime_xp) + '</b><span>Lifetime XP</span></div><div><b>' + esc(user.spendable_xp) +
        '</b><span>доступно XP</span></div></div>' + Object.keys(languages).map(function (lang) {
          const details = languages[lang] || {};
          const topics = Array.isArray(details.topics) ? details.topics : [];
          return '<h3>' + (lang === 'english' ? 'English' : '中文') + ' · ' + esc(details.known) + '/' +
            esc(details.touched) + '</h3><div class="chip-row">' + topics.map(function (topic) {
              return '<span class="topic-chip static">' + esc(topic.topic) + ' · ' + esc(topic.mastery_percent) + '%</span>';
            }).join('') + '</div>';
        }).join('') + '</section>';
      target.scrollIntoView({behavior: 'smooth', block: 'nearest'});
    } catch (error) {
      reportError('admin-user-detail', error);
      toast(error && error.message ? error.message : error);
    }
  }

  function bindUsers() {
    queryAll('[data-admin-user]').forEach(function (row) {
      row.addEventListener('click', function () {
        void openAdminUser(row.dataset.adminUser);
      });
    });
  }

  async function renderAdmin() {
    assertAdmin();
    if (!frontend.has('content-governance')) throw new Error('Content governance module is missing');
    if (!frontend.has('admin-ops')) throw new Error('Admin operations module is missing');

    const data = await loadAdminData();
    const main = query('#main');
    if (!main) throw new Error('Admin analytics view missing #main');

    main.innerHTML = pageHead(
      'Pilot control',
      'Admin / Analytics',
      'Контент, пользователи и учебная статистика. XP остаётся мотивационной метрикой и не подменяет реальную оценку компетенций.'
    ) + kpiHTML(data.analytics, data.telemetry) +
      ops().pilotGovernanceHTML() +
      itDashboardHTML(data.itDashboard) +
      learningErrorTelemetryHTML(data.learningErrorTelemetry) +
      content().questionQualityHTML(data.questionQuality) +
      usersTableHTML(data.users) +
      content().adminContentHTML();

    bindUsers();
    ops().bindPilotGovernance();
    ops().bindITDashboard();
    content().bindAdminContent();
  }

  frontend.register('admin-analytics', {
    load: loadAdminData,
    renderAdmin: renderAdmin,
    openAdminUser: openAdminUser,
    kpiHTML: kpiHTML,
    learningErrorTelemetryHTML: learningErrorTelemetryHTML,
    itDashboardHTML: itDashboardHTML,
    usersTableHTML: usersTableHTML
  });
})(typeof window !== 'undefined' ? window : globalThis);
