/**
 * NSPD Ghana — user management page (Administrator only).
 * CRUD against /api/users. Per-row role/active editing with explicit
 * Save buttons, plus temp-password resets that force a change at next login.
 */
(function () {
  var ROLES = ['Viewer', 'Reviewer', 'Administrator'];
  var currentUser = null;

  function show(boxId, message) {
    var box = document.getElementById(boxId);
    box.textContent = message;
    box.style.display = '';
    setTimeout(function () { box.style.display = 'none'; }, 6000);
  }

  function roleSelect(user) {
    return '<select class="form-control" data-role="' + user.id + '" style="min-width:130px;">' +
      ROLES.map(function (role) {
        return '<option' + (user.role === role ? ' selected' : '') + '>' + role + '</option>';
      }).join('') + '</select>';
  }

  function renderUsers(users) {
    var tbody = document.getElementById('usersBody');
    tbody.innerHTML = users.map(function (user) {
      var isSelf = currentUser && user.id === currentUser.id;
      return '<tr>' +
        '<td><strong>' + esc(user.username) + '</strong>' + (isSelf ? ' <span class="muted">(you)</span>' : '') + '</td>' +
        '<td>' + esc(user.full_name) + '</td>' +
        '<td class="text-sm">' + esc(user.email) + '</td>' +
        '<td>' + roleSelect(user) + '</td>' +
        '<td class="text-center"><input type="checkbox" data-active="' + user.id + '"' +
          (user.is_active ? ' checked' : '') + (isSelf ? ' disabled' : '') + '></td>' +
        '<td class="text-sm">' + (user.last_login ? fmtDateLong(user.last_login) : 'Never') + '</td>' +
        '<td class="text-center" style="white-space:nowrap;">' +
          '<button class="btn btn-primary btn-sm" data-save="' + user.id + '">Save</button> ' +
          '<button class="btn btn-secondary btn-sm" data-reset="' + user.id + '" data-username="' + esc(user.username) + '">Reset Password</button>' +
        '</td>' +
      '</tr>';
    }).join('');

    tbody.querySelectorAll('button[data-save]').forEach(function (button) {
      button.addEventListener('click', function () {
        var id = button.getAttribute('data-save');
        var role = tbody.querySelector('select[data-role="' + id + '"]').value;
        var isActive = tbody.querySelector('input[data-active="' + id + '"]').checked;
        API.fetch('/api/users/' + id, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ role: role, is_active: isActive })
        })
          .then(function (response) {
            return response.json().then(function (data) {
              if (!response.ok) throw new Error(data.detail || 'Update failed');
              show('createSuccess', 'User updated.');
              loadUsers();
            });
          })
          .catch(function (error) {
            show('createError', error.message || 'Update failed.');
          });
      });
    });

    tbody.querySelectorAll('button[data-reset]').forEach(function (button) {
      button.addEventListener('click', function () {
        var username = button.getAttribute('data-username');
        var temp = window.prompt('New temporary password for ' + username + ' (min 8 characters):');
        if (temp === null) return;
        if (temp.length < 8) {
          show('createError', 'Temporary password must be at least 8 characters.');
          return;
        }
        API.fetch('/api/users/' + button.getAttribute('data-reset') + '/reset-password', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ temp_password: temp })
        })
          .then(function (response) {
            return response.json().then(function (data) {
              if (!response.ok) throw new Error(data.detail || 'Reset failed');
              show('createSuccess', 'Password reset. ' + username + ' must change it at next login.');
              loadUsers();
            });
          })
          .catch(function (error) {
            show('createError', error.message || 'Reset failed.');
          });
      });
    });
  }

  function loadUsers() {
    API.json('/api/users')
      .then(function (data) { renderUsers(data.users || []); })
      .catch(function (error) {
        console.error('Failed to load users:', error);
        document.getElementById('usersBody').innerHTML =
          '<tr><td colspan="7" class="table-empty">Failed to load users</td></tr>';
      });
  }

  initLayout('users', 'User Management').then(function (user) {
    if (!user) return;
    if (user.role !== 'Administrator') {
      window.location.href = 'dashboard.html';
      return;
    }
    currentUser = user;
    loadUsers();

    document.getElementById('createForm').addEventListener('submit', function (e) {
      e.preventDefault();
      API.fetch('/api/users', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          username: document.getElementById('newUsername').value.trim(),
          full_name: document.getElementById('newFullName').value.trim(),
          email: document.getElementById('newEmail').value.trim(),
          role: document.getElementById('newRole').value,
          temp_password: document.getElementById('newPassword').value
        })
      })
        .then(function (response) {
          return response.json().then(function (data) {
            if (!response.ok) {
              var detail = data.detail;
              if (Array.isArray(detail)) detail = detail.map(function (d) { return d.msg; }).join('; ');
              throw new Error(detail || 'Could not create the user');
            }
            document.getElementById('createForm').reset();
            show('createSuccess', 'User "' + data.user.username + '" created.');
            loadUsers();
          });
        })
        .catch(function (error) {
          show('createError', error.message || 'Could not create the user.');
        });
    });
  });
})();
