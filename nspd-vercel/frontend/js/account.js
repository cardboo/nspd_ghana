/**
 * NSPD Ghana — my account page.
 * Profile from GET /api/account/profile; password change via
 * POST /api/account/password. Handles the forced-change flow for users
 * created with a temporary password.
 */
(function () {
  function detailItem(label, valueHtml) {
    return '<div class="detail-item">' +
      '<div class="detail-label">' + esc(label) + '</div>' +
      '<div class="detail-value">' + valueHtml + '</div>' +
    '</div>';
  }

  initLayout('account', 'My Account').then(function (user) {
    if (!user) return;

    if (user.must_change_password) {
      document.getElementById('forcedNotice').style.display = '';
    }

    API.json('/api/account/profile')
      .then(function (data) {
        var profile = data.user;
        var html = '';
        html += detailItem('Username', esc(profile.username));
        html += detailItem('Full Name', esc(profile.full_name));
        html += detailItem('Email', esc(profile.email));
        html += detailItem('Role', esc(profile.role));
        html += detailItem('Member Since', esc(fmtDateShort(profile.created_at)));
        if (profile.last_login) {
          html += detailItem('Last Login', esc(fmtDateLong(profile.last_login)));
        }
        document.getElementById('profileGrid').innerHTML = html;
        renderTotpState(profile.totp_enabled);
      })
      .catch(function (error) {
        console.error('Failed to load profile:', error);
      });

    // ── Two-factor authentication ──

    function totpShow(id, message) {
      var box = document.getElementById(id);
      box.textContent = message;
      box.style.display = '';
    }

    function totpHide(id) {
      document.getElementById(id).style.display = 'none';
    }

    function renderTotpState(enabled) {
      totpHide('totpError');
      document.getElementById('totpSetupPanel').style.display = 'none';
      if (enabled) {
        document.getElementById('totpStatus').textContent =
          'Two-factor authentication is ENABLED. Signing in requires a code from your authenticator app.';
        document.getElementById('totpSetupBtn').style.display = 'none';
        document.getElementById('totpDisableForm').style.display = '';
      } else {
        document.getElementById('totpStatus').textContent =
          'Two-factor authentication is OFF. Strongly recommended for Administrator accounts.';
        document.getElementById('totpSetupBtn').style.display = '';
        document.getElementById('totpDisableForm').style.display = 'none';
      }
    }

    document.getElementById('totpSetupBtn').addEventListener('click', function () {
      totpHide('totpError');
      totpHide('totpSuccess');
      API.fetch('/api/account/2fa/setup', { method: 'POST' })
        .then(function (response) {
          return response.json().then(function (data) {
            if (!response.ok) throw new Error(data.detail || 'Setup failed');
            document.getElementById('totpSetupBtn').style.display = 'none';
            document.getElementById('totpSetupPanel').style.display = '';
            document.getElementById('totpSecret').textContent = data.secret;
            var qrContainer = document.getElementById('totpQr');
            qrContainer.innerHTML = '';
            if (window.QRCode) {
              new QRCode(qrContainer, { text: data.otpauth_uri, width: 180, height: 180 });
            } else {
              qrContainer.innerHTML = '<span class="muted">QR library unavailable — enter the secret manually.</span>';
            }
          });
        })
        .catch(function (error) {
          totpShow('totpError', error.message || '2FA setup failed.');
        });
    });

    document.getElementById('totpEnableBtn').addEventListener('click', function () {
      totpHide('totpError');
      API.fetch('/api/account/2fa/enable', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code: document.getElementById('totpEnableCode').value.trim() })
      })
        .then(function (response) {
          return response.json().then(function (data) {
            if (!response.ok) throw new Error(data.detail || 'Could not enable 2FA');
            totpShow('totpSuccess', 'Two-factor authentication enabled.');
            renderTotpState(true);
          });
        })
        .catch(function (error) {
          totpShow('totpError', error.message || 'Could not enable 2FA.');
        });
    });

    document.getElementById('totpDisableForm').addEventListener('submit', function (e) {
      e.preventDefault();
      totpHide('totpError');
      totpHide('totpSuccess');
      API.fetch('/api/account/2fa/disable', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          password: document.getElementById('totpDisablePassword').value,
          code: document.getElementById('totpDisableCode').value.trim()
        })
      })
        .then(function (response) {
          return response.json().then(function (data) {
            if (!response.ok) throw new Error(data.detail || 'Could not disable 2FA');
            document.getElementById('totpDisableForm').reset();
            totpShow('totpSuccess', 'Two-factor authentication disabled.');
            renderTotpState(false);
          });
        })
        .catch(function (error) {
          totpShow('totpError', error.message || 'Could not disable 2FA.');
        });
    });

    var form = document.getElementById('passwordForm');
    var errorBox = document.getElementById('passwordError');
    var successBox = document.getElementById('passwordSuccess');

    form.addEventListener('submit', function (e) {
      e.preventDefault();
      errorBox.style.display = 'none';
      successBox.style.display = 'none';

      var current = document.getElementById('currentPassword').value;
      var next = document.getElementById('newPassword').value;
      var confirm = document.getElementById('confirmPassword').value;

      if (next !== confirm) {
        errorBox.textContent = 'New passwords do not match.';
        errorBox.style.display = '';
        return;
      }

      API.fetch('/api/account/password', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ current_password: current, new_password: next })
      })
        .then(function (response) {
          return response.json().then(function (data) {
            if (!response.ok) {
              throw new Error(data.detail || 'Password change failed');
            }
            form.reset();
            if (user.must_change_password) {
              // Forced flow complete -> into the app
              window.location.href = 'dashboard.html';
              return;
            }
            successBox.textContent = 'Password changed successfully.';
            successBox.style.display = '';
          });
        })
        .catch(function (error) {
          errorBox.textContent = error.message || 'Password change failed.';
          errorBox.style.display = '';
        });
    });
  });
})();
