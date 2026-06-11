/**
 * NSPD Ghana — Sidebar toggle for mobile
 *
 * Same logic as the original public/js/sidebar.js, wrapped in an init
 * function because the sidebar is now injected by layout.js after load.
 */
window.initSidebar = function () {
  var toggle = document.getElementById('sidebarToggle');
  var sidebar = document.querySelector('.sidebar');

  if (!toggle || !sidebar) return;

  // Create overlay element
  var overlay = document.createElement('div');
  overlay.className = 'sidebar-overlay';
  document.body.appendChild(overlay);

  function openSidebar() {
    sidebar.classList.add('open');
    overlay.classList.add('active');
  }

  function closeSidebar() {
    sidebar.classList.remove('open');
    overlay.classList.remove('active');
  }

  toggle.addEventListener('click', function () {
    if (sidebar.classList.contains('open')) {
      closeSidebar();
    } else {
      openSidebar();
    }
  });

  overlay.addEventListener('click', closeSidebar);

  // Close on Escape key
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') closeSidebar();
  });
};
