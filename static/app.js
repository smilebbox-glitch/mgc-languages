const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => Array.from(root.querySelectorAll(selector));

const state = {
  user: null,
  authMode: 'login',
  language: 'chinese',
  view: 'home',
  summary: null,
  topics: [],
  level: 'A1',
  topic: null,
  topicDetail: null,
  quiz: null,
  quizIndex: 0,
  quizScore: 0,
  quizAnswered: false,
  scenarioItems: [],
  scenarioTopic: 'Все',
  scenarioIndex: 0,
  scenarioScore: 0,
  scenarioAnswered: false,
  courseData: null,
  courseDay: 1,
  pairIndex: 0,
  pairAnswered: false,
  dayQuiz: null,
  dayQuizIndex: 0,
  dayQuizScore: 0,
  dayQuizAnswered: false,
  exam: null,
  examIndex: 0,
  examScore: 0,
  examAnswered: false,
  knowledgeItems: [],
  knowledgeId: null,
  knowledgeTopic: 'Все',
  gamification: null,
  rewards: null,
  nudges: [],
  notificationSettings: null,
  gameType: null,
  gameSession: null,
  gameAnswers: [],
  gameIndex: 0,
  practiceSessionId: null,
  xpPack: null,
  adminUsers: [],
  adminTerms: [],
  adminTaxonomy: null,
  learningPrefs: {show_pinyin:true, show_reading:true, server_audio_enabled:true},
  chineseFoundations: null,
  toneLab: null,
  pronunciationStatus: null,
  activeAudio: null,
  activeAudioUrl: null,
  activeAudioController: null,
  managerTeam: null,
  meta: null,
  itDashboard: null,
  pilot: {features:{},groups:[],assignments:[]},
  pilotGroups: [],
  pilotFeatures: [],
  pilotGovernance: null,
  questionQuality: null
};

const languageName = () => state.language === 'english' ? 'английский' : 'китайский';
const targetLabel = () => state.language === 'english' ? 'English' : '中文 · 普通话';

function esc(value) {
  return String(value == null ? '' : value).replace(/[&<>"']/g, function (char) {
    return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[char];
  });
}

function cookieValue(name) {
  const prefix = name + '=';
  const row = document.cookie.split(';').map(v => v.trim()).find(v => v.startsWith(prefix));
  return row ? decodeURIComponent(row.slice(prefix.length)) : '';
}

function setServiceStatus(message) {
  let node = $('#serviceStatus');
  if (!node) {
    node = document.createElement('div');
    node.id = 'serviceStatus';
    node.className = 'service-status hidden';
    document.body.appendChild(node);
  }
  if (!message) { node.classList.add('hidden'); node.textContent = ''; return; }
  node.textContent = message;
  node.classList.remove('hidden');
}

async function api(url, options) {
  const opts = Object.assign({credentials: 'same-origin'}, options || {});
  opts.headers = Object.assign({}, opts.headers || {});
  if (opts.body && !(opts.body instanceof FormData)) {
    opts.headers = Object.assign({'Content-Type': 'application/json'}, opts.headers || {});
  }
  const method = String(opts.method || 'GET').toUpperCase();
  if (['POST','PUT','PATCH','DELETE'].includes(method)) {
    const csrf = cookieValue('mgc_csrf');
    if (csrf) opts.headers['X-CSRF-Token'] = csrf;
  }
  const response = await fetch(url, opts);
  let data = {};
  try { data = await response.json(); } catch (_) {}
  if (response.status === 401 && !url.includes('/api/login')) {
    showAuth();
    throw new Error('Требуется повторный вход');
  }
  if (!response.ok) {
    if (response.status === 503 && data.code === 'database_unavailable') {
      setServiceStatus('Сервис временно недоступен из-за базы данных. Интерфейс остаётся открыт; повторите действие через несколько секунд.');
    }
    throw new Error(data.detail || 'Не удалось выполнить запрос');
  }
  if (!url.includes('/api/pronunciation/')) setServiceStatus('');
  return data;
}

function toast(message) {
  const node = $('#toast');
  node.textContent = message;
  node.classList.remove('hidden');
  clearTimeout(toast.timer);
  toast.timer = setTimeout(function () { node.classList.add('hidden'); }, 3200);
}

function showAuth() {
  $('#appView').classList.add('hidden');
  $('#authView').classList.remove('hidden');
}

function showApp() {
  $('#authView').classList.add('hidden');
  $('#appView').classList.remove('hidden');
}

function setAuthMode(mode) {
  state.authMode = mode;
  $$('.auth-tab').forEach(function (button) {
    button.classList.toggle('active', button.dataset.authMode === mode);
  });
  $('#displayNameWrap').classList.toggle('hidden', mode !== 'register');
  $('#authSubmit').textContent = mode === 'register' ? 'Создать аккаунт' : 'Войти';
  $('#password').autocomplete = mode === 'register' ? 'new-password' : 'current-password';
  $('#authMessage').textContent = '';
}

async function submitAuth(event) {
  event.preventDefault();
  const message = $('#authMessage');
  message.textContent = '';
  const payload = {
    username: $('#username').value.trim(),
    password: $('#password').value,
    display_name: $('#displayName').value.trim() || null
  };
  const endpoint = state.authMode === 'register' ? '/api/register' : '/api/login';
  try {
    $('#authSubmit').disabled = true;
    const result = await api(endpoint, {method: 'POST', body: JSON.stringify(payload)});
    state.user = result.user;
    state.language = result.user.preferred_language || 'chinese';
    showApp();
    await loadLanguage();
    await setView('home');
  } catch (error) {
    message.textContent = error.message;
  } finally {
    $('#authSubmit').disabled = false;
  }
}

async function boot() {
  bindStaticEvents();
  try { state.meta = await api('/api/meta'); } catch (_) { state.meta = {auth_mode:'local', registration_enabled:true}; }
  configureAuthUi();
  try {
    state.user = await api('/api/me');
    state.language = state.user.preferred_language || 'chinese';
    showApp();
    await loadLanguage();
    await setView('home');
  } catch (_) {
    showAuth();
  }
}

function configureAuthUi() {
  const meta = state.meta || {};
  const oidc = meta.auth_mode === 'oidc';
  $('#oidcLogin').classList.toggle('hidden', !oidc);
  $('#authForm').classList.toggle('hidden', oidc);
  $('#authTabs').classList.toggle('hidden', oidc);
  const registerTab = $('[data-auth-mode="register"]');
  if (registerTab) registerTab.classList.toggle('hidden', !meta.registration_enabled);
  if (!meta.registration_enabled && state.authMode === 'register') setAuthMode('login');
}

function bindStaticEvents() {
  $$('.auth-tab').forEach(function (button) {
    button.addEventListener('click', function () { setAuthMode(button.dataset.authMode); });
  });
  $('#authForm').addEventListener('submit', submitAuth);
  $('#oidcLogin').addEventListener('click', function () { window.location.href = '/api/auth/oidc/login'; });
  $('#pinyinToggle').addEventListener('click', togglePinyin);
  $$('[data-view]').forEach(function (button) {
    button.addEventListener('click', function () { setView(button.dataset.view); });
  });
  $$('[data-language]').forEach(function (button) {
    button.addEventListener('click', function () { switchLanguage(button.dataset.language); });
  });
  $('#logoutButton').addEventListener('click', async function () {
    try { await api('/api/logout', {method: 'POST'}); } catch (_) {}
    state.user = null;
    showAuth();
  });
  $('#menuToggle').addEventListener('click', function () {
    $('#sidebar').classList.toggle('open');
    $('#backdrop').classList.toggle('hidden');
  });
  $('#backdrop').addEventListener('click', closeMenu);
  $('#main').addEventListener('click', delegatedClick);
}

function closeMenu() {
  $('#sidebar').classList.remove('open');
  $('#backdrop').classList.add('hidden');
}

async function delegatedClick(event) {
  const speak = event.target.closest('[data-speak-text]');
  if (speak) {
    const original = speak.textContent;
    speak.disabled = true; speak.textContent = '…';
    try {
      await playPronunciation(speak.dataset.speakText, Number(speak.dataset.speakRate || .9), speak.dataset.speakLanguage || state.language);
    } finally {
      speak.disabled = false; speak.textContent = original;
    }
    return;
  }
  const go = event.target.closest('[data-go]');
  if (go) {
    if (go.dataset.topic) {
      state.topic = go.dataset.topic;
      state.scenarioTopic = go.dataset.topic;
      if (go.dataset.go === 'quiz') {
        state.quiz = null;
        state.quizIndex = 0;
        state.quizScore = 0;
      }
      if (go.dataset.go === 'roleplay') {
        state.scenarioIndex = 0;
        state.scenarioAnswered = false;
      }
    }
    await setView(go.dataset.go);
  }
}

function resetLanguageState() {
  state.topic = null;
  state.topicDetail = null;
  state.quiz = null;
  state.scenarioItems = [];
  state.scenarioTopic = 'Все';
  state.scenarioIndex = 0;
  state.scenarioScore = 0;
  state.scenarioAnswered = false;
  state.courseData = null;
  state.dayQuiz = null;
  state.exam = null;
  state.knowledgeItems = [];
  state.knowledgeId = null;
  state.knowledgeTopic = 'Все';
  state.level = 'A1';
  state.gameSession = null;
  state.gameAnswers = [];
  state.xpPack = null;
}


async function switchLanguage(language) {
  if (language === state.language) return;
  state.language = language;
  resetLanguageState();
  await api('/api/me/language', {method: 'POST', body: JSON.stringify({language: language})});
  await loadLanguage();
  await setView('home');
}

async function loadLanguage() {
  const values = await Promise.all([
    api('/api/language/' + state.language + '/summary'),
    api('/api/language/' + state.language + '/topics'),
    api('/api/gamification/me'),
    api('/api/notifications/pending'),
    api('/api/learning/preferences'),
    api('/api/pronunciation/status').catch(function () { return {server_available:false,engine:'browser-fallback'}; }),
    api('/api/pilot/me').catch(function(){ return {features:{},groups:[],assignments:[],chinese_standard:{name:'Путунхуа (普通话)',label:'стандартный китайский'}}; })
  ]);
  state.summary = values[0];
  state.topics = values[1];
  state.gamification = values[2];
  state.nudges = values[3].items || [];
  state.notificationSettings = values[3].settings || null;
  state.learningPrefs = values[4] || state.learningPrefs;
  state.pronunciationStatus = values[5] || null;
  state.pilot = values[6] || state.pilot;
  if (!state.topic && state.topics.length) state.topic = state.topics[0].label;
  $$('[data-language]').forEach(function (button) {
    button.classList.toggle('active', button.dataset.language === state.language);
  });
  const xpPill = $('#xpPill');
  if (xpPill) xpPill.textContent = state.gamification.spendable_xp + ' XP';
  const adminNav = $('#adminNav');
  if (adminNav) adminNav.classList.toggle('hidden', !['admin','editor'].includes(state.user.role));
  const managerNav = $('#managerNav');
  if (managerNav) managerNav.classList.toggle('hidden', state.user.role !== 'manager');
  updateLearningControls();
  maybeBrowserNudge();
}

function featureEnabled(key) {
  const flags = (state.pilot && state.pilot.features) || {};
  return flags[key] !== false;
}

function applyFeatureVisibility() {
  $$('[data-view="games"]').forEach(function(x){ x.classList.toggle('hidden', !featureEnabled('games')); });
  $$('[data-view="xp"]').forEach(function(x){ x.classList.toggle('hidden', !featureEnabled('xp_economy')); });
  $$('[data-view="notifications"]').forEach(function(x){ x.classList.toggle('hidden', !featureEnabled('learning_nudges')); });
  $$('[data-view="assistant"]').forEach(function(x){ x.classList.toggle('hidden', !featureEnabled('ai_assistant')); });
  const pill=$('#xpPill'); if (pill) pill.classList.toggle('hidden', !featureEnabled('xp_economy'));
}

function chineseStandardBannerHTML() {
  return '<section class="putonghua-learning-banner"><div class="putonghua-learning-icon">普</div><div><b>Вы изучаете Путунхуа (普通话)</b><span>Стандартный китайский для школы, работы и общения между регионами Китая.</span></div><small>Диалекты в разделе «Информация о китайском» — только справка, их не нужно учить.</small></section>';
}

function ensureChineseStandardBanner() {
  if (state.language !== 'chinese') return;
  const learningViews = new Set(['home','topics','quiz','roleplay','course30','exam','games']);
  if (!learningViews.has(state.view) || $('#main .putonghua-learning-banner')) return;
  const main=$('#main');
  if (main) main.insertAdjacentHTML('afterbegin', chineseStandardBannerHTML());
}

function updateLearningControls() {
  const chinese = state.language === 'chinese';
  const basics = $('#chineseBasicsNav');
  if (basics) basics.classList.toggle('hidden', !chinese || !featureEnabled('chinese_reference'));
  const toggle = $('#pinyinToggle');
  if (toggle) {
    toggle.classList.toggle('hidden', !chinese);
    toggle.textContent = '拼 Pinyin: ' + (state.learningPrefs.show_pinyin ? 'вкл' : 'выкл');
    toggle.classList.toggle('off', !state.learningPrefs.show_pinyin);
  }
  document.body.classList.toggle('pinyin-off', chinese && !state.learningPrefs.show_pinyin);
  document.body.classList.toggle('reading-off', !state.learningPrefs.show_reading);
  applyFeatureVisibility();
}


async function saveLearningPrefs(next) {
  state.learningPrefs = Object.assign({}, state.learningPrefs, next || {});
  state.learningPrefs = await api('/api/learning/preferences', {method:'PUT', body:JSON.stringify(state.learningPrefs)});
  updateLearningControls();
  return state.learningPrefs;
}

async function togglePinyin() {
  try {
    await saveLearningPrefs({show_pinyin: !state.learningPrefs.show_pinyin});
    toast(state.learningPrefs.show_pinyin ? 'Pinyin включён' : 'Pinyin скрыт');
    await renderView();
  } catch (error) { toast(error.message); }
}

async function refreshGamification() {
  state.gamification = await api('/api/gamification/me');
  const xpPill = $('#xpPill');
  if (xpPill) xpPill.textContent = state.gamification.spendable_xp + ' XP';
  return state.gamification;
}

function maybeBrowserNudge() {
  if (!state.nudges.length || !state.notificationSettings || !state.notificationSettings.browser_enabled) return;
  if (!('Notification' in window) || Notification.permission !== 'granted') return;
  const item = state.nudges[0];
  try { new Notification(item.title, {body: item.body, tag: 'mgc-learning-nudge'}); } catch (_) {}
}

async function setView(view) {
  state.view = view;
  closeMenu();
  $$('[data-view]').forEach(function (button) {
    button.classList.toggle('active', button.dataset.view === view);
  });
  $('#main').innerHTML = '<div class="loading-card"><span class="spinner"></span><p>Загрузка</p></div>';
  try {
    await renderView();
  } catch (error) {
    $('#main').innerHTML = '<div class="empty"><h2>Не удалось открыть раздел</h2><p>' + esc(error.message) + '</p><button class="primary" data-go="home">На главную</button></div>';
  }
}

async function renderView() {
  const renderers = {
    home: renderHome,
    topics: renderTopics,
    quiz: renderQuiz,
    roleplay: renderRoleplay,
    course30: renderCourse30,
    exam: renderExam,
    assistant: renderAssistant,
    knowledge: renderKnowledge,
    games: renderGames,
    xp: renderXP,
    notifications: renderNotifications,
    'chinese-basics': renderChineseBasics,
    manager: renderManager,
    admin: renderAdmin
  };
  const featureByView = {games:'games',xp:'xp_economy',notifications:'learning_nudges',assistant:'ai_assistant','chinese-basics':'chinese_reference'};
  if (featureByView[state.view] && !featureEnabled(featureByView[state.view])) throw new Error('Эта функция пока не включена для вашей волны пилота');
  await (renderers[state.view] || renderHome)();
  ensureChineseStandardBanner();
}

