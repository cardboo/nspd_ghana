/**
 * NSPD Ghana — applicant portal auth pages.
 * One script serves portal-register.html, portal-login.html, and
 * verify.html (it wires up whichever forms exist on the page).
 */
(function () {

  function showBox(id, message) {
    var box = document.getElementById(id);
    if (!box) return;
    box.textContent = message;
    box.style.display = '';
  }

  function hideBox(id) {
    var box = document.getElementById(id);
    if (box) box.style.display = 'none';
  }

  function detailText(data, fallback) {
    var detail = data && data.detail;
    if (Array.isArray(detail)) {
      return detail.map(function (d) { return d.msg; }).join('; ');
    }
    return detail || fallback;
  }

  // ── Registration page ──
  var registerForm = document.getElementById('registerForm');
  if (registerForm) {
    registerForm.addEventListener('submit', function (e) {
      e.preventDefault();
      hideBox('registerError');
      hideBox('registerSuccess');

      var password = document.getElementById('password').value;
      if (password !== document.getElementById('confirmPassword').value) {
        showBox('registerError', 'Passwords do not match.');
        return;
      }

      fetch('/api/portal/register', {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          full_name: document.getElementById('fullName').value.trim(),
          email: document.getElementById('email').value.trim(),
          password: password
        })
      })
        .then(function (response) {
          return response.json().catch(function () { return {}; }).then(function (data) {
            if (!response.ok) {
              throw new Error(detailText(data, 'Registration failed'));
            }
            registerForm.style.display = 'none';
            if (data.verification_required) {
              showBox('registerSuccess',
                'Account created. Please check your email for a verification link before signing in.');
            } else {
              showBox('registerSuccess', 'Account created. Redirecting to sign in...');
              setTimeout(function () { window.location.href = 'portal-login.html'; }, 1500);
            }
          });
        })
        .catch(function (error) {
          showBox('registerError', error.message || 'Registration failed.');
        });
    });
  }

  // ── Login page ──
  var loginForm = document.getElementById('portalLoginForm');
  if (loginForm) {
    // Already signed in? Straight to the portal.
    fetch('/api/portal/me', { credentials: 'same-origin' })
      .then(function (response) {
        if (response.ok) window.location.href = 'portal.html';
      })
      .catch(function () {});

    loginForm.addEventListener('submit', function (e) {
      e.preventDefault();
      hideBox('loginError');
      hideBox('resendBox');

      fetch('/api/portal/login', {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: document.getElementById('email').value.trim(),
          password: document.getElementById('password').value
        })
      })
        .then(function (response) {
          return response.json().catch(function () { return {}; }).then(function (data) {
            if (!response.ok) {
              // Unverified email -> offer to resend the verification link
              if (response.status === 403) {
                var resendBox = document.getElementById('resendBox');
                if (resendBox) resendBox.style.display = '';
              }
              throw new Error(detailText(data, 'Invalid email or password'));
            }
            window.location.href = 'portal.html';
          });
        })
        .catch(function (error) {
          showBox('loginError', error.message || 'Sign in failed.');
        });
    });

    var resendLink = document.getElementById('resendLink');
    if (resendLink) {
      resendLink.addEventListener('click', function (e) {
        e.preventDefault();
        fetch('/api/portal/resend-verification', {
          method: 'POST',
          credentials: 'same-origin',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email: document.getElementById('email').value.trim() })
        })
          .then(function (response) {
            return response.json().catch(function () { return {}; }).then(function (data) {
              hideBox('loginError');
              document.getElementById('resendBox').textContent =
                data.message || 'If the account exists, a new verification link has been sent.';
            });
          })
          .catch(function () {
            showBox('loginError', 'Could not resend the verification email.');
          });
      });
    }
  }

  // ── Verify page ──
  var verifyStatus = document.getElementById('verifyStatus');
  if (verifyStatus) {
    var token = new URLSearchParams(window.location.search).get('token') || '';
    fetch('/api/portal/verify?token=' + encodeURIComponent(token), { credentials: 'same-origin' })
      .then(function (response) {
        return response.json().catch(function () { return {}; }).then(function (data) {
          if (!response.ok) {
            verifyStatus.className = 'alert alert-danger';
            verifyStatus.textContent = detailText(data, 'Verification failed.');
            return;
          }
          verifyStatus.textContent = data.message || 'Email verified. You can now sign in.';
        });
      })
      .catch(function () {
        verifyStatus.className = 'alert alert-danger';
        verifyStatus.textContent = 'Verification failed. Please try again.';
      });
  }
})();
