/* v6.0.20: validate modular frontend core and publish pilot readiness. */
(function () {
  'use strict';

  const frontend = window.MGCFrontend;
  if (!frontend) throw new Error('MGCFrontend runtime is missing');

  try {
    const requiredModules = [
      'error-boundary',
      'legacy-app',
      'service-status',
      'api-client',
      'app-state',
      'pilot-home',
      'learning',
      'game-lab-v618',
      'game-engagement-v618',
      'factory-journey-v619',
      'arcade-missions-v620',
      'arcade-mastery-v620',
      'practice-games',
      'support-notifications',
      'assistant-knowledge',
      'final-assessment',
      'chinese-reference',
      'content-governance',
      'admin-ops',
      'admin-analytics',
      'manager-admin',
      'legacy-retirement',
      'navigation',
      'session-lifecycle',
      'auth-department'
    ];
    const missingModules = requiredModules.filter(function (name) { return !frontend.has(name); });
    if (missingModules.length) {
      throw new Error('Frontend modules missing: ' + missingModules.join(', '));
    }

    const requiredDomIds = [
      'authView', 'authForm', 'username', 'department', 'password',
      'appView', 'main', 'sidebar', 'logoutButton', 'toast'
    ];
    const missingDom = requiredDomIds.filter(function (id) { return !document.getElementById(id); });
    if (missingDom.length) throw new Error('Frontend DOM contract missing: ' + missingDom.join(', '));

    frontend.markReady();
    frontend.get('error-boundary').reconcile();
    document.dispatchEvent(new CustomEvent('mgc:frontend-ready', {
      detail: {version: frontend.version, modules: frontend.list(), pilotCandidate: 'v6.0.20'}
    }));
  } catch (error) {
    const message = frontend.fail(error);
    const main = document.getElementById('main');
    if (main) {
      main.innerHTML = '<div class="card"><h2>Не удалось загрузить интерфейс</h2><p>' +
        String(message).replace(/[&<>"']/g, function (char) {
          return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[char];
        }) + '</p></div>';
    }
    throw error;
  }
})();
