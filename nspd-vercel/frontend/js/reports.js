/**
 * NSPD Ghana — reports/analytics page.
 *
 * The Chart.js code is carried over unchanged from reports.php; only the
 * data source moved from api/reports-data.php to GET /api/reports/data,
 * and the filter dropdowns (previously rendered server-side) now load
 * from GET /api/reports/filters.
 */

var charts = {};

var chartColors = {
  primary: '#1e3a5f',
  secondary: '#2563eb',
  accent: '#fbbf24',
  success: '#10b981',
  warning: '#f59e0b',
  danger: '#ef4444',
  info: '#06b6d4',
  gray: '#64748b'
};

function hideLoaders() {
  document.querySelectorAll('.chart-loading').forEach(function (el) { el.style.display = 'none'; });
}

function showLoaders() {
  document.querySelectorAll('.chart-loading').forEach(function (el) { el.style.display = 'flex'; });
}

function loadChartData(filters) {
  showLoaders();
  API.fetch('/api/reports/data?' + new URLSearchParams(filters || {}))
    .then(function (response) {
      if (!response.ok) throw new Error('Failed to load data');
      return response.json();
    })
    .then(function (data) {
      hideLoaders();
      updateCharts(data);
    })
    .catch(function (error) {
      hideLoaders();
      console.error('Error loading chart data:', error);
    });
}

function updateCharts(data) {
  // 1. Primary Trends Chart (Line)
  if (charts.trendsChart) charts.trendsChart.destroy();
  charts.trendsChart = new Chart(document.getElementById('trendsChart'), {
    type: 'line',
    data: {
      labels: data.applicationTrends.labels,
      datasets: [{
        label: 'New Registrations',
        data: data.applicationTrends.values,
        borderColor: chartColors.primary,
        backgroundColor: chartColors.primary + '15',
        borderWidth: 3,
        pointBackgroundColor: chartColors.primary,
        pointRadius: 4,
        tension: 0.4,
        fill: true
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        y: { beginAtZero: true, grid: { color: '#eee' } },
        x: { grid: { display: false } }
      }
    }
  });

  // 2. Rank Distribution (Bar)
  if (charts.rankChart) charts.rankChart.destroy();
  charts.rankChart = new Chart(document.getElementById('rankChart'), {
    type: 'bar',
    data: {
      labels: data.rankDistribution.labels,
      datasets: [{
        label: 'Seafarers',
        data: data.rankDistribution.values,
        backgroundColor: chartColors.primary,
        borderRadius: 4
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: { y: { beginAtZero: true } }
    }
  });

  // 3. Sea Experience Distribution (Pie)
  if (charts.experienceChart) charts.experienceChart.destroy();
  charts.experienceChart = new Chart(document.getElementById('experienceChart'), {
    type: 'pie',
    data: {
      labels: data.experienceDistribution.labels,
      datasets: [{
        data: data.experienceDistribution.values,
        backgroundColor: [chartColors.primary, chartColors.secondary, chartColors.accent, chartColors.info]
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { position: 'right' } }
    }
  });

  // 4. Certification Coverage (Doughnut)
  if (charts.certChart) charts.certChart.destroy();
  charts.certChart = new Chart(document.getElementById('certChart'), {
    type: 'doughnut',
    data: {
      labels: data.certificationCoverage.labels,
      datasets: [{
        data: data.certificationCoverage.values,
        backgroundColor: [chartColors.primary, chartColors.accent, '#e2e8f0']
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { position: 'bottom' } }
    }
  });

  // 5. Medical Fitness Status (Pie)
  if (charts.medicalChart) charts.medicalChart.destroy();
  charts.medicalChart = new Chart(document.getElementById('medicalChart'), {
    type: 'pie',
    data: {
      labels: data.medicalStatus.labels,
      datasets: [{
        data: data.medicalStatus.values,
        backgroundColor: [chartColors.success, chartColors.danger]
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { position: 'bottom' } }
    }
  });
}

function populateSelect(selectId, values) {
  var select = document.getElementById(selectId);
  values.forEach(function (value) {
    var option = document.createElement('option');
    option.value = value;
    option.textContent = value;
    select.appendChild(option);
  });
}

(function () {
  initLayout('reports', 'Reports').then(function (user) {
    if (!user) return;

    // Filter dropdown options (ranks + ship types)
    API.json('/api/reports/filters')
      .then(function (data) {
        populateSelect('rankFilter', data.ranks || []);
        populateSelect('shipTypeFilter', data.ship_types || []);
      })
      .catch(function (error) {
        console.error('Failed to load filter options:', error);
      });

    // Filter form handler
    document.getElementById('filterForm').addEventListener('submit', function (e) {
      e.preventDefault();
      var formData = new FormData(this);
      var filters = Object.fromEntries(formData.entries());
      loadChartData(filters);
    });

    // Reset button handler
    document.getElementById('resetBtn').addEventListener('click', function () {
      document.getElementById('filterForm').reset();
      loadChartData();
    });

    // Initial load
    loadChartData();
  });
})();
