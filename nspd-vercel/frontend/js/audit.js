/**
 * NSPD Ghana — audit log page (Administrator only).
 * Paginated view of GET /api/audit with action/username filters.
 */
(function () {
  var params = new URLSearchParams(window.location.search);
  var page = Math.max(1, parseInt(params.get('page') || '1', 10) || 1);
  var action = (params.get('action') || '').trim();
  var username = (params.get('username') || '').trim();

  function pageUrl(p) {
    return 'audit.html?' + new URLSearchParams({ page: p, action: action, username: username });
  }

  function fmtTime(isoString) {
    if (!isoString) return '';
    var d = new Date(isoString);
    if (isNaN(d.getTime())) return '';
    return fmtDateShort(isoString) + ' ' +
      String(d.getHours()).padStart(2, '0') + ':' +
      String(d.getMinutes()).padStart(2, '0') + ':' +
      String(d.getSeconds()).padStart(2, '0');
  }

  function entityRef(entry) {
    if (!entry.entity) return '';
    if (entry.entity === 'application' && entry.entity_id) {
      return '<a class="link-primary" href="view-submission.html?id=' + entry.entity_id + '">' +
        esc(entry.entity + ' #' + entry.entity_id) + '</a>';
    }
    return esc(entry.entity + (entry.entity_id ? ' #' + entry.entity_id : ''));
  }

  function renderPagination(currentPage, totalPages) {
    var container = document.getElementById('pagination');
    if (totalPages <= 1) { container.style.display = 'none'; return; }
    var html = '';
    if (currentPage > 1) {
      html += '<a href="' + pageUrl(1) + '" class="pagination-link">First</a>';
      html += '<a href="' + pageUrl(currentPage - 1) + '" class="pagination-link">Prev</a>';
    }
    for (var i = Math.max(1, currentPage - 2); i <= Math.min(totalPages, currentPage + 2); i++) {
      html += '<a href="' + pageUrl(i) + '" class="pagination-link' +
        (i === currentPage ? ' active' : '') + '">' + i + '</a>';
    }
    if (currentPage < totalPages) {
      html += '<a href="' + pageUrl(currentPage + 1) + '" class="pagination-link">Next</a>';
      html += '<a href="' + pageUrl(totalPages) + '" class="pagination-link">Last</a>';
    }
    container.innerHTML = html;
    container.style.display = '';
  }

  initLayout('audit', 'Audit Log').then(function (user) {
    if (!user) return;
    if (user.role !== 'Administrator') {
      window.location.href = 'dashboard.html';
      return;
    }

    document.querySelector('input[name="username"]').value = username;

    API.json('/api/audit?' + new URLSearchParams({ page: page, action: action, username: username }))
      .then(function (data) {
        // Action dropdown from the distinct actions present in the log
        var select = document.getElementById('actionSelect');
        (data.actions || []).forEach(function (a) {
          var option = document.createElement('option');
          option.value = a;
          option.textContent = a;
          if (a === action) option.selected = true;
          select.appendChild(option);
        });

        document.getElementById('resultsInfo').textContent =
          'Showing ' + data.items.length + ' of ' + data.total + ' entries';

        var tbody = document.getElementById('auditBody');
        if (!data.items.length) {
          tbody.innerHTML = '<tr><td colspan="6" class="table-empty">No audit entries found</td></tr>';
        } else {
          tbody.innerHTML = data.items.map(function (entry) {
            return '<tr>' +
              '<td class="text-sm" style="white-space:nowrap;">' + fmtTime(entry.created_at) + '</td>' +
              '<td><strong>' + esc(entry.username) + '</strong></td>' +
              '<td class="text-sm">' + esc(entry.action) + '</td>' +
              '<td class="text-sm">' + entityRef(entry) + '</td>' +
              '<td class="text-sm">' + esc(entry.details || '') + '</td>' +
              '<td class="text-sm">' + esc(entry.ip_address || '') + '</td>' +
            '</tr>';
          }).join('');
        }

        renderPagination(data.page, data.total_pages);
      })
      .catch(function (error) {
        console.error('Failed to load audit log:', error);
        document.getElementById('auditBody').innerHTML =
          '<tr><td colspan="6" class="table-empty">Failed to load audit log</td></tr>';
      });
  });
})();
