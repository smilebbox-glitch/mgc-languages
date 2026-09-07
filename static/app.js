/* v6.0.16: physical frontend compatibility shell.
 * Feature views live in static/frontend modules; this file keeps only shared
 * session, language-loading, audio, practice and DOM primitives.
 */
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
  phraseSelected: [],
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
  learningErrorTelemetry: null,
  pilot: {features:{},groups:[],assignments:[]},
  pilotGroups: [],
  pilotFeatures: [],
  pilotGovernance: null,
  questionQuality: null
};

function esc(value) {
  return String(value == null ? '' : value).replace(/[&<>"']/g, function (char) {
    return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[char];
  });
}

function cookieValue(name) {
  const prefix = name + '=';
  const row = document.cookie.split(';').map(function (value) { return value.trim(); })
    .find(function (value) { return value.startsWith(prefix); });
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
  if (!message) {
    node.classList.add('hidden');
    node.textContent = '';
    return;
  }
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
  if (!node) return;
  node.textContent = String(message || '');
  node.classList.remove('hidden');
  clearTimeout(toast.timer);
  toast.timer = setTimeout(function () { node.classList.add('hidden'); }, 3200);
}

function showAuth() {
  const app = $('#appView');
  const auth = $('#authView');
  if (app) app.classList.add('hidden');
  if (auth) auth.classList.remove('hidden');
}

function showApp() {
  const auth = $('#authView');
  const app = $('#appView');
  if (auth) auth.classList.add('hidden');
  if (app) app.classList.remove('hidden');
}

function setAuthMode(mode) {
  state.authMode = mode;
  $$('.auth-tab').forEach(function (button) {
    button.classList.toggle('active', button.dataset.authMode === mode);
  });
  const displayName = $('#displayNameWrap');
  const submit = $('#authSubmit');
  const password = $('#password');
  const message = $('#authMessage');
  if (displayName) displayName.classList.toggle('hidden', mode !== 'register');
  if (submit) submit.textContent = mode === 'register' ? 'Создать аккаунт' : 'Войти';
  if (password) password.autocomplete = mode === 'register' ? 'new-password' : 'current-password';
  if (message) message.textContent = '';
}

async function submitAuth(event) {
  event.preventDefault();
  const message = $('#authMessage');
  if (message) message.textContent = '';
  const payload = {
    username: $('#username') ? $('#username').value.trim() : '',
    password: $('#password') ? $('#password').value : '',
    display_name: $('#displayName') ? ($('#displayName').value.trim() || null) : null,
    department: $('#department') ? ($('#department').value.trim() || null) : null
  };
  const endpoint = state.authMode === 'register' ? '/api/register' : '/api/login';
  try {
    const submit = $('#authSubmit');
    if (submit) submit.disabled = true;
    const result = await api(endpoint, {method: 'POST', body: JSON.stringify(payload)});
    state.user = result.user;
    state.language = result.user.preferred_language || 'chinese';
    showApp();
    await loadLanguage();
    await setView('home');
  } catch (error) {
    if (message) message.textContent = error.message;
  } finally {
    const submit = $('#authSubmit');
    if (submit) submit.disabled = false;
  }
}

async function boot() {
  bindStaticEvents();
  try {
    state.meta = await api('/api/meta');
  } catch (_) {
    state.meta = {auth_mode:'local', registration_enabled:true};
  }
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
  const oidcLogin = $('#oidcLogin');
  const authForm = $('#authForm');
  const authTabs = $('#authTabs');
  if (oidcLogin) oidcLogin.classList.toggle('hidden', !oidc);
  if (authForm) authForm.classList.toggle('hidden', oidc);
  if (authTabs) authTabs.classList.toggle('hidden', oidc);
  const registerTab = $('[data-auth-mode="register"]');
  if (registerTab) registerTab.classList.toggle('hidden', !meta.registration_enabled);
  if (!meta.registration_enabled && state.authMode === 'register') setAuthMode('login');
}

function bindStaticEvents() {
  if (bindStaticEvents.installed) return;
  bindStaticEvents.installed = true;

  $$('.auth-tab').forEach(function (button) {
    button.addEventListener('click', function () { setAuthMode(button.dataset.authMode); });
  });

  const authForm = $('#authForm');
  if (authForm) authForm.addEventListener('submit', submitAuth);
  const oidcLogin = $('#oidcLogin');
  if (oidcLogin) oidcLogin.addEventListener('click', function () {
    window.location.href = '/api/auth/oidc/login';
  });

  const logout = $('#logoutButton');
  if (logout) logout.addEventListener('click', async function () {
    try { await api('/api/logout', {method: 'POST'}); } catch (_) {}
    state.user = null;
    showAuth();
  });

  const menu = $('#menuToggle');
  if (menu) menu.addEventListener('click', function () {
    const sidebar = $('#sidebar');
    const backdrop = $('#backdrop');
    if (sidebar) sidebar.classList.toggle('open');
    if (backdrop) backdrop.classList.toggle('hidden');
  });
  const backdrop = $('#backdrop');
  if (backdrop) backdrop.addEventListener('click', closeMenu);

  const main = $('#main');
  if (main) main.addEventListener('click', delegatedAudioClick);
}

