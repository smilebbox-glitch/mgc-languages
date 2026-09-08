/* v6.0.20: adaptive daily missions and department boss challenge for Automotive Arcade. */
(function (root) {
  'use strict';

  const frontend = root.MGCFrontend;
  if (!frontend) throw new Error('MGCFrontend runtime is missing');
  if (frontend.has('arcade-missions-v620')) return;

  const BOSS_BY_GROUP = Object.freeze({
    paint: {id:'defect_detective', topic:'Окраска', title:'Paint Shop Boss', copy:'Финальная проверка дефектов покрытия.'},
    logistics: {id:'logistics_route', topic:'Логистика JIT/JIS', title:'Material Flow Boss', copy:'Соберите поток без остановки линии.'},
    body: {id:'hotspot', topic:'Кузов и компоненты', title:'Body Shop Boss', copy:'Найдите ключевые детали на автомобиле.'},
    assembly: {id:'assembly_order', topic:'Сборка автомобиля', title:'Assembly Boss', copy:'Восстановите правильную последовательность сборки.'},
    quality: {id:'quality_gate', topic:'Качество в автопроме', title:'Quality Gate Boss', copy:'Примите точное решение PASS / REWORK / HOLD.'},
    rd: {id:'bom_builder', topic:'R&D автомобиля', title:'Engineering Boss', copy:'Свяжите компонент с правильной подсистемой.'},
    purchasing: {id:'dialogue_choice', topic:'Закупки / локализация / ВЭД', title:'Supplier Boss', copy:'Выберите профессиональную реплику в переговорах.'},
    default: {id:'shift_incident', topic:'', title:'Shift Boss', copy:'Примите решение в реальной сменной ситуации.'}
  });

  const TOPIC_BY_GROUP = Object.freeze({
    paint:'Окраска', logistics:'Логистика JIT/JIS', body:'Кузов и компоненты',
    assembly:'Сборка автомобиля', quality:'Качество в автопроме', rd:'R&D автомобиля',
    purchasing:'Закупки / локализация / ВЭД', default:''
  });

  let installed = false;
  let observer = null;

  function stateApi() { return frontend.get('app-state'); }
  function snapshot() { return stateApi().current(); }
  function gameLab() { return frontend.get('game-lab-v618'); }
  function engagement() { return frontend.get('game-engagement-v618'); }
  function query(selector, scope) { return (scope || document).querySelector(selector); }
  function queryAll(selector, scope) { return Array.from((scope || document).querySelectorAll(selector)); }
  function esc(value) {
    return String(value == null ? '' : value).replace(/[&<>"']/g, function (char) {
      return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot',"'":'&#039;'}[char];
    });
  }

  function userKey() {
    const user = snapshot().user || {};
    return String(user.id || user.username || 'guest');
  }

  function todayKey() {
    const now = new Date();
    return [now.getFullYear(), String(now.getMonth() + 1).padStart(2, '0'), String(now.getDate()).padStart(2, '0')].join('-');
  }

  function stableHash(value) {
    let hash = 2166136261;
    const text = String(value || '');
    for (let index = 0; index < text.length; index += 1) {
      hash ^= text.charCodeAt(index);
      hash = Math.imul(hash, 16777619);
    }
    return hash >>> 0;
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

  function storageKey() {
    return 'mgc-arcade-missions-v620-' + userKey() + '-' + String(snapshot().language || 'chinese') + '-' + todayKey();
  }

  function loadDaily() {
    try {
      const value = JSON.parse(root.localStorage.getItem(storageKey()) || '{}');
      return Object.assign({date:todayKey(), done:{}, scores:{}, bossDone:false, bossScore:0}, value || {});
    } catch (_) {
      return {date:todayKey(), done:{}, scores:{}, bossDone:false, bossScore:0};
    }
  }

  function saveDaily(value) {
    try { root.localStorage.setItem(storageKey(), JSON.stringify(value)); } catch (_) { /* non-fatal */ }
  }

  function catalog() {
    return Array.isArray(gameLab().catalog) ? gameLab().catalog : [];
  }

  function gameById(id) {
    return catalog().find(function (game) { return game.id === id; }) || null;
  }

  function distinctPick(candidates, used, seed) {
    const clean = candidates.filter(function (id) { return id && !used.has(id) && gameById(id); });
    if (!clean.length) return null;
    return clean[stableHash(seed) % clean.length];
  }

  function missionPlan() {
    const progress = engagement().progress();
    const group = departmentGroup(departmentName());
    const language = String(snapshot().language || 'chinese');
    const seed = todayKey() + '|' + userKey() + '|' + language + '|' + group;
    const used = new Set();
    const recommended = engagement().recommendationsForDepartment(departmentName());
    const allIds = catalog().map(function (game) { return game.id; });

    const departmentGame = distinctPick(recommended, used, seed + '|department') || distinctPick(allIds, used, seed + '|department-fallback');
    if (departmentGame) used.add(departmentGame);

    const unseen = allIds.filter(function (id) { return !(progress.tried || {})[id]; });
    const discoveryGame = distinctPick(unseen.length ? unseen : allIds, used, seed + '|discover');
    if (discoveryGame) used.add(discoveryGame);

    const weak = Object.keys(progress.tried || {}).filter(function (id) { return gameById(id) && !used.has(id); }).sort(function (a, b) {
      const delta = Number((progress.best || {})[a] || 0) - Number((progress.best || {})[b] || 0);
      return delta || a.localeCompare(b);
    });
    const recoveryGame = distinctPick(weak.length ? weak.slice(0, 6) : allIds, used, seed + '|recover') || distinctPick(allIds, used, seed + '|recover-fallback');

    const topic = TOPIC_BY_GROUP[group] || '';
    return [
      {slot:'department', label:'ЦЕХОВАЯ МИССИЯ', game:departmentGame, topic:topic, copy:'Закрепить лексику, связанную с вашим рабочим направлением.'},
      {slot:'discovery', label:'НОВАЯ МЕХАНИКА', game:discoveryGame, topic:'', copy:'Попробовать игровой формат, который вы ещё не проходили.'},
      {slot:'recovery', label:'ТОЧКА РОСТА', game:recoveryGame, topic:topic, copy:'Вернуться к механике с самым слабым результатом и улучшить его.'}
    ].filter(function (mission) { return Boolean(mission.game); });
  }

  function bossPlan() {
    return BOSS_BY_GROUP[departmentGroup(departmentName())] || BOSS_BY_GROUP.default;
  }

  function completedCount(daily, missions) {
    return missions.filter(function (mission) { return Boolean((daily.done || {})[mission.slot]); }).length;
  }

  function missionSignature(daily, missions) {
    return [todayKey(), snapshot().language || '', departmentName(), daily.bossDone ? 1 : 0, daily.bossScore || 0]
      .concat(missions.map(function (mission) {
        return mission.slot + ':' + mission.game + ':' + ((daily.done || {})[mission.slot] ? 1 : 0) + ':' + Number((daily.scores || {})[mission.slot] || 0);
      })).join('|');
  }

  function launch(gameId, topic) {
    stateApi().set('topic', String(topic || ''));
    return Promise.resolve(gameLab().startGame(gameId)).catch(function () { /* game lab owns user-facing error */ });
  }

  function missionCard(mission, daily) {
    const game = gameById(mission.game);
    if (!game) return '';
    const done = Boolean((daily.done || {})[mission.slot]);
    const score = Number((daily.scores || {})[mission.slot] || 0);
    return '<button class="arcade-mission-card ' + (done ? 'done' : '') + '" data-mission-slot="' + esc(mission.slot) +
      '" data-start-v618-game="' + esc(game.id) + '" data-mission-topic="' + esc(mission.topic) + '">' +
      '<span class="mission-check">' + (done ? '✓' : game.icon || '◇') + '</span>' +
      '<span class="mission-copy"><small>' + esc(mission.label) + '</small><b>' + esc(game.title) + '</b><em>' + esc(mission.copy) + '</em></span>' +
      '<strong>' + (done ? ('DONE ' + score + '/5') : 'СТАРТ') + '</strong></button>';
  }

  function renderPanel() {
    const main = query('#main');
    const grid = main && query('.game-lab-grid', main);
    if (!main || !grid) return;

    const missions = missionPlan();
    if (missions.length < 3) return;
    const daily = loadDaily();
    const signature = missionSignature(daily, missions);
    const existing = query('.arcade-missions-v620', main);
    if (existing && existing.dataset.missionSignature === signature) return;
    if (existing) existing.remove();

    const doneCount = completedCount(daily, missions);
    const boss = bossPlan();
    const bossUnlocked = doneCount >= missions.length;
    const bossGame = gameById(boss.id);
    const panel = document.createElement('section');
    panel.className = 'arcade-missions-v620';
    panel.dataset.missionSignature = signature;
    panel.innerHTML =
      '<div class="mission-console-head"><div><span class="kicker">DAILY MISSIONS · v6.0.20</span><h2>Три короткие миссии на сегодня</h2>' +
      '<p>Сервис смешивает ваш цех, новую механику и слабое место. После 3/3 открывается Boss Shift.</p></div>' +
      '<div class="mission-progress"><span>СЕГОДНЯ</span><b>' + doneCount + '/3</b><small>миссий завершено</small><div><i style="width:' + Math.round((doneCount / 3) * 100) + '%"></i></div></div></div>' +
      '<div class="arcade-mission-grid">' + missions.map(function (mission) { return missionCard(mission, daily); }).join('') + '</div>' +
      '<div class="boss-shift ' + (bossUnlocked ? 'unlocked' : 'locked') + (daily.bossDone ? ' done' : '') + '">' +
      '<div class="boss-light"><i></i><i></i><i></i></div><div><small>' + (daily.bossDone ? 'BOSS COMPLETE' : bossUnlocked ? 'BOSS UNLOCKED' : 'LOCKED · COMPLETE 3/3') +
      '</small><h3>' + esc(boss.title) + '</h3><p>' + esc(boss.copy) + '</p></div>' +
      '<button class="primary" data-boss-v620 data-start-v618-game="' + esc(boss.id) + '" data-mission-topic="' + esc(boss.topic) + '"' +
      (bossUnlocked ? '' : ' disabled') + '>' + (daily.bossDone ? ('Повторить · BEST ' + Number(daily.bossScore || 0) + '/5') : 'Запустить Boss Shift →') + '</button></div>';

    const anchor = query('.factory-journey-v619', main) || query('.arcade-engagement', main) || grid;
    anchor.parentNode.insertBefore(panel, anchor);

    queryAll('[data-mission-slot]', panel).forEach(function (button) {
      button.addEventListener('click', function () {
        void launch(button.dataset.startV618Game, button.dataset.missionTopic);
      });
    });
    const bossButton = query('[data-boss-v620]', panel);
    if (bossButton && !bossButton.disabled) bossButton.addEventListener('click', function () {
      void launch(bossButton.dataset.startV618Game, bossButton.dataset.missionTopic);
    });
  }

  function readScore() {
    const node = query('.game-result-score');
    if (!node) return null;
    const numbers = String(node.textContent || '').match(/\d+/g) || [];
    if (!numbers.length) return null;
    return Number(numbers[0] || 0);
  }

  function captureResult() {
    const panel = query('.game-result-panel');
    if (!panel || panel.dataset.missionV620Captured === 'true') return;
    const score = readScore();
    if (score == null) return;
    panel.dataset.missionV620Captured = 'true';

    const progress = engagement().progress();
    const lastGame = String(progress.lastGame || '');
    if (!lastGame) return;
    const daily = loadDaily();
    const missions = missionPlan();
    const mission = missions.find(function (item) { return item.game === lastGame && !(daily.done || {})[item.slot]; });
    if (mission) {
      daily.done[mission.slot] = true;
      daily.scores[mission.slot] = score;
      saveDaily(daily);
      return;
    }

    const boss = bossPlan();
    if (lastGame === boss.id && completedCount(daily, missions) >= missions.length) {
      daily.bossDone = true;
      daily.bossScore = Math.max(Number(daily.bossScore || 0), score);
      saveDaily(daily);
    }
  }

  function reconcile() {
    captureResult();
    renderPanel();
  }

  function install() {
    if (installed) return;
    installed = true;
    document.addEventListener('mgc:state-change', function () { root.setTimeout(reconcile, 0); });
    observer = new MutationObserver(function () { reconcile(); });
    const main = query('#main');
    if (main) observer.observe(main, {childList:true, subtree:true});
    reconcile();
  }

  frontend.register('arcade-missions-v620', {
    install:install,
    reconcile:reconcile,
    plan:function () { return missionPlan(); },
    daily:function () { return loadDaily(); },
    boss:function () { return bossPlan(); }
  });

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', install, {once:true});
  else install();
})(typeof window !== 'undefined' ? window : globalThis);
