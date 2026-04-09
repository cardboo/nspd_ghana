<?php
$current_page = basename($_SERVER['PHP_SELF']);
?>
<aside class="sidebar">
    <div class="sidebar-header">
        <div class="sidebar-logo">NSPD GHANA</div>
        <small class="sidebar-subtitle">Dashboard</small>
    </div>
    <nav class="sidebar-nav">
        <a href="dashboard.php" class="nav-item <?php echo $current_page === 'dashboard.php' ? 'active' : ''; ?>">
            <span class="nav-icon">&#128202;</span> Dashboard
        </a>
        <a href="submissions.php" class="nav-item <?php echo $current_page === 'submissions.php' ? 'active' : ''; ?>">
            <span class="nav-icon">&#128196;</span> Submissions
        </a>
        <a href="reports.php" class="nav-item <?php echo $current_page === 'reports.php' ? 'active' : ''; ?>">
            <span class="nav-icon">&#128200;</span> Reports
        </a>
    </nav>
    <div class="sidebar-footer">
        <p>&copy; <?php echo date('Y'); ?> Ghana Maritime Authority</p>
    </div>
</aside>
<!-- Mobile sidebar toggle -->
<button class="sidebar-toggle" id="sidebarToggle" aria-label="Toggle sidebar">&#9776;</button>
