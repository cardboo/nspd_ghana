/**
 * NSPD Ghana — certificate expiry watchlist (Reviewer+).
 * Data from GET /api/reports/expiring?days=N.
 */
(function () {
  function load(days) {
    API.json('/api/reports/expiring?days=' + days)
      .then(function (data) {
        var items = data.items || [];
        document.getElementById('resultsInfo').textContent =
          items.length + ' certificate(s) expired or expiring within ' + data.days + ' days';

        var tbody = document.getElementById('expiryBody');
        if (!items.length) {
          tbody.innerHTML = '<tr><td colspan="8" class="table-empty">Nothing expiring in this window &#127881;</td></tr>';
          return;
        }
        tbody.innerHTML = items.map(function (item) {
          var seafarer = item.seafarer || {};
          return '<tr>' +
            '<td class="text-sm" style="white-space:nowrap;">' + fmtDateShort(item.expires_on) + '</td>' +
            '<td>' + certBadge(item.status) + '</td>' +
            '<td>' + esc(item.title) + '</td>' +
            '<td class="text-sm">' + esc(item.cert_type) + '</td>' +
            '<td>' + esc((seafarer.first_name || '') + ' ' + (seafarer.surname || '')) + '</td>' +
            '<td class="text-sm">' + esc(seafarer.position_rank || '') + '</td>' +
            '<td>' + statusBadge(seafarer.application_status) + '</td>' +
            '<td class="text-center">' +
              '<a href="view-submission.html?id=' + seafarer.application_id + '" class="btn btn-primary btn-sm">View</a>' +
            '</td>' +
          '</tr>';
        }).join('');
      })
      .catch(function (error) {
        console.error('Failed to load expiry watchlist:', error);
        document.getElementById('expiryBody').innerHTML =
          '<tr><td colspan="8" class="table-empty">Failed to load</td></tr>';
      });
  }

  initLayout('expiry', 'Expiry Watch').then(function (user) {
    if (!user) return;
    if (user.role !== 'Administrator' && user.role !== 'Reviewer') {
      window.location.href = 'dashboard.html';
      return;
    }

    load(document.getElementById('horizonSelect').value);

    document.getElementById('horizonForm').addEventListener('submit', function (e) {
      e.preventDefault();
      load(document.getElementById('horizonSelect').value);
    });
  });
})();
