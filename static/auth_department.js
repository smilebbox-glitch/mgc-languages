/* v6.0.0: department-aware auth module over frontend API/state/navigation core. */
(function () {
  'use strict';

  let installed = false;

  function install() {
    if (installed) return;
    const frontend = window.MGCFrontend;
    if (!frontend) throw new Error('MGCFrontend runtime is missing');
    for (const name of ['api-client', 'app-state', 'navigation']) {
      if (!frontend.has(name)) throw new Error('Auth frontend dependency is missing: ' + name);
    }

    const form = document.querySelector('#authForm');
    const department = document.querySelector('#department');
    const username = document.querySelector('#username');
    if (!form || !department || !username) return;
    installed = true;

    const apiClient = frontend.get('api-client');
    const appState = frontend.get('app-state');
    const navigation = frontend.get('navigation');

    username.addEventListener('input', function () {
      if (username.value.trim().toLowerCase() === 'admin' && !department.value) {
        department.value = 'Администрация';
      }
    });

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

      const payload = {
        username: username.value.trim(),
        password: document.querySelector('#password').value,
        display_name: document.querySelector('#displayName').value.trim() || null,
        department: selectedDepartment
      };
      const endpoint = appState.get('authMode') === 'register' ? '/api/register' : '/api/login';

      try {
        if (submit) submit.disabled = true;
        const result = await apiClient.request(endpoint, {
          method: 'POST',
          body: JSON.stringify(payload)
        });
        await navigation.enterUserSession(result.user);
      } catch (error) {
        if (message) message.textContent = error.message;
      } finally {
        if (submit) submit.disabled = false;
      }
    }, true);
  }

  const moduleApi = Object.freeze({install: install});
  if (!window.MGCFrontend) throw new Error('MGCFrontend runtime is missing');
  if (!window.MGCFrontend.has('auth-department')) {
    window.MGCFrontend.register('auth-department', moduleApi);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', install, {once: true});
  } else {
    install();
  }
})();