function pageHead(kicker, title, subtitle) {
  return '<div class="page-head"><div><div class="kicker">' + esc(kicker) + '</div><h1>' + esc(title) + '</h1><p>' + esc(subtitle) + '</p></div></div>';
}

function levelChips(active) {
  return ['A1','A2','B1','B2','C1'].map(function (level) {
    return '<button class="level-chip ' + (level === active ? 'active' : '') + '" data-level="' + level + '">' + level + '</button>';
  }).join('');
}

function topicCards(limit) {
  const topics = typeof limit === 'number' ? state.topics.slice(0, limit) : state.topics;
  return topics.map(function (topic, index) {
    const examples = (topic.examples || []).map(function (item) { return '<span>' + esc(item) + '</span>'; }).join('');
    return '<button class="topic-card" data-open-topic="' + esc(topic.label) + '">' +
      '<span class="topic-icon">' + String(index + 1).padStart(2, '0') + '</span>' +
      '<h3>' + esc(topic.label) + '</h3><p>' + esc(topic.description) + '</p>' +
      '<div class="topic-examples">' + examples + '</div><small>' + topic.count + ' терминов · открыть →</small></button>';
  }).join('');
}

function bindTopicCards() {
  $$('[data-open-topic]').forEach(function (button) {
    button.addEventListener('click', async function () {
      state.topic = button.dataset.openTopic;
      state.topicDetail = state.topic;
      await setView('topics');
    });
  });
}


function xpPanelHTML() {
  const g = state.gamification || {level:1,title:'Новичок I',lifetime_xp:0,spendable_xp:0,weekly_xp:0,progress_xp:0,level_xp:500};
  const pct = Math.min(100, Math.round((g.progress_xp || 0) * 100 / Math.max(1, g.level_xp || 500)));
  return '<section class="xp-overview card"><div><div class="kicker">УРОВЕНЬ ' + g.level + '</div><h2>' + esc(g.title) + '</h2><p>Lifetime: <b>' + g.lifetime_xp + ' XP</b> · доступно для помощи: <b>' + g.spendable_xp + ' XP</b> · неделя: ' + g.weekly_xp + ' XP</p></div>' +
    '<div class="xp-levelbar"><i style="width:' + pct + '%"></i></div><button class="ghost" data-go="xp">Использовать XP →</button></section>';
}

function nudgeHTML() {
  if (!state.nudges || !state.nudges.length) return '';
  const item = state.nudges[0];
  return '<section class="nudge-card"><div><div class="kicker">НЕНАВЯЗЧИВОЕ НАПОМИНАНИЕ</div><h3>' + esc(item.title) + '</h3><p>' + esc(item.body) + '</p></div>' +
    '<div class="actions"><button class="primary" data-nudge-open="' + item.id + '" data-target="' + esc(item.target_view) + '">Открыть</button><button class="ghost" data-nudge-dismiss="' + item.id + '">Не сейчас</button></div></section>';
}

function pilotCohortHTML() {
  const groups=(state.pilot && state.pilot.groups || []).filter(function(g){return g.active;});
  if (!groups.length) return '';
  const wave=state.pilot.wave == null ? '—' : state.pilot.wave;
  return '<section class="pilot-cohort-strip"><div><b>Пилот · Wave '+esc(wave)+'</b><span>'+groups.map(function(g){return esc(g.name);}).join(' · ')+'</span></div><small>Функции могут включаться поэтапно для вашей группы.</small></section>';
}


async function renderHome() {
  const title = state.language === 'english' ? 'Английский для автопрома' : 'Путунхуа для автопрома';
  const accent = state.language === 'english' ? 'ENGLISH' : '中文';
  const progress = state.summary.progress;
  $('#main').innerHTML =
    '<section class="hero"><div class="kicker">MGC LANGUAGE LAB · ' + esc(targetLabel()) + '</div>' +
      '<h1>' + esc(title) + '<br><span>' + accent + '</span></h1>' +
      '<p>Термины, реальные рабочие ситуации и тренировка коммуникации в Автопромышленности.</p>' +
      '<div class="hero-actions"><button class="primary" data-go="topics">Выбрать тему</button><button class="ghost" data-go="roleplay">Начать сценарий</button></div>' +
    '</section>' +
    pilotCohortHTML() +
    ((state.pilot.assignments||[]).length ? '<section class="card pilot-assignments"><div class="kicker">МОЙ ПИЛОТНЫЙ ТРЕК</div><h3>Назначено вашей группе</h3>'+state.pilot.assignments.map(function(a){return '<div class="pilot-assignment"><b>'+esc(a.track_name)+'</b><span>'+(a.language==='chinese'?'Путунхуа / 中文':'English')+(a.topic?' · '+esc(a.topic):'')+' · цель '+esc(a.target_level)+(a.due_date?' · до '+esc(a.due_date):'')+'</span></div>';}).join('')+'</section>' : '') +
    nudgeHTML() + (featureEnabled('xp_economy') ? xpPanelHTML() : '') +
    '<div class="grid three">' +
      '<button class="card action-card" data-go="topics"><span class="number">01</span><h3>Темы</h3><p>Слова и рабочие фразы по цехам и функциям.</p></button>' +
      '<button class="card action-card" data-go="quiz"><span class="number">02</span><h3>Тест</h3><p>Короткая проверка по выбранной теме и уровню.</p></button>' +
      '<button class="card action-card" data-go="roleplay"><span class="number">03</span><h3>Сценарии</h3><p>Мини-игра с решениями для реальных рабочих разговоров.</p></button>' +
    '</div>' +
    '<div class="section-title"><h2>Уровень обучения</h2></div>' +
    '<div class="card"><div class="level-strip">' + levelChips(state.level) + '</div><p class="muted" id="levelDescription">' + esc(state.summary.level_labels[state.level]) + '</p></div>' +
    '<div class="section-title"><h2>Профессиональные темы</h2><button class="ghost" data-go="topics">Все ' + state.topics.length + '</button></div>' +
    '<div class="topic-grid">' + topicCards(9) + '</div>' +
    '<div class="section-title"><h2>Ваш прогресс</h2></div>' +
    '<div class="progress-dashboard">' +
      '<button class="progress-tile" data-go="topics"><b>' + progress.percent + '%</b><span>терминов изучено</span></button>' +
      '<button class="progress-tile" data-go="course30"><b>' + progress.completed_days + '/30</b><span>дней курса завершено</span></button>' +
      '<button class="progress-tile" data-go="exam"><b>' + progress.best_exam + '/50</b><span>' + (progress.exam_passed ? 'экзамен сдан' : 'лучший результат') + '</span></button>' +
    '</div>';
  bindLevelSelection(false);
  bindTopicCards();
  $$('[data-nudge-open]').forEach(function (button) { button.addEventListener('click', async function () { await api('/api/notifications/' + button.dataset.nudgeOpen + '/read', {method:'POST'}); state.nudges = state.nudges.filter(function (x) { return String(x.id) !== button.dataset.nudgeOpen; }); await setView(button.dataset.target || 'home'); }); });
  $$('[data-nudge-dismiss]').forEach(function (button) { button.addEventListener('click', async function () { await api('/api/notifications/' + button.dataset.nudgeDismiss + '/read', {method:'POST'}); state.nudges = state.nudges.filter(function (x) { return String(x.id) !== button.dataset.nudgeDismiss; }); renderHome(); }); });
}

function bindLevelSelection(rerender) {
  $$('[data-level]', $('#main')).forEach(function (button) {
    button.addEventListener('click', async function () {
      state.level = button.dataset.level;
      if (rerender) await renderView();
      else {
        $$('[data-level]', $('#main')).forEach(function (item) { item.classList.toggle('active', item.dataset.level === state.level); });
        const description = $('#levelDescription');
        if (description) description.textContent = state.summary.level_labels[state.level];
      }
    });
  });
}

function topicOptions(selected) {
  return state.topics.map(function (topic) {
    return '<option value="' + esc(topic.label) + '" ' + (topic.label === selected ? 'selected' : '') + '>' + esc(topic.label) + '</option>';
  }).join('');
}

function termCard(item) {
  const lang = item.language || state.language;
  const pronunciationClass = lang === 'chinese' ? 'pinyin' : 'ipa-line';
  const examplePronClass = lang === 'chinese' ? 'pinyin-line' : 'ipa-line';
  return '<article class="term-card"><div class="meta">' + esc(item.level + ' · ' + item.topic + (item.shop ? ' · ' + item.shop : '')) + '</div>' +
    '<div class="target">' + esc(item.term) + '</div>' +
    (item.pronunciation ? '<div class="' + pronunciationClass + '">' + esc(item.pronunciation) + '</div>' : '') +
    (item.reading ? '<div class="reading-line">≈ ' + esc(item.reading) + ' <small>как читать</small></div>' : '') +
    '<div class="pronunciation-actions"><button class="listen-button" data-speak-text="' + esc(item.term) + '" data-speak-language="' + lang + '" data-speak-rate="0.9">▶ Послушать</button><button class="listen-button subtle" data-speak-text="' + esc(item.term) + '" data-speak-language="' + lang + '" data-speak-rate="0.68">0.7×</button></div>' +
    '<div class="translation">' + esc(item.translation) + '</div>' +
    (item.example && item.example !== item.term ? '<div class="term-example"><div class="example-head"><span>' + esc(item.example) + '</span><button class="mini-listen" data-speak-text="' + esc(item.example) + '" data-speak-language="' + lang + '" data-speak-rate="0.86">▶</button></div>' +
      (item.example_pronunciation ? '<div class="' + examplePronClass + '">' + esc(item.example_pronunciation) + '</div>' : '') +
      '<span>' + esc(item.example_translation) + '</span></div>' : '') + '</article>';
}

async function renderTopics() {
  if (!state.topicDetail) {
    $('#main').innerHTML = pageHead('Отраслевой словарь', 'Темы', 'Выберите конкретный процесс или функцию — слова не смешиваются в одну длинную ленту.') +
      '<div class="topic-grid">' + topicCards() + '</div>';
    bindTopicCards();
    return;
  }
  state.topic = state.topicDetail;
  const result = await api('/api/language/' + state.language + '/terms?topic=' + encodeURIComponent(state.topicDetail) + '&limit=500');
  $('#main').innerHTML =
    '<div class="topic-detail-head"><button id="allTopics" class="ghost">← Все темы</button><div><div class="kicker">Словарь темы</div><h1>' + esc(state.topicDetail) + '</h1><p>' + result.total + ' терминов по уровням A1–C1.</p></div></div>' +
    '<div class="topic-actions"><button class="primary" data-go="quiz" data-topic="' + esc(state.topicDetail) + '">Пройти тест</button><button class="secondary" data-go="roleplay" data-topic="' + esc(state.topicDetail) + '">Открыть сценарии</button></div>' +
    '<div class="filter-bar"><div class="level-strip"><button class="level-chip active" data-topic-level="ALL">Все</button>' +
      ['A1','A2','B1','B2','C1'].map(function (level) { return '<button class="level-chip" data-topic-level="' + level + '">' + level + '</button>'; }).join('') +
    '</div></div><div id="topicTerms" class="term-list">' + result.items.map(termCard).join('') + '</div>';
  $('#allTopics').addEventListener('click', function () { state.topicDetail = null; renderTopics(); });
  $$('[data-topic-level]').forEach(function (button) {
    button.addEventListener('click', function () {
      $$('[data-topic-level]').forEach(function (item) { item.classList.toggle('active', item === button); });
      const level = button.dataset.topicLevel;
      const filtered = level === 'ALL' ? result.items : result.items.filter(function (item) { return item.level === level; });
      $('#topicTerms').innerHTML = filtered.length ? filtered.map(termCard).join('') : '<div class="empty">На этом уровне пока нет терминов.</div>';
    });
  });
}


function newSessionId(prefix) {
  if (window.crypto && crypto.randomUUID) return prefix + '-' + crypto.randomUUID();
  return prefix + '-' + Date.now() + '-' + Math.random().toString(36).slice(2);
}

async function submitPractice(kind, sessionId, score, total, topic) {
  if (!sessionId) return null;
  try {
    const result = await api('/api/practice/result', {method:'POST', body: JSON.stringify({session_id:sessionId, kind:kind, language:state.language, topic:topic || '', score:score, total:total})});
    if (result.profile) {
      state.gamification = result.profile;
      const pill = $('#xpPill'); if (pill) pill.textContent = state.gamification.spendable_xp + ' XP';
    }
    if (result.awarded) toast('+' + result.awarded + ' XP');
    return result;
  } catch (_) { return null; }
}

async function buyQuizHelp(rewardId, question) {
  try {
    const result = await api('/api/gamification/spend', {method:'POST', body:JSON.stringify({reward_id:rewardId, language:state.language, context:{term_id:question.id, options:question.options}})});
    state.gamification = result.profile;
    const pill = $('#xpPill'); if (pill) pill.textContent = state.gamification.spendable_xp + ' XP';
    const box = $('#quizHintBox');
    const value = result.result || {};
    if (value.type === 'eliminate') {
      $$('[data-answer]').forEach(function (button) { if (button.textContent === value.option) { button.disabled = true; button.classList.add('eliminated'); } });
      if (box) box.innerHTML = '<div class="hint-result">Один неверный вариант убран · −' + result.spent + ' XP</div>';
    } else if (value.type === 'audio') {
      speakText(value.text, value.rate || .7);
      if (box) box.innerHTML = '<div class="hint-result">Фраза произнесена медленнее · −' + result.spent + ' XP</div>';
    } else {
      const text = value.text || value.target || 'Подсказка активирована';
      if (box) box.innerHTML = '<div class="hint-result">' + esc(text) + ' · −' + result.spent + ' XP</div>';
    }
  } catch (error) { toast(error.message); }
}

function browserSpeak(text, rate, language) {
  if (!('speechSynthesis' in window)) throw new Error('В браузере нет SpeechSynthesis');
  speechSynthesis.cancel();
  const utter = new SpeechSynthesisUtterance(text);
  const langTag = language === 'chinese' ? 'zh-CN' : 'en-US';
  utter.lang = langTag;
  utter.rate = rate || .9;
  const voices = speechSynthesis.getVoices ? speechSynthesis.getVoices() : [];
  const exact = voices.find(function (voice) { return String(voice.lang || '').toLowerCase() === langTag.toLowerCase(); });
  const family = voices.find(function (voice) { return String(voice.lang || '').toLowerCase().startsWith(language === 'chinese' ? 'zh' : 'en'); });
  if (exact || family) utter.voice = exact || family;
  speechSynthesis.speak(utter);
}

async function playPronunciation(text, rate, language) {
  const lang = language || state.language;
  const speed = rate || .9;
  if (!text) return;
  if (state.activeAudio) { try { state.activeAudio.pause(); } catch (_) {} state.activeAudio = null; }
  if (state.activeAudioUrl) { try { URL.revokeObjectURL(state.activeAudioUrl); } catch (_) {} state.activeAudioUrl = null; }
  if (state.activeAudioController) { try { state.activeAudioController.abort(); } catch (_) {} state.activeAudioController = null; }
  const serverAllowed = featureEnabled('server_audio') && (!state.learningPrefs || state.learningPrefs.server_audio_enabled !== false);
  if (serverAllowed && (!state.pronunciationStatus || state.pronunciationStatus.server_available !== false)) {
    const controller = new AbortController();
    state.activeAudioController = controller;
    const timer = setTimeout(function () { controller.abort(); }, 6000);
    try {
      const csrf = cookieValue('mgc_csrf');
      const headers = {'Content-Type':'application/json'};
      if (csrf) headers['X-CSRF-Token'] = csrf;
      const response = await fetch('/api/pronunciation/audio', {method:'POST', credentials:'same-origin', headers:headers, body:JSON.stringify({language:lang, rate:speed, text:text}), signal:controller.signal});
      if (response.ok) {
        const blob = await response.blob();
        if (!String(blob.type || '').startsWith('audio/')) throw new Error('invalid audio response');
        const url = URL.createObjectURL(blob);
        const audio = new Audio(url);
        audio.preload = 'auto';
        state.activeAudio = audio; state.activeAudioUrl = url;
        const cleanup = function () {
          if (state.activeAudioUrl === url) { URL.revokeObjectURL(url); state.activeAudioUrl = null; state.activeAudio = null; }
        };
        audio.addEventListener('ended', cleanup, {once:true});
        audio.addEventListener('error', cleanup, {once:true});
        await audio.play();
        return;
      }
    } catch (_) {
      // The local server voice is optional at runtime; browser speech is the deliberate fallback.
    } finally {
      clearTimeout(timer);
      if (state.activeAudioController === controller) state.activeAudioController = null;
    }
  }
  try {
    browserSpeak(text, speed, lang);
    toast('Серверный голос недоступен — использован голос браузера');
  } catch (_) {
    toast('Не удалось воспроизвести звук. IT может проверить /api/pronunciation/status');
  }
}

