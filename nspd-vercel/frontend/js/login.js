/**
 * NSPD Ghana — login page.
 *
 * Replaces the PHP form-POST in login.php with a fetch() call to
 * POST /api/auth/login. The CSRF hidden field is no longer needed: the
 * API only accepts JSON bodies and the auth cookie is SameSite=Strict,
 * which blocks cross-site form submissions by design.
 */
(function () {
  // If already logged in, redirect to dashboard (mirrors login.php)
  fetch('/api/auth/me', { credentials: 'same-origin' })
    .then(function (response) {
      if (response.ok) window.location.href = 'dashboard.html';
    })
    .catch(function () {});

  var form = document.getElementById('loginForm');
  var errorBox = document.getElementById('loginError');
  var submitButton = form.querySelector('button[type="submit"]');
  var preAuthToken = null;

  function showError(message) {
    errorBox.textContent = message;
    errorBox.style.display = '';
  }

  function finishLogin(data) {
    var mustChange = data.user && data.user.must_change_password;
    window.location.href = mustChange ? 'account.html' : 'dashboard.html';
  }

  form.addEventListener('submit', function (e) {
    e.preventDefault();
    errorBox.style.display = 'none';
    submitButton.disabled = true;

    var username = document.getElementById('username').value;
    var password = document.getElementById('password').value;

    fetch('/api/auth/login', {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: username, password: password })
    })
      .then(function (response) {
        if (response.ok) {
          return response.json()
            .catch(function () { return {}; })
            .then(function (data) {
              // Two-factor accounts get a pre-auth token and a code step
              if (data.totp_required) {
                preAuthToken = data.pre_auth_token;
                form.style.display = 'none';
                document.getElementById('totpForm').style.display = '';
                document.getElementById('totpCode').focus();
                return;
              }
              finishLogin(data);
            });
        }
        return response.json()
          .catch(function () { return {}; })
          .then(function (data) {
            showError(data.detail || 'Invalid username or password');
          });
      })
      .catch(function () {
        showError('Unable to reach the server. Please try again.');
      })
      .then(function () {
        submitButton.disabled = false;
      });
  });

  // Two-factor code step
  document.getElementById('totpForm').addEventListener('submit', function (e) {
    e.preventDefault();
    errorBox.style.display = 'none';

    fetch('/api/auth/totp', {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        pre_auth_token: preAuthToken,
        code: document.getElementById('totpCode').value.trim()
      })
    })
      .then(function (response) {
        return response.json()
          .catch(function () { return {}; })
          .then(function (data) {
            if (!response.ok) {
              showError(data.detail || 'Invalid authentication code');
              // Expired pre-auth session -> back to the password step
              if (response.status === 401 && data.detail && data.detail.indexOf('expired') !== -1) {
                document.getElementById('totpForm').style.display = 'none';
                form.style.display = '';
              }
              return;
            }
            finishLogin(data);
          });
      })
      .catch(function () {
        showError('Unable to reach the server. Please try again.');
      });
  });
})();
