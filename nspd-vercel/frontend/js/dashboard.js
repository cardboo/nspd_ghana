/**
 * NSPD Ghana — dashboard page.
 * Replaces the PHP-side queries in dashboard.php with GET /api/dashboard/stats.
 */
(function () {
  initLayout('dashboard', 'Overview').then(function (user) {
    if (!user) return;

    API.json('/api/dashboard/stats')
      .then(function (data) {
        document.getElementById('statTotal').textContent = fmtNumber(data.total_submissions);
        document.getElementById('statAvg').textContent = fmtYears(data.avg_experience) + ' Years';
        document.getElementById('statRank').textContent = data.most_common_rank || 'N/A';
        document.getElementById('statRecent').textContent = fmtNumber(data.recent_24h);
        document.getElementById('statPending').textContent = fmtNumber(data.pending_review);

        var tbody = document.getElementById('recentBody');
        var rows = data.recent_submissions || [];

        if (!rows.length) {
          tbody.innerHTML = '<tr><td colspan="6" class="table-empty">No submissions yet</td></tr>';
          return;
        }

        tbody.innerHTML = rows.map(function (row) {
          return '<tr>' +
            '<td>' + esc(row.first_name + ' ' + row.surname) + '</td>' +
            '<td>' + esc(row.position_rank) + '</td>' +
            '<td>' + esc(fmtYears(row.total_sea_experience_years)) + ' Years</td>' +
            '<td>' + statusBadge(row.status) + '</td>' +
            '<td>' + fmtDateShort(row.submitted_at) + '</td>' +
            '<td><a href="view-submission.html?id=' + encodeURIComponent(row.id) + '" class="link-primary">View</a></td>' +
          '</tr>';
        }).join('');
      })
      .catch(function (error) {
        console.error('Failed to load dashboard stats:', error);
      });
  });
})();