function speakText(text, rate) { return playPronunciation(text, rate, state.language); }

async function renderQuiz() {
  if (!state.quiz) {
    $('#main').innerHTML = pageHead('Проверка знаний', 'Тест по теме', 'До 10 вопросов. Pinyin можно включать и выключать; произношение доступно отдельной кнопкой.') +
      '<div class="card quiz-setup"><label>Тема<select id="quizTopic">' + topicOptions(state.topic) + '</select></label>' +
      '<div><div class="field-label">Уровень</div><div class="level-strip">' + levelChips(state.level) + '</div></div>' +
      '<button id="startQuiz" class="primary">Начать тест</button></div>';
    $('#quizTopic').addEventListener('change', function (event) { state.topic = event.target.value; });
    bindLevelSelection(false);
    $('#startQuiz').addEventListener('click', startQuiz);
    return;
  }
  if (state.quizIndex >= state.quiz.length) {
    if (state.practiceSessionId) { await submitPractice('quiz', state.practiceSessionId, state.quizScore, state.quiz.length, state.topic); state.practiceSessionId = null; }
    $('#main').innerHTML = pageHead('Тест завершён', 'Результат', 'Вы можете повторить тему или перейти к рабочим сценариям.') +
      '<div class="card exam-intro"><div class="result-score">' + state.quizScore + '/' + state.quiz.length + '</div><p>Правильных ответов</p>' +
      '<div class="actions centered"><button id="retryQuiz" class="primary">Пройти ещё раз</button><button data-go="roleplay" data-topic="' + esc(state.topic) + '" class="secondary">Сценарии по теме</button></div></div>';
    $('#retryQuiz').addEventListener('click', function () { state.quiz = null; state.quizIndex = 0; state.quizScore = 0; renderQuiz(); });
    return;
  }
  const question = state.quiz[state.quizIndex];
  $('#main').innerHTML = '<div class="quiz-stage"><div class="quiz-progress"><i style="width:' + (((state.quizIndex + 1) / state.quiz.length) * 100) + '%"></i></div>' +
    '<div class="card question-card"><div class="kicker">' + esc(question.level + ' · ' + question.topic + ' · ' + (state.quizIndex + 1) + '/' + state.quiz.length) + '</div>' +
    '<h2>' + esc(question.prompt) + '</h2>' + (question.pronunciation ? '<div class="' + (state.language === 'chinese' ? 'question-pinyin' : 'ipa-line') + '">' + esc(question.pronunciation) + '</div>' : '') +
    (question.reading ? '<div class="reading-line">≈ ' + esc(question.reading) + ' <small>как читать</small></div>' : '') +
    (question.audio_text ? '<div class="pronunciation-actions"><button class="listen-button" data-speak-text="' + esc(question.audio_text) + '" data-speak-language="' + state.language + '" data-speak-rate="0.88">▶ Послушать</button><button class="listen-button subtle" data-speak-text="' + esc(question.audio_text) + '" data-speak-language="' + state.language + '" data-speak-rate="0.65">медленно</button></div>' : '') +
    '<div class="options">' + question.options.map(function (option, index) { return '<button class="option" data-answer="' + index + '">' + esc(option) + '</button>'; }).join('') +
    '</div><div class="quiz-help"><button class="micro-action" data-buy-hint="hint_small">Подсказка · 10 XP</button><button class="micro-action" data-buy-hint="eliminate_option">Убрать вариант · 20 XP</button>' + (state.language === 'chinese' ? '<button class="micro-action" data-buy-hint="show_pinyin">Pinyin · 10 XP</button>' : '') + '</div><div id="quizHintBox"></div><div id="quizNextWrap"></div></div></div>';
  $$('[data-answer]').forEach(function (button) {
    button.addEventListener('click', function () { answerQuiz(Number(button.dataset.answer)); });
  });
  $$('[data-buy-hint]').forEach(function (button) { button.addEventListener('click', function () { buyQuizHelp(button.dataset.buyHint, question); }); });
}

async function startQuiz() {
  const data = await api('/api/language/' + state.language + '/quiz?topic=' + encodeURIComponent(state.topic) + '&level=' + state.level + '&count=10');
  state.quiz = data.questions;
  state.practiceSessionId = newSessionId('quiz');
  state.quizIndex = 0;
  state.quizScore = 0;
  state.quizAnswered = false;
  renderQuiz();
}

function answerQuiz(index) {
  if (state.quizAnswered) return;
  state.quizAnswered = true;
  const question = state.quiz[state.quizIndex];
  if (index === question.correct_index) state.quizScore += 1;
  $$('[data-answer]').forEach(function (button) {
    const value = Number(button.dataset.answer);
    if (value === question.correct_index) button.classList.add('correct');
    else if (value === index) button.classList.add('wrong');
    button.disabled = true;
  });
  $('#quizNextWrap').innerHTML = '<div class="answer-feedback"><b>' +
    (index === question.correct_index ? 'Верно' : 'Правильный ответ: ' + esc(question.options[question.correct_index])) +
    '</b><p>' + esc(question.explanation || '') + '</p></div><button id="quizNext" class="primary wide">' +
    (state.quizIndex === state.quiz.length - 1 ? 'Показать результат' : 'Следующий вопрос') + '</button>';
  $('#quizNext').addEventListener('click', function () {
    state.quizIndex += 1;
    state.quizAnswered = false;
    renderQuiz();
  });
}

function scenarioProgressKey() {
  return 'mgc-scenarios-' + (state.user ? state.user.id : 'guest') + '-' + state.language;
}

function getScenarioProgress() {
  try { return JSON.parse(localStorage.getItem(scenarioProgressKey()) || '{}'); } catch (_) { return {}; }
}

function saveScenarioProgress(id, correct) {
  const progress = getScenarioProgress();
  const current = progress[id] || {attempts: 0, correct: 0};
  current.attempts += 1;
  if (correct) current.correct += 1;
  progress[id] = current;
  localStorage.setItem(scenarioProgressKey(), JSON.stringify(progress));
}

async function renderRoleplay() {
  if (!state.scenarioItems.length) state.scenarioItems = await api('/api/language/' + state.language + '/roleplays');
  const availableTopics = ['Все'].concat(Array.from(new Set(state.scenarioItems.map(function (item) { return item.topic; }))));
  if (!availableTopics.includes(state.scenarioTopic)) state.scenarioTopic = 'Все';
  const filtered = state.scenarioTopic === 'Все' ? state.scenarioItems : state.scenarioItems.filter(function (item) { return item.topic === state.scenarioTopic; });
  if (state.scenarioIndex >= filtered.length) state.scenarioIndex = 0;
  const item = filtered[state.scenarioIndex];
  const completed = Object.keys(getScenarioProgress()).length;
  if (!item) {
    $('#main').innerHTML = pageHead('Практика', 'Сценарии', 'Для выбранной темы сценариев пока нет.') + '<button class="ghost" data-go="topics">Выбрать другую тему</button>';
    return;
  }
  $('#main').innerHTML = pageHead('Коммуникационный тренажёр', 'Рабочие сценарии', 'Ситуации, MGC-сценарии и Role Play объединены в одну мини-игру.') +
    '<div class="scenario-toolbar"><div class="chip-row">' + availableTopics.map(function (topic) {
      return '<button class="topic-chip ' + (topic === state.scenarioTopic ? 'active' : '') + '" data-scenario-topic="' + esc(topic) + '">' + esc(topic) + '</button>';
    }).join('') + '</div><div class="scenario-stats"><b>' + state.scenarioScore + ' XP</b><span>' + completed + ' сценариев попробовано</span></div></div>' +
    '<div class="scenario-stage"><div class="quiz-progress"><i style="width:' + (((state.scenarioIndex + 1) / filtered.length) * 100) + '%"></i></div>' +
      '<div class="scenario-meta"><span>' + (state.scenarioIndex + 1) + ' / ' + filtered.length + '</span><span>' + esc(item.topic) + '</span></div>' +
      '<div class="card scenario-question"><div class="kicker">' + esc(item.title) + '</div><h2>' + esc(item.question) + '</h2>' +
        (item.question_pronunciation ? '<div class="' + (state.language === 'chinese' ? 'question-pinyin' : 'ipa-line') + '">' + esc(item.question_pronunciation) + '</div>' : '') +
        (item.question_reading ? '<div class="reading-line">≈ ' + esc(item.question_reading) + '</div>' : '') +
        '<div class="pronunciation-actions"><button class="listen-button" data-speak-text="' + esc(item.question) + '" data-speak-language="' + state.language + '">▶ Вопрос</button></div>' +
        '<p class="scenario-translation">' + esc(item.question_translation) + '</p>' +
        '<div class="roles">' + item.roles.map(function (role) { return '<span>' + esc(role) + '</span>'; }).join('') + '</div>' +
        '<div class="scenario-options">' + item.options.map(function (option, index) {
          return '<div class="scenario-option-wrap"><button class="scenario-option" data-scenario-answer="' + index + '"><b>' + esc(option.text) + '</b>' +
            (option.pronunciation ? '<span class="' + (state.language === 'chinese' ? 'pinyin-line' : 'ipa-line') + '">' + esc(option.pronunciation) + '</span>' : '') +
            (option.reading ? '<span class="reading-line">≈ ' + esc(option.reading) + '</span>' : '') +
            '<span class="answer-translation hidden">' + esc(option.translation) + '</span></button><button class="mini-listen scenario-listen" data-speak-text="' + esc(option.text) + '" data-speak-language="' + state.language + '">▶</button></div>';
        }).join('') + '</div><div id="scenarioFeedback"></div></div></div>';
  $$('[data-scenario-topic]').forEach(function (button) {
    button.addEventListener('click', function () {
      state.scenarioTopic = button.dataset.scenarioTopic;
      state.scenarioIndex = 0;
      state.scenarioScore = 0;
      state.scenarioAnswered = false;
      renderRoleplay();
    });
  });
  $$('[data-scenario-answer]').forEach(function (button) {
    button.addEventListener('click', function () { answerScenario(item, Number(button.dataset.scenarioAnswer), filtered.length); });
  });
}

async function answerScenario(item, selectedIndex, total) {
  if (state.scenarioAnswered) return;
  state.scenarioAnswered = true;
  const correct = item.options[selectedIndex].correct;
  saveScenarioProgress(item.id, correct);
  $$('[data-scenario-answer]').forEach(function (button) {
    const index = Number(button.dataset.scenarioAnswer);
    button.disabled = true;
    button.classList.toggle('correct', item.options[index].correct);
    button.classList.toggle('wrong', index === selectedIndex && !item.options[index].correct);
    const translation = $('.answer-translation', button);
    if (translation) translation.classList.remove('hidden');
  });
  const practice = await submitPractice('scenario', newSessionId('scenario-' + item.id), correct ? 1 : 0, 1, item.topic);
  const earned = practice && practice.awarded ? practice.awarded : 0;
  if (earned) state.scenarioScore += earned;
  $('#scenarioFeedback').innerHTML = '<div class="answer-feedback"><b>' + (correct ? ('+' + earned + ' XP · точный ответ') : (earned ? ('+' + earned + ' XP за попытку') : 'Посмотрите профессиональную формулировку')) + '</b>' +
    '<p><strong>Цель:</strong> ' + esc(item.goal) + '</p><ol class="checklist">' + item.prompts.map(function (prompt) { return '<li>' + esc(prompt) + '</li>'; }).join('') + '</ol></div>' +
    '<button id="nextScenario" class="primary wide">' + (state.scenarioIndex + 1 >= total ? 'Начать круг заново' : 'Следующая ситуация') + '</button>';
  $('#nextScenario').addEventListener('click', function () {
    state.scenarioIndex = (state.scenarioIndex + 1) % total;
    state.scenarioAnswered = false;
    renderRoleplay();
  });
}

function makePairOptions(day, termIndex) {
  const correct = day.terms[termIndex];
  const others = day.terms.filter(function (_, index) { return index !== termIndex; }).slice(0, 2);
  const options = [correct].concat(others).map(function (item) { return {translation: item.translation, correct: item.id === correct.id}; });
  return options.sort(function (a, b) { return a.translation.localeCompare(b.translation); });
}

async function renderCourse30() {
  state.courseData = await api('/api/language/' + state.language + '/course30');
  const day = state.courseData.days.find(function (item) { return item.day === state.courseDay; }) || state.courseData.days[0];
  if (state.dayQuiz) {
    renderDayQuiz(day);
    return;
  }
  const pairTerm = day.terms[state.pairIndex % day.terms.length];
  const pairOptions = makePairOptions(day, state.pairIndex % day.terms.length);
  $('#main').innerHTML = pageHead('Учебная программа', '30 дней · ' + (state.language === 'english' ? 'English' : '中文'), 'Каждый день: новые термины, короткая активность, рабочий кейс и обязательный тест.') +
    '<div class="course-overview"><div><b>' + state.courseData.completed_days + ' / 30 дней</b><span>завершено</span></div><div class="course-progress"><i style="width:' + (state.courseData.completed_days / 30 * 100) + '%"></i></div><strong>' + Math.round(state.courseData.completed_days / 30 * 100) + '%</strong></div>' +
    '<div class="day-grid">' + state.courseData.days.map(function (item) {
      return '<button class="day-card ' + (item.day === day.day ? 'active' : '') + ' ' + (item.completed ? 'completed' : '') + '" data-day="' + item.day + '"><b>' + (item.completed ? '✓' : item.day) + '</b><span>' + esc(item.level + ' · ' + item.topic) + '</span></button>';
    }).join('') + '</div>' +
    '<div class="section-title"><h2>' + esc(day.title) + '</h2><span class="day-score">' + (day.completed ? 'Лучший тест: ' + day.best_score + '/5' : 'Зачёт: 4/5') + '</span></div>' +
    '<div class="activity-steps">' + day.activities.map(function (activity, index) { return '<span class="' + (index === 0 || day.completed ? 'done' : '') + '"><b>' + (index + 1) + '</b>' + esc(activity) + '</span>'; }).join('') + '</div>' +
    '<div class="grid two course-content"><section class="card"><div class="kicker">' + esc(day.level + ' · ' + languageName()) + '</div><h3>Термины дня</h3><p>' + esc(day.task) + '</p><div class="term-list compact">' + day.terms.map(termCard).join('') + '</div></section>' +
      '<section class="card pair-game"><div class="kicker">Активность</div><h3>Соберите пару</h3><p>Выберите перевод для термина.</p><div class="pair-target">' + esc(pairTerm.term) + '</div>' +
        (pairTerm.pronunciation ? '<div class="question-pinyin">' + esc(pairTerm.pronunciation) + '</div>' : '') +
        '<div class="options">' + pairOptions.map(function (option, index) { return '<button class="option" data-pair-answer="' + index + '" data-correct="' + option.correct + '">' + esc(option.translation) + '</button>'; }).join('') + '</div><div id="pairFeedback"></div></section></div>' +
    '<div class="course-actions"><button class="secondary" data-go="roleplay" data-topic="' + esc(day.topic) + '">Мини-кейс по теме</button><button id="startDayQuiz" class="primary">Пройти тест дня · 5 вопросов</button></div>';
  $$('[data-day]').forEach(function (button) {
    button.addEventListener('click', function () {
      state.courseDay = Number(button.dataset.day);
      state.pairIndex = 0;
      state.pairAnswered = false;
      state.dayQuiz = null;
      renderCourse30();
    });
  });
  $$('[data-pair-answer]').forEach(function (button) {
    button.addEventListener('click', function () { answerPair(button, day); });
  });
  $('#startDayQuiz').addEventListener('click', function () {
    state.dayQuiz = day.quiz;
    state.dayQuizIndex = 0;
    state.dayQuizScore = 0;
    state.dayQuizAnswered = false;
    renderCourse30();
  });
}

