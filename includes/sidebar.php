<?php
// Determine current page for active class
$current_page = basename($_SERVER['PHP_SELF']);
?>
<aside class="sidebar">
    <div class="sidebar-header">
        <div class="sidebar-logo">NSPD GHANA</div>
        <small style="opacity: 0.7">Dashboard </small>
    </div>
    <nav class="sidebar-nav">
        <a href="dashboard.php" class="nav-item <?php echo $current_page == 'dashboard.php' ? 'active' : ''; ?>">
            <i>📊</i> Dashboard
        </a>
        <a href="submissions.php" class="nav-item <?php echo $current_page == 'submissions.php' ? 'active' : ''; ?>">
            <i>📄</i> Submissions
        </a>
        <!-- Added Reports navigation link -->
        <a href="reports.php" class="nav-item <?php echo $current_page == 'reports.php' ? 'active' : ''; ?>">
            <i>📈</i> Reports
        </a>
        <!-- <a href="#" class="nav-item">
            <i>⚙️</i> Settings
        </a>
        <a href="#" class="nav-item">
            <i>📂</i> Archive -->
        </a>
    </nav>
    <div class="sidebar-footer" style="padding: 1.5rem; border-top: 1px solid rgba(255,255,255,0.1)">
        <p style="font-size: 0.75rem; opacity: 0.6">© 2025 Ghana Maritime Authority</p>
    </div>
</aside>
