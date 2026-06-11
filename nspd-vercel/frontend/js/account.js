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
      })
      .catch(function (error) {
        console.error('Failed to load profile:', error);
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