async function answerPair(button, day) {
  if (state.pairAnswered) return;
  state.pairAnswered = true;
  const correct = button.dataset.correct === 'true';
  $$('[data-pair-answer]').forEach(function (item) {
    item.disabled = true;
    if (item.dataset.correct === 'true') item.classList.add('correct');
  });
  if (!correct) button.classList.add('wrong');
  const practice = await submitPractice('pair', newSessionId('pair-' + day.day + '-' + state.pairIndex), correct ? 1 : 0, 1, day.topic);
  const earned = practice && practice.awarded ? practice.awarded : 0;
  $('#pairFeedback').innerHTML = '<div class="answer-feedback"><b>' + (correct ? ('Верно · +' + earned + ' XP') : ('Пара показана выше' + (earned ? ' · +' + earned + ' XP за попытку' : ''))) + '</b></div><button id="nextPair" class="ghost wide">Следующий термин</button>';
  $('#nextPair').addEventListener('click', function () {
    state.pairIndex = (state.pairIndex + 1) % day.terms.length;
    state.pairAnswered = false;
    renderCourse30();
  });
}

function renderDayQuiz(day) {
  if (state.dayQuizIndex >= state.dayQuiz.length) {
    const passed = state.dayQuizScore >= 4;
    $('#main').innerHTML = pageHead('Тест дня завершён', passed ? 'День ' + day.day + ' пройден' : 'Нужно ещё одно повторение', passed ? 'Результат сохранён в вашем прогрессе.' : 'Для зачёта нужно минимум 4 правильных ответа из 5.') +
      '<div class="card exam-intro"><div class="result-score">' + state.dayQuizScore + '/5</div><p>' + (passed ? 'Отлично — следующий день открыт.' : 'Повторите термины и попробуйте снова.') + '</p>' +
      '<button id="finishDayQuiz" class="primary">' + (passed ? 'Вернуться к курсу' : 'Повторить материал') + '</button></div>';
    $('#finishDayQuiz').addEventListener('click', async function () {
      if (passed) {
        await api('/api/course-day/result', {method: 'POST', body: JSON.stringify({language: state.language, day: day.day, score: state.dayQuizScore, total: 5})});
        await submitPractice('course_day', newSessionId('course-' + state.language + '-' + day.day), state.dayQuizScore, 5, day.topic);
        state.summary = await api('/api/language/' + state.language + '/summary');
      }
      state.dayQuiz = null;
      state.dayQuizIndex = 0;
      state.dayQuizScore = 0;
      renderCourse30();
    });
    return;
  }
  const question = state.dayQuiz[state.dayQuizIndex];
  $('#main').innerHTML = '<div class="quiz-stage"><button id="leaveDayQuiz" class="ghost">← К материалу дня</button><div class="quiz-progress"><i style="width:' + ((state.dayQuizIndex + 1) * 20) + '%"></i></div>' +
    '<div class="card question-card"><div class="kicker">День ' + day.day + ' · вопрос ' + (state.dayQuizIndex + 1) + ' из 5</div><h2>' + esc(question.prompt) + '</h2>' +
    (question.pronunciation ? '<div class="question-pinyin">' + esc(question.pronunciation) + '</div>' : '') +
    '<div class="options">' + question.options.map(function (option, index) { return '<button class="option" data-day-answer="' + index + '">' + esc(option) + '</button>'; }).join('') + '</div><div id="dayQuizNext"></div></div></div>';
  $('#leaveDayQuiz').addEventListener('click', function () { state.dayQuiz = null; renderCourse30(); });
  $$('[data-day-answer]').forEach(function (button) {
    button.addEventListener('click', function () { answerDayQuiz(question, Number(button.dataset.dayAnswer)); });
  });
}

function answerDayQuiz(question, index) {
  if (state.dayQuizAnswered) return;
  state.dayQuizAnswered = true;
  if (index === question.correct_index) state.dayQuizScore += 1;
  $$('[data-day-answer]').forEach(function (button) {
    const value = Number(button.dataset.dayAnswer);
    if (value === question.correct_index) button.classList.add('correct');
    else if (value === index) button.classList.add('wrong');
    button.disabled = true;
  });
  $('#dayQuizNext').innerHTML = '<div class="answer-feedback"><b>' + (index === question.correct_index ? 'Верно' : 'Правильный ответ: ' + esc(question.options[question.correct_index])) + '</b><p>' + esc(question.explanation) + '</p></div>' +
    '<button id="nextDayQuestion" class="primary wide">' + (state.dayQuizIndex === 4 ? 'Завершить тест' : 'Следующий вопрос') + '</button>';
  $('#nextDayQuestion').addEventListener('click', function () {
    state.dayQuizIndex += 1;
    state.dayQuizAnswered = false;
    renderCourse30();
  });
}

async function renderExam() {
  if (!state.exam) {
    $('#main').innerHTML = pageHead('Итоговая проверка', 'Финальный экзамен', '50 вопросов от A1 до C1. Экзамен сдан при результате 35/50 или выше.') +
      '<div class="card exam-intro"><h2>Проверка всей программы</h2><div class="exam-levels">' +
      ['A1 · 10','A2 · 10','B1 · 10','B2 · 10','C1 · 10'].map(function (item) { return '<span>' + item + '</span>'; }).join('') +
      '</div><p>Перевод, обратный перевод, рабочий контекст и выбор точной формулировки. Для китайского pinyin отображается в каждом вопросе.</p>' +
      '<div class="pass-rule">Проходной результат <b>35 из 50</b></div><button id="startExam" class="primary">Начать экзамен</button></div>';
    $('#startExam').addEventListener('click', startExam);
    return;
  }
  if (state.examIndex >= state.exam.length) {
    const passed = state.examScore >= 35;
    const percent = Math.round(state.examScore * 2);
    $('#main').innerHTML = pageHead('Экзамен завершён', passed ? 'Экзамен сдан' : 'Экзамен пока не сдан', passed ? 'Вы преодолели порог 35/50.' : 'Повторите слабые темы и попробуйте снова.') +
      '<div class="card exam-intro ' + (passed ? 'exam-pass' : 'exam-retry') + '"><div class="result-score">' + state.examScore + '/50</div><p>' + percent + '% правильных ответов</p>' +
      '<button id="restartExam" class="primary">Пройти заново</button></div>';
    $('#restartExam').addEventListener('click', function () { state.exam = null; state.examIndex = 0; state.examScore = 0; renderExam(); });
    return;
  }
  const question = state.exam[state.examIndex];
  $('#main').innerHTML = '<div class="quiz-stage"><div class="exam-score-live">Правильно: <b>' + state.examScore + '</b></div><div class="quiz-progress"><i style="width:' + ((state.examIndex + 1) * 2) + '%"></i></div>' +
    '<div class="card question-card"><div class="kicker">' + esc(question.level + ' · вопрос ' + (state.examIndex + 1) + ' из 50') + '</div><h2>' + esc(question.prompt) + '</h2>' +
    (question.pronunciation ? '<div class="question-pinyin">' + esc(question.pronunciation) + '</div>' : '') +
    '<div class="options">' + question.options.map(function (option, index) { return '<button class="option" data-exam-answer="' + index + '">' + esc(option) + '</button>'; }).join('') + '</div><div id="examNextWrap"></div></div></div>';
  $$('[data-exam-answer]').forEach(function (button) {
    button.addEventListener('click', function () { answerExam(Number(button.dataset.examAnswer)); });
  });
}

async function startExam() {
  const data = await api('/api/language/' + state.language + '/final-exam');
  state.exam = data.questions;
  state.examIndex = 0;
  state.examScore = 0;
  state.examAnswered = false;
  renderExam();
}

function answerExam(index) {
  if (state.examAnswered) return;
  state.examAnswered = true;
  const question = state.exam[state.examIndex];
  if (index === question.correct_index) state.examScore += 1;
  $$('[data-exam-answer]').forEach(function (button) {
    const value = Number(button.dataset.examAnswer);
    if (value === question.correct_index) button.classList.add('correct');
    else if (value === index) button.classList.add('wrong');
    button.disabled = true;
  });
  $('#examNextWrap').innerHTML = '<div class="answer-feedback"><b>' + (index === question.correct_index ? 'Верно' : 'Правильный ответ: ' + esc(question.options[question.correct_index])) + '</b><p>' + esc(question.explanation || '') + '</p></div>' +
    '<button id="examNext" class="primary wide">' + (state.examIndex === 49 ? 'Завершить экзамен' : 'Следующий вопрос') + '</button>';
  $('#examNext').addEventListener('click', async function () {
    state.examIndex += 1;
    state.examAnswered = false;
    if (state.examIndex === 50) {
      try {
        await api('/api/final-exam/result', {method: 'POST', body: JSON.stringify({language: state.language, score: state.examScore, total: 50, answers: []})});
        await submitPractice('exam', newSessionId('exam-' + state.language), state.examScore, 50, 'Final Exam');
        state.summary = await api('/api/language/' + state.language + '/summary');
      } catch (_) {}
    }
    renderExam();
  });
}

function renderAssistant() {
  const examples = state.language === 'english'
    ? ['How do I discuss a welding defect?', 'Phrase for escalating an SOP risk', 'How do I request a cost breakdown?']
    : ['如何讨论焊接缺陷？', '如何升级量产风险？', '如何要求提供成本明细？'];
  $('#main').innerHTML = pageHead('Помощник по базе', 'ИИ-помощник', 'Находит подходящие термины и проверенные рабочие формулировки на выбранном языке.') +
    '<div class="tool-layout"><div class="card"><label>Вопрос<textarea id="assistantQuestion" placeholder="Опишите рабочую ситуацию"></textarea></label>' +
      '<div class="chip-row examples-row">' + examples.map(function (item) { return '<button class="topic-chip" data-ai-example="' + esc(item) + '">' + esc(item) + '</button>'; }).join('') + '</div>' +
      '<button id="askAssistant" class="primary wide">Найти формулировку</button></div>' +
      '<div id="assistantResult" class="answer-box"><b>Как пользоваться</b><p>Опишите задачу своими словами: дефект, переговоры, запуск, финансы или производство.</p></div></div>';
  $$('[data-ai-example]').forEach(function (button) { button.addEventListener('click', function () { $('#assistantQuestion').value = button.dataset.aiExample; }); });
  $('#askAssistant').addEventListener('click', askAssistant);
}

async function askAssistant() {
  const question = $('#assistantQuestion').value.trim();
  if (!question) { toast('Введите вопрос'); return; }
  const resultBox = $('#assistantResult');
  resultBox.innerHTML = '<span class="spinner"></span>';
  try {
    const data = await api('/api/assistant', {method: 'POST', body: JSON.stringify({language: state.language, question: question})});
    resultBox.innerHTML = '<b>' + esc(data.answer) + '</b><div class="result-list">' + data.evidence.map(termCard).join('') + '</div><p class="muted">' + esc(data.note) + '</p>';
  } catch (error) {
    resultBox.innerHTML = '<b>Ошибка</b><p>' + esc(error.message) + '</p>';
  }
}

async function renderKnowledge() {
  if (!state.knowledgeItems.length) state.knowledgeItems = await api('/api/knowledge?language=' + state.language);
  if (state.knowledgeId) {
    const item = state.knowledgeItems.find(function (row) { return row.id === state.knowledgeId; });
    if (item) {
      $('#main').innerHTML = '<button id="backKnowledge" class="ghost">← База знаний</button>' + pageHead(item.topic, item.title, item.situation) +
        '<div class="knowledge-detail"><section class="card"><div class="kicker">Что делать</div><ol class="knowledge-steps">' + item.steps.map(function (step) { return '<li>' + esc(step) + '</li>'; }).join('') + '</ol>' +
          '<div class="avoid-box"><b>Не делайте так</b><p>' + esc(item.avoid) + '</p></div></section>' +
          '<section class="card phrase-panel"><div class="kicker">Рабочая формулировка</div><div class="target-line">' + esc(item.target) + '</div>' +
            (item.pronunciation ? '<div class="pinyin-line">' + esc(item.pronunciation) + '</div>' : '') + '<div class="translation-line">' + esc(item.translation) + '</div>' +
            '<div class="pronunciation-actions"><button class="listen-button" data-speak-text="' + esc(item.target) + '" data-speak-language="' + state.language + '">▶ Послушать</button></div>' +
            '<button class="primary wide" data-go="roleplay" data-topic="' + esc(item.topic) + '">Отработать похожий сценарий</button></section></div>';
      $('#backKnowledge').addEventListener('click', function () { state.knowledgeId = null; renderKnowledge(); });
      return;
    }
  }
  const topics = ['Все'].concat(Array.from(new Set(state.knowledgeItems.map(function (item) { return item.topic; }))));
  const filtered = state.knowledgeTopic === 'Все' ? state.knowledgeItems : state.knowledgeItems.filter(function (item) { return item.topic === state.knowledgeTopic; });
  $('#main').innerHTML = pageHead('Практические инструкции', 'База знаний', 'Реальные рабочие ситуации: что проверить, чего избегать и какую фразу использовать.') +
    '<div class="chip-row knowledge-filter">' + topics.map(function (topic) { return '<button class="topic-chip ' + (topic === state.knowledgeTopic ? 'active' : '') + '" data-knowledge-topic="' + esc(topic) + '">' + esc(topic) + '</button>'; }).join('') + '</div>' +
    '<div class="knowledge-grid">' + filtered.map(function (item, index) {
      return '<button class="knowledge-card" data-knowledge="' + esc(item.id) + '"><div class="kicker">Ситуация ' + String(index + 1).padStart(2, '0') + ' · ' + esc(item.topic) + '</div><h3>' + esc(item.title) + '</h3><p>' + esc(item.situation) + '</p><span>Открыть инструкцию →</span></button>';
    }).join('') + '</div>';
  $$('[data-knowledge-topic]').forEach(function (button) { button.addEventListener('click', function () { state.knowledgeTopic = button.dataset.knowledgeTopic; renderKnowledge(); }); });
  $$('[data-knowledge]').forEach(function (button) { button.addEventListener('click', function () { state.knowledgeId = button.dataset.knowledge; renderKnowledge(); }); });
}




function toneLabStart(data) {
  const rounds = data.tones.filter(function(t){ return t.number >= 1 && t.number <= 4; });
  const deck = rounds.concat(rounds).sort(function(){ return Math.random() - 0.5; }).slice(0, 5);
  state.toneLab = {deck:deck, index:0, score:0, answered:false, sessionId:'tone-lab-'+Date.now()+'-'+Math.random().toString(36).slice(2,8)};
  renderToneLabRound();
}

