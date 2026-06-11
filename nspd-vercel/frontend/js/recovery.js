/**
 * NSPD Ghana — password recovery pages (staff and applicant realms).
 *
 * Both forgot-password.html and reset-password.html include this script.
 * The realm comes from the `for` query parameter (`staff` or `portal`,
 * defaulting to portal) and decides which API endpoints and login page
 * are used.
 */
(function () {
  var params = new URLSearchParams(window.location.search);
  var realm = params.get('for') === 'staff' ? 'staff' : 'portal';

  var endpoints = realm === 'staff'
    ? { forgot: '/api/auth/forgot-password', reset: '/api/auth/reset-password', login: 'login.html' }
    : { forgot: '/api/portal/forgot-password', reset: '/api/portal/reset-password', login: 'portal-login.html' };

  var backLink = document.getElementById('backToLogin');
  if (backLink) backLink.href = endpoints.login;

  function show(id, message) {
    var box = document.getElementById(id);
    box.textContent = message;
    box.style.display = '';
  }

  function hide(id) {
    document.getElementById(id).style.display = 'none';
  }

  function detailText(data, fallback) {
    var detail = data && data.detail;
    if (Array.isArray(detail)) {
      return detail.map(function (d) { return d.msg; }).join('; ');
    }
    return detail || fallback;
  }

  // ── Forgot-password page ──
  var forgotForm = document.getElementById('forgotForm');
  if (forgotForm) {
    if (realm === 'staff') {
      document.getElementById('realmSubtitle').textContent = 'Staff password reset';
      document.getElementById('identifierLabel').textContent = 'Username or email';
    } else {
      document.getElementById('realmSubtitle').textContent = 'Seafarer portal password reset';
      document.getElementById('identifierLabel').textContent = 'Email address';
    }

    forgotForm.addEventListener('submit', function (e) {
      e.preventDefault();
      hide('forgotError');
      hide('forgotSuccess');

      fetch(endpoints.forgot, {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ identifier: document.getElementById('identifier').value.trim() })
      })
        .then(function (response) {
          return response.json().catch(function () { return {}; }).then(function (data) {
            if (!response.ok) {
              throw new Error(detailText(data, 'Request failed'));
            }
            forgotForm.style.display = 'none';
            show('forgotSuccess', data.message || 'If the account exists, a reset link has been sent.');
          });
        })
        .catch(function (error) {
          show('forgotError', error.message || 'Request failed. Please try again.');
        });
    });
  }

  // ── Reset-password page ──
  var resetForm = document.getElementById('resetForm');
  if (resetForm) {
    var token = params.get('token') || '';
    if (!token) {
      resetForm.style.display = 'none';
      show('resetError', 'This reset link is invalid. Please request a new one.');
      return;
    }

    resetForm.addEventListener('submit', function (e) {
      e.preventDefault();
      hide('resetError');
      hide('resetSuccess');

      var newPassword = document.getElementById('newPassword').value;
      if (newPassword !== document.getElementById('confirmPassword').value) {
        show('resetError', 'Passwords do not match.');
        return;
      }

      fetch(endpoints.reset, {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token: token, new_password: newPassword })
      })
        .then(function (response) {
          return response.json().catch(function () { return {}; }).then(function (data) {
            if (!response.ok) {
              throw new Error(detailText(data, 'Reset failed'));
            }
            resetForm.style.display = 'none';
            show('resetSuccess', (data.message || 'Password reset.') + ' Redirecting to sign in...');
            setTimeout(function () { window.location.href = endpoints.login; }, 2000);
          });
        })
        .catch(function (error) {
          show('resetError', error.message || 'Reset failed. The link may have expired.');
        });
    });
  }
})();
