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

  function showError(message) {
    errorBox.textContent = message;
    errorBox.style.display = '';
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
              var mustChange = data.user && data.user.must_change_password;
              window.location.href = mustChange ? 'account.html' : 'dashboard.html';
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
})();