function renderToneLabRound() {
  const box = $('#toneLabBody');
  if (!box || !state.toneLab) return;
  const lab = state.toneLab;
  if (lab.index >= lab.deck.length) {
    box.innerHTML = '<div class="tone-lab-finish"><b>'+lab.score+' / '+lab.deck.length+'</b><p>Готово. Здесь цель — начать слышать направление тона, а не получить идеальный результат.</p><button id="toneLabAgain" class="secondary">Ещё 5 звуков</button></div>';
    api('/api/practice/result',{method:'POST',body:JSON.stringify({session_id:lab.sessionId,kind:'tone_lab',language:'chinese',topic:'Pinyin · тоны',score:lab.score,total:lab.deck.length})}).then(function(result){
      if(result && result.awarded) toast('Tone Lab: +'+result.awarded+' XP');
      refreshGamification();
    }).catch(function(){});
    $('#toneLabAgain').addEventListener('click', function(){ toneLabStart(state.chineseFoundations); });
    return;
  }
  const tone = lab.deck[lab.index];
  box.innerHTML = '<div class="tone-lab-question"><div class="kicker">ЗВУК '+(lab.index+1)+' / '+lab.deck.length+'</div><h3>Как движется голос?</h3><button id="toneLabPlay" class="audio-button">▶ Послушать слог</button><div class="tone-choice-grid">'+[1,2,3,4].map(function(n){const t=state.chineseFoundations.tones.find(function(x){return x.number===n;});return '<button class="tone-choice" data-tone-choice="'+n+'"><b>'+n+'</b><span>'+esc(t.gesture)+'</span></button>';}).join('')+'</div><div id="toneLabFeedback"></div></div>';
  $('#toneLabPlay').addEventListener('click', function(){ speakText(tone.hanzi,'chinese',0.7,this); });
  $$('[data-tone-choice]').forEach(function(button){button.addEventListener('click',function(){
    if(lab.answered) return;
    lab.answered=true;
    const picked=Number(button.dataset.toneChoice);
    const ok=picked===tone.number;
    if(ok) lab.score += 1;
    $$('[data-tone-choice]').forEach(function(b){b.disabled=true;if(Number(b.dataset.toneChoice)===tone.number)b.classList.add('correct');else if(b===button&&!ok)b.classList.add('wrong');});
    $('#toneLabFeedback').innerHTML='<div class="tone-lab-feedback '+(ok?'ok':'no')+'"><b>'+(ok?'Верно':'Почти')+': '+tone.number+'-й тон — '+esc(tone.gesture)+'</b><p>'+esc(tone.hanzi)+' · <span class="pinyin-line">'+esc(tone.pinyin)+'</span> · '+esc(tone.ru)+'. '+esc(tone.hint)+'</p><button id="toneLabNext" class="primary">Дальше</button></div>';
    $('#toneLabNext').addEventListener('click',function(){lab.index+=1;lab.answered=false;renderToneLabRound();});
  });});
}

async function renderChineseBasics() {
  if (state.language !== 'chinese') { await setView('home'); return; }
  if (!state.chineseFoundations) state.chineseFoundations = await api('/api/chinese/foundations');
  const d = state.chineseFoundations;
  const toneCards = d.tones.map(function (tone) {
    return '<article class="tone-card tone-' + tone.number + '"><div class="tone-number">' + (tone.number || '·') + '</div><div><b>' + esc(tone.name) + ' тон · ' + esc(tone.gesture) + '</b><div class="tone-word">' + esc(tone.hanzi) + ' <span class="pinyin-line">' + esc(tone.pinyin) + '</span></div><p>' + esc(tone.ru) + ' · ' + esc(tone.hint) + '</p></div><button class="mini-listen" data-speak-text="' + esc(tone.hanzi) + '" data-speak-language="chinese" data-speak-rate="0.72">▶</button></article>';
  }).join('');
  const initials = d.initials.map(function (group) { return '<section class="sound-group"><h3>' + esc(group.group) + '</h3><div class="sound-grid">' + group.items.map(function (x) { return '<div class="sound-chip"><div class="sound-chip-head"><b>' + esc(x.pinyin) + '</b><button class="mini-listen" data-speak-text="' + esc(x.example_hanzi || x.sample || '') + '" data-speak-language="chinese" data-speak-rate="0.72">▶</button></div><span>≈ ' + esc(x.ru) + '</span><div class="sound-example"><strong>' + esc(x.example_hanzi || x.sample || '') + '</strong><em class="pinyin-line">' + esc(x.example_pinyin || x.sample_pinyin || '') + '</em><small>≈ ' + esc(x.example_reading || '') + ' · ' + esc(x.example_ru || '') + '</small></div><small>' + esc(x.hint) + '</small></div>'; }).join('') + '</div></section>'; }).join('');
  const finals = d.finals.map(function (group) { return '<section class="sound-group"><h3>' + esc(group.group) + '</h3><div class="final-grid">' + group.items.map(function (x) { return '<div class="final-chip"><div><div class="sound-chip-head"><b>' + esc(x.pinyin) + '</b><button class="mini-listen" data-speak-text="' + esc(x.example_hanzi || x.sample || '') + '" data-speak-language="chinese" data-speak-rate="0.72">▶</button></div><div><strong>' + esc(x.example_hanzi || x.sample || '') + '</strong> <span class="pinyin-line">' + esc(x.example_pinyin || x.sample_pinyin || '') + '</span></div><small>≈ ' + esc(x.example_reading || '') + ' · ' + esc(x.hint || x.ru || '') + '</small></div></div>'; }).join('') + '</div></section>'; }).join('');
  const starter = d.starter_terms.map(function (x) { return '<article class="starter-word"><div><div class="target">' + esc(x.hanzi) + '</div><div class="pinyin-line">' + esc(x.pinyin) + '</div><div class="reading-line">≈ ' + esc(x.reading) + '</div><div class="translation">' + esc(x.ru) + '</div></div><div class="pronunciation-actions"><button class="listen-button" data-speak-text="' + esc(x.hanzi) + '" data-speak-language="chinese">▶</button><button class="listen-button subtle" data-speak-text="' + esc(x.hanzi) + '" data-speak-language="chinese" data-speak-rate="0.62">медленно</button></div></article>'; }).join('');
  const pt = d.putonghua || {};
  const dialectGroups = (pt.groups || []).map(function (x, i) { return '<details class="dialect-card"><summary><span class="dialect-number">' + (i+1) + '</span><div><b>' + esc(x.zh) + ' · ' + esc(x.name) + '</b><small>' + esc(x.where) + '</small></div><span class="chevron">⌄</span></summary><div class="dialect-body"><p><b>Пример:</b> ' + esc(x.examples) + '</p><p>' + esc(x.friendly) + '</p></div></details>'; }).join('');
  const dialectComparisons = (pt.comparison_examples || []).map(function (item) {
    const standard = item.standard || {};
    const variants = (item.variants || []).map(function(v){
      return '<div class="dialect-variant"><div class="dialect-variant-head"><b>'+esc(v.label)+'</b><small>'+esc(v.place||'')+'</small></div><div class="dialect-phrase">'+esc(v.text||'')+'</div><div class="dialect-roman">'+esc(v.romanization||'')+' <span>'+esc(v.system||'')+'</span></div><div class="dialect-reading">'+esc(v.reading_ru||'')+'</div><p>'+esc(v.note||'')+'</p></div>';
    }).join('');
    return '<article class="dialect-compare-card"><div class="dialect-compare-title"><div><div class="kicker">ОДИН СМЫСЛ · РАЗНЫЙ ЗВУК</div><h3>'+esc(item.meaning||'')+'</h3><p>'+esc(item.lesson||'')+'</p></div></div><div class="dialect-standard"><div><b>Путунхуа</b><div class="dialect-phrase">'+esc(standard.text||'')+'</div><div class="pinyin-line">'+esc(standard.romanization||'')+'</div><small>≈ '+esc(standard.reading_ru||'')+'</small></div>'+(standard.audio?'<button class="listen-button" data-speak-text="'+esc(standard.text||'')+'" data-speak-language="chinese" data-speak-rate="0.78">▶ Путунхуа</button>':'')+'</div><div class="dialect-variants">'+variants+'</div></article>';
  }).join('');
  const comparisonInfo = pt.comparison_intro || {};
  const dialectComparisonHtml = dialectComparisons ? '<section class="card dialect-comparison-intro"><div class="kicker">СРАВНИТЕ ГЛАЗАМИ И УШАМИ</div><h2>'+esc(comparisonInfo.title||'Как один смысл звучит по-разному')+'</h2><p class="lead">'+esc(comparisonInfo.simple||'')+'</p><div class="warning-soft">'+esc(comparisonInfo.tone_note||'')+'</div><p class="muted">'+esc(comparisonInfo.audio_note||'')+'</p></section><div class="dialect-comparisons">'+dialectComparisons+'</div><p class="muted dialect-safety">'+esc(pt.comparison_safety||'')+'</p>' : '';
  const putonghuaHtml = pt.title ? '<div class="section-title"><h2>Справка: Путунхуа и диалекты</h2><span>не отдельный учебный трек</span></div><section class="reference-only-strip"><b>Это справочная информация.</b><span>Учить диалекты не нужно. Все уроки, тесты, XP и итоговый экзамен по китайскому относятся к Путунхуа.</span></section>' +
    '<section class="card putonghua-hero"><div class="putonghua-mark">普</div><div><div class="kicker">普通话 · PǓTŌNGHUÀ</div><h2>' + esc(pt.title) + '</h2><p class="lead">' + esc(pt.simple) + '</p><div class="friendly-steps compact">' + (pt.official_basis || []).map(function(x,i){return '<div><b>'+(i+1)+'</b><p>'+esc(x)+'</p></div>';}).join('') + '</div><div class="warning-soft">' + esc(pt.not_beijing_dialect || '') + '</div></div></section>' +
    '<section class="card workplace-language"><div><div class="kicker">НА ЗАВОДЕ</div><h2>Что вы услышите в реальной работе</h2><p>' + esc(pt.workplace || '') + '</p><div class="factory-phrase"><div><strong>请说普通话，可以吗？</strong><span class="pinyin-line">qǐng shuō pǔtōnghuà, kěyǐ ma?</span><small>Можно, пожалуйста, говорить на Путунхуа?</small></div><button class="listen-button" data-speak-text="请说普通话，可以吗？" data-speak-language="chinese" data-speak-rate="0.78">▶ Послушать</button></div></div></section>' +
    '<section class="card dialect-count"><div class="big-ten">10<span>групп</span></div><div><div class="kicker">НЕ 10 ОТДЕЛЬНЫХ «ДИАЛЕКТОВ»</div><h2>' + esc((pt.how_many || {}).headline || '') + '</h2><p>' + esc((pt.how_many || {}).simple || '') + '</p><div class="context-warning">' + esc((pt.how_many || {}).important || '') + '</div></div></section>' +
    dialectComparisonHtml +
    '<div class="section-title"><h2>10 крупных групп</h2><span>откройте любую карточку</span></div><div class="dialect-grid">' + dialectGroups + '</div>' +
    '<section class="card accent-dialect-card"><div class="kicker">ВАЖНО НЕ ПУТАТЬ</div><h2>' + esc((pt.accent_vs_dialect || {}).title || '') + '</h2><div class="grid two"><div class="context-clue"><b>Акцент</b><p>' + esc((pt.accent_vs_dialect || {}).accent || '') + '</p></div><div class="context-clue"><b>Местная разновидность / 方言</b><p>' + esc((pt.accent_vs_dialect || {}).dialect || '') + '</p></div></div><div class="warning-soft">' + esc((pt.accent_vs_dialect || {}).factory_tip || '') + '</div></section>' +
    '<section class="card dialect-faq"><div class="kicker">БЕЗ ЛИНГВИСТИЧЕСКОЙ ПАНИКИ</div><h2>Четыре вопроса новичка</h2><div class="faq-grid">' + (pt.mini_facts || []).map(function(x){return '<div class="faq-item"><b>'+esc(x.q)+'</b><p>'+esc(x.a)+'</p></div>';}).join('') + '</div><p class="muted">' + esc(pt.safe_message || '') + '</p></section>' : '';
  $('#main').innerHTML = pageHead('中文 · 普通话', d.title, d.subtitle) +
    '<section class="putonghua-primary-card"><div class="putonghua-primary-badge">УЧИМ: ПУТУНХУА 普通话</div><h2>Весь основной китайский курс — стандартный китайский</h2><p>'+esc((d.learning_standard||{}).primary_message||'Вы изучаете Путунхуа — стандартный китайский.')+'</p><div class="warning-soft">'+esc((d.learning_standard||{}).reference_message||'Диалекты ниже — только справка.')+'</div></section>' +
    '<section class="card foundations-intro"><div class="foundation-mascot">拼</div><div><h2>Главная идея</h2><p><b>Иероглиф — что написано. Pinyin — как произнести. Тон — мелодия слога.</b></p><p>Не нужно запоминать всё за один день. Сначала научитесь узнавать систему, потом слух начнёт собирать её автоматически.</p></div></section>' +
    '<div class="truth-grid">' + d.truths.map(function (x,i) { return '<div class="truth-card"><b>' + (i+1) + '</b><p>' + esc(x) + '</p></div>'; }).join('') + '</div>' +
    '<section class="card pinyin-explainer"><div><div class="kicker">PINYIN</div><h2>' + esc(d.pinyin.title) + '</h2><p>' + esc(d.pinyin.simple) + '</p><div class="syllable-formula"><span>zh</span><i>+</i><span>i</span><i>+</i><span>↘</span><i>=</i><strong>zhì</strong></div><p class="muted">' + esc(d.pinyin.formula) + '</p><div class="warning-soft">' + esc(d.pinyin.warning) + '</div></div><div class="foundation-example"><div class="target">' + esc(d.pinyin.example.hanzi) + '</div><div class="pinyin-line">' + esc(d.pinyin.example.pinyin) + '</div><div class="reading-line">≈ ' + esc(d.pinyin.example.reading) + '</div><p>' + esc(d.pinyin.example.ru) + '</p><button class="listen-button" data-speak-text="' + esc(d.pinyin.example.hanzi) + '" data-speak-language="chinese">▶ Послушать</button></div></section>' +
    '<div class="section-title"><h2>5 тонов — послушайте разницу</h2><span>не зубрить, а услышать</span></div><div class="tone-grid">' + toneCards + '</div>' +
    '<section class="card tone-lab-card"><div><div class="kicker">TONE LAB</div><h2>Угадайте направление тона на слух</h2><p>Всего 5 коротких звуков. Ошибка здесь — нормальная часть обучения: сервис сразу показывает движение голоса.</p></div><div id="toneLabBody"><button id="toneLabStart" class="primary">▶ Начать на 2 минуты</button></div></section>' +
    '<section class="card context-card"><div class="kicker">КОНТЕКСТ</div><h2>' + esc(d.context.title) + '</h2><p class="lead">' + esc(d.context.simple) + '</p><div class="grid two">' + d.context.clues.map(function (x) { return '<div class="context-clue"><b>' + esc(x.title) + '</b><p>' + esc(x.text) + '</p></div>'; }).join('') + '</div><div class="context-warning">' + esc(d.context.but) + '</div><div class="context-compare"><div><div class="target">' + esc(d.context.example.a.hanzi) + '</div><div class="pinyin-line">' + esc(d.context.example.a.pinyin) + '</div><p>' + esc(d.context.example.a.ru) + '</p><button class="mini-listen" data-speak-text="' + esc(d.context.example.a.hanzi) + '" data-speak-language="chinese">▶</button></div><div><div class="target">' + esc(d.context.example.b.hanzi) + '</div><div class="pinyin-line">' + esc(d.context.example.b.pinyin) + '</div><p>' + esc(d.context.example.b.ru) + '</p><button class="mini-listen" data-speak-text="' + esc(d.context.example.b.hanzi) + '" data-speak-language="chinese">▶</button></div></div><p><b>' + esc(d.context.example.lesson) + '</b></p></section>' +
    putonghuaHtml +
    '<div class="section-title"><h2>«Алфавит» Pinyin: звуки, а не буквы</h2><span>инициали + финали</span></div><section class="card"><p class="lead">Китайский слог удобнее собирать как конструктор. <b>Инициаль</b> — начало слога, <b>финаль</b> — его основная звучащая часть. Нажимайте ▶: звук даётся через настоящий китайский слог, а не через название латинской буквы.</p><div class="warning-soft">' + esc(d.sound_map_note || '') + '</div>' + initials + finals + '</section>' +
    '<section class="card sound-advice-card"><div class="kicker">КАК ТРЕНИРОВАТЬСЯ</div><h2>' + esc(d.sound_advice.title) + '</h2><div class="friendly-steps">' + d.sound_advice.items.map(function(x,i){return '<div><b>'+(i+1)+'</b><p>'+esc(x)+'</p></div>';}).join('') + '</div></section>' +
    '<section class="card tone-change-card"><div class="kicker">ЖИВАЯ РЕЧЬ</div><h2>' + esc(d.tone_changes.title) + '</h2><ol class="friendly-list">' + d.tone_changes.items.map(function(x){return '<li>'+esc(x)+'</li>';}).join('') + '</ol></section>' +
    '<div class="section-title"><h2>Маршрут новичка</h2><span>без перегруза</span></div><div class="mini-path">' + d.mini_path.map(function(x){return '<article class="mini-path-card"><b>'+x.step+'</b><div><h3>'+esc(x.title)+'</h3><p>'+esc(x.text)+'</p></div></article>';}).join('') + '</div>' +
    '<div class="section-title"><h2>10 слов, с которых можно начать</h2><span>послушайте обычную и медленную скорость</span></div><div class="starter-grid">' + starter + '</div>' +
    '<section class="card learning-settings-card"><div><div class="kicker">МОЙ РЕЖИМ</div><h2>Сколько подсказок показывать</h2><p>Можно постепенно отказаться от Pinyin, когда иероглифы и звучание начнут узнавать сами.</p></div><div class="settings-switches"><label class="toggle-line"><input id="foundationPinyin" type="checkbox" ' + (state.learningPrefs.show_pinyin ? 'checked' : '') + '> Показывать Pinyin в обучении</label><label class="toggle-line"><input id="foundationReading" type="checkbox" ' + (state.learningPrefs.show_reading ? 'checked' : '') + '> Показывать приблизительное чтение для русскоязычного новичка</label><label class="toggle-line"><input id="foundationServerAudio" type="checkbox" ' + (state.learningPrefs.server_audio_enabled ? 'checked' : '') + '> Сначала использовать стабильное серверное аудио</label><button id="saveFoundationPrefs" class="primary">Сохранить</button><small>Аудио: ' + esc(state.pronunciationStatus && state.pronunciationStatus.server_available ? ('offline server · ' + state.pronunciationStatus.engine) : 'browser fallback') + '</small></div></section>';
  $('#toneLabStart').addEventListener('click', function () { toneLabStart(d); });
  $('#saveFoundationPrefs').addEventListener('click', async function () {
    try {
      await saveLearningPrefs({show_pinyin:$('#foundationPinyin').checked, show_reading:$('#foundationReading').checked, server_audio_enabled:$('#foundationServerAudio').checked});
      toast('Настройки обучения сохранены');
      renderChineseBasics();
    } catch (error) { toast(error.message); }
  });
}

