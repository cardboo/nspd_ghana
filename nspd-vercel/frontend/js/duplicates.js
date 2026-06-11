/**
 * NSPD Ghana — data quality page (Reviewer+).
 * Renders GET /api/reports/duplicates grouped by the duplicated value.
 */
(function () {
  function groupBy(items, keyFn) {
    var groups = {};
    var order = [];
    items.forEach(function (item) {
      var key = keyFn(item);
      if (!groups[key]) {
        groups[key] = [];
        order.push(key);
      }
      groups[key].push(item);
    });
    return order.map(function (key) { return { key: key, items: groups[key] }; });
  }

  function renderGroups(tbodyId, groups) {
    var tbody = document.getElementById(tbodyId);
    if (!groups.length) {
      tbody.innerHTML = '<tr><td colspan="5" class="table-empty">No duplicates found &#127881;</td></tr>';
      return;
    }
    var html = '';
    groups.forEach(function (group) {
      html += '<tr class="dup-group-header"><td colspan="5">' +
        esc(group.key) + ' &mdash; ' + group.items.length + ' submissions</td></tr>';
      group.items.forEach(function (app) {
        html += '<tr>' +
          '<td>' + esc(app.first_name + ' ' + app.surname) + '</td>' +
          '<td>' + esc(app.position_rank) + '</td>' +
          '<td>' + statusBadge(app.status) + '</td>' +
          '<td class="text-sm">' + fmtDateShort(app.submitted_at) + '</td>' +
          '<td class="text-center">' +
            '<a href="view-submission.html?id=' + encodeURIComponent(app.id) + '" class="btn btn-primary btn-sm">View</a>' +
          '</td>' +
        '</tr>';
      });
    });
    tbody.innerHTML = html;
  }

  initLayout('duplicates', 'Data Quality').then(function (user) {
    if (!user) return;
    if (user.role !== 'Administrator' && user.role !== 'Reviewer') {
      window.location.href = 'dashboard.html';
      return;
    }

    API.json('/api/reports/duplicates')
      .then(function (data) {
        var emailGroups = groupBy(data.by_email || [], function (a) { return a.email; });
        var phoneGroups = groupBy(data.by_telephone || [], function (a) { return a.telephone; });

        document.getElementById('emailGroupCount').textContent = emailGroups.length;
        document.getElementById('phoneGroupCount').textContent = phoneGroups.length;

        renderGroups('emailBody', emailGroups);
        renderGroups('phoneBody', phoneGroups);
      })
      .catch(function (error) {
        console.error('Failed to load duplicates:', error);
        document.getElementById('emailBody').innerHTML =
          '<tr><td colspan="5" class="table-empty">Failed to load</td></tr>';
        document.getElementById('phoneBody').innerHTML =
          '<tr><td colspan="5" class="table-empty">Failed to load</td></tr>';
      });
  });
})();
