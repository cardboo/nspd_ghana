/**
 * NSPD Ghana — shared layout (sidebar + header).
 *
 * Replaces includes/sidebar.php and includes/header.php. Each page calls
 * initLayout(currentPage, pageTitle); it verifies the session against
 * /api/auth/me (redirecting to login.html on 401, like require_auth()),
 * enforces forced password changes, then injects the sidebar and header.
 *
 * Nav items are role-gated: Data Quality needs Reviewer+, Users and
 * Audit Log need Administrator. The server enforces the same rules.
 */

function sidebarHTML(currentPage, user) {
  function item(page, href, icon, label) {
    return '<a href="' + href + '" class="nav-item' +
      (currentPage === page ? ' active' : '') + '">' +
      '<span class="nav-icon">' + icon + '</span> ' + label + '</a>';
  }

  var role = user.role || 'Viewer';
  var nav = '';
  nav += item('dashboard', 'dashboard.html', '&#128202;', 'Dashboard');
  nav += item('submissions', 'submissions.html', '&#128196;', 'Submissions');
  nav += item('reports', 'reports.html', '&#128200;', 'Reports');
  if (role === 'Administrator' || role === 'Reviewer') {
    nav += item('expiry', 'expiry.html', '&#9200;', 'Expiry Watch');
    nav += item('duplicates', 'duplicates.html', '&#128269;', 'Data Quality');
  }
  if (role === 'Administrator') {
    nav += item('users', 'users.html', '&#128101;', 'Users');
    nav += item('audit', 'audit.html', '&#128220;', 'Audit Log');
  }
  nav += item('account', 'account.html', '&#9881;', 'My Account');

  return '' +
    '<aside class="sidebar">' +
      '<div class="sidebar-header">' +
        '<div class="sidebar-logo">NSPD GHANA</div>' +
        '<small class="sidebar-subtitle">Dashboard</small>' +
      '</div>' +
      '<nav class="sidebar-nav">' + nav + '</nav>' +
      '<div class="sidebar-footer">' +
        '<p>&copy; ' + new Date().getFullYear() + ' Ghana Maritime Authority</p>' +
      '</div>' +
    '</aside>' +
    '<button class="sidebar-toggle" id="sidebarToggle" aria-label="Toggle sidebar">&#9776;</button>';
}

function headerHTML(title, user) {
  return '' +
    '<header class="top-header">' +
      '<div class="header-left">' +
        '<h2 class="header-title">' + esc(title) + '</h2>' +
      '</div>' +
      '<div class="header-right">' +
        '<a href="account.html" class="header-user-info" style="text-decoration:none;color:inherit;">' +
          '<div class="header-user-name">' + esc(user.full_name || 'User') + '</div>' +
          '<div class="header-user-role">' + esc(user.role || 'Viewer') + '</div>' +
        '</a>' +
        '<a href="#" id="logoutLink" class="btn btn-primary btn-sm">Logout</a>' +
      '</div>' +
    '</header>';
}

/** Status badge shared by submissions, detail, dashboard, duplicates pages. */
function statusBadge(status) {
  var value = status || 'Pending';
  var cls = 'status-' + value.toLowerCase().replace(/\s+/g, '-');
  return '<span class="status-badge ' + cls + '">' + esc(value) + '</span>';
}

/**
 * Authenticates and renders the shared layout.
 * Resolves with the current user, or null if the user was redirected.
 */
function initLayout(currentPage, pageTitle) {
  return API.json('/api/auth/me')
    .then(function (data) {
      var user = data.user;

      // Forced password change: only the account page is reachable
      if (user.must_change_password && currentPage !== 'account') {
        window.location.href = 'account.html';
        return null;
      }

      var sidebarSlot = document.getElementById('sidebar-placeholder');
      if (sidebarSlot) sidebarSlot.outerHTML = sidebarHTML(currentPage, user);

      var headerSlot = document.getElementById('header-placeholder');
      if (headerSlot) headerSlot.outerHTML = headerHTML(pageTitle, user);

      var logoutLink = document.getElementById('logoutLink');
      if (logoutLink) {
        logoutLink.addEventListener('click', function (e) {
          e.preventDefault();
          fetch('/api/auth/logout', { method: 'POST', credentials: 'same-origin' })
            .catch(function () {})
            .then(function () {
              window.location.href = 'login.html';
            });
        });
      }

      window.initSidebar();
      return user;
    })
    .catch(function () {
      // 401 already triggered the redirect inside API.fetch
      return null;
    });
}