async function renderManager() {
  if (state.user.role !== 'manager') throw new Error('Раздел доступен руководителю подразделения');
  state.managerTeam = await api('/api/manager/team');
  const users = state.managerTeam.users || [];
  $('#main').innerHTML = pageHead('Department scope', 'Моя команда · ' + state.managerTeam.department, 'Только сотрудники вашего подразделения. XP показан как мотивационная активность и не является оценкой профессиональной пригодности.') +
    '<div class="table-wrap"><table class="admin-table"><thead><tr><th>Сотрудник</th><th>Уровень</th><th>XP</th><th>Освоено</th><th>Активность</th></tr></thead><tbody>' + users.map(function(u){return '<tr data-manager-user="'+u.id+'"><td><b>'+esc(u.display_name)+'</b><small>'+esc(u.username)+'</small></td><td>'+u.level+' · '+esc(u.level_title)+'</td><td>'+u.lifetime_xp+'</td><td>'+u.terms_known+'/'+u.terms_touched+'</td><td>'+esc(u.last_activity_at ? new Date(u.last_activity_at).toLocaleDateString() : '—')+'</td></tr>';}).join('') + '</tbody></table></div><div id="managerUserDetail"></div>';
  $$('[data-manager-user]').forEach(function(row){row.addEventListener('click', async function(){const u=await api('/api/manager/team/'+row.dataset.managerUser+'/learning-stats'); $('#managerUserDetail').innerHTML='<section class="card admin-user-detail"><div class="section-title"><h2>'+esc(u.display_name)+'</h2><span>'+esc(u.department)+'</span></div>'+Object.keys(u.languages).map(function(lang){const x=u.languages[lang];return '<h3>'+(lang==='english'?'English':'中文')+' · '+x.known+'/'+x.touched+'</h3><div class="chip-row">'+x.topics.map(function(t){return '<span class="topic-chip static">'+esc(t.topic)+' · '+t.mastery_percent+'%</span>';}).join('')+'</div>';}).join('')+'</section>';});});
}

const GAME_LABELS = {
  match: ['Word Match', 'Сопоставьте термин и перевод'],
  listening: ['Listening Sprint', 'Прослушайте термин и выберите значение'],
  phrase: ['Phrase Builder', 'Соберите рабочую фразу в правильном порядке'],
  mistake: ['Find the Mistake', 'Найдите точное значение среди похожих вариантов']
};

async function renderGames() {
  if (!state.gameSession) {
    $('#main').innerHTML = pageHead('3–5 минут', 'Игры', 'Короткие упражнения без давления. XP начисляется сервером, повторное фармление одной и той же активности ограничивается.') +
      '<div class="game-grid">' + Object.keys(GAME_LABELS).map(function (key) {
        return '<button class="game-card" data-start-game="' + key + '"><div class="game-symbol">' + (key === 'match' ? '↔' : key === 'listening' ? '◖' : key === 'phrase' ? '≡' : '✓') + '</div><h3>' + GAME_LABELS[key][0] + '</h3><p>' + GAME_LABELS[key][1] + '</p><span>Начать →</span></button>';
      }).join('') + '</div>' + xpPanelHTML();
    $$('[data-start-game]').forEach(function (button) { button.addEventListener('click', function () { startGame(button.dataset.startGame); }); });
    return;
  }
  if (state.gameIndex >= state.gameSession.items.length) {
    const finishing = state.gameSession;
    state.gameSession = null;
    const result = await api('/api/games/' + finishing.session_id + '/finish', {method:'POST', body:JSON.stringify({answers:state.gameAnswers})});
    if (result.profile) state.gamification = result.profile;
    $('#xpPill').textContent = state.gamification.spendable_xp + ' XP';
    $('#main').innerHTML = pageHead('Игра завершена', 'Результат ' + result.score + '/' + result.total, 'Короткая практика закончена. Можно остановиться здесь — ежедневной обязанности нет.') +
      '<div class="card exam-intro"><div class="result-score">' + result.score + '/' + result.total + '</div><p>+' + (result.awarded || 0) + ' XP · баланс ' + state.gamification.spendable_xp + ' XP</p><button class="primary" data-go="games">Ещё одна игра</button></div>';
    state.gameAnswers = []; state.gameIndex = 0;
    return;
  }
  const item = state.gameSession.items[state.gameIndex];
  const type = state.gameSession.game_type;
  let body = '';
  if (type === 'match') {
    const options = state.gameSession.items.slice().sort(function () { return Math.random() - .5; });
    body = '<h2>' + esc(item.term) + '</h2>' + (item.pronunciation ? '<div class="' + (state.language === 'chinese' ? 'question-pinyin' : 'ipa-line') + '">' + esc(item.pronunciation) + '</div>' : '') + (item.reading ? '<div class="reading-line">≈ ' + esc(item.reading) + '</div>' : '') + '<div class="pronunciation-actions"><button class="listen-button" data-speak-text="' + esc(item.term) + '" data-speak-language="' + state.language + '">▶ Послушать</button></div>' +
      '<div class="options">' + options.map(function (x) { return '<button class="option" data-game-answer="' + esc(x.id) + '">' + esc(x.translation) + '</button>'; }).join('') + '</div>';
  } else if (type === 'listening') {
    body = '<button id="playGameAudio" class="audio-button">▶ Прослушать</button>' + (item.pronunciation ? '<div class="' + (state.language === 'chinese' ? 'question-pinyin' : 'ipa-line') + '">' + esc(item.pronunciation) + '</div>' : '') + (item.reading ? '<div class="reading-line">≈ ' + esc(item.reading) + '</div>' : '') +
      '<div class="options">' + item.options.map(function (x,i) { return '<button class="option" data-game-answer="' + i + '">' + esc(x) + '</button>'; }).join('') + '</div>';
  } else if (type === 'mistake') {
    body = '<h2>' + esc(item.term) + '</h2>' + (item.pronunciation ? '<div class="' + (state.language === 'chinese' ? 'question-pinyin' : 'ipa-line') + '">' + esc(item.pronunciation) + '</div>' : '') + (item.reading ? '<div class="reading-line">≈ ' + esc(item.reading) + '</div>' : '') + '<div class="pronunciation-actions"><button class="listen-button" data-speak-text="' + esc(item.term) + '" data-speak-language="' + state.language + '">▶ Послушать</button></div><p>Какое значение точное?</p>' +
      '<div class="options">' + item.options.map(function (x,i) { return '<button class="option" data-game-answer="' + i + '">' + esc(x) + '</button>'; }).join('') + '</div>';
  } else {
    state.phraseSelected = state.phraseSelected || [];
    body = '<p class="translation-line">' + esc(item.translation) + '</p><div id="phraseBuilt" class="phrase-built">' + state.phraseSelected.map(esc).join(' ') + '</div>' +
      '<div class="token-bank">' + item.tokens.map(function (x,i) { return '<button class="token" data-token-index="' + i + '">' + esc(x) + '</button>'; }).join('') + '</div><div class="actions"><button id="phraseReset" class="ghost">Сбросить</button><button id="phraseDone" class="primary">Готово</button></div>';
  }
  $('#main').innerHTML = pageHead(GAME_LABELS[type][0], GAME_LABELS[type][1], (state.gameIndex + 1) + ' из ' + state.gameSession.items.length) +
    '<div class="quiz-stage"><div class="quiz-progress"><i style="width:' + ((state.gameIndex+1)/state.gameSession.items.length*100) + '%"></i></div><div class="card question-card">' + body + '</div></div>';
  if ($('#playGameAudio')) $('#playGameAudio').addEventListener('click', function () { speakText(item.audio_text, .82); });
  $$('[data-game-answer]').forEach(function (button) { button.addEventListener('click', function () { const raw = button.dataset.gameAnswer; state.gameAnswers.push(type === 'match' ? raw : Number(raw)); state.gameIndex += 1; renderGames(); }); });
  $$('[data-token-index]').forEach(function (button) { button.addEventListener('click', function () { if (button.disabled) return; button.disabled = true; state.phraseSelected.push(item.tokens[Number(button.dataset.tokenIndex)]); $('#phraseBuilt').textContent = state.phraseSelected.join(' '); }); });
  if ($('#phraseReset')) $('#phraseReset').addEventListener('click', function () { state.phraseSelected = []; renderGames(); });
  if ($('#phraseDone')) $('#phraseDone').addEventListener('click', function () { state.gameAnswers.push(state.phraseSelected.slice()); state.phraseSelected = []; state.gameIndex += 1; renderGames(); });
}

async function startGame(type) {
  try {
    const url = '/api/games/' + type + '/start?language=' + encodeURIComponent(state.language) + '&topic=' + encodeURIComponent(state.topic || '');
    state.gameSession = await api(url, {method:'POST'});
    state.gameAnswers = []; state.gameIndex = 0; state.phraseSelected = [];
    renderGames();
  } catch (error) { toast(error.message); }
}

async function renderXP() {
  state.gamification = await refreshGamification();
  state.rewards = await api('/api/gamification/rewards');
  const helpOnly = new Set(['hint_small','show_pinyin','slow_audio','eliminate_option','sentence_start','explain_word','pronunciation_breakdown','work_example','mistake_explain']);
  const packHtml = state.xpPack ? renderXpPack(state.xpPack) : '';
  $('#main').innerHTML = pageHead('XP economy', 'Опыт, который помогает учиться', 'Уровень не уменьшается. Тратится только доступный баланс XP; основные рабочие функции сервиса всегда бесплатны.') +
    xpPanelHTML() + '<div class="section-title"><h2>Практическая помощь</h2><span>Баланс: ' + state.gamification.spendable_xp + ' XP</span></div>' +
    '<div class="reward-grid">' + state.rewards.items.map(function (item) {
      const disabled = helpOnly.has(item.id);
      return '<article class="reward-card"><div><div class="reward-price">' + item.price + ' XP</div><h3>' + esc(item.title) + '</h3><p>' + esc(item.description) + '</p></div>' +
        (disabled ? '<small>Используется прямо внутри задания</small>' : '<button class="primary" data-buy-reward="' + esc(item.id) + '">Активировать</button>') + '</article>';
    }).join('') + '</div>' + packHtml;
  $$('[data-buy-reward]').forEach(function (button) { button.addEventListener('click', function () { buyReward(button.dataset.buyReward); }); });
}

function renderXpPack(pack) {
  if (!pack) return '';
  if (pack.items && pack.items.length && pack.items[0].term) {
    return '<div class="section-title"><h2>' + esc(pack.title || 'Персональная тренировка') + '</h2></div><div class="term-list">' + pack.items.map(termCard).join('') + '</div>';
  }
  if (pack.items && pack.items.length) {
    return '<div class="section-title"><h2>Открытая практика</h2></div><div class="knowledge-grid">' + pack.items.map(function (x) { return '<article class="card"><div class="kicker">' + esc(x.topic || 'Scenario') + '</div><h3>' + esc(x.title || '') + '</h3><p>' + esc(x.question_translation || x.goal || '') + '</p></article>'; }).join('') + '</div>';
  }
  return '';
}

async function buyReward(id) {
  try {
    const result = await api('/api/gamification/spend', {method:'POST', body:JSON.stringify({reward_id:id, language:state.language, context:{topic:state.topic || ''}})});
    state.gamification = result.profile; state.xpPack = result.result;
    $('#xpPill').textContent = state.gamification.spendable_xp + ' XP';
    toast('−' + result.spent + ' XP · ' + result.reward.title);
    renderXP();
  } catch (error) { toast(error.message); }
}

