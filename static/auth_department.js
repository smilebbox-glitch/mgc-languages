/* v5.9.9: department-aware auth module registered through MGCFrontend. */
(function () {
  'use strict';

  let installed = false;

  function install() {
    if (installed) return;
    const form = document.querySelector('#authForm');
    const department = document.querySelector('#department');
    const username = document.querySelector('#username');
    if (!form || !department || !username) return;
    installed = true;

    username.addEventListener('input', function () {
      if (username.value.trim().toLowerCase() === 'admin' && !department.value) {
        department.value = 'Администрация';
      }
    });

    /*
     * Capture phase intentionally runs before the historical bubble listener
     * installed by static/app.js. Department therefore stays isolated from the
     * large legacy bundle while preserving the existing auth flow.
     */
    form.addEventListener('submit', async function (event) {
      event.preventDefault();
      event.stopImmediatePropagation();

      const message = document.querySelector('#authMessage');
      const submit = document.querySelector('#authSubmit');
      if (message) message.textContent = '';

      const selectedDepartment = department.value.trim();
      if (!selectedDepartment) {
        if (message) message.textContent = 'Выберите отдел';
        department.focus();
        return;
      }

      const legacy = window.MGCFrontend && window.MGCFrontend.has('legacy-app')
        ? window.MGCFrontend.get('legacy-app')
        : null;
      const request = legacy ? legacy.api : api;
      const currentState = legacy ? legacy.getState() : state;
      const payload = {
        username: username.value.trim(),
        password: document.querySelector('#password').value,
        display_name: document.querySelector('#displayName').value.trim() || null,
        department: selectedDepartment
      };
      const endpoint = currentState.authMode === 'register' ? '/api/register' : '/api/login';

      try {
        if (submit) submit.disabled = true;
        const result = await request(endpoint, {method: 'POST', body: JSON.stringify(payload)});
        currentState.user = result.user;
        currentState.language = result.user.preferred_language || 'chinese';
        if (legacy) {
          legacy.showApp();
          await legacy.loadLanguage();
          await legacy.setView('home');
        } else {
          showApp();
          await loadLanguage();
          await setView('home');
        }
      } catch (error) {
        if (message) message.textContent = error.message;
      } finally {
        if (submit) submit.disabled = false;
      }
    }, true);
  }

  const moduleApi = Object.freeze({install: install});
  if (window.MGCFrontend && !window.MGCFrontend.has('auth-department')) {
    window.MGCFrontend.register('auth-department', moduleApi);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', install, {once: true});
  } else {
    install();
  }
})();
