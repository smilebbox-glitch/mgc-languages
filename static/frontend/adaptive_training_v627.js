/* v6.0.27: persistent adaptive training loop from server-side game and Shift Simulation history. */
(function (root) {
  "use strict";

  const frontend = root.MGCFrontend;
  if (!frontend) throw new Error("MGCFrontend runtime is missing");
  if (frontend.has("adaptive-training-v627")) return;

  let installed = false;
  let observer = null;
  let scheduled = false;
  let loading = false;
  let cachedKey = "";
  let cachedPlan = null;
  let resultToken = "";

  function legacy() { return frontend.get("legacy-app"); }
  function state() { return frontend.get("app-state"); }
  function api() { return frontend.get("api-client"); }
  function current() { return state().current(); }
  function query(selector, scope) { return legacy().query(selector, scope); }
  function queryAll(selector, scope) { return legacy().queryAll(selector, scope); }
  function esc(value) { return legacy().escapeHtml(value); }
  function toast(value) { legacy().toast(String(value || "")); }

  function planKey() {
    const snapshot = current();
    const user = snapshot.user || {};
    return String(user.id || user.username || "anonymous") + "|" + String(snapshot.language || "chinese");
  }

  async function loadPlan(force) {
    const key = planKey();
    if (!force && cachedPlan && cachedKey === key) return cachedPlan;
    if (loading) return cachedPlan;
    loading = true;
    try {
      const language = String(current().language || "chinese");
      cachedPlan = await api().request('/api/adaptive-training/plan?language=' + encodeURIComponent(language));
      cachedKey = key;
      return cachedPlan;
    } finally {
      loading = false;
    }
  }

  function confidenceLabel(value) {
    if (value === "high") return "высокая уверенность";
    if (value === "medium") return "средняя уверенность";
    return "стартовый профиль";
  }

  function stepMarkup(step, compact) {
    const action = step.kind === "game"
      ? '<button type="button" class="' + (Number(step.step) === 1 ? "primary" : "ghost") + '" data-v627-game="' + esc(step.game_type) + '">' + (Number(step.step) === 1 ? "Начать →" : "Тренировать") + '</button>'
      : '<button type="button" class="ghost" data-v627-shift>Проверить в смене</button>';
    return '<div class="v627-step ' + (compact ? "compact" : "") + '"><span>' + esc(step.step) + '</span><div><b>' + esc(step.title) + '</b><p>' + esc(step.purpose) + '</p></div>' + action + '</div>';
  }

  function panelMarkup(plan, compact) {
    const reasons = Array.isArray(plan.reasons) ? plan.reasons : [];
    const steps = Array.isArray(plan.plan) ? plan.plan : [];
    const source = plan.source || {};
    return '<section class="v627-panel ' + (compact ? "compact" : "") + '">' +
      '<div class="v627-head"><div><span>ADAPTIVE TRAINING LOOP · v6.0.27</span><h2>' + (compact ? "Следующий шаг после результата" : "Персональный маршрут следующей тренировки") + '</h2>' +
      '<p>Сервис объединяет историю игр и Shift Review и меняет маршрут по мере накопления результатов.</p></div>' +
      '<div class="v627-focus"><small>ФОКУС</small><b>' + esc(plan.focus_label || "—") + '</b><span>' + esc(confidenceLabel(plan.confidence)) + '</span></div></div>' +
      (reasons.length ? '<div class="v627-reasons">' + reasons.slice(0, compact ? 2 : 3).map(function (reason) { return '<span>' + esc(reason) + '</span>'; }).join("") + '</div>' : '') +
      '<div class="v627-steps">' + steps.map(function (step) { return stepMarkup(step, compact); }).join("") + '</div>' +
      '<div class="v627-meta"><span>Игровых результатов: <b>' + esc(source.completed_games || 0) + '</b></span><span>Shift Review: <b>' + esc(source.completed_shifts || 0) + '</b></span><span>Дополнительный XP: <b>нет</b></span></div>' +
      '<small class="v627-policy">Адаптация меняет только учебный маршрут. Max-5 и серверный anti-farm остаются без изменений.</small></section>';
  }

  function bindActions(scope) {
    queryAll("[data-v627-game]", scope).forEach(function (button) {
      if (button.dataset.v627Bound === "1") return;
      button.dataset.v627Bound = "1";
      button.addEventListener("click", function () {
        const lab = frontend.get("game-lab-v618");
        if (lab && typeof lab.startGame === "function") void lab.startGame(button.dataset.v627Game);
      });
    });
    queryAll("[data-v627-shift]", scope).forEach(function (button) {
      if (button.dataset.v627Bound === "1") return;
      button.dataset.v627Bound = "1";
      button.addEventListener("click", openShiftSimulation);
    });
  }

  function openShiftSimulation() {
    function launch() {
      const start = query("[data-v624-start]");
      if (!start) return false;
      start.click();
      const host = query(".v624-sim-host");
      if (host && host.scrollIntoView) host.scrollIntoView({behavior:"smooth", block:"start"});
      return true;
    }
    if (launch()) return;
    const lab = frontend.get("game-lab-v618");
    if (lab && typeof lab.render === "function") lab.render();
    root.setTimeout(function () {
      if (!launch()) toast("Откройте блок Shift Simulation в разделе «Игры».");
    }, 80);
  }

  async function renderCatalogPlan() {
    if (String(current().view || "") !== "games") return;
    const summary = query(".game-lab-summary");
    if (!summary || query(".v627-panel:not(.compact)")) return;
    try {
      const plan = await loadPlan(false);
      if (!plan || !summary.isConnected || query(".v627-panel:not(.compact)")) return;
      summary.insertAdjacentHTML("afterend", panelMarkup(plan, false));
      const panel = query(".v627-panel:not(.compact)");
      if (panel) bindActions(panel);
    } catch (_) {
      // Adaptive recommendations are non-blocking; the core game catalog stays usable.
    }
  }

  async function renderResultPlan() {
    const result = query(".game-result-panel");
    if (!result) {
      resultToken = "";
      return;
    }
    const score = query(".game-result-score", result);
    const token = planKey() + "|" + (score ? String(score.textContent || "") : "result");
    if (resultToken === token && query(".v627-panel.compact")) return;
    resultToken = token;
    try {
      const plan = await loadPlan(true);
      if (!plan || !result.isConnected || query(".v627-panel.compact")) return;
      const leaderboard = query(".v626-leaderboard");
      const anchor = leaderboard && leaderboard.isConnected ? leaderboard : result;
      anchor.insertAdjacentHTML("afterend", panelMarkup(plan, true));
      const panel = query(".v627-panel.compact");
      if (panel) bindActions(panel);
    } catch (_) {
      // A completed result must never be hidden because recommendation refresh failed.
    }
  }

  function decorate() {
    scheduled = false;
    if (String(current().view || "") !== "games") return;
    void renderCatalogPlan();
    void renderResultPlan();
  }

  function schedule() {
    if (scheduled) return;
    scheduled = true;
    if (root.requestAnimationFrame) root.requestAnimationFrame(decorate);
    else root.setTimeout(decorate, 0);
  }

  function invalidate() {
    cachedKey = "";
    cachedPlan = null;
    resultToken = "";
    schedule();
  }

  function install() {
    if (installed) return;
    installed = true;
    const main = query("#main");
    if (main && root.MutationObserver) {
      observer = new MutationObserver(schedule);
      observer.observe(main, {childList:true, subtree:true});
    }
    document.addEventListener("mgc:state-change", function (event) {
      const detail = event && event.detail ? event.detail : {};
      if (detail.language || detail.user) invalidate();
      else schedule();
    });
    document.addEventListener("mgc:frontend-ready", schedule);
    schedule();
  }

  frontend.register("adaptive-training-v627", {
    panelMarkup:panelMarkup,
    loadPlan:loadPlan,
    openShiftSimulation:openShiftSimulation,
    invalidate:invalidate,
    decorate:decorate,
    install:install
  });

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", install, {once:true});
  else install();
})(typeof window !== "undefined" ? window : globalThis);