async function renderNotifications() {
  const values = await Promise.all([api('/api/notifications/settings'), api('/api/notifications/pending')]);
  state.notificationSettings = values[0]; state.nudges = values[1].items || [];
  const s = state.notificationSettings;
  $('#main').innerHTML = pageHead('Learning Nudge Engine', 'Напоминания без давления', 'Сервис пишет редко, только когда есть смысл продолжить. После трёх проигнорированных напоминаний он замолкает до вашего возвращения.') +
    '<div class="grid two"><section class="card"><h3>Частота</h3><label>Режим<select id="nudgeMode"><option value="off">Выключены</option><option value="minimal">Минимальные · примерно раз в неделю</option><option value="normal">Обычные · по необходимости раз в 2–4 дня</option><option value="active">Активные · можно ежедневно</option></select></label>' +
      '<div class="grid two compact-grid"><label>Не раньше<input id="nudgeStart" type="time" value="' + esc(s.window_start) + '"></label><label>Не позже<input id="nudgeEnd" type="time" value="' + esc(s.window_end) + '"></label></div>' +
      '<label class="toggle-line"><input id="browserNudges" type="checkbox" ' + (s.browser_enabled ? 'checked' : '') + '> Показывать браузерное уведомление, когда сервис открыт</label><button id="saveNudges" class="primary">Сохранить</button><button id="enableBrowser" class="ghost">Разрешить уведомления браузера</button></section>' +
      '<section class="card"><h3>Последние</h3>' + (state.nudges.length ? state.nudges.map(function (x) { return '<div class="nudge-history"><b>' + esc(x.title) + '</b><p>' + esc(x.body) + '</p><button class="ghost small-button" data-read-nudge="' + x.id + '">Прочитано</button></div>'; }).join('') : '<p class="muted">Сейчас ничего не требует внимания.</p>') + '</section></div>';
  $('#nudgeMode').value = s.mode;
  $('#saveNudges').addEventListener('click', saveNudgeSettings);
  $('#enableBrowser').addEventListener('click', async function () { if (!('Notification' in window)) { toast('Браузер не поддерживает Notifications API'); return; } const permission = await Notification.requestPermission(); toast(permission === 'granted' ? 'Разрешено' : 'Не разрешено'); if (permission === 'granted') $('#browserNudges').checked = true; });
  $$('[data-read-nudge]').forEach(function (b) { b.addEventListener('click', async function () { await api('/api/notifications/' + b.dataset.readNudge + '/read', {method:'POST'}); renderNotifications(); }); });
}

async function saveNudgeSettings() {
  try {
    const payload = {mode:$('#nudgeMode').value, window_start:$('#nudgeStart').value, window_end:$('#nudgeEnd').value, browser_enabled:$('#browserNudges').checked};
    await api('/api/notifications/settings', {method:'PUT', body:JSON.stringify(payload)}); toast('Настройки сохранены'); renderNotifications();
  } catch (error) { toast(error.message); }
}

async function renderAdmin() {
  if (!['admin','editor'].includes(state.user.role)) throw new Error('Недостаточно прав');
  const isAdmin = state.user.role === 'admin';
  if (!isAdmin) {
    const values = await Promise.all([api('/api/admin/taxonomy'), api('/api/admin/terms'), api('/api/admin/learning/question-quality')]);
    state.adminTaxonomy = values[0]; state.adminTerms = values[1] || []; state.questionQuality=values[2];
    $('#main').innerHTML = pageHead('Content control', 'Language Expert / Editor', 'Управление корпоративной терминологией. Пользовательская аналитика доступна только Admin.') + questionQualityHTML(state.questionQuality) + adminContentHTML();
    bindAdminContent();
    return;
  }
  const values = await Promise.all([api('/api/admin/analytics'), api('/api/admin/users'), api('/api/admin/taxonomy'), api('/api/admin/terms'), api('/api/admin/pilot-telemetry'), api('/api/admin/it-dashboard'), api('/api/admin/learning-error-telemetry'), api('/api/admin/pilot/governance-summary'), api('/api/admin/pilot/groups'), api('/api/admin/pilot/features'), api('/api/admin/learning/question-quality')]);
  const analytics = values[0]; state.adminUsers = values[1]; state.adminTaxonomy = values[2]; state.adminTerms = values[3] || []; const telemetry = values[4]; state.itDashboard = values[5]; state.learningErrorTelemetry = values[6]; state.pilotGovernance=values[7]; state.pilotGroups=values[8]||[]; state.pilotFeatures=values[9]||[]; state.questionQuality=values[10];
  $('#main').innerHTML = pageHead('Pilot control', 'Admin / Analytics', 'Контент, пользователи и учебная статистика. XP остаётся мотивационной метрикой и не подменяет реальную оценку компетенций.') +
    '<div class="progress-dashboard admin-kpis"><div class="progress-tile"><b>' + analytics.users + '</b><span>пользователей</span></div><div class="progress-tile"><b>' + analytics.active_7d + '</b><span>активны 7 дней</span></div><div class="progress-tile"><b>' + telemetry.practice_accuracy_7d + '%</b><span>точность практики 7д</span></div><div class="progress-tile"><b>' + telemetry.games_completed_7d + '</b><span>игр завершено 7д</span></div></div>' +
    '<section class="card telemetry-strip"><b>Audio</b><span>' + (telemetry.server_tts_available ? ('offline · '+esc(telemetry.tts_engine)) : 'browser fallback') + '</span><b>Подразделения</b><span>' + telemetry.departments.length + '</span><b>Практика 7д</b><span>' + telemetry.practice_sessions_7d + '</span></section>' +
    pilotGovernanceHTML() +
    itDashboardHTML(state.itDashboard) +
    learningErrorTelemetryHTML(state.learningErrorTelemetry) + questionQualityHTML(state.questionQuality) +
    '<div class="section-title"><h2>Пользователи</h2></div><div class="table-wrap"><table class="admin-table"><thead><tr><th>Сотрудник</th><th>Подразделение</th><th>Роль</th><th>Уровень</th><th>XP</th><th>Изучено</th><th>Последняя активность</th></tr></thead><tbody>' + state.adminUsers.map(function (u) { return '<tr data-admin-user="' + u.id + '"><td><b>' + esc(u.display_name) + '</b><small>' + esc(u.username) + '</small></td><td>' + esc(u.department || 'General') + '</td><td>' + esc(u.role) + '</td><td>' + u.level + ' · ' + esc(u.level_title) + '</td><td>' + u.lifetime_xp + '</td><td>' + u.terms_known + '/' + u.terms_touched + '</td><td>' + esc(u.last_activity_at ? new Date(u.last_activity_at).toLocaleDateString() : '—') + '</td></tr>'; }).join('') + '</tbody></table></div><div id="adminUserDetail"></div>' + adminContentHTML();
  $$('[data-admin-user]').forEach(function (row) { row.addEventListener('click', function () { openAdminUser(row.dataset.adminUser); }); });
  bindPilotGovernance();
  bindITDashboard();
  bindAdminContent();
}

function itDashboardHTML(d) {
  if (!d) return '';
  const r = d.readiness || {}; const checks = r.checks || {}; const events = d.events_24h || {}; const maintenance = d.maintenance || {};
  const dbLatency = checks.database_latency_ms == null ? '—' : checks.database_latency_ms + ' ms';
  const tts = d.tts || {}; const slo=d.slo||{}; const recovery=d.recovery||{}; const alerts=(d.alerts||{}).items||[];
  const db=d.database||{}; const pool=db.pool||{}; const q=db.query_telemetry||{}; const recoveryEvidence=d.recovery_evidence||{};
  const backup=recoveryEvidence.backup||{}; const restore=recoveryEvidence.restore_rehearsal||{}; const objectives=recoveryEvidence.objectives||{};
  const sloStatus=slo.status==='met'?'SLO OK':(slo.status==='insufficient_data'?'мало данных':'SLO MISS');
  const backupLabel=backup.age_minutes==null?'нет evidence':Number(backup.age_minutes).toFixed(0)+' мин';
  const restoreLabel=restore.age_days==null?'нет evidence':Number(restore.age_days).toFixed(1)+' дн';
  const alertHtml=alerts.length?'<div class="pilot-alert-list">'+alerts.map(function(a){return '<div class="pilot-alert alert-'+esc(a.severity)+'"><div><b>'+esc(a.title)+'</b><span>'+esc(a.component)+' · '+esc(a.status)+'</span><p>'+esc(a.detail)+'</p></div>'+(a.status==='open'?'<button class="secondary" data-alert-ack="'+a.id+'">Принято</button>':'')+'</div>';}).join('')+'</div>':'<div class="ops-empty">Активных IT alerts нет.</div>';
  return '<div class="section-title"><h2>IT · Pilot Operations</h2><span>'+esc(recovery.state||'unknown')+'</span></div>' +
    '<section class="card it-dashboard '+(r.ready?'it-ok':'it-attention')+'"><div class="grid four">' +
    '<div><b>'+(r.ready?'Готов':'Проверить')+'</b><span>readiness</span></div>' +
    '<div><b>'+esc(recovery.state||'—')+'</b><span>recovery state</span></div>' +
    '<div><b>'+esc(dbLatency)+'</b><span>DB latency</span></div>' +
    '<div><b>'+Number((d.alerts||{}).active_count||0)+'</b><span>active alerts</span></div></div>' +
    '<div class="slo-grid"><div><b>'+Number(slo.availability_percent||0).toFixed(2)+'%</b><span>availability · target '+Number((slo.targets||{}).availability_percent||0).toFixed(1)+'%</span></div><div><b>'+Number(slo.error_rate_percent||0).toFixed(2)+'%</b><span>5xx rate</span></div><div><b>'+Number(slo.p95_ms||0).toFixed(0)+' ms</b><span>p95 · target '+Number((slo.targets||{}).p95_ms||0)+' ms</span></div><div><b>'+esc(sloStatus)+'</b><span>'+Number(slo.samples||0)+' samples / '+Number(slo.window_minutes||0)+' min</span></div></div>' +
    '<div class="slo-grid ops-detail-grid"><div><b>'+Number(q.p95_ms||0).toFixed(1)+' ms</b><span>DB query p95 · '+Number(q.slow_queries||0)+' slow</span></div><div><b>'+Number(pool.saturation_percent||0).toFixed(1)+'%</b><span>DB pool saturation</span></div><div><b>'+esc(backupLabel)+'</b><span>backup age · '+esc(backup.status||'unknown')+'</span></div><div><b>'+esc(restoreLabel)+'</b><span>restore evidence · '+esc(restore.status||'unknown')+'</span></div></div>' +
    '<div class="telemetry-strip compact"><b>Schema</b><span>'+esc((checks.schema_head||{}).current || '—')+'</span><b>TTS</b><span>'+(tts.circuit_open?'circuit OPEN':(tts.server_available?'offline':'browser fallback'))+'</span><b>HTTP 5xx</b><span>'+Number((d.http||{}).server_errors_since_start||0)+'</span><b>RPO/RTO</b><span>'+Number(objectives.rpo_target_minutes||0)+'m / '+Number(objectives.rto_target_minutes||0)+'m</span></div>' +
    '<div class="ops-subtitle"><b>Alerts</b><span>acknowledge означает «IT увидел», а не «проблема устранена»</span></div>'+alertHtml+
    ((q.top_slow_fingerprints||[]).length?'<details><summary>Slow-query fingerprints · без SQL/параметров</summary><div class="event-list">'+q.top_slow_fingerprints.slice(0,6).map(function(x){return '<div><b>'+esc(x.operation)+' · '+esc(x.fingerprint)+'</b><span>'+Number(x.count||0)+' × · max '+Number(x.max_ms||0).toFixed(1)+' ms</span></div>';}).join('')+'</div></details>':'')+
    '<div class="maintenance-row"><span>К очистке: '+Object.values(maintenance.counts||{}).reduce(function(a,b){return a+Number(b||0);},0)+'</span><button id="maintenancePreview" class="secondary">Проверить cleanup</button><button id="maintenanceRun" class="secondary">Запустить cleanup</button></div>' +
    (d.recent_events && d.recent_events.length ? '<details><summary>Последние operational events</summary><div class="event-list">'+d.recent_events.slice(0,8).map(function(e){return '<div><b>'+esc(e.component)+' · '+esc(e.event_type)+'</b><span>'+esc(e.severity)+' · '+esc(e.path||'')+'</span></div>';}).join('')+'</div></details>' : '') + '</section>';
}

function pilotGovernanceHTML() {
  const g=state.pilotGovernance||{}; const groups=state.pilotGroups||[]; const flags=state.pilotFeatures||[];
  const options=(state.adminUsers||[]).map(function(u){return '<option value="'+u.id+'">'+esc(u.display_name)+' · '+esc(u.department||'General')+'</option>';}).join('');
  const flagRows=flags.map(function(f){return '<span class="governance-flag">'+esc(f.flag_key)+' · '+(f.default_enabled?'default ON':'default OFF')+'</span>';}).join('');
  const groupCards=groups.map(function(x){
    const memberChips=x.members.map(function(m){return '<span class="member-chip">'+esc(m.display_name)+'<button type="button" data-pilot-remove-member="'+x.id+'|'+m.id+'" title="Убрать из группы">×</button></span>';}).join('') || '<small>пока нет участников</small>';
    const startValue=x.starts_at?String(x.starts_at).slice(0,16):''; const endValue=x.ends_at?String(x.ends_at).slice(0,16):'';
    return '<article class="card governance-group"><div class="section-title"><div><h3>'+esc(x.name)+'</h3><span>'+esc(x.department)+' · wave '+x.wave+' · '+esc(x.status)+(x.active?' · ACTIVE':'')+'</span></div><a href="/api/admin/pilot/export.csv?group_id='+x.id+'" target="_blank">CSV</a></div>'+
      '<div class="governance-members"><b>Участники: '+x.members.length+'</b><div class="member-chip-row">'+memberChips+'</div></div>'+
      '<div class="grid two compact-grid"><select data-pilot-member-select="'+x.id+'">'+options+'</select><button class="secondary" data-pilot-add-member="'+x.id+'">Добавить участника</button></div>'+
      '<div class="grid four compact-grid rollout-controls"><label>Статус<select data-pilot-group-status="'+x.id+'"><option '+(x.status==='draft'?'selected':'')+'>draft</option><option '+(x.status==='active'?'selected':'')+'>active</option><option '+(x.status==='paused'?'selected':'')+'>paused</option><option '+(x.status==='completed'?'selected':'')+'>completed</option></select></label><label>Wave<input data-pilot-group-wave="'+x.id+'" type="number" min="1" max="100" value="'+x.wave+'"></label><label>Старт<input data-pilot-group-start="'+x.id+'" type="datetime-local" value="'+esc(startValue)+'"></label><label>Окончание<input data-pilot-group-end="'+x.id+'" type="datetime-local" value="'+esc(endValue)+'"></label></div><button class="secondary" data-pilot-save-group="'+x.id+'">Сохранить rollout</button>'+
      '<div class="feature-toggle-grid">'+flags.map(function(f){const effective=(Object.prototype.hasOwnProperty.call(x.features,f.flag_key)?x.features[f.flag_key]:f.default_enabled);return '<label class="toggle-line"><input type="checkbox" data-pilot-feature="'+x.id+'|'+esc(f.flag_key)+'" '+(effective?'checked':'')+'> '+esc(f.title)+'</label>';}).join('')+'</div>'+
      '<div class="grid four"><input data-assign-name="'+x.id+'" placeholder="Трек: Quality Putonghua"><input data-assign-topic="'+x.id+'" placeholder="Тема: Quality / R&D"><select data-assign-language="'+x.id+'"><option value="chinese">Путунхуа / 中文</option><option value="english">English</option></select><select data-assign-level="'+x.id+'"><option>A1</option><option>A2</option><option>B1</option><option>B2</option><option>C1</option></select></div><div class="grid two compact-grid"><label>Дедлайн<input data-assign-due="'+x.id+'" type="date"></label><button class="secondary" data-pilot-assign="'+x.id+'">Назначить трек</button></div>'+
      (x.assignments&&x.assignments.length?'<div class="assignment-list">'+x.assignments.map(function(a){return '<span>'+esc(a.track_name)+' · '+(a.language==='chinese'?'Путунхуа':'English')+(a.topic?' · '+esc(a.topic):'')+' · '+esc(a.target_level)+(a.due_date?' · до '+esc(a.due_date):'')+' <button type="button" data-pilot-remove-assignment="'+x.id+'|'+a.id+'" title="Снять назначение">×</button></span>';}).join('')+'</div>':'')+'</article>';
  }).join('');
  return '<div class="section-title"><h2>Pilot Governance</h2><span>группы · волны · feature flags · quotas</span></div><section class="card governance-overview"><div class="grid four"><div><b>'+Number(g.groups_active||0)+'/'+Number(g.groups_total||0)+'</b><span>активных групп</span></div><div><b>'+Number(g.memberships||0)+'</b><span>назначений пользователей</span></div><div><b>'+Number(g.assignments||0)+'</b><span>учебных треков</span></div><div><b>'+((g.waves||[]).join(', ')||'—')+'</b><span>волны</span></div></div><p><b>Китайский:</b> '+esc(g.chinese_standard||'Путунхуа — основной трек.')+'</p><div class="quota-row"><span>XP '+Number((g.quotas||{}).daily_xp||0)+'/день</span><span>Игры '+Number((g.quotas||{}).daily_games||0)+'</span><span>TTS '+Number((g.quotas||{}).daily_tts||0)+'</span><span>Практика '+Number((g.quotas||{}).daily_practice||0)+'</span></div><div class="governance-flags">'+flagRows+'</div><a class="button-link" href="/api/admin/pilot/export.csv" target="_blank">Экспорт результатов CSV</a></section>'+
  '<section class="card governance-create"><h3>Новая группа / волна</h3><div class="grid four"><label>Название<input id="pilotGroupName" placeholder="R&D pilot"></label><label>Подразделение<input id="pilotGroupDepartment" value="General"></label><label>Волна<input id="pilotGroupWave" type="number" min="1" value="1"></label><label>Статус<select id="pilotGroupStatus"><option>draft</option><option>active</option><option>paused</option><option>completed</option></select></label></div><div class="grid two"><label>Старт<input id="pilotGroupStart" type="datetime-local"></label><label>Окончание<input id="pilotGroupEnd" type="datetime-local"></label></div><button id="createPilotGroup" class="primary">Создать группу</button></section>'+
  '<div class="governance-groups">'+groupCards+'</div>';
}