function closeMenu() {
  const sidebar = $('#sidebar');
  const backdrop = $('#backdrop');
  if (sidebar) sidebar.classList.remove('open');
  if (backdrop) backdrop.classList.add('hidden');
}

async function delegatedAudioClick(event) {
  const speak = event.target && event.target.closest ? event.target.closest('[data-speak-text]') : null;
  if (!speak) return;
  const original = speak.textContent;
  speak.disabled = true;
  speak.textContent = '…';
  try {
    await playPronunciation(
      speak.dataset.speakText,
      Number(speak.dataset.speakRate || .9),
      speak.dataset.speakLanguage || state.language
    );
  } finally {
    speak.disabled = false;
    speak.textContent = original;
  }
}

async function loadLanguage() {
  const values = await Promise.all([
    api('/api/language/' + state.language + '/summary'),
    api('/api/language/' + state.language + '/topics'),
    api('/api/gamification/me'),
    api('/api/notifications/pending'),
    api('/api/learning/preferences'),
    api('/api/pronunciation/status').catch(function () {
      return {server_available:false,engine:'browser-fallback'};
    }),
    api('/api/pilot/me').catch(function () {
      return {
        features:{},
        groups:[],
        assignments:[],
        chinese_standard:{name:'Путунхуа (普通话)',label:'стандартный китайский'}
      };
    })
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
  if (xpPill && state.gamification) xpPill.textContent = state.gamification.spendable_xp + ' XP';
  const adminNav = $('#adminNav');
  if (adminNav) adminNav.classList.toggle('hidden', !state.user || !['admin','editor'].includes(state.user.role));
  const managerNav = $('#managerNav');
  if (managerNav) managerNav.classList.toggle('hidden', !state.user || state.user.role !== 'manager');
  updateLearningControls();
  maybeBrowserNudge();
}

function featureEnabled(key) {
  const flags = (state.pilot && state.pilot.features) || {};
  return flags[key] !== false;
}

function applyFeatureVisibility() {
  $$('[data-view="games"]').forEach(function (node) {
    node.classList.toggle('hidden', !featureEnabled('games'));
  });
  $$('[data-view="xp"]').forEach(function (node) {
    node.classList.toggle('hidden', !featureEnabled('xp_economy'));
  });
  $$('[data-view="notifications"]').forEach(function (node) {
    node.classList.toggle('hidden', !featureEnabled('learning_nudges'));
  });
  $$('[data-view="assistant"]').forEach(function (node) {
    node.classList.toggle('hidden', !featureEnabled('ai_assistant'));
  });
  const pill = $('#xpPill');
  if (pill) pill.classList.toggle('hidden', !featureEnabled('xp_economy'));
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

function maybeBrowserNudge() {
  if (!state.nudges.length || !state.notificationSettings || !state.notificationSettings.browser_enabled) return;
  if (!('Notification' in window) || Notification.permission !== 'granted') return;
  const item = state.nudges[0];
  try {
    new Notification(item.title, {body: item.body, tag: 'mgc-learning-nudge'});
  } catch (_) {}
}

function modularOwner(view) {
  const frontend = window.MGCFrontend;
  if (!frontend) return null;
  const names = [
    'learning',
    'practice-games',
    'support-notifications',
    'assistant-knowledge',
    'final-assessment',
    'chinese-reference',
    'manager-admin'
  ];
  for (const name of names) {
    if (!frontend.has(name)) continue;
    const module = frontend.get(name);
    if (module && typeof module.owns === 'function' && module.owns(view)) return module;
  }
  return null;
}

async function setView(view) {
  const target = String(view || 'home');
  const owner = modularOwner(target);
  if (!owner || typeof owner.navigate !== 'function') {
    throw new Error('Нет модульного владельца раздела: ' + target);
  }
  return owner.navigate(target);
}

function chineseStandardBannerHTML() {
  return '<section class="putonghua-learning-banner"><div class="putonghua-learning-icon">普</div><div><b>' +
    'Вы изучаете Путунхуа (普通话)</b><span>Стандартный китайский для школы, работы и общения между регионами Китая.' +
    '</span></div><small>Диалекты в разделе «Информация о китайском» — только справка, их не нужно учить.</small></section>';
}

function ensureChineseStandardBanner() {
  if (state.language !== 'chinese') return;
  const learningViews = new Set(['home','topics','quiz','roleplay','course30','exam','games']);
  if (!learningViews.has(state.view) || $('#main .putonghua-learning-banner')) return;
  const main = $('#main');
  if (main) main.insertAdjacentHTML('afterbegin', chineseStandardBannerHTML());
}

function newSessionId(prefix) {
  if (window.crypto && crypto.randomUUID) return prefix + '-' + crypto.randomUUID();
  return prefix + '-' + Date.now() + '-' + Math.random().toString(36).slice(2);
}

async function submitPractice(kind, sessionId, score, total, topic) {
  if (!sessionId) return null;
  try {
    const result = await api('/api/practice/result', {
      method:'POST',
      body: JSON.stringify({
        session_id:sessionId,
        kind:kind,
        language:state.language,
        topic:topic || '',
        score:score,
        total:total
      })
    });
    if (result.profile) {
      state.gamification = result.profile;
      const pill = $('#xpPill');
      if (pill) pill.textContent = state.gamification.spendable_xp + ' XP';
    }
    if (result.awarded) toast('+' + result.awarded + ' XP');
    return result;
  } catch (_) {
    return null;
  }
}

function browserSpeak(text, rate, language) {
  if (!('speechSynthesis' in window)) throw new Error('В браузере нет SpeechSynthesis');
  speechSynthesis.cancel();
  const utter = new SpeechSynthesisUtterance(text);
  const langTag = language === 'chinese' ? 'zh-CN' : 'en-US';
  utter.lang = langTag;
  utter.rate = rate || .9;
  const voices = speechSynthesis.getVoices ? speechSynthesis.getVoices() : [];
  const exact = voices.find(function (voice) {
    return String(voice.lang || '').toLowerCase() === langTag.toLowerCase();
  });
  const family = voices.find(function (voice) {
    return String(voice.lang || '').toLowerCase().startsWith(language === 'chinese' ? 'zh' : 'en');
  });
  if (exact || family) utter.voice = exact || family;
  speechSynthesis.speak(utter);
}

async function playPronunciation(text, rate, language) {
  const lang = language || state.language;
  const speed = rate || .9;
  if (!text) return;

  if (state.activeAudio) {
    try { state.activeAudio.pause(); } catch (_) {}
    state.activeAudio = null;
  }
  if (state.activeAudioUrl) {
    try { URL.revokeObjectURL(state.activeAudioUrl); } catch (_) {}
    state.activeAudioUrl = null;
  }
  if (state.activeAudioController) {
    try { state.activeAudioController.abort(); } catch (_) {}
    state.activeAudioController = null;
  }

  const serverAllowed = featureEnabled('server_audio') &&
    (!state.learningPrefs || state.learningPrefs.server_audio_enabled !== false);
  if (serverAllowed && (!state.pronunciationStatus || state.pronunciationStatus.server_available !== false)) {
    const controller = new AbortController();
    state.activeAudioController = controller;
    const timer = setTimeout(function () { controller.abort(); }, 6000);
    try {
      const csrf = cookieValue('mgc_csrf');
      const headers = {'Content-Type':'application/json'};
      if (csrf) headers['X-CSRF-Token'] = csrf;
      const response = await fetch('/api/pronunciation/audio', {
        method:'POST',
        credentials:'same-origin',
        headers:headers,
        body:JSON.stringify({language:lang, rate:speed, text:text}),
        signal:controller.signal
      });
      if (response.ok) {
        const blob = await response.blob();
        if (!String(blob.type || '').startsWith('audio/')) throw new Error('invalid audio response');
        const url = URL.createObjectURL(blob);
        const audio = new Audio(url);
        audio.preload = 'auto';
        state.activeAudio = audio;
        state.activeAudioUrl = url;
        const cleanup = function () {
          if (state.activeAudioUrl === url) {
            URL.revokeObjectURL(url);
            state.activeAudioUrl = null;
            state.activeAudio = null;
          }
        };
        audio.addEventListener('ended', cleanup, {once:true});
        audio.addEventListener('error', cleanup, {once:true});
        await audio.play();
        return;
      }
    } catch (_) {
      // Server audio is optional; browser speech is the deliberate fallback.
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

document.addEventListener('DOMContentLoaded', boot);
