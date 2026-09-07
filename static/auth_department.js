/* v5.9.7: department-aware auth UI layered over the legacy frontend bundle. */
(function () {
  'use strict';

  document.addEventListener('DOMContentLoaded', function () {
    const form = document.querySelector('#authForm');
    const department = document.querySelector('#department');
    const username = document.querySelector('#username');
    if (!form || !department || !username) return;

    username.addEventListener('input', function () {
      if (username.value.trim().toLowerCase() === 'admin' && !department.value) {
        department.value = 'Администрация';
      }
    });

    /*
     * Capture phase intentionally runs before the historical bubble listener
     * installed by static/app.js. This lets v5.9.7 add department without a
     * risky whole-file rewrite of the large frontend bundle.
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

      const payload = {
        username: username.value.trim(),
        password: document.querySelector('#password').value,
        display_name: document.querySelector('#displayName').value.trim() || null,
        department: selectedDepartment
      };
      const endpoint = state.authMode === 'register' ? '/api/register' : '/api/login';

      try {
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
        if (submit) submit.disabled = false;
      }
    }, true);
  });
})();
