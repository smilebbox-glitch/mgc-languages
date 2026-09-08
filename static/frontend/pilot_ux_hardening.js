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

  function voiceScore(voice, language) {
    const lang = String(voice && voice.lang || '').toLowerCase();
    const name = String(voice && voice.name || '').toLowerCase();
    const wanted = language === 'chinese' ? 'zh' : 'en';
    if (!lang.startsWith(wanted)) return -1000;

    let score = 20;
    if (language === 'chinese' && (lang === 'zh-cn' || lang === 'zh-hans-cn')) score += 35;
    if (language === 'english' && lang === 'en-us') score += 30;
    if (/natural|neural|online|premium/.test(name)) score += 90;

    if (language === 'chinese' && /xiaoxiao|xiaoyi|yunxi|yunyang|huihui|yaoyao|tingting|普通话|putonghua|mandarin/.test(name)) score += 55;
    if (language === 'english' && /aria|jenny|guy|ava|andrew|emma|brian|samantha|google us english/.test(name)) score += 55;

    if (/espeak|festival|compact|robot/.test(name)) score -= 140;
    if (voice && voice.localService === false) score += 8;
    if (voice && voice.default) score += 4;
    return score;
  }

  function availableVoices() {
    if (!('speechSynthesis' in window) || typeof speechSynthesis.getVoices !== 'function') return [];
    return speechSynthesis.getVoices() || [];
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
        resolve(availableVoices());
      };
      if ('speechSynthesis' in window) speechSynthesis.addEventListener('voiceschanged', finish, {once:true});
      setTimeout(finish, 350);
    });
  }

  async function speakNaturally(text, rate, language) {
    if (!text || !('speechSynthesis' in window) || typeof window.SpeechSynthesisUtterance !== 'function') return false;
    const voices = await waitForVoices();
    const ranked = voices
      .map(function (voice) { return {voice: voice, score: voiceScore(voice, language)}; })
      .filter(function (item) { return item.score > 0; })
      .sort(function (a, b) { return b.score - a.score; });
    if (!ranked.length) return false;

    return new Promise(function (resolve) {
      try {
        speechSynthesis.cancel();
        const utterance = new SpeechSynthesisUtterance(String(text));
        utterance.lang = language === 'chinese' ? 'zh-CN' : 'en-US';
        utterance.voice = ranked[0].voice;
        const requested = Number(rate || 0.9);
        utterance.rate = Math.max(0.72, Math.min(1.08, requested || 0.9));
        utterance.pitch = language === 'chinese' ? 1.02 : 1.0;
        utterance.volume = 1;
        utterance.onend = function () { resolve(true); };
        utterance.onerror = function () { resolve(false); };
        speechSynthesis.speak(utterance);
      } catch (_) {
        resolve(false);
      }
    });
  }

  if (originalPlayPronunciation) {
    window.playPronunciation = async function (text, rate, language) {
      const normalizedLanguage = language === 'chinese' ? 'chinese' : 'english';
      const natural = await speakNaturally(text, rate, normalizedLanguage);
      if (natural) return;
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
