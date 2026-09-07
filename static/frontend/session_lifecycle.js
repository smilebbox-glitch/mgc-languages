/* v6.0.1: modular session bootstrap and logout lifecycle. */
(function () {
  'use strict';

  const frontend = window.MGCFrontend;
  if (!frontend) throw new Error('MGCFrontend runtime is missing');
  if (frontend.has('session-lifecycle')) return;

  const legacy = frontend.get('legacy-app');
  const apiClient = frontend.get('api-client');
  const appState = frontend.get('app-state');
  const navigation = frontend.get('navigation');

  async function bootstrap() {
    legacy.bindStaticEvents();

    let meta;
    try {
      meta = await apiClient.request('/api/meta');
    } catch (_) {
      meta = {auth_mode: 'local', registration_enabled: true};
    }
    appState.set('meta', meta);
    legacy.configureAuthUi();

    try {
      const user = await apiClient.request('/api/me');
      await navigation.enterUserSession(user);
    } catch (_) {
      navigation.showAuth();
    }
  }

  async function logout() {
    try {
      await apiClient.request('/api/logout', {method: 'POST'});
    } catch (_) {}
    navigation.leaveUserSession();
  }

  function installLogoutGuard() {
    const button = document.getElementById('logoutButton');
    if (!button) throw new Error('Session lifecycle missing logoutButton');
    button.addEventListener('click', function (event) {
      event.preventDefault();
      event.stopImmediatePropagation();
      void logout();
    }, true);
  }

  document.removeEventListener('DOMContentLoaded', legacy.boot);
  document.addEventListener('DOMContentLoaded', bootstrap, {once: true});
  installLogoutGuard();

  frontend.register('session-lifecycle', {
    bootstrap: bootstrap,
    logout: logout
  });
})();
