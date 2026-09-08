/* v6.0.20 mastery patch: competency map and adaptive next-step guidance for Automotive Arcade. */
(function (root) {
  'use strict';

  const frontend = root.MGCFrontend;
  if (!frontend) throw new Error('MGCFrontend runtime is missing');
  if (frontend.has('arcade-mastery-v620')) return;

  const SKILLS = Object.freeze([
    {id:'vocabulary', title:'Терминология', icon:'Aa', games:['match','mistake','memory_pairs','odd_one_out','rapid_recall']},
    {id:'listening', title:'Аудирование', icon:'◖', games:['listening','rapid_recall','dialogue_choice']},
    {id:'production', title:'Производство', icon:'▥', games:['assembly_order','shop_route','tool_select','hotspot']},
    {id:'quality', title:'Качество', icon:'✓', games:['defect_detective','quality_gate','spec_check','safety_spot']},
    {id:'logistics', title:'Логистика', icon:'⇢', games:['logistics_route','kanban','shop_route','shift_incident']},
    {id:'engineering', title:'Инженерия', icon:'⊞', games:['bom_builder','hotspot','spec_check','assembly_order']},
    {id:'communication', title:'Коммуникация', icon:'“”', games:['dialogue_choice','phrase','shift_incident','listening']}
  ]);

  const FOCUS = Object.freeze({
    paint:['quality','production','vocabulary'],
    logistics:['logistics','communication','vocabulary'],
    body:['engineering','production','quality'],
    assembly:['production','quality','vocabulary'],
    quality:['quality','engineering','vocabulary'],
    rd:['engineering','communication','quality'],
    purchasing:['communication','logistics','vocabulary'],
    default:['vocabulary','communication','production']
  });

  const ACHIEVEMENTS = Object.freeze([
    {id:'starter', title:'Первый заезд', hint:'Попробовать 3 механики', test:function (s) { return s.tried >= 3; }},
    {id:'explorer', title:'Исследователь', hint:'Попробовать 10 механик', test:function (s) { return s.tried >= 10; }},
    {id:'garage', title:'Полный гараж', hint:'Попробовать все 20 механик', test:function (s) { return s.tried >= 20; }},
    {id:'clean', title:'Чистая смена', hint:'Получить пять результатов 5/5', test:function (s) { return s.perfect >= 5; }},
    {id:'habit', title:'Стабильность', hint:'Пять активных дней', test:function (s) { return s.days >= 5; }},
    {id:'specialist', title:'Цеховой специалист', hint:'70% по приоритетным навыкам', test:function (s) { return s.focus >= 70; }}
  ]);

  let installed = false;
  let observer = null;
  let refreshTimer = null;

  function stateApi() { return frontend.get('app-state'); }
  function snapshot() { return stateApi().current(); }
  function gameLab() { return frontend.get('game-lab-v618'); }
  function engagement() { return frontend.get('game-engagement-v618'); }
  function query(selector, scope) { return (scope || document).querySelector(selector); }
  function queryAll(selector, scope) { return Array.from((scope || document).querySelectorAll(selector)); }
  function esc(value) {
    return String(value == null ? '' : value).replace(/[&<>"']/g, function (char) {
      return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[char];
    });
  }

  function departmentName() {
    const user = snapshot().user || {};
    const direct = String(user.department || user.dept || '').trim();
    if (direct) return direct;
    const node = query('#userProfileDept');
    return node ? String(node.textContent || '').trim() : '';
  }

  function departmentGroup(value) {
    const name = String(value || '').toLocaleLowerCase('ru-RU');
    if (/окраск|paint/.test(name)) return 'paint';
    if (/логист|склад|supply/.test(name)) return 'logistics';
    if (/кузов|компонент|свар|штамп|body|weld|stamp/.test(name)) return 'body';
    if (/сбор|производ|assembly|production/.test(name)) return 'assembly';
    if (/качеств|quality/.test(name)) return 'quality';
    if (/r&d|\brd\b|разработ|инженер|engineering/.test(name)) return 'rd';
    if (/закуп|commercial|purchas|procure/.test(name)) return 'purchasing';
    return 'default';
  }

  function catalog() {
    return Array.isArray(gameLab().catalog) ? gameLab().catalog : [];
  }

  function gameById(id) {
    return catalog().find(function (game) { return game.id === id; }) || null;
  }

  function progress() {
    const value = engagement().progress();
    return value && typeof value === 'object' ? value : {tried:{}, completed:{}, best:{}, days:{}};
  }

  function skillScore(skill, p) {
    let scorePoints = 0;
    let tried = 0;
    skill.games.forEach(function (id) {
      const best = Math.max(0, Math.min(5, Number((p.best || {})[id] || 0)));
      scorePoints += best;
      if ((p.tried || {})[id]) tried += 1;
    });
    const accuracy = (scorePoints / Math.max(1, skill.games.length * 5)) * 100;
    const coverage = (tried / Math.max(1, skill.games.length)) * 100;
    return Math.round((accuracy * 0.75) + (coverage * 0.25));
  }

  function skillRows(p) {
    return SKILLS.map(function (skill) {
      return Object.assign({}, skill, {score:skillScore(skill, p)});
    });
  }

  function tier(score) {
    if (score >= 90) return 'MASTER';
    if (score >= 75) return 'EXPERT';
    if (score >= 60) return 'SPECIALIST';
    if (score >= 40) return 'OPERATOR';
    if (score >= 20) return 'DEVELOPING';
    return 'ROOKIE';
  }

  function summary(p, rows) {
    const tried = Object.keys(p.tried || {}).length;
    const completed = Object.keys(p.completed || {}).length;
    const perfect = Object.keys(p.best || {}).filter(function (id) { return Number(p.best[id] || 0) >= 5; }).length;
    const days = Object.keys(p.days || {}).length;
    const overall = Math.round(rows.reduce(function (acc, row) { return acc + row.score; }, 0) / Math.max(1, rows.length));
    const focusIds = FOCUS[departmentGroup(departmentName())] || FOCUS.default;
    const focusRows = rows.filter(function (row) { return focusIds.indexOf(row.id) !== -1; });
    const focus = Math.round(focusRows.reduce(function (acc, row) { return acc + row.score; }, 0) / Math.max(1, focusRows.length));
    return {tried:tried, completed:completed, perfect:perfect, days:days, overall:overall, focus:focus, focusIds:focusIds};
  }

  function weakestRow(rows, focusIds) {
    const focused = rows.filter(function (row) { return focusIds.indexOf(row.id) !== -1; });
    const pool = focused.length ? focused : rows;
    return pool.slice().sort(function (a, b) { return a.score - b.score || a.title.localeCompare(b.title); })[0] || rows[0];
  }

  function nextGameForSkill(skill, p) {
    if (!skill) return null;
    const candidates = skill.games.map(function (id) {
      return {id:id, game:gameById(id), best:Number((p.best || {})[id] || 0), tried:Boolean((p.tried || {})[id])};
    }).filter(function (item) { return Boolean(item.game); });
    candidates.sort(function (a, b) {
      if (a.tried !== b.tried) return a.tried ? 1 : -1;
      return a.best - b.best || a.game.title.localeCompare(b.game.title);
    });
    return candidates[0] || null;
  }

  function achievementCards(stats) {
    return ACHIEVEMENTS.map(function (item) {
      const unlocked = Boolean(item.test(stats));
      return '<div class="mastery-achievement ' + (unlocked ? 'unlocked' : 'locked') + '">' +
        '<span>' + (unlocked ? '✓' : '○') + '</span><div><b>' + esc(item.title) + '</b><small>' + esc(item.hint) + '</small></div></div>';
    }).join('');
  }

  function skillCards(rows, p, focusIds) {
    return rows.map(function (row) {
      const focus = focusIds.indexOf(row.id) !== -1;
      const next = nextGameForSkill(row, p);
      const bestText = next && next.game ? next.game.title : 'Нет доступной игры';
      return '<button class="mastery-skill-card ' + (focus ? 'focus' : '') + '" data-mastery-skill="' + esc(row.id) + '"' +
        (next ? ' data-master-game="' + esc(next.id) + '"' : ' disabled') + '>' +
        '<span class="mastery-skill-icon">' + esc(row.icon) + '</span><span class="mastery-skill-copy"><small>' +
        (focus ? 'ПРИОРИТЕТ ЦЕХА' : 'НАВЫК') + '</small><b>' + esc(row.title) + '</b><em>Следующее: ' + esc(bestText) + '</em></span>' +
        '<span class="mastery-score"><b>' + row.score + '%</b><i><u style="width:' + row.score + '%"></u></i><small>' + tier(row.score) + '</small></span></button>';
    }).join('');
  }

  function signature(p, rows, stats) {
    return [snapshot().language || '', departmentName(), stats.overall, stats.focus, stats.tried, stats.perfect, stats.days]
      .concat(rows.map(function (row) { return row.id + ':' + row.score; })).join('|');
  }

  function launch(gameId) {
    if (!gameId) return;
    Promise.resolve(gameLab().startGame(gameId)).catch(function () { /* game lab owns user-facing error */ });
  }

  function render() {
    const main = query('#main');
    const grid = main && query('.game-lab-grid', main);
    if (!main || !grid) return;

    const p = progress();
    const rows = skillRows(p);
    const stats = summary(p, rows);
    const weakest = weakestRow(rows, stats.focusIds);
    const next = nextGameForSkill(weakest, p);
    const sig = signature(p, rows, stats);
    const existing = query('.arcade-mastery-v620', main);
    if (existing && existing.dataset.masterySignature === sig) return;
    if (existing) existing.remove();

    const panel = document.createElement('section');
    panel.className = 'arcade-mastery-v620';
    panel.dataset.masterySignature = sig;
    panel.innerHTML =
      '<div class="mastery-head"><div><span class="kicker">ARCADE MASTERY · SKILL MAP</span><h2>Карта навыков по вашей игровой практике</h2>' +
      '<p>Сервис переводит результаты 20 игр в семь рабочих компетенций и показывает, что тренировать дальше.</p></div>' +
      '<div class="mastery-ring" style="--mastery:' + stats.overall + '"><div><b>' + stats.overall + '%</b><small>' + tier(stats.overall) + '</small></div></div></div>' +
      '<div class="mastery-summary"><span><b>' + stats.focus + '%</b><small>фокус вашего отдела</small></span><span><b>' + stats.tried + '/20</b><small>механик попробовано</small></span>' +
      '<span><b>' + stats.perfect + '</b><small>идеальных 5/5</small></span><span><b>' + stats.days + '</b><small>активных дней</small></span></div>' +
      '<div class="mastery-next"><div><small>СЛЕДУЮЩИЙ АПГРЕЙД</small><h3>' + esc(weakest ? weakest.title : 'Практика') + '</h3><p>' +
      (next && next.game ? ('Сейчас выгоднее всего пройти «' + esc(next.game.title) + '»: это самый слабый приоритетный навык.') : 'Продолжайте игровые сессии — карта обновится автоматически.') +
      '</p></div>' + (next && next.game ? '<button class="primary" data-master-game="' + esc(next.id) + '">Тренировать слабое место →</button>' : '') + '</div>' +
      '<div class="mastery-grid">' + skillCards(rows, p, stats.focusIds) + '</div>' +
      '<div class="mastery-achievements"><div class="mastery-section-title"><b>Достижения</b><span>Без искусственного фарма XP</span></div><div class="mastery-achievement-grid">' +
      achievementCards(stats) + '</div></div>';

    const anchor = query('.factory-journey-v619', main) || query('.game-lab-grid', main);
    anchor.parentNode.insertBefore(panel, anchor);
    queryAll('[data-master-game]', panel).forEach(function (button) {
      button.addEventListener('click', function () { launch(button.dataset.masterGame); });
    });
  }

  function scheduleRender() {
    if (refreshTimer) root.clearTimeout(refreshTimer);
    refreshTimer = root.setTimeout(function () {
      refreshTimer = null;
      render();
    }, 24);
  }

  function install() {
    if (installed) return;
    installed = true;
    document.addEventListener('mgc:state-change', scheduleRender);
    const main = query('#main');
    observer = new MutationObserver(scheduleRender);
    if (main) observer.observe(main, {childList:true, subtree:true});
    scheduleRender();
  }

  frontend.register('arcade-mastery-v620', {
    install:install,
    render:render,
    skills:SKILLS,
    score:function () {
      const p = progress();
      const rows = skillRows(p);
      return summary(p, rows);
    }
  });

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', install, {once:true});
  else install();
})(typeof window !== 'undefined' ? window : globalThis);
