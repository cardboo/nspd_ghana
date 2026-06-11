/**
 * NSPD Ghana — submissions list page.
 *
 * Replaces submissions.php. Filters still navigate with GET query
 * parameters (the form submits to submissions.html), so URLs remain
 * shareable exactly like the PHP version. v2 adds a status column/filter
 * and sortable column headers.
 */
(function () {
  var params = new URLSearchParams(window.location.search);
  var page = Math.max(1, parseInt(params.get('page') || '1', 10) || 1);
  var search = (params.get('search') || '').trim();
  var rank = (params.get('rank') || '').trim();
  var status = (params.get('status') || '').trim();
  var sort = (params.get('sort') || 'date').trim();
  var dir = (params.get('dir') || 'desc').trim() === 'asc' ? 'asc' : 'desc';

  function buildQuery(overrides) {
    var q = new URLSearchParams({
      page: page, search: search, rank: rank, status: status, sort: sort, dir: dir
    });
    Object.keys(overrides || {}).forEach(function (key) {
      q.set(key, overrides[key]);
    });
    return q.toString();
  }

  function pageUrl(p) {
    return 'submissions.html?' + buildQuery({ page: p });
  }

  function badge(value) {
    if (value === 'Yes') {
      return '<span class="badge badge-success">&#10003;</span>';
    }
    return '<span class="badge badge-danger">&#10007;</span>';
  }

  function renderSortHeaders() {
    document.querySelectorAll('#submissionsHead th[data-sort]').forEach(function (th) {
      var key = th.getAttribute('data-sort');
      var label = th.textContent.trim();
      var arrow = '';
      var nextDir = 'asc';
      if (sort === key) {
        arrow = dir === 'asc' ? ' <span class="sort-arrow">&#9650;</span>' : ' <span class="sort-arrow">&#9660;</span>';
        nextDir = dir === 'asc' ? 'desc' : 'asc';
      }
      th.innerHTML = '<a class="sort-link" href="submissions.html?' +
        buildQuery({ sort: key, dir: nextDir, page: 1 }) + '">' + esc(label) + arrow + '</a>';
    });
  }

  var canBulk = false;

  function renderRows(items) {
    var tbody = document.getElementById('submissionsBody');
    var columns = canBulk ? 9 : 8;
    if (!items.length) {
      tbody.innerHTML = '<tr><td colspan="' + columns + '" class="table-empty">No submissions found</td></tr>';
      return;
    }
    tbody.innerHTML = items.map(function (app) {
      return '<tr>' +
        (canBulk
          ? '<td class="text-center"><input type="checkbox" class="row-select" value="' + app.id + '"></td>'
          : '') +
        '<td>' + esc(app.first_name + ' ' + app.surname) + '</td>' +
        '<td><strong class="text-primary">' + esc(app.position_rank) + '</strong></td>' +
        '<td class="text-sm">' + esc(app.email) + '</td>' +
        '<td>' + badge(app.short_courses_rmu) + '</td>' +
        '<td>' + badge(app.medicals) + '</td>' +
        '<td>' + statusBadge(app.status) + '</td>' +
        '<td class="text-sm">' + fmtDateShort(app.submitted_at) + '</td>' +
        '<td class="text-center">' +
          '<a href="view-submission.html?id=' + encodeURIComponent(app.id) + '" class="btn btn-primary btn-sm">View</a>' +
        '</td>' +
      '</tr>';
    }).join('');

    if (canBulk) {
      tbody.querySelectorAll('.row-select').forEach(function (box) {
        box.addEventListener('change', updateBulkBar);
      });
    }
  }

  // ── Bulk review actions (Reviewer+) ──

  function selectedIds() {
    return Array.from(document.querySelectorAll('.row-select:checked')).map(function (box) {
      return parseInt(box.value, 10);
    });
  }

  function updateBulkBar() {
    var count = selectedIds().length;
    document.getElementById('bulkCount').textContent = count;
    document.getElementById('bulkBar').style.display = count ? '' : 'none';
  }

  function wireBulkActions() {
    document.getElementById('selectAllTh').style.display = '';
    document.getElementById('selectAll').addEventListener('change', function () {
      var checked = this.checked;
      document.querySelectorAll('.row-select').forEach(function (box) { box.checked = checked; });
      updateBulkBar();
    });

    document.querySelectorAll('#bulkBar button[data-bulk]').forEach(function (button) {
      button.addEventListener('click', function () {
        var ids = selectedIds();
        var newStatus = button.getAttribute('data-bulk');
        var message = document.getElementById('bulkMessage');
        if (!ids.length) return;
        if (ids.length > 20) {
          message.textContent = 'Select at most 20 applications per action.';
          return;
        }
        if (!window.confirm('Set ' + ids.length + ' application(s) to "' + newStatus + '"?')) return;

        message.textContent = 'Working...';
        API.fetch('/api/applications/bulk-status', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ ids: ids, status: newStatus })
        })
          .then(function (response) {
            return response.json().then(function (data) {
              if (!response.ok) throw new Error((data.detail && data.detail.toString()) || 'Bulk update failed');
              message.textContent = data.updated.length + ' updated, ' +
                data.skipped.length + ' skipped. Reloading...';
              setTimeout(function () { window.location.reload(); }, 900);
            });
          })
          .catch(function (error) {
            message.textContent = error.message || 'Bulk update failed.';
          });
      });
    });
  }

  function renderPagination(currentPage, totalPages) {
    var container = document.getElementById('pagination');
    if (totalPages <= 1) {
      container.style.display = 'none';
      return;
    }

    var html = '';
    if (currentPage > 1) {
      html += '<a href="' + pageUrl(1) + '" class="pagination-link">First</a>';
      html += '<a href="' + pageUrl(currentPage - 1) + '" class="pagination-link">Prev</a>';
    }
    var start = Math.max(1, currentPage - 2);
    var end = Math.min(totalPages, currentPage + 2);
    for (var i = start; i <= end; i++) {
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

  initLayout('submissions', 'Submissions').then(function (user) {
    if (!user) return;

    // Restore filter inputs from the URL
    document.querySelector('input[name="search"]').value = search;
    document.getElementById('statusSelect').value = status;
    document.getElementById('sortInput').value = sort;
    document.getElementById('dirInput').value = dir;
    if (search || rank || status) {
      document.getElementById('clearLink').style.display = '';
    }

    renderSortHeaders();

    // Export CSV and bulk actions are restricted to Administrator/Reviewer
    if (user.role === 'Administrator' || user.role === 'Reviewer') {
      var exportLink = document.getElementById('exportCsvLink');
      exportLink.href = '/api/exports/csv?' + new URLSearchParams({
        search: search, rank: rank, status: status
      });
      exportLink.style.display = '';
      canBulk = true;
      wireBulkActions();
    }

    // Rank filter dropdown
    API.json('/api/applications/ranks')
      .then(function (data) {
        var select = document.getElementById('rankSelect');
        (data.ranks || []).forEach(function (r) {
          var option = document.createElement('option');
          option.value = r;
          option.textContent = r;
          if (r === rank) option.selected = true;
          select.appendChild(option);
        });
      })
      .catch(function (error) {
        console.error('Failed to load ranks:', error);
      });

    // Submissions list
    API.json('/api/applications?' + buildQuery())
      .then(function (data) {
        document.getElementById('resultsInfo').textContent =
          'Showing ' + data.items.length + ' of ' + data.total + ' submissions';
        renderRows(data.items);
        renderPagination(data.page, data.total_pages);
      })
      .catch(function (error) {
        console.error('Failed to load submissions:', error);
        document.getElementById('submissionsBody').innerHTML =
          '<tr><td colspan="8" class="table-empty">Failed to load submissions</td></tr>';
      });
  });
})();
