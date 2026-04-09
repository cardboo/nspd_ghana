<?php
require_once 'includes/auth.php';
require_auth(); // Updated function name from require_authenticate() to require_auth() to match the definition in includes/auth.php
require_once 'includes/db.php';
$pdo = get_db_connection();
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Seafarer Registry Analytics - Maritime Training Dashboard</title>
    <link rel="stylesheet" href="public/css/style.css">
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
</head>
<body>
    <?php include 'includes/sidebar.php'; ?>
    
    <div class="main-content">
        <?php include 'includes/header.php'; ?>
        
        <div class="content-area">
            <div class="page-header">
                <h1>Seafarer Registry Analytics</h1>
                <p>Institutional overview of registered seafarers and compliance status</p>
            </div>

            <!-- Filter Section -->
            <div class="card filter-card">
                <div class="card-header">
                    <h3>Filters</h3>
                </div>
                <div class="card-body">
                    <form id="filterForm" class="filter-form">
                        <div class="filter-group">
                            <label for="rankFilter">Rank</label>
                            <select id="rankFilter" name="rank">
                                <option value="">All Ranks</option>
                                <?php
                                try {
                                    $ranks = $pdo->query("SELECT DISTINCT position_rank FROM applications WHERE position_rank IS NOT NULL AND position_rank != '' ORDER BY position_rank")->fetchAll();
                                    foreach ($ranks as $rank) {
                                        echo "<option value='" . htmlspecialchars($rank['position_rank']) . "'>" . htmlspecialchars($rank['position_rank']) . "</option>";
                                    }
                                } catch (PDOException $e) {
                                    echo "<!-- Rank Query Error: " . htmlspecialchars($e->getMessage()) . " -->";
                                }
                                ?>
                            </select>
                        </div>
                        
                        <div class="filter-group">
                            <label for="courseFilter">Short Course</label>
                            <select id="courseFilter" name="course">
                                <option value="">All Courses</option>
                                <?php
                                try {
                                    $courses = $pdo->query("SELECT DISTINCT short_courses_rmu FROM applications WHERE short_courses_rmu IS NOT NULL AND short_courses_rmu != '' ORDER BY short_courses_rmu")->fetchAll();
                                    foreach ($courses as $course) {
                                        echo "<option value='" . htmlspecialchars($course['short_courses_rmu']) . "'>" . htmlspecialchars($course['short_courses_rmu']) . "</option>";
                                    }
                                } catch (PDOException $e) {
                                    echo "<!-- Course Query Error: " . htmlspecialchars($e->getMessage()) . " -->";
                                }
                                ?>
                            </select>
                        </div>
                        
                        <div class="filter-group">
                            <label for="medicalFilter">Medical Status</label>
                            <select id="medicalFilter" name="medical">
                                <option value="">All Status</option>
                                <?php
                                try {
                                    $medicals = $pdo->query("SELECT DISTINCT medical_cert_status FROM applications WHERE medical_cert_status IS NOT NULL AND medical_cert_status != '' ORDER BY medical_cert_status")->fetchAll();
                                    if ($medicals) {
                                        foreach ($medicals as $med) {
                                            echo "<option value='" . htmlspecialchars($med['medical_cert_status']) . "'>" . htmlspecialchars($med['medical_cert_status']) . "</option>";
                                        }
                                    } else {
                                        echo '<option value="valid">Valid</option>';
                                        echo '<option value="expired">Expired</option>';
                                    }
                                } catch (PDOException $e) {
                                    echo '<option value="valid">Valid</option><option value="expired">Expired</option>';
                                }
                                ?>
                            </select>
                        </div>
                        
                        <div class="filter-group">
                            <label for="shipTypeFilter">Ship Type</label>
                            <select id="shipTypeFilter" name="ship_type">
                                <option value="">All Types</option>
                                <?php
                                try {
                                    $shipTypes = $pdo->query("SELECT DISTINCT last_ship_type FROM applications WHERE last_ship_type IS NOT NULL AND last_ship_type != '' ORDER BY last_ship_type")->fetchAll();
                                    foreach ($shipTypes as $type) {
                                        echo "<option value='" . htmlspecialchars($type['last_ship_type']) . "'>" . htmlspecialchars($type['last_ship_type']) . "</option>";
                                    }
                                } catch (PDOException $e) {
                                    echo "<!-- Ship Type Query Error: " . htmlspecialchars($e->getMessage()) . " -->";
                                }
                                ?>
                            </select>
                        </div>
                        
                        <div class="filter-actions">
                            <button type="submit" class="btn btn-primary">Apply Filters</button>
                            <button type="button" id="resetBtn" class="btn" style="background: #64748b; color: white;">Reset</button>
                        </div>
                    </form>
                </div>
            </div>

            <!-- SECTION 1 – PRIMARY TREND CHART (FULL WIDTH) -->
            <div class="reports-layout-row">
                <div class="card">
                    <div class="card-header">
                        <h3>Registered Seafarers Over Time</h3>
                    </div>
                    <div class="card-body">
                        <div class="chart-canvas-wrapper chart-h-primary">
                            <canvas id="trendsChart"></canvas>
                        </div>
                    </div>
                </div>
            </div>

            <!-- SECTION 2 – CORE DISTRIBUTION CHARTS (TWO-COLUMN ROW) -->
            <div class="reports-layout-row two-col">
                <!-- Seafarers by Rank -->
                <div class="card">
                    <div class="card-header">
                        <h3>Seafarers by Rank</h3>
                    </div>
                    <div class="card-body">
                        <div class="chart-canvas-wrapper chart-h-core">
                            <canvas id="rankChart"></canvas>
                        </div>
                    </div>
                </div>

                <!-- Sea Experience Distribution -->
                <div class="card">
                    <div class="card-header">
                        <h3>Sea Experience Distribution</h3>
                    </div>
                    <div class="card-body">
                        <div class="chart-canvas-wrapper chart-h-core">
                            <canvas id="experienceChart"></canvas>
                        </div>
                    </div>
                </div>
            </div>

            <!-- SECTION 3 – COMPLIANCE & READINESS CHARTS (SECONDARY) -->
            <div class="reports-layout-row two-col">
                <!-- Certification Coverage -->
                <div class="card">
                    <div class="card-header">
                        <h3>Certification Coverage</h3>
                    </div>
                    <div class="card-body">
                        <div class="chart-canvas-wrapper chart-h-secondary">
                            <canvas id="certChart"></canvas>
                        </div>
                    </div>
                </div>

                <!-- Medical Fitness Status -->
                <div class="card">
                    <div class="card-header">
                        <h3>Medical Fitness Status</h3>
                    </div>
                    <div class="card-body">
                        <div class="chart-canvas-wrapper chart-h-secondary">
                            <canvas id="medicalChart"></canvas>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        // Initialize charts
        let charts = {};
        
        // Chart colors based on maritime theme
        const chartColors = {
            primary: '#1e3a5f',
            secondary: '#2563eb',
            accent: '#fbbf24',
            success: '#10b981',
            warning: '#f59e0b',
            danger: '#ef4444',
            info: '#06b6d4',
            gray: '#64748b'
        };

        function loadChartData(filters = {}) {
            fetch('api/reports-data.php?' + new URLSearchParams(filters))
                .then(response => response.json())
                .then(data => {
                    updateCharts(data);
                })
                .catch(error => console.error('[v0] Error loading chart data:', error));
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
                    labels: ['0–2 years', '3–5 years', '6–10 years', '10+ years'],
                    datasets: [{
                       data: data.experienceDistribution.values, // Example placeholder matching requirement
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
                    labels: ['RMU Short Courses', 'GMA Familiarisation / ISPS', 'Incomplete'],
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
                    labels: ['Medically Fit', 'Not Medically Fit'],
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

        // Filter form handler
        document.getElementById('filterForm').addEventListener('submit', function(e) {
            e.preventDefault();
            const formData = new FormData(this);
            const filters = Object.fromEntries(formData.entries());
            loadChartData(filters);
        });

        // Reset button handler
        document.getElementById('resetBtn').addEventListener('click', function() {
            document.getElementById('filterForm').reset();
            loadChartData();
        });

        // Initial load
        loadChartData();
    </script>
</body>
</html>
