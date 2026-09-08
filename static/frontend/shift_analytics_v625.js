/* v6.0.25: persistent account-scoped Shift Simulation history, trend analysis and next-training guidance. */
(function (root) {
  "use strict";

  const frontend = root.MGCFrontend;
  if (!frontend) throw new Error("MGCFrontend runtime is missing");
  if (frontend.has("shift-analytics-v625")) return;

  const API_ROOT = "/api/shift-simulations";
  const PENDING_KEY = "mgc.v625.shift.pending";
  const DIMENSIONS = Object.freeze([
    {key:"production_control", label:"Production control"},
    {key:"prioritization", label:"Prioritization"},
    {key:"production_judgement", label:"Production judgement"},
    {key:"language", label:"Language"}
  ]);
  const FACTORY_LABELS = Object.freeze({
    "Стабильность линии":"line",
    "Защита качества":"quality",
    "Material runway":"material",
    "Supplier control":"supplier",
    "Нагрузка команды":"load"
  });
  const FOCUS = Object.freeze({
    production_control:{title:"Production control", text:"Повторите связанную смену с акцентом на containment, restart criteria и evidence до release.", practice:"Shift Simulation + Quality Gate"},
    prioritization:{title:"Prioritization", text:"Тренируйте выбор первого действия: customer / safety / line-stop / run-out должны опережать менее необратимые риски.", practice:"Shift Simulation + Shift Incident"},
    production_judgement:{title:"Production judgement", text:"Усилите техническую логику решений: traceability, first-off, approved stock, quality gate и controlled restart.", practice:"Quality Gate + Spec or NOK? + Shift Incident"},
    language:{title:"Language", text:"Делайте рабочие сообщения измеримыми: факт + объект/lot + требуемое действие + owner + deadline + evidence.", practice:"Dialogue Duel + Phrase Builder"}
  });
  const FACTORY_FOCUS = Object.freeze({
    line:"Линия: отработайте Andon, containment и критерии контролируемого restart.",
    quality:"Качество: раньше фиксируйте suspect window, last known good и evidence перед release.",
    material:"Материал: считайте run-out, approved stock, sequencing и fallback как один recovery plan.",
    supplier:"Поставщик: требуйте part/lot/quantity, ETA, owner, deadline и подтверждающие evidence.",
    load:"Нагрузка: сокращайте параллельный firefighting через одного owner, checkpoint и структурированный handover."
  });

  let installed = false;
  let observer = null;
  let scheduled = false;
  let loading = false;
  let historyData = null;

  function legacy() { return frontend.get("legacy-app"); }
  function state() { return frontend.get("app-state"); }
  function api() { return frontend.get("api-client"); }
  function current() { return state().current(); }
  function query(selector, scope) { return legacy().query(selector, scope); }
  function queryAll(selector, scope) { return legacy().queryAll(selector, scope); }
  function esc(value) { return legacy().escapeHtml(value); }
  function number(value) {
    const parsed = Number(String(value == null ? "" : value).replace(/[^0-9.-]/g, ""));
    return Number.isFinite(parsed) ? Math.max(0, Math.min(100, Math.round(parsed))) : 0;
  }

  function makeSessionId() {
    if (root.crypto && typeof root.crypto.randomUUID === "function") return "shift-v625-" + root.crypto.randomUUID();
    return "shift-v625-" + Date.now() + "-" + Math.random().toString(36).slice(2, 12);
  }

  function readPending() {
    try {
      const parsed = JSON.parse(root.localStorage.getItem(PENDING_KEY) || "[]");
      return Array.isArray(parsed) ? parsed.slice(-10) : [];
    } catch (_) {
      return [];
    }
  }

  function writePending(items) {
    try { root.localStorage.setItem(PENDING_KEY, JSON.stringify((items || []).slice(-10))); } catch (_) {}
  }

  function enqueue(payload) {
    const items = readPending();
    if (!items.some(function (row) { return row.session_id === payload.session_id; })) items.push(payload);
    writePending(items);
  }

  async function flushPending() {
    const items = readPending();
    if (!items.length) return;
    const remaining = [];
    for (const payload of items) {
      try {
        await api().request(API_ROOT, {method:"POST", body:JSON.stringify(payload)});
      } catch (_) {
        remaining.push(payload);
      }
    }
    writePending(remaining);
  }

  function scoreMap(summary) {
    const scores = Object.create(null);
    queryAll(".v624-score-grid > div", summary).forEach(function (card) {
      const label = query("span", card);
      const value = query("b", card);
      if (!label || !value) return;
      const text = String(label.textContent || "").trim();
      const match = DIMENSIONS.find(function (item) { return item.label === text; });
      if (match) scores[match.key] = number(value.textContent);
    });
    return scores;
  }

  function finalMetrics(summary) {
    const metrics = {line:0, quality:0, material:0, supplier:0, load:0};
    queryAll(".v624-final-metrics > b", summary).forEach(function (row) {
      const small = query("small", row);
      if (!small) return;
      const label = String(row.childNodes[0] ? row.childNodes[0].textContent : row.textContent || "").trim();
      const key = FACTORY_LABELS[label];
      if (key) metrics[key] = number(small.textContent);
    });
    return metrics;
  }

  function weakestDimension(scores) {
    return DIMENSIONS.slice().sort(function (a, b) {
      return Number(scores[a.key] || 0) - Number(scores[b.key] || 0);
    })[0].key;
  }

  function weakestFactory(metrics) {
    return Object.keys(metrics).sort(function (a, b) {
      const av = a === "load" ? 100 - Number(metrics[a] || 0) : Number(metrics[a] || 0);
      const bv = b === "load" ? 100 - Number(metrics[b] || 0) : Number(metrics[b] || 0);
      return av - bv;
    })[0];
  }

  function summaryPayload(summary) {
    const scores = scoreMap(summary);
    const metrics = finalMetrics(summary);
    const total = query(".v624-total b", summary);
    if (DIMENSIONS.some(function (item) { return typeof scores[item.key] !== "number"; })) return null;
    return {
      session_id:makeSessionId(),
      language:String(current().language || "chinese") === "english" ? "english" : "chinese",
      production_control:scores.production_control,
      prioritization:scores.prioritization,
      production_judgement:scores.production_judgement,
      language_score:scores.language,
      total_score:number(total ? total.textContent : 0),
      weakest_dimension:weakestDimension(scores),
      factory_weakest:weakestFactory(metrics),
      line:metrics.line,
      quality:metrics.quality,
      material:metrics.material,
      supplier:metrics.supplier,
      load:metrics.load
    };
  }

  async function captureCompletedShift() {
    const summary = query(".v624-summary");
    if (!summary || summary.dataset.v625Captured === "1") return false;
    const payload = summaryPayload(summary);
    if (!payload) return false;
    summary.dataset.v625Captured = "1";
    try {
      await api().request(API_ROOT, {method:"POST", body:JSON.stringify(payload)});
      await loadHistory(true);
      const note = query(".v625-save-state");
      if (note) note.textContent = "Последняя смена сохранена в профиль.";
    } catch (_) {
      enqueue(payload);
      const note = query(".v625-save-state");
      if (note) note.textContent = "Результат сохранён локально и будет синхронизирован при восстановлении связи.";
    }
    return true;
  }

  function trendText(summary) {
    if (!summary || summary.trend_delta == null) return "Тренд появится после нескольких завершённых смен";
    const delta = Number(summary.trend_delta || 0);
    if (delta > 0) return "+" + delta + " к предыдущему окну";
    if (delta < 0) return String(delta) + " к предыдущему окну";
    return "Без изменения к предыдущему окну";
  }

  function dimensionCards(summary) {
    const averages = summary && summary.averages ? summary.averages : {};
    return DIMENSIONS.map(function (item) {
      const value = averages[item.key];
      return '<div class="v625-dimension"><span>' + esc(item.label) + '</span><b>' + (value == null ? "—" : esc(value)) + '</b><small>среднее /100</small></div>';
    }).join("");
  }

  function recurringWeakness(items) {
    const counts = Object.create(null);
    (items || []).forEach(function (item) {
      const key = String(item.weakest_dimension || "");
      if (FOCUS[key]) counts[key] = (counts[key] || 0) + 1;
    });
    return Object.keys(counts).sort(function (a, b) { return counts[b] - counts[a]; })[0] || null;
  }

  function historyRows(items) {
    if (!items || !items.length) {
      return '<div class="v625-empty"><b>Истории пока нет</b><p>Завершите первую Shift Simulation — результат автоматически сохранится в ваш профиль.</p></div>';
    }
    return '<div class="v625-history-list">' + items.slice(0, 6).map(function (item) {
      const date = item.created_at ? new Date(item.created_at) : null;
      const dateText = date && !Number.isNaN(date.getTime()) ? date.toLocaleDateString("ru-RU", {day:"2-digit", month:"2-digit", year:"2-digit"}) : "—";
      return '<div class="v625-history-row"><div><span>' + esc(dateText) + '</span><b>' + esc(item.language === "english" ? "English" : "中文 · Putonghua") + '</b></div>' +
        '<strong>' + esc(item.total_score) + '<small>/100</small></strong>' +
        '<div class="v625-mini-scores"><span>Control ' + esc(item.production_control) + '</span><span>Priority ' + esc(item.prioritization) + '</span><span>Judgement ' + esc(item.production_judgement) + '</span><span>Language ' + esc(item.language) + '</span></div></div>';
    }).join("") + '</div>';
  }

  function panelMarkup(data) {
    const items = data && Array.isArray(data.items) ? data.items : [];
    const summary = data && data.summary ? data.summary : {count:0, latest_total:null, trend_delta:null, averages:{}, weakest_dimension:null, factory_weakest:null};
    const recurring = recurringWeakness(items) || summary.weakest_dimension;
    const focus = recurring && FOCUS[recurring] ? FOCUS[recurring] : null;
    const factory = summary.factory_weakest && FACTORY_FOCUS[summary.factory_weakest] ? FACTORY_FOCUS[summary.factory_weakest] : null;
    return '<section class="v625-analytics-panel"><div class="v625-head"><div><span>PERSONAL SHIFT ANALYTICS · v6.0.25</span><h2>Как вы управляете производственной сменой</h2>' +
      '<p>История сохраняется под вашим аккаунтом в PostgreSQL. Здесь видны повторяющиеся слабые места, а не только последний результат.</p></div>' +
      '<div class="v625-kpis"><div><b>' + esc(summary.count || 0) + '</b><span>смен</span></div><div><b>' + (summary.latest_total == null ? "—" : esc(summary.latest_total)) + '</b><span>последняя</span></div><div><b>' + esc(trendText(summary)) + '</b><span>динамика</span></div></div></div>' +
      '<div class="v625-dimensions">' + dimensionCards(summary) + '</div>' +
      (focus ? '<div class="v625-focus"><div><span>ПОВТОРЯЮЩАЯСЯ ТОЧКА РОСТА</span><h3>' + esc(focus.title) + '</h3><p>' + esc(focus.text) + '</p><small>Следующая практика: ' + esc(focus.practice) + '</small></div>' +
        '<button type="button" class="primary" data-v625-retry>Тренировать в новой смене</button></div>' : '') +
      (factory ? '<div class="v625-factory-focus"><span>Производственный сигнал</span><p>' + esc(factory) + '</p></div>' : '') +
      '<div class="v625-history"><div class="v625-history-title"><span>ПОСЛЕДНИЕ СМЕНЫ</span><small class="v625-save-state">Результаты синхронизируются автоматически</small></div>' + historyRows(items) + '</div></section>';
  }

  function renderPanel() {
    const panel = query(".v625-analytics-panel");
    if (!panel) return false;
    const holder = document.createElement("div");
    holder.innerHTML = panelMarkup(historyData);
    const replacement = holder.firstElementChild;
    if (replacement) panel.replaceWith(replacement);
    bindPanel();
    return true;
  }

  function ensurePanel() {
    const launcher = query(".v624-launcher");
    if (!launcher) return false;
    if (!query(".v625-analytics-panel")) launcher.insertAdjacentHTML("afterend", panelMarkup(historyData));
    bindPanel();
    return true;
  }

  function bindPanel() {
    const retry = query("[data-v625-retry]");
    if (retry && retry.dataset.v625Bound !== "1") {
      retry.dataset.v625Bound = "1";
      retry.addEventListener("click", function () {
        const start = query("[data-v624-start]");
        if (start) start.click();
      });
    }
  }

  async function loadHistory(force) {
    if (loading) return;
    if (historyData && !force) {
      renderPanel();
      return;
    }
    loading = true;
    try {
      await flushPending();
      historyData = await api().request(API_ROOT + "/history?limit=20");
      renderPanel();
    } catch (_) {
      if (!historyData) historyData = {items:[], summary:{count:0, latest_total:null, trend_delta:null, averages:{}, weakest_dimension:null, factory_weakest:null}};
      renderPanel();
      const note = query(".v625-save-state");
      if (note) note.textContent = "История временно недоступна; новые результаты будут синхронизированы позже.";
    } finally {
      loading = false;
    }
  }

  function decorate() {
    scheduled = false;
    if (String(current().view || "") !== "games") return;
    if (ensurePanel() && !historyData) loadHistory(false);
    captureCompletedShift();
  }

  function scheduleDecorate() {
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
      observer = new MutationObserver(scheduleDecorate);
      observer.observe(main, {childList:true, subtree:true});
    }
    document.addEventListener("mgc:state-change", scheduleDecorate);
    document.addEventListener("mgc:frontend-ready", scheduleDecorate);
    scheduleDecorate();
  }

  frontend.register("shift-analytics-v625", {
    apiRoot:API_ROOT,
    dimensions:DIMENSIONS,
    focus:FOCUS,
    summaryPayload:summaryPayload,
    loadHistory:loadHistory,
    decorate:decorate,
    install:install
  });

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", install, {once:true});
  else install();
})(typeof window !== "undefined" ? window : globalThis);
