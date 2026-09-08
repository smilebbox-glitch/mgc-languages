/* v6.0.28: pilot UX hardening with batched DOM work and natural browser TTS. */
(function () {
  'use strict';

  const frontend = window.MGCFrontend;
  if (frontend && frontend.has && frontend.has('pilot-ux-hardening')) return;

  const PINYIN_FALLBACK = Object.freeze({
    '整车装配': 'zhěng chē zhuāng pèi',
    '总装': 'zǒng zhuāng',
    '总装线': 'zǒng zhuāng xiàn',
    '焊接': 'hàn jiē',
    '涂装': 'tú zhuāng',
    '冲压': 'chōng yā',
    '质量': 'zhì liàng',
    '物流': 'wù liú',
    '发动机': 'fā dòng jī',
    '变速箱': 'biàn sù xiāng',
    '底盘': 'dǐ pán',
    '车身': 'chē shēn'
  });

  const REMOVE_SELECTORS = Object.freeze([
    '.pilot-next-head blockquote',
    '.pilot-hero-quote',
    '.pilot-hero-message',
    '.pilot-quote-card'
  ]);

  const NATURAL_VOICE_NAME = /natural|neural|online|premium|enhanced|siri|aria|jenny|guy|ava|andrew|emma|brian|samantha|daniel|karen|moira|serena|xiaoxiao|xiaoyi|yunxi|yunyang|huihui|yaoyao|tingting|meijia|sinji|普通话|putonghua|mandarin|google us english/i;
  const ROBOTIC_VOICE_NAME = /espeak|festival|compact|robot|eloquence/i;
  const MIN_NATURAL_VOICE_SCORE = 72;
  const VOICE_CACHE = {items: [], ready: false};

  function cleanDecorativeCopy(root) {
    const scope = root && root.querySelectorAll ? root : document;
    REMOVE_SELECTORS.forEach(function (selector) {
      scope.querySelectorAll(selector).forEach(function (node) { node.remove(); });
    });
  }

  function fillMissingPinyin(root) {
    const scope = root && root.querySelectorAll ? root : document;
    scope.querySelectorAll('.game-question h2').forEach(function (heading) {
      const card = heading.closest('.game-question');
      if (!card || card.querySelector('.question-pinyin')) return;
      const term = String(heading.textContent || '').trim();
      const pinyin = PINYIN_FALLBACK[term];
      if (!pinyin) return;
      const line = document.createElement('div');
      line.className = 'question-pinyin pilot-pinyin-fallback';
      line.textContent = pinyin;
      heading.insertAdjacentElement('afterend', line);
    });
  }

  function applyDomFixes(root) {
    cleanDecorativeCopy(root);
    fillMissingPinyin(root);
  }

  const originalPlayPronunciation = typeof window.playPronunciation === 'function'
    ? window.playPronunciation
    : null;

  function normalizeLocale(value) {
    return String(value || '').trim().toLowerCase().replace('_', '-');
  }

  function voiceScore(voice, language) {
    const lang = normalizeLocale(voice && voice.lang);
    const name = String(voice && voice.name || '');
    const wanted = language === 'chinese' ? 'zh' : 'en';
    if (!lang.startsWith(wanted)) return -1000;

    let score = 24;
    if (language === 'chinese' && (lang === 'zh-cn' || lang === 'zh-hans-cn')) score += 38;
    if (language === 'english' && lang === 'en-us') score += 34;
    if (language === 'english' && /^en-(gb|au|ca)$/.test(lang)) score += 18;

    if (NATURAL_VOICE_NAME.test(name)) score += 92;
    if (/natural|neural|premium|enhanced/i.test(name)) score += 42;
    if (ROBOTIC_VOICE_NAME.test(name)) score -= 180;

    // A local OS/browser voice is preferred for privacy and usually has lower latency.
    if (voice && voice.localService === true) score += 34;
    else if (voice && voice.localService === false) score += 6;
    if (voice && voice.default) score += 8;
    return score;
  }

  function refreshVoiceCache() {
    if (!('speechSynthesis' in window) || typeof speechSynthesis.getVoices !== 'function') {
      VOICE_CACHE.items = [];
      VOICE_CACHE.ready = true;
      return VOICE_CACHE.items;
    }
    VOICE_CACHE.items = speechSynthesis.getVoices() || [];
    VOICE_CACHE.ready = VOICE_CACHE.items.length > 0;
    return VOICE_CACHE.items;
  }

  function availableVoices() {
    if (VOICE_CACHE.ready && VOICE_CACHE.items.length) return VOICE_CACHE.items;
    return refreshVoiceCache();
  }

  function waitForVoices() {
    const immediate = availableVoices();
    if (immediate.length) return Promise.resolve(immediate);
    return new Promise(function (resolve) {
      let settled = false;
      const finish = function () {
        if (settled) return;
        settled = true;
        if ('speechSynthesis' in window) speechSynthesis.removeEventListener('voiceschanged', finish);
        resolve(refreshVoiceCache());
      };
      if ('speechSynthesis' in window) speechSynthesis.addEventListener('voiceschanged', finish, {once:true});
      setTimeout(finish, 450);
    });
  }

  function naturalRate(requestedRate, language) {
    const requested = Number(requestedRate || 0.9);
    if (requested <= 0.75) return Math.max(0.62, Math.min(0.76, requested));
    if (language === 'chinese') return Math.max(0.84, Math.min(0.98, requested * 1.01));
    return Math.max(0.88, Math.min(1.03, requested * 1.04));
  }

  function selectNaturalVoice(voices, language) {
    const ranked = voices
      .map(function (voice) { return {voice: voice, score: voiceScore(voice, language)}; })
      .filter(function (item) { return item.score >= MIN_NATURAL_VOICE_SCORE; })
      .sort(function (a, b) {
        if (b.score !== a.score) return b.score - a.score;
        if (Boolean(a.voice.localService) !== Boolean(b.voice.localService)) return a.voice.localService ? -1 : 1;
        return String(a.voice.name || '').localeCompare(String(b.voice.name || ''));
      });
    return ranked.length ? ranked[0].voice : null;
  }

  async function speakNaturally(text, rate, language) {
    if (!text || !('speechSynthesis' in window) || typeof window.SpeechSynthesisUtterance !== 'function') return false;
    const voices = await waitForVoices();
    const voice = selectNaturalVoice(voices, language);
    if (!voice) return false;

    return new Promise(function (resolve) {
      try {
        speechSynthesis.cancel();
        const utterance = new SpeechSynthesisUtterance(String(text));
        utterance.lang = language === 'chinese' ? 'zh-CN' : 'en-US';
        utterance.voice = voice;
        utterance.rate = naturalRate(rate, language);
        utterance.pitch = 1.0;
        utterance.volume = 1;
        utterance.onend = function () { resolve(true); };
        utterance.onerror = function () { resolve(false); };
        speechSynthesis.speak(utterance);
      } catch (_) {
        resolve(false);
      }
    });
  }

  if ('speechSynthesis' in window) {
    refreshVoiceCache();
    speechSynthesis.addEventListener('voiceschanged', refreshVoiceCache);
  }

  if (originalPlayPronunciation) {
    window.playPronunciation = async function (text, rate, language) {
      const normalizedLanguage = language === 'chinese' ? 'chinese' : 'english';
      const natural = await speakNaturally(text, rate, normalizedLanguage);
      if (natural) return;
      // Keep the frozen offline eSpeak/eSpeak-NG path as the reliable fallback.
      return originalPlayPronunciation(text, rate, language);
    };
  }

  const pendingRoots = new Set();
  let domFrame = 0;

  function flushDomFixes() {
    domFrame = 0;
    const roots = Array.from(pendingRoots);
    pendingRoots.clear();
    roots.forEach(function (node) {
      if (node && node.isConnected !== false) applyDomFixes(node);
    });
  }

  function queueDomFixes(node) {
    if (!node || node.nodeType !== 1) return;
    pendingRoots.add(node);
    if (domFrame) return;
    if (window.requestAnimationFrame) domFrame = window.requestAnimationFrame(flushDomFixes);
    else domFrame = window.setTimeout(flushDomFixes, 0);
  }

  const observer = new MutationObserver(function (mutations) {
    mutations.forEach(function (mutation) {
      mutation.addedNodes.forEach(function (node) { queueDomFixes(node); });
    });
  });

  if (document.documentElement) {
    observer.observe(document.documentElement, {childList:true, subtree:true});
    applyDomFixes(document);
  }

  if (frontend && frontend.register) {
    frontend.register('pilot-ux-hardening', {
      owns: function () { return false; },
      apply: applyDomFixes,
      queue: queueDomFixes,
      pinyinFallback: PINYIN_FALLBACK
    });
  }
})();