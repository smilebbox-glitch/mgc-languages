/* v6.0.15: retire app.js globals whose active views are fully modular. */
(function (root) {
  'use strict';

  const frontend = root.MGCFrontend;
  if (!frontend) throw new Error('MGCFrontend runtime is missing');
  if (frontend.has('legacy-retirement')) return;

  const REQUIRED_OWNERS = Object.freeze([
    'learning',
    'practice-games',
    'support-notifications',
    'assistant-knowledge',
    'final-assessment',
    'content-governance',
    'admin-ops',
    'admin-analytics',
    'manager-admin',
    'chinese-reference'
  ]);

  const RETIRED_GLOBALS = Object.freeze([
    'renderHome',
    'renderTopics',
    'renderQuiz',
    'startQuiz',
    'answerQuiz',
    'buyQuizHelp',
    'renderCourse30',
    'makePairOptions',
    'answerPair',
    'renderDayQuiz',
    'answerDayQuiz',
    'scenarioProgressKey',
    'getScenarioProgress',
    'saveScenarioProgress',
    'renderRoleplay',
    'answerScenario',
    'renderGames',
    'startGame',
    'renderXP',
    'renderXpPack',
    'buyReward',
    'xpPanelHTML',
    'refreshGamification',
    'renderNotifications',
    'saveNudgeSettings',
    'renderAssistant',
    'askAssistant',
    'renderKnowledge',
    'renderExam',
    'startExam',
    'answerExam',
    'renderManager',
    'openManagerUser',
    'renderAdmin',
    'itDashboardHTML',
    'pilotGovernanceHTML',
    'bindPilotGovernance',
    'learningErrorTelemetryHTML',
    'bindITDashboard',
    'questionQualityHTML',
    'adminTermCard',
    'adminContentHTML',
    'bindAdminContent',
    'openAdminUser',
    'toneLabStart',
    'renderToneLabRound',
    'renderChineseBasics'
  ]);

  const missingOwners = REQUIRED_OWNERS.filter(function (name) { return !frontend.has(name); });
  if (missingOwners.length) {
    throw new Error('Cannot retire legacy frontend before modular owners load: ' + missingOwners.join(', '));
  }

  const present = [];
  RETIRED_GLOBALS.forEach(function (name) {
    if (typeof root[name] === 'function') present.push(name);
    root[name] = undefined;
  });

  frontend.register('legacy-retirement', {
    retired: RETIRED_GLOBALS,
    presentAtRetirement: Object.freeze(present.slice()),
    remainingBridgeSurface: frontend.get('legacy-app').surface,
    isRetired: function (name) {
      return RETIRED_GLOBALS.includes(String(name || '')) && typeof root[String(name || '')] !== 'function';
    }
  });
})(typeof window !== 'undefined' ? window : globalThis);
