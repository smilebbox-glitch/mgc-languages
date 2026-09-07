/* v6.0.10: modular pilot-governance and IT administrative controls. */
(function (root) {
  'use strict';

  const frontend = root.MGCFrontend;
  if (!frontend) throw new Error('MGCFrontend runtime is missing');
  if (frontend.has('admin-ops')) return;

  const original = {
    pilotGovernanceHTML: typeof root.pilotGovernanceHTML === 'function' ? root.pilotGovernanceHTML : null,
    bindPilotGovernance: typeof root.bindPilotGovernance === 'function' ? root.bindPilotGovernance : null,
    itDashboardHTML: typeof root.itDashboardHTML === 'function' ? root.itDashboardHTML : null,
    bindITDashboard: typeof root.bindITDashboard === 'function' ? root.bindITDashboard : null
  };

  function legacy() { return frontend.get('legacy-app'); }
  function state() { return frontend.get('app-state'); }
  function api() { return frontend.get('api-client'); }
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
      String(scope || 'admin-ops'),
      error && error.message ? error.message : error,
      '', 0, 0
    );
  }

  function css(value) {
    const text = String(value == null ? '' : value);
    if (root.CSS && typeof root.CSS.escape === 'function') return root.CSS.escape(text);
    return text.replace(/[^a-zA-Z0-9_-]/g, function (char) { return '\\' + char; });
  }

  function isoOrNull(value) {
    return value ? new Date(value).toISOString() : null;
  }

  async function rerenderAdmin() {
    if (frontend.has('manager-admin')) return frontend.get('manager-admin').renderAdmin();
    return null;
  }

  function pilotGovernanceHTML() {
    assertAdmin();
    const snapshot = current();
    const governance = snapshot.pilotGovernance || {};
    const groups = Array.isArray(snapshot.pilotGroups) ? snapshot.pilotGroups : [];
    const flags = Array.isArray(snapshot.pilotFeatures) ? snapshot.pilotFeatures : [];
    const users = Array.isArray(snapshot.adminUsers) ? snapshot.adminUsers : [];

    const options = users.map(function (user) {
      return '<option value="' + esc(user.id) + '">' + esc(user.display_name) + ' · ' +
        esc(user.department || 'General') + '</option>';
    }).join('');

    const flagRows = flags.map(function (flag) {
      return '<span class="governance-flag">' + esc(flag.flag_key) + ' · ' +
        (flag.default_enabled ? 'default ON' : 'default OFF') + '</span>';
    }).join('');

    const groupCards = groups.map(function (group) {
      const members = Array.isArray(group.members) ? group.members : [];
      const assignments = Array.isArray(group.assignments) ? group.assignments : [];
      const features = group.features || {};
      const memberChips = members.map(function (member) {
        return '<span class="member-chip">' + esc(member.display_name) +
          '<button type="button" data-pilot-remove-member="' + esc(group.id) + '|' + esc(member.id) +
          '" title="Убрать из группы">×</button></span>';
      }).join('') || '<small>пока нет участников</small>';
      const startValue = group.starts_at ? String(group.starts_at).slice(0, 16) : '';
      const endValue = group.ends_at ? String(group.ends_at).slice(0, 16) : '';

      return '<article class="card governance-group"><div class="section-title"><div><h3>' + esc(group.name) +
        '</h3><span>' + esc(group.department) + ' · wave ' + esc(group.wave) + ' · ' + esc(group.status) +
        (group.active ? ' · ACTIVE' : '') + '</span></div><a href="/api/admin/pilot/export.csv?group_id=' +
        encodeURIComponent(group.id) + '" target="_blank">CSV</a></div>' +
        '<div class="governance-members"><b>Участники: ' + members.length + '</b><div class="member-chip-row">' +
        memberChips + '</div></div>' +
        '<div class="grid two compact-grid"><select data-pilot-member-select="' + esc(group.id) + '">' + options +
        '</select><button class="secondary" data-pilot-add-member="' + esc(group.id) + '">Добавить участника</button></div>' +
        '<div class="grid four compact-grid rollout-controls"><label>Статус<select data-pilot-group-status="' + esc(group.id) +
        '"><option ' + (group.status === 'draft' ? 'selected' : '') + '>draft</option><option ' +
        (group.status === 'active' ? 'selected' : '') + '>active</option><option ' +
        (group.status === 'paused' ? 'selected' : '') + '>paused</option><option ' +
        (group.status === 'completed' ? 'selected' : '') + '>completed</option></select></label>' +
        '<label>Wave<input data-pilot-group-wave="' + esc(group.id) + '" type="number" min="1" max="100" value="' +
        esc(group.wave) + '"></label><label>Старт<input data-pilot-group-start="' + esc(group.id) +
        '" type="datetime-local" value="' + esc(startValue) + '"></label><label>Окончание<input data-pilot-group-end="' +
        esc(group.id) + '" type="datetime-local" value="' + esc(endValue) + '"></label></div>' +
        '<button class="secondary" data-pilot-save-group="' + esc(group.id) + '">Сохранить rollout</button>' +
        '<div class="feature-toggle-grid">' + flags.map(function (flag) {
          const effective = Object.prototype.hasOwnProperty.call(features, flag.flag_key) ?
            features[flag.flag_key] : flag.default_enabled;
          return '<label class="toggle-line"><input type="checkbox" data-pilot-feature="' + esc(group.id) + '|' +
            esc(flag.flag_key) + '" ' + (effective ? 'checked' : '') + '> ' + esc(flag.title) + '</label>';
        }).join('') + '</div>' +
        '<div class="grid four"><input data-assign-name="' + esc(group.id) + '" placeholder="Трек: Quality Putonghua">' +
        '<input data-assign-topic="' + esc(group.id) + '" placeholder="Тема: Quality / R&D"><select data-assign-language="' +
        esc(group.id) + '"><option value="chinese">Путунхуа / 中文</option><option value="english">English</option></select>' +
        '<select data-assign-level="' + esc(group.id) + '"><option>A1</option><option>A2</option><option>B1</option>' +
        '<option>B2</option><option>C1</option></select></div><div class="grid two compact-grid"><label>Дедлайн' +
        '<input data-assign-due="' + esc(group.id) + '" type="date"></label><button class="secondary" data-pilot-assign="' +
        esc(group.id) + '">Назначить трек</button></div>' +
        (assignments.length ? '<div class="assignment-list">' + assignments.map(function (assignment) {
          return '<span>' + esc(assignment.track_name) + ' · ' +
            (assignment.language === 'chinese' ? 'Путунхуа' : 'English') +
            (assignment.topic ? ' · ' + esc(assignment.topic) : '') + ' · ' + esc(assignment.target_level) +
            (assignment.due_date ? ' · до ' + esc(assignment.due_date) : '') +
            ' <button type="button" data-pilot-remove-assignment="' + esc(group.id) + '|' + esc(assignment.id) +
            '" title="Снять назначение">×</button></span>';
        }).join('') + '</div>' : '') + '</article>';
    }).join('');

    const quotas = governance.quotas || {};
    return '<div class="section-title"><h2>Pilot Governance</h2><span>группы · волны · feature flags · quotas</span></div>' +
      '<section class="card governance-overview"><div class="grid four"><div><b>' +
      Number(governance.groups_active || 0) + '/' + Number(governance.groups_total || 0) + '</b><span>активных групп</span></div>' +
      '<div><b>' + Number(governance.memberships || 0) + '</b><span>назначений пользователей</span></div><div><b>' +
      Number(governance.assignments || 0) + '</b><span>учебных треков</span></div><div><b>' +
      esc((governance.waves || []).join(', ') || '—') + '</b><span>волны</span></div></div><p><b>Китайский:</b> ' +
      esc(governance.chinese_standard || 'Путунхуа — основной трек.') + '</p><div class="quota-row"><span>XP ' +
      Number(quotas.daily_xp || 0) + '/день</span><span>Игры ' + Number(quotas.daily_games || 0) + '</span><span>TTS ' +
      Number(quotas.daily_tts || 0) + '</span><span>Практика ' + Number(quotas.daily_practice || 0) +
      '</span></div><div class="governance-flags">' + flagRows +
      '</div><a class="button-link" href="/api/admin/pilot/export.csv" target="_blank">Экспорт результатов CSV</a></section>' +
      '<section class="card governance-create"><h3>Новая группа / волна</h3><div class="grid four">' +
      '<label>Название<input id="pilotGroupName" placeholder="R&D pilot"></label><label>Подразделение' +
      '<input id="pilotGroupDepartment" value="General"></label><label>Волна<input id="pilotGroupWave" type="number" min="1" value="1"></label>' +
      '<label>Статус<select id="pilotGroupStatus"><option>draft</option><option>active</option><option>paused</option>' +
      '<option>completed</option></select></label></div><div class="grid two"><label>Старт<input id="pilotGroupStart" type="datetime-local"></label>' +
      '<label>Окончание<input id="pilotGroupEnd" type="datetime-local"></label></div><button id="createPilotGroup" class="primary">Создать группу</button></section>' +
      '<div class="governance-groups">' + groupCards + '</div>';
  }

  function bindPilotGovernance() {
    assertAdmin();
    const create = query('#createPilotGroup');
    if (create) create.addEventListener('click', async function () {
      try {
        await api().request('/api/admin/pilot/groups', {
          method: 'POST',
          body: JSON.stringify({
            name: query('#pilotGroupName').value,
            department: query('#pilotGroupDepartment').value,
            description: '',
            status: query('#pilotGroupStatus').value,
            wave: Number(query('#pilotGroupWave').value || 1),
            starts_at: isoOrNull(query('#pilotGroupStart').value),
            ends_at: isoOrNull(query('#pilotGroupEnd').value)
          })
        });
        toast('Группа пилота создана');
        await rerenderAdmin();
      } catch (error) { reportError('pilot-create-group', error); toast(error.message || error); }
    });

    queryAll('[data-pilot-add-member]').forEach(function (button) {
      button.addEventListener('click', async function () {
        const groupId = button.dataset.pilotAddMember;
        const select = query('[data-pilot-member-select="' + css(groupId) + '"]');
        try {
          await api().request('/api/admin/pilot/groups/' + encodeURIComponent(groupId) + '/members/' +
            encodeURIComponent(select.value), {method: 'POST'});
          toast('Участник добавлен');
          await rerenderAdmin();
        } catch (error) { reportError('pilot-add-member', error); toast(error.message || error); }
      });
    });

    queryAll('[data-pilot-remove-member]').forEach(function (button) {
      button.addEventListener('click', async function () {
        const parts = String(button.dataset.pilotRemoveMember || '').split('|');
        try {
          await api().request('/api/admin/pilot/groups/' + encodeURIComponent(parts[0]) + '/members/' +
            encodeURIComponent(parts[1]), {method: 'DELETE'});
          toast('Участник убран из группы');
          await rerenderAdmin();
        } catch (error) { reportError('pilot-remove-member', error); toast(error.message || error); }
      });
    });

    queryAll('[data-pilot-save-group]').forEach(function (button) {
      button.addEventListener('click', async function () {
        const groupId = button.dataset.pilotSaveGroup;
        try {
          await api().request('/api/admin/pilot/groups/' + encodeURIComponent(groupId), {
            method: 'PATCH',
            body: JSON.stringify({
              status: query('[data-pilot-group-status="' + css(groupId) + '"]').value,
              wave: Number(query('[data-pilot-group-wave="' + css(groupId) + '"]').value || 1),
              starts_at: isoOrNull(query('[data-pilot-group-start="' + css(groupId) + '"]').value),
              ends_at: isoOrNull(query('[data-pilot-group-end="' + css(groupId) + '"]').value)
            })
          });
          toast('Параметры rollout сохранены');
          await rerenderAdmin();
        } catch (error) { reportError('pilot-save-group', error); toast(error.message || error); }
      });
    });

    queryAll('[data-pilot-feature]').forEach(function (checkbox) {
      checkbox.addEventListener('change', async function () {
        const parts = String(checkbox.dataset.pilotFeature || '').split('|');
        try {
          await api().request('/api/admin/pilot/groups/' + encodeURIComponent(parts[0]) + '/features/' +
            encodeURIComponent(parts[1]), {method: 'PUT', body: JSON.stringify({enabled: checkbox.checked})});
          toast('Feature flag обновлён');
        } catch (error) {
          checkbox.checked = !checkbox.checked;
          reportError('pilot-feature-flag', error);
          toast(error.message || error);
        }
      });
    });

    queryAll('[data-pilot-assign]').forEach(function (button) {
      button.addEventListener('click', async function () {
        const groupId = button.dataset.pilotAssign;
        try {
          await api().request('/api/admin/pilot/groups/' + encodeURIComponent(groupId) + '/assignments', {
            method: 'POST',
            body: JSON.stringify({
              language: (query('[data-assign-language="' + css(groupId) + '"]') || {}).value || 'chinese',
              track_name: (query('[data-assign-name="' + css(groupId) + '"]') || {}).value || '',
              topic: (query('[data-assign-topic="' + css(groupId) + '"]') || {}).value || '',
              target_level: (query('[data-assign-level="' + css(groupId) + '"]') || {}).value || 'A1',
              due_date: (query('[data-assign-due="' + css(groupId) + '"]') || {}).value || ''
            })
          });
          toast('Учебный трек назначен');
          await rerenderAdmin();
        } catch (error) { reportError('pilot-assign-track', error); toast(error.message || error); }
      });
    });

    queryAll('[data-pilot-remove-assignment]').forEach(function (button) {
      button.addEventListener('click', async function () {
        const parts = String(button.dataset.pilotRemoveAssignment || '').split('|');
        try {
          await api().request('/api/admin/pilot/groups/' + encodeURIComponent(parts[0]) + '/assignments/' +
            encodeURIComponent(parts[1]), {method: 'DELETE'});
          toast('Назначение снято');
          await rerenderAdmin();
        } catch (error) { reportError('pilot-remove-assignment', error); toast(error.message || error); }
      });
    });
  }

  function itDashboardHTML(data) {
    assertAdmin();
    if (!original.itDashboardHTML) return '';
    return original.itDashboardHTML(data);
  }

  function bindITDashboard() {
    assertAdmin();
    const preview = query('#maintenancePreview');
    const run = query('#maintenanceRun');
    if (preview) preview.addEventListener('click', async function () {
      try {
        const result = await api().request('/api/admin/maintenance/cleanup?dry_run=true', {method: 'POST'});
        const count = Object.values(result.counts || {}).reduce(function (sum, value) {
          return sum + Number(value || 0);
        }, 0);
        toast('К очистке: ' + count);
      } catch (error) { reportError('it-cleanup-preview', error); toast(error.message || error); }
    });
    if (run) run.addEventListener('click', async function () {
      try {
        const result = await api().request('/api/admin/maintenance/cleanup?dry_run=false', {method: 'POST'});
        const count = Object.values(result.counts || {}).reduce(function (sum, value) {
          return sum + Number(value || 0);
        }, 0);
        toast('Cleanup выполнен: ' + count);
        await rerenderAdmin();
      } catch (error) { reportError('it-cleanup-run', error); toast(error.message || error); }
    });
    queryAll('[data-alert-ack]').forEach(function (button) {
      button.addEventListener('click', async function () {
        try {
          await api().request('/api/admin/alerts/' + encodeURIComponent(button.dataset.alertAck) + '/ack', {
            method: 'PATCH', body: JSON.stringify({note: 'Acknowledged from IT dashboard'})
          });
          toast('Alert принят IT');
          await rerenderAdmin();
        } catch (error) { reportError('it-alert-ack', error); toast(error.message || error); }
      });
    });
  }

  function installLegacyAdapters() {
    root.pilotGovernanceHTML = pilotGovernanceHTML;
    root.bindPilotGovernance = bindPilotGovernance;
    root.itDashboardHTML = itDashboardHTML;
    root.bindITDashboard = bindITDashboard;
  }

  frontend.register('admin-ops', {
    pilotGovernanceHTML: pilotGovernanceHTML,
    bindPilotGovernance: bindPilotGovernance,
    itDashboardHTML: itDashboardHTML,
    bindITDashboard: bindITDashboard,
    installLegacyAdapters: installLegacyAdapters,
    legacyFallbacks: original
  });

  installLegacyAdapters();
})(typeof window !== 'undefined' ? window : globalThis);
