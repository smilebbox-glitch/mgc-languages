/* v6.0.26: department manager analytics and Top-10 timed learning leaderboards. */
(function (root) {
  "use strict";

  const frontend = root.MGCFrontend;
  if (!frontend) throw new Error("MGCFrontend runtime is missing");
  if (frontend.has("team-leaderboard-v626")) return;

  const DIMENSIONS = Object.freeze([
    {key:"production_control", label:"Production control"},
    {key:"prioritization", label:"Prioritization"},
    {key:"production_judgement", label:"Production judgement"},
    {key:"language", label:"Language"}
  ]);
  const FACTORY = Object.freeze([
    {key:"line", label:"Line"}, {key:"quality", label:"Quality"},
    {key:"material", label:"Material"}, {key:"supplier", label:"Supplier"},
    {key:"load", label:"Team load control"}
  ]);

  let installed = false;
  let observer = null;
  let scheduled = false;
  let lastGame = null;
  let leaderboardLoading = false;
  let leaderboardKey = "";
  let managerLoading = false;
  let managerKey = "";

  function legacy() { return frontend.get("legacy-app"); }
  function state() { return frontend.get("app-state"); }
  function api() { return frontend.get("api-client"); }
  function current() { return state().current(); }
  function query(selector, scope) { return legacy().query(selector, scope); }
  function esc(value) { return legacy().escapeHtml(value); }

  function formatTime(ms) {
    const value = Math.max(0, Number(ms || 0));
    if (value >= 60000) {
      const minutes = Math.floor(value / 60000);
      const seconds = Math.floor((value % 60000) / 1000);
      return minutes + ":" + String(seconds).padStart(2, "0");
    }
    return (value / 1000).toFixed(1) + " с";
  }

  function rememberGame() {
    const session = current().gameSession;
    if (!session || !session.session_id || !session.game_type) return;
    lastGame = {
      session_id:String(session.session_id),
      game_type:String(session.game_type),
      language:String(session.language || current().language || "chinese"),
      topic:String(session.topic || "")
    };
  }

  function leaderboardMarkup(data) {
    const rows = data && Array.isArray(data.ranking) ? data.ranking : [];
    const currentPosition = data && data.current_position != null ? Number(data.current_position) : null;
    return '<section class="v626-leaderboard"><div class="v626-leaderboard-head"><div><span>TOP 10 · SCORE + TIME</span>' +
      '<h2>Таблица лидеров подразделения</h2><p>Сначала выше результат, при равных очках — меньшее время. В рейтинг входит только лучшая попытка сотрудника.</p></div>' +
      '<div class="v626-position"><b>' + (currentPosition == null ? "—" : esc(currentPosition)) + '</b><span>ваше место</span></div></div>' +
      (rows.length ? '<div class="v626-ranking">' + rows.map(function (row) {
        return '<div class="v626-rank-row ' + (row.is_current_user ? "current" : "") + '"><b class="v626-rank">' + esc(row.rank) + '</b>' +
          '<span class="v626-name">' + esc(row.display_name) + (row.is_current_user ? '<small>Вы</small>' : '') + '</span>' +
          '<strong>' + esc(row.score) + '<small>/' + esc(row.total) + '</small></strong><time>' + esc(formatTime(row.duration_ms)) + '</time></div>';
      }).join("") + '</div>' : '<div class="v626-empty"><b>Рейтинг формируется</b><p>Нужно хотя бы одно завершённое сервером игровое задание в вашем подразделении.</p></div>') +
      '<small class="v626-rule">Учебный рейтинг. Не используется как HR-оценка и не влияет на XP.</small></section>';
  }

  async function renderLeaderboard() {
    rememberGame();
    const resultCard = query(".result-score");
    if (!resultCard || !lastGame || query(".v626-leaderboard") || leaderboardLoading) return;
    const key = [lastGame.session_id, lastGame.game_type, lastGame.language, lastGame.topic].join("|");
    if (leaderboardKey === key) return;
    leaderboardLoading = true;
    try {
      const url = '/api/leaderboards/games/' + encodeURIComponent(lastGame.game_type) +
        '?language=' + encodeURIComponent(lastGame.language) +
        '&topic=' + encodeURIComponent(lastGame.topic) + '&limit=10';
      const data = await api().request(url);
      const card = resultCard.closest ? resultCard.closest(".card") : null;
      if (card && !query(".v626-leaderboard")) card.insertAdjacentHTML("afterend", leaderboardMarkup(data));
      leaderboardKey = key;
    } catch (_) {
      const card = resultCard.closest ? resultCard.closest(".card") : null;
      if (card && !query(".v626-leaderboard")) {
        card.insertAdjacentHTML("afterend", '<section class="v626-leaderboard compact"><b>Таблица лидеров временно недоступна</b><p>Результат задания сохранён; рейтинг можно увидеть после следующего прохождения.</p></section>');
      }
    } finally {
      leaderboardLoading = false;
    }
  }

  function metricCards(values, rows, suffix) {
    return rows.map(function (item) {
      const value = values && values[item.key] != null ? values[item.key] : null;
      return '<div><span>' + esc(item.label) + '</span><b>' + (value == null ? "—" : esc(value)) + '</b><small>' + esc(suffix) + '</small></div>';
    }).join("");
  }

  function managerMarkup(data) {
    const summary = data && data.summary ? data.summary : {};
    const mix = summary.language_mix || {};
    return '<section class="v626-team-panel"><div class="v626-team-head"><div><span>TEAM ANALYTICS · v6.0.26</span><h2>Учебная картина подразделения</h2>' +
      '<p>Агрегаты по Shift Simulation без рейтинга сотрудников. Руководителю показывается только разрешённый department scope.</p></div>' +
      '<div class="v626-team-kpis"><div><b>' + esc(summary.participants || 0) + '/' + esc(summary.eligible_users || 0) + '</b><span>участники</span></div>' +
      '<div><b>' + esc(summary.completed_shifts || 0) + '</b><span>смены</span></div><div><b>' + esc(summary.participation_percent || 0) + '%</b><span>охват</span></div></div></div>' +
      '<div class="v626-subtitle"><b>Средние учебные компетенции</b><span>китайских смен: ' + esc(mix.chinese || 0) + ' · английских: ' + esc(mix.english || 0) + '</span></div>' +
      '<div class="v626-team-grid">' + metricCards(summary.averages || {}, DIMENSIONS, "из 100") + '</div>' +
      '<div class="v626-subtitle"><b>Factory health после симуляций</b><span>Load нормализован: выше = лучше контролируется нагрузка</span></div>' +
      '<div class="v626-factory-grid">' + metricCards(summary.factory_health || {}, FACTORY, "health /100") + '</div>' +
      '<div class="v626-focus-row"><div><span>КОМАНДНЫЙ ФОКУС</span><b>' + esc(summary.weakest_dimension || "—") + '</b><p>' + esc(summary.recommended_training || "Нужно больше завершённых смен для устойчивого сигнала.") + '</p></div>' +
      '<div><span>ПРОИЗВОДСТВЕННЫЙ ФОКУС</span><b>' + esc(summary.weakest_factory || "—") + '</b><p>' + esc(summary.factory_training || "Нужно больше данных.") + '</p></div></div>' +
      '<small class="v626-privacy">' + esc((data && data.note) || "Учебная агрегированная аналитика; не HR-рейтинг.") + '</small></section>';
  }

  async function renderManagerAnalytics() {
    const snapshot = current();
    if (String(snapshot.view || "") !== "manager") return;
    const table = query(".admin-table");
    if (!table || query(".v626-team-panel") || managerLoading) return;
    const department = snapshot.user && snapshot.user.department ? String(snapshot.user.department) : "";
    const language = String(snapshot.language || "chinese");
    const key = department + "|" + language;
    if (managerKey === key) return;
    managerLoading = true;
    try {
      const data = await api().request('/api/manager/shift-analytics?language=' + encodeURIComponent(language));
      const wrap = table.closest ? table.closest(".table-wrap") : null;
      if (wrap && !query(".v626-team-panel")) wrap.insertAdjacentHTML("beforebegin", managerMarkup(data));
      managerKey = key;
    } catch (_) {
      const wrap = table.closest ? table.closest(".table-wrap") : null;
      if (wrap && !query(".v626-team-panel")) wrap.insertAdjacentHTML("beforebegin", '<section class="v626-team-panel compact"><b>Командная аналитика временно недоступна</b></section>');
    } finally {
      managerLoading = false;
    }
  }

  function decorate() {
    scheduled = false;
    rememberGame();
    void renderLeaderboard();
    void renderManagerAnalytics();
  }

  function schedule() {
    if (scheduled) return;
    scheduled = true;
    if (root.requestAnimationFrame) root.requestAnimationFrame(decorate);
    else root.setTimeout(decorate, 0);
  }

  function install() {
    if (installed) return;
    installed = true;
    const main = query("#main");
    if (main && root.MutationObserver) {
      observer = new MutationObserver(schedule);
      observer.observe(main, {childList:true, subtree:true});
    }
    document.addEventListener("mgc:state-change", schedule);
    document.addEventListener("mgc:frontend-ready", schedule);
    schedule();
  }

  frontend.register("team-leaderboard-v626", {
    formatTime:formatTime,
    leaderboardMarkup:leaderboardMarkup,
    managerMarkup:managerMarkup,
    decorate:decorate,
    install:install
  });

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", install, {once:true});
  else install();
})(typeof window !== "undefined" ? window : globalThis);