function bindPilotGovernance() {
  function isoOrNull(value){ return value ? new Date(value).toISOString() : null; }
  const create=$('#createPilotGroup'); if(create) create.addEventListener('click',async function(){try{await api('/api/admin/pilot/groups',{method:'POST',body:JSON.stringify({name:$('#pilotGroupName').value,department:$('#pilotGroupDepartment').value,description:'',status:$('#pilotGroupStatus').value,wave:Number($('#pilotGroupWave').value||1),starts_at:isoOrNull($('#pilotGroupStart').value),ends_at:isoOrNull($('#pilotGroupEnd').value)})});toast('Группа пилота создана');renderAdmin();}catch(e){toast(e.message);}});
  $$('[data-pilot-add-member]').forEach(function(b){b.addEventListener('click',async function(){const gid=b.dataset.pilotAddMember;const sel=$('[data-pilot-member-select="'+gid+'"]');try{await api('/api/admin/pilot/groups/'+gid+'/members/'+sel.value,{method:'POST'});toast('Участник добавлен');renderAdmin();}catch(e){toast(e.message);}});});
  $$('[data-pilot-remove-member]').forEach(function(b){b.addEventListener('click',async function(){const parts=b.dataset.pilotRemoveMember.split('|');try{await api('/api/admin/pilot/groups/'+parts[0]+'/members/'+parts[1],{method:'DELETE'});toast('Участник убран из группы');renderAdmin();}catch(e){toast(e.message);}});});
  $$('[data-pilot-save-group]').forEach(function(b){b.addEventListener('click',async function(){const gid=b.dataset.pilotSaveGroup;try{await api('/api/admin/pilot/groups/'+gid,{method:'PATCH',body:JSON.stringify({status:$('[data-pilot-group-status="'+gid+'"]').value,wave:Number($('[data-pilot-group-wave="'+gid+'"]').value||1),starts_at:isoOrNull($('[data-pilot-group-start="'+gid+'"]').value),ends_at:isoOrNull($('[data-pilot-group-end="'+gid+'"]').value)})});toast('Параметры rollout сохранены');renderAdmin();}catch(e){toast(e.message);}});});
  $$('[data-pilot-feature]').forEach(function(c){c.addEventListener('change',async function(){const parts=c.dataset.pilotFeature.split('|');try{await api('/api/admin/pilot/groups/'+parts[0]+'/features/'+encodeURIComponent(parts[1]),{method:'PUT',body:JSON.stringify({enabled:c.checked})});toast('Feature flag обновлён');}catch(e){c.checked=!c.checked;toast(e.message);}});});
  $$('[data-pilot-assign]').forEach(function(b){b.addEventListener('click',async function(){const gid=b.dataset.pilotAssign;const name=$('[data-assign-name=\"'+gid+'\"]')?.value||'';const topic=$('[data-assign-topic=\"'+gid+'\"]')?.value||'';const due=$('[data-assign-due=\"'+gid+'\"]')?.value||'';try{await api('/api/admin/pilot/groups/'+gid+'/assignments',{method:'POST',body:JSON.stringify({language:$('[data-assign-language=\"'+gid+'\"]')?.value||'chinese',track_name:name,topic:topic,target_level:$('[data-assign-level=\"'+gid+'\"]')?.value||'A1',due_date:due})});toast('Учебный трек назначен');renderAdmin();}catch(e){toast(e.message);}});});
  $$('[data-pilot-remove-assignment]').forEach(function(b){b.addEventListener('click',async function(){const parts=b.dataset.pilotRemoveAssignment.split('|');try{await api('/api/admin/pilot/groups/'+parts[0]+'/assignments/'+parts[1],{method:'DELETE'});toast('Назначение снято');renderAdmin();}catch(e){toast(e.message);}});});
}

function learningErrorTelemetryHTML(d) {
  if (!d) return '';
  const weak=(d.weak_topics||[]).slice(0,6);
  return '<div class="section-title"><h2>Качество обучения · ошибки</h2><span>агрегировано · '+Number(d.days||7)+' дней</span></div><section class="card learning-error-telemetry"><div class="grid four"><div><b>'+Number(d.accuracy_percent||0).toFixed(1)+'%</b><span>точность</span></div><div><b>'+Number(d.previous_accuracy_percent||0).toFixed(1)+'%</b><span>предыдущий период</span></div><div><b>'+Number(d.errors||0)+'</b><span>ошибок</span></div><div><b>'+Number(d.users_with_errors||0)+'</b><span>пользователей с ошибками</span></div></div><div class="weak-topic-grid">'+(weak.length?weak.map(function(x){return '<div><b>'+esc(x.name)+'</b><span>'+Number(x.accuracy_percent||0).toFixed(1)+'% · '+Number(x.errors||0)+' ошибок</span><small>'+Number(x.sessions||0)+' сессий / '+Number(x.questions||0)+' заданий</small></div>';}).join(''):'<p class="muted">Недостаточно данных для слабых тем.</p>')+'</div><p class="muted">'+esc(d.note||'')+'</p></section>';
}

function bindITDashboard() {
  const preview=$('#maintenancePreview'); const run=$('#maintenanceRun');
  if (preview) preview.addEventListener('click', async function(){ try { const r=await api('/api/admin/maintenance/cleanup?dry_run=true',{method:'POST'}); toast('К очистке: '+Object.values(r.counts||{}).reduce(function(a,b){return a+Number(b||0);},0)); } catch(e){toast(e.message);} });
  if (run) run.addEventListener('click', async function(){ try { const r=await api('/api/admin/maintenance/cleanup?dry_run=false',{method:'POST'}); toast('Cleanup выполнен: '+Object.values(r.counts||{}).reduce(function(a,b){return a+Number(b||0);},0)); await renderAdmin(); } catch(e){toast(e.message);} });
  $$('[data-alert-ack]').forEach(function(button){button.addEventListener('click',async function(){try{await api('/api/admin/alerts/'+button.dataset.alertAck+'/ack',{method:'PATCH',body:JSON.stringify({note:'Acknowledged from IT dashboard'})});toast('Alert принят IT');await renderAdmin();}catch(e){toast(e.message);}});});
}

function questionQualityHTML(d) {
  if (!d) return '';
  const flagged=(d.items||[]).filter(function(x){return x.flag;}).slice(0,8);
  return '<div class="section-title"><h2>Качество заданий</h2><span>adaptive telemetry</span></div><section class="card"><p class="muted">Сигнал для проверки контента, а не HR-оценка сотрудника.</p>'+(flagged.length?'<div class="weak-topic-grid">'+flagged.map(function(x){return '<div><b>'+esc(x.question_id)+'</b><span>'+Number(x.accuracy_percent||0).toFixed(1)+'% · '+Number(x.attempts||0)+' попыток</span><small>'+esc(x.topic||x.kind)+' · '+esc(x.flag)+'</small></div>';}).join('')+'</div>':'<p>Пока нет вопросов, требующих проверки.</p>')+'</section>';
}

function adminTermCard(item) {
  const actions=[];
  if (item.status!=='published') actions.push('<button class="secondary mini" data-term-submit="'+item.db_id+'">На проверку</button>');
  if (state.user.role==='admin' && item.status==='review') { actions.push('<button class="primary mini" data-term-approve="'+item.db_id+'">Утвердить</button>'); actions.push('<button class="secondary mini" data-term-reject="'+item.db_id+'">Вернуть</button>'); }
  actions.push('<button class="secondary mini" data-term-history="'+item.db_id+'">Версии</button>');
  return '<article class="term-card admin-governed-term"><div class="meta">'+esc(item.level+' · '+item.topic+' · '+item.status)+'</div><div class="target">'+esc(item.term)+'</div><div class="translation">'+esc(item.translation)+'</div><div class="reading-line">Источник: '+esc(item.source_type||'manual')+(item.source_ref?' · '+esc(item.source_ref):'')+'</div><div class="pronunciation-actions">'+actions.join('')+'</div><div class="term-history-slot" data-term-history-slot="'+item.db_id+'"></div></article>';
}

function adminContentHTML() {
  const t = state.adminTaxonomy;
  return '<div class="section-title"><h2>Добавить термин</h2><span>English / 中文 · тема · цех</span></div><section class="card admin-term-form"><div class="grid three"><label>Язык<select id="termLanguage"><option value="chinese">中文</option><option value="english">English</option></select></label><label>Уровень<select id="termLevel">' + t.levels.map(function(x){return '<option>'+x+'</option>';}).join('') + '</select></label><label>Цех / функция<input id="termShop" list="shopList"></label></div><datalist id="shopList">' + t.shops.map(function(x){return '<option value="'+esc(x)+'">';}).join('') + '</datalist><datalist id="topicList">' + t.topics.map(function(x){return '<option value="'+esc(x)+'">';}).join('') + '</datalist>' +
    '<div class="grid two"><label>Тема<input id="termTopic" list="topicList" required></label><label>Подтема<input id="termSubtopic"></label></div><div class="grid two"><label>Термин<input id="termValue" required></label><label>Перевод<input id="termTranslation" required></label></div><div class="grid three"><label>Pinyin / IPA<input id="termPronunciation"></label><label>Как читать (приблизительно)<input id="termReading"></label><label>Tags<input id="termTags"></label></div><div class="grid two"><label>Источник<select id="termSourceType"><option value="manual">Ручной ввод</option><option value="company_standard">Стандарт компании</option><option value="supplier">Поставщик</option><option value="work_instruction">Рабочая инструкция</option><option value="engineering_document">Инженерный документ</option><option value="language_expert">Language Expert</option><option value="public_dictionary">Словарь</option><option value="ai_suggestion">AI suggestion</option></select></label><label>Ссылка / номер документа<input id="termSourceRef"></label></div><div class="grid two"><label>Пример<textarea id="termExample"></textarea></label><label>Перевод примера<textarea id="termExampleTranslation"></textarea></label></div><button id="createTerm" class="primary">Опубликовать термин</button></section>' +
    '<div class="section-title"><h2>Массовый импорт</h2><span>XLSX / CSV</span></div><section class="card"><input id="termImport" type="file" accept=".xlsx,.csv"><button id="importTerms" class="secondary">Импортировать</button><p class="muted">Колонки: language, shop, topic, subtopic, level, term, pronunciation/pinyin, reading, translation, example, example_translation, tags, source_type, source_ref, status.</p></section>' +
    '<div class="section-title"><h2>Кастомные термины</h2><span>' + state.adminTerms.length + '</span></div><div class="term-list compact">' + state.adminTerms.slice(0,30).map(adminTermCard).join('') + '</div>';
}

function bindAdminContent() {
  $('#createTerm').addEventListener('click', async function () {
    try {
      const payload = {language:$('#termLanguage').value, level:$('#termLevel').value, shop:$('#termShop').value, topic:$('#termTopic').value, subtopic:$('#termSubtopic').value, term:$('#termValue').value, pronunciation:$('#termPronunciation').value, reading:$('#termReading').value, translation:$('#termTranslation').value, example:$('#termExample').value, example_translation:$('#termExampleTranslation').value, tags:$('#termTags').value, source_type:$('#termSourceType').value, source_ref:$('#termSourceRef').value, status:'published'};
      await api('/api/admin/terms', {method:'POST', body:JSON.stringify(payload)}); toast('Термин опубликован'); await loadLanguage(); renderAdmin();
    } catch (error) { toast(error.message); }
  });
  $('#importTerms').addEventListener('click', async function () {
    const file = $('#termImport').files[0]; if (!file) { toast('Выберите XLSX или CSV'); return; }
    const data = new FormData(); data.append('file', file);
    try { const result = await api('/api/admin/terms/import?default_language=' + encodeURIComponent(state.language), {method:'POST', body:data}); toast('Импортировано: ' + result.created + (result.error_count ? ' · ошибок: ' + result.error_count : '')); await loadLanguage(); renderAdmin(); } catch (error) { toast(error.message); }
  });
  $$('[data-term-submit]').forEach(function(b){b.addEventListener('click',async function(){try{await api('/api/admin/terms/'+b.dataset.termSubmit+'/submit-review',{method:'POST'});toast('Отправлено на проверку');renderAdmin();}catch(e){toast(e.message);}});});
  $$('[data-term-approve]').forEach(function(b){b.addEventListener('click',async function(){try{await api('/api/admin/terms/'+b.dataset.termApprove+'/approve',{method:'POST',body:JSON.stringify({note:'Approved in Content Governance'})});toast('Термин утверждён');await loadLanguage();renderAdmin();}catch(e){toast(e.message);}});});
  $$('[data-term-reject]').forEach(function(b){b.addEventListener('click',async function(){try{await api('/api/admin/terms/'+b.dataset.termReject+'/reject',{method:'POST',body:JSON.stringify({note:'Returned for correction'})});toast('Возвращено на доработку');renderAdmin();}catch(e){toast(e.message);}});});
  $$('[data-term-history]').forEach(function(b){b.addEventListener('click',async function(){try{const h=await api('/api/admin/terms/'+b.dataset.termHistory+'/revisions');const slot=$('[data-term-history-slot="'+b.dataset.termHistory+'"]');slot.innerHTML='<small>Версий: '+h.revisions.length+' · проверок: '+h.reviews.length+'</small>';}catch(e){toast(e.message);}});});
}

async function openAdminUser(id) {
  try {
    const u = await api('/api/admin/users/' + id + '/learning-stats');
    $('#adminUserDetail').innerHTML = '<section class="card admin-user-detail"><div class="section-title"><h2>' + esc(u.display_name) + '</h2><span>' + esc(u.role) + '</span></div><div class="grid three"><div><b>' + u.level + '</b><span>уровень · ' + esc(u.level_title) + '</span></div><div><b>' + u.lifetime_xp + '</b><span>Lifetime XP</span></div><div><b>' + u.spendable_xp + '</b><span>доступно XP</span></div></div>' + Object.keys(u.languages).map(function (lang) { const x=u.languages[lang]; return '<h3>' + (lang==='english'?'English':'中文') + ' · ' + x.known + '/' + x.touched + '</h3><div class="chip-row">' + x.topics.map(function(t){return '<span class="topic-chip static">'+esc(t.topic)+' · '+t.mastery_percent+'%</span>';}).join('') + '</div>'; }).join('') + '</section>';
    $('#adminUserDetail').scrollIntoView({behavior:'smooth', block:'nearest'});
  } catch (error) { toast(error.message); }
}

document.addEventListener('DOMContentLoaded', boot);
