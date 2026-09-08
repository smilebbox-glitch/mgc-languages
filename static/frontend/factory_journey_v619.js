/* v6.0.19: Factory Journey — guided automotive learning route over the 20-mode arcade. */
(function (root) {
  'use strict';

  const frontend = root.MGCFrontend;
  if (!frontend) throw new Error('MGCFrontend runtime is missing');
  if (frontend.has('factory-journey-v619')) return;

  const STATIONS = Object.freeze([
    {id:'press', title:'Штамповка', subtitle:'Press Shop', topic:'Штамповка', game:'shop_route', icon:'01', copy:'Распределите термин по правильному цеху и закрепите производственную логику.'},
    {id:'body', title:'Кузов / сварка', subtitle:'Body Shop', topic:'Кузов и компоненты', game:'hotspot', icon:'02', copy:'Найдите деталь на автомобиле и свяжите название с реальным расположением.'},
    {id:'paint', title:'Окраска', subtitle:'Paint Shop', topic:'Окраска', game:'defect_detective', icon:'03', copy:'Распознавайте дефекты покрытия и профессиональную терминологию окрасочного цеха.'},
    {id:'assembly', title:'Сборка', subtitle:'Assembly Shop', topic:'Сборка автомобиля', game:'assembly_order', icon:'04', copy:'Соберите технологическую последовательность и закрепите рабочие фразы.'},
    {id:'quality', title:'Качество', subtitle:'Quality Gate', topic:'Качество в автопроме', game:'quality_gate', icon:'05', copy:'Примите решение PASS / REWORK / HOLD по фактическим данным.'},
    {id:'logistics', title:'Логистика', subtitle:'Material Flow', topic:'Логистика JIT/JIS', game:'logistics_route', icon:'06', copy:'Постройте материальный поток от приёмки до линии и выучите JIT/JIS лексику.'}
  ]);

  let observer = null;
  let installed = false;

  function gameLab() { return frontend.get('game-lab-v618'); }
  function engagement() { return frontend.get('game-engagement-v618'); }
  function stateApi() { return frontend.get('app-state'); }
  function query(selector, scope) { return (scope || document).querySelector(selector); }
  function queryAll(selector, scope) { return Array.from((scope || document).querySelectorAll(selector)); }
  function esc(value) {
    return String(value == null ? '' : value).replace(/[&<>"']/g, function (char) {
      return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[char];
    });
  }

  function progress() {
    const value = engagement().progress();
    return value && typeof value === 'object' ? value : {tried:{}, completed:{}, best:{}};
  }

  function stationDone(station, data) {
    return Number((data.completed || {})[station.game] || 0) > 0;
  }

  function stationBest(station, data) {
    return Number((data.best || {})[station.game] || 0);
  }

  function stationUnlocked(index, data) {
    if (index === 0) return true;
    return stationDone(STATIONS[index - 1], data);
  }

  function journeySummary(data) {
    const completed = STATIONS.filter(function (station) { return stationDone(station, data); }).length;
    const perfect = STATIONS.filter(function (station) { return stationBest(station, data) >= 5; }).length;
    const pct = Math.round((completed / STATIONS.length) * 100);
    return {completed:completed, perfect:perfect, pct:pct};
  }

  function journeySignature(data) {
    return STATIONS.map(function (station, index) {
      return [station.id, stationDone(station, data) ? 1 : 0, stationBest(station, data), stationUnlocked(index, data) ? 1 : 0].join(':');
    }).join('|');
  }

  function nextStation(data) {
    for (let index = 0; index < STATIONS.length; index += 1) {
      if (stationUnlocked(index, data) && !stationDone(STATIONS[index], data)) return STATIONS[index];
    }
    return STATIONS[STATIONS.length - 1];
  }

  function launchStation(game, topic) {
    stateApi().set('topic', String(topic || ''));
    return Promise.resolve(gameLab().startGame(game)).catch(function () { /* game lab owns error UI */ });
  }

  function stationHTML(station, index, data) {
    const done = stationDone(station, data);
    const unlocked = stationUnlocked(index, data);
    const best = stationBest(station, data);
    const stateClass = done ? 'done' : unlocked ? 'unlocked' : 'locked';
    const stateText = done ? ('BEST ' + best + '/5') : unlocked ? 'ДОСТУПНО' : 'ЗАКРЫТО';
    return '<button class="factory-journey-station ' + stateClass + '" data-factory-station="' + esc(station.id) +
      '" data-start-v618-game="' + esc(station.game) + '" data-factory-topic="' + esc(station.topic) + '"' +
      (unlocked ? '' : ' disabled') + '>' +
      '<span class="factory-station-index">' + esc(station.icon) + '</span>' +
      '<span class="factory-station-copy"><small>' + esc(station.subtitle) + '</small><b>' + esc(station.title) +
      '</b><em>' + esc(station.copy) + '</em></span><strong>' + esc(stateText) + '</strong></button>';
  }

  function renderJourney() {
    const main = query('#main');
    if (!main) return;
    const arcade = query('.arcade-engagement', main);
    const catalog = query('.game-lab-grid', main);
    if (!catalog) return;

    const data = progress();
    const signature = journeySignature(data);
    const existing = query('.factory-journey-v619', main);
    if (existing && existing.dataset.journeySignature === signature) return;
    if (existing) existing.remove();

    const summary = journeySummary(data);
    const next = nextStation(data);
    const section = document.createElement('section');
    section.className = 'factory-journey-v619';
    section.dataset.journeySignature = signature;
    section.innerHTML =
      '<div class="factory-journey-head"><div><span class="kicker">FACTORY JOURNEY · v6.0.19</span>' +
      '<h2>Пройдите автомобиль через весь завод</h2>' +
      '<p>Шесть связанных станций превращают отдельные мини-игры в один маршрут: от штамповки до логистики. Следующая станция открывается после завершения предыдущей, а каждая запускается на словаре своего цеха.</p></div>' +
      '<div class="factory-journey-meter"><span>МАРШРУТ</span><b>' + summary.completed + '/6</b><small>станций завершено</small>' +
      '<div><i style="width:' + summary.pct + '%"></i></div></div></div>' +
      '<div class="factory-conveyor" aria-label="Маршрут по цехам"><div class="factory-conveyor-line"></div>' +
      STATIONS.map(function (station, index) { return stationHTML(station, index, data); }).join('') + '</div>' +
      '<div class="factory-journey-footer"><div><b>' + summary.perfect + '</b><span>идеальных станций 5/5</span></div>' +
      '<div><b>' + summary.pct + '%</b><span>маршрута пройдено</span></div>' +
      '<button class="primary" data-factory-continue data-start-v618-game="' + esc(next.game) +
      '" data-factory-topic="' + esc(next.topic) + '">' +
      (summary.completed >= STATIONS.length ? 'Повторить финальную станцию' : 'Продолжить маршрут') + ' →</button></div>';

    if (arcade && arcade.parentNode) arcade.parentNode.insertBefore(section, arcade.nextSibling);
    else catalog.parentNode.insertBefore(section, catalog);

    queryAll('[data-factory-station]:not(:disabled)', section).forEach(function (button) {
      button.addEventListener('click', function () {
        void launchStation(button.dataset.startV618Game, button.dataset.factoryTopic);
      });
    });

    const continueButton = query('[data-factory-continue]', section);
    if (continueButton) continueButton.addEventListener('click', function () {
      void launchStation(continueButton.dataset.startV618Game, continueButton.dataset.factoryTopic);
    });
  }

  function reconcile() {
    if (!frontend.has('game-lab-v618') || !frontend.has('game-engagement-v618')) return;
    root.setTimeout(renderJourney, 0);
  }

  function install() {
    if (installed) return;
    installed = true;
    const main = query('#main');
    if (main) {
      observer = new MutationObserver(function () { reconcile(); });
      observer.observe(main, {childList:true, subtree:true});
    }
    document.addEventListener('mgc:state-change', reconcile);
    reconcile();
  }

  frontend.register('factory-journey-v619', {
    install:install,
    reconcile:reconcile,
    stations:STATIONS,
    summary:function () { return journeySummary(progress()); }
  });

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', install, {once:true});
  else install();
})(typeof window !== 'undefined' ? window : globalThis);
