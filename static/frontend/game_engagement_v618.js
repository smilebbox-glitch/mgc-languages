/* v6.0.18: engagement layer for the 20-mode Automotive Arcade. */
(function (root) {
  'use strict';

  const frontend = root.MGCFrontend;
  if (!frontend) throw new Error('MGCFrontend runtime is missing');
  if (frontend.has('game-engagement-v618')) return;

  const RECOMMENDATIONS = Object.freeze({
    paint: ['defect_detective', 'spec_check', 'tool_select', 'safety_spot'],
    logistics: ['logistics_route', 'kanban', 'shop_route', 'rapid_recall'],
    body: ['hotspot', 'bom_builder', 'assembly_order', 'defect_detective'],
    assembly: ['assembly_order', 'tool_select', 'quality_gate', 'rapid_recall'],
    quality: ['defect_detective', 'quality_gate', 'spec_check', 'odd_one_out'],
    rd: ['bom_builder', 'spec_check', 'dialogue_choice', 'odd_one_out'],
    purchasing: ['dialogue_choice', 'logistics_route', 'kanban', 'shift_incident'],
    default: ['hotspot', 'dialogue_choice', 'shift_incident', 'memory_pairs']
  });

  let observer = null;
  let installed = false;

  function state() { return frontend.get('app-state').current(); }
  function gameLab() { return frontend.get('game-lab-v618'); }
  function query(selector, scope) { return (scope || document).querySelector(selector); }
  function queryAll(selector, scope) { return Array.from((scope || document).querySelectorAll(selector)); }
  function esc(value) {
    return String(value == null ? '' : value).replace(/[&<>"']/g, function (char) {
      return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[char];
    });
  }

  function currentUserKey() {
    const snapshot = state();
    const user = snapshot.user || {};
    return String(user.id || user.username || 'guest');
  }

  function storageKey() {
    const snapshot = state();
    return 'mgc-arcade-v618-' + currentUserKey() + '-' + String(snapshot.language || 'chinese');
  }

  function emptyProgress() {
    return {tried:{}, completed:{}, best:{}, days:{}, lastGame:''};
  }

  function loadProgress() {
    try {
      const parsed = JSON.parse(root.localStorage.getItem(storageKey()) || '{}');
      return Object.assign(emptyProgress(), parsed || {});
    } catch (_) {
      return emptyProgress();
    }
  }

  function saveProgress(progress) {
    try { root.localStorage.setItem(storageKey(), JSON.stringify(progress)); } catch (_) { /* non-fatal */ }
  }

  function departmentName() {
    const snapshot = state();
    const user = snapshot.user || {};
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
    if (/r&d|rd|разработ|инженер|engineering/.test(name)) return 'rd';
    if (/закуп|commercial|purchas|procure/.test(name)) return 'purchasing';
    return 'default';
  }

  function catalog() {
    return Array.isArray(gameLab().catalog) ? gameLab().catalog : [];
  }

  function byId(id) {
    return catalog().find(function (item) { return item.id === id; }) || null;
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

  function recommendedIds() {
    const group = departmentGroup(departmentName());
    return (RECOMMENDATIONS[group] || RECOMMENDATIONS.default).slice();
  }

  function dailyGame() {
    const games = catalog();
    if (!games.length) return null;
    const seed = todayKey() + '|' + departmentGroup(departmentName()) + '|' + String(state().language || '');
    return games[stableHash(seed) % games.length];
  }

  function markStarted(id) {
    if (!id) return;
    const progress = loadProgress();
    progress.tried[id] = Date.now();
    progress.lastGame = id;
    saveProgress(progress);
    refreshBadges();
  }

  function readScore() {
    const node = query('.game-result-score');
    if (!node) return null;
    const numbers = String(node.textContent || '').match(/\d+/g) || [];
    if (!numbers.length) return null;
    return {score:Number(numbers[0] || 0), total:Number(numbers[1] || 5)};
  }

  function captureResult() {
    const panel = query('.game-result-panel');
    if (!panel || panel.dataset.engagementCaptured === 'true') return;
    const result = readScore();
    if (!result) return;
    panel.dataset.engagementCaptured = 'true';
    const progress = loadProgress();
    const id = progress.lastGame;
    if (!id) return;
    progress.completed[id] = Number(progress.completed[id] || 0) + 1;
    progress.best[id] = Math.max(Number(progress.best[id] || 0), result.score);
    progress.days[todayKey()] = true;
    saveProgress(progress);
  }

  function recommendedCards(ids) {
    const progress = loadProgress();
    return ids.map(function (id) {
      const game = byId(id);
      if (!game) return '';
      const best = Number(progress.best[id] || 0);
      return '<button class="arcade-rec-card" data-engage-game="' + esc(id) + '">' +
        '<span class="arcade-rec-icon">' + esc(game.icon || '◇') + '</span>' +
        '<span><small>' + esc(game.group || 'Игра') + '</small><b>' + esc(game.title) + '</b>' +
        '<em>' + esc(game.desc || '') + '</em></span>' +
        (best ? '<strong>BEST ' + best + '/5</strong>' : '<strong>СТАРТ</strong>') +
        '</button>';
    }).join('');
  }

  function progressSummary(progress) {
    const tried = Object.keys(progress.tried || {}).length;
    const completed = Object.keys(progress.completed || {}).length;
    const perfect = Object.keys(progress.best || {}).filter(function (id) { return Number(progress.best[id] || 0) >= 5; }).length;
    return {tried:tried, completed:completed, perfect:perfect, pct:Math.round((Math.min(20, tried) / 20) * 100)};
  }

  function augmentCatalog() {
    const grid = query('.game-lab-grid');
    if (!grid) return;
    const main = query('#main');
    if (!main || query('.arcade-engagement', main)) {
      refreshBadges();
      return;
    }

    const progress = loadProgress();
    const summary = progressSummary(progress);
    const department = departmentName() || 'вашего направления';
    const recommended = recommendedIds();
    const daily = dailyGame();
    const anchor = query('.game-lab-summary', main) || grid;
    const panel = document.createElement('section');
    panel.className = 'arcade-engagement';
    panel.innerHTML =
      '<div class="arcade-engagement-head"><div><span class="kicker">ПЕРСОНАЛЬНАЯ АРКАДА</span><h2>Рекомендовано для: ' +
      esc(department) + '</h2><p>Короткие игровые сессии по 5 заданий. Сервис поднимает наверх механики, которые ближе к вашему рабочему контексту.</p></div>' +
      '<div class="arcade-passport"><span>ARCADE PASSPORT</span><b>' + summary.tried + '/20</b><small>механик попробовано</small>' +
      '<div><i style="width:' + summary.pct + '%"></i></div></div></div>' +
      '<div class="arcade-engagement-grid"><div class="arcade-recommend"><div class="arcade-section-title"><b>Для вашего направления</b><span>4 быстрых старта</span></div>' +
      '<div class="arcade-rec-grid">' + recommendedCards(recommended) + '</div></div>' +
      (daily ? '<aside class="arcade-daily"><span>ИГРА ДНЯ · ' + esc(todayKey()) + '</span><div class="arcade-daily-icon">' + esc(daily.icon || '◇') +
        '</div><small>' + esc(daily.group || 'Игра') + '</small><h3>' + esc(daily.title) + '</h3><p>' + esc(daily.desc || '') +
        '</p><button class="primary wide" data-engage-game="' + esc(daily.id) + '">Играть сейчас</button></aside>' : '') +
      '</div><div class="arcade-stats-row"><span><b>' + summary.completed + '</b> игр завершено</span><span><b>' + summary.perfect +
      '</b> идеальных 5/5</span><span><b>' + Object.keys(progress.days || {}).length + '</b> активных дней</span></div>';

    anchor.parentNode.insertBefore(panel, anchor);
    queryAll('[data-engage-game]', panel).forEach(function (button) {
      button.addEventListener('click', function () {
        const id = button.dataset.engageGame;
        markStarted(id);
        Promise.resolve(gameLab().startGame(id)).catch(function () { /* game lab owns user-facing error */ });
      });
    });
    refreshBadges();
  }

  function refreshBadges() {
    const progress = loadProgress();
    queryAll('[data-start-v618-game]').forEach(function (card) {
      const id = card.dataset.startV618Game;
      if (!id) return;
      const tried = Boolean(progress.tried[id]);
      const best = Number(progress.best[id] || 0);
      let badge = query('.arcade-card-progress', card);
      if (!tried && !badge) return;
      if (!badge) {
        badge = document.createElement('span');
        badge.className = 'arcade-card-progress';
        card.appendChild(badge);
      }
      badge.textContent = best ? ('BEST ' + best + '/5') : 'ПРОБОВАЛИ';
      badge.classList.toggle('perfect', best >= 5);
    });

    const passport = query('.arcade-passport');
    if (passport) {
      const summary = progressSummary(progress);
      const count = query('b', passport);
      const bar = query('i', passport);
      if (count) count.textContent = summary.tried + '/20';
      if (bar) bar.style.width = summary.pct + '%';
    }
  }

  function onDocumentClick(event) {
    const start = event.target && event.target.closest ? event.target.closest('[data-start-v618-game]') : null;
    if (start) markStarted(start.dataset.startV618Game);
    const replay = event.target && event.target.closest ? event.target.closest('[data-replay-v618]') : null;
    if (replay) markStarted(replay.dataset.replayV618);
  }

  function reconcile() {
    augmentCatalog();
    captureResult();
  }

  function install() {
    if (installed) return;
    installed = true;
    document.addEventListener('click', onDocumentClick, true);
    document.addEventListener('mgc:state-change', function () { root.setTimeout(reconcile, 0); });
    observer = new MutationObserver(function () { reconcile(); });
    const main = query('#main');
    if (main) observer.observe(main, {childList:true, subtree:true});
    reconcile();
  }

  frontend.register('game-engagement-v618', {
    install:install,
    reconcile:reconcile,
    recommendationsForDepartment:function (name) {
      return (RECOMMENDATIONS[departmentGroup(name)] || RECOMMENDATIONS.default).slice();
    },
    progress:function () { return loadProgress(); }
  });

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', install, {once:true});
  else install();
})(typeof window !== 'undefined' ? window : globalThis);
