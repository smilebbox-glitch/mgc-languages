/* v6.0.13: isolate only the remaining shared app.js compatibility surface. */
(function () {
  'use strict';

  const frontend = window.MGCFrontend;
  if (!frontend) throw new Error('MGCFrontend runtime is missing');

  function requireFunction(name, value) {
    if (typeof value !== 'function') throw new Error('Frontend contract missing function: ' + name);
    return value;
  }

  if (typeof state === 'undefined' || !state) {
    throw new Error('Frontend contract missing state');
  }

  if (!frontend.has('legacy-app')) {
    const bridge = {
      getState: function () { return state; },
      boot: requireFunction('boot', boot),
      bindStaticEvents: requireFunction('bindStaticEvents', bindStaticEvents),
      configureAuthUi: requireFunction('configureAuthUi', configureAuthUi),
      setView: requireFunction('setView', setView),
      loadLanguage: requireFunction('loadLanguage', loadLanguage),
      showApp: requireFunction('showApp', showApp),
      showAuth: requireFunction('showAuth', showAuth),
      closeMenu: requireFunction('closeMenu', closeMenu),
      ensureChineseStandardBanner: requireFunction('ensureChineseStandardBanner', ensureChineseStandardBanner),
      renderLearningHome: requireFunction('renderHome', renderHome),
      renderLearningTopics: requireFunction('renderTopics', renderTopics),
      renderLearningQuiz: requireFunction('renderQuiz', renderQuiz),
      renderLearningCourse30: requireFunction('renderCourse30', renderCourse30),
      renderPracticeRoleplay: requireFunction('renderRoleplay', renderRoleplay),
      renderPracticeGames: requireFunction('renderGames', renderGames),
      renderPracticeXP: requireFunction('renderXP', renderXP),
      newSessionId: requireFunction('newSessionId', newSessionId),
      submitPractice: requireFunction('submitPractice', submitPractice),
      setServiceStatus: requireFunction('setServiceStatus', setServiceStatus),
      toast: requireFunction('toast', toast),
      escapeHtml: requireFunction('esc', esc),
      query: requireFunction('$', $),
      queryAll: requireFunction('$$', $$)
    };
    bridge.surface = Object.freeze(Object.keys(bridge));
    frontend.register('legacy-app', bridge);
  }
})();
