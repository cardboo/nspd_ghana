<?php
if (!isset($user)) {
    require_once __DIR__ . '/auth.php';
    $user = get_auth_user();
}

// Dynamic page title based on current page
$page_titles = [
    'dashboard.php' => 'Overview',
    'submissions.php' => 'Submissions',
    'reports.php' => 'Reports',
    'view-submission.php' => 'Submission Details',
];
$current = basename($_SERVER['PHP_SELF']);
$header_title = $page_title ?? ($page_titles[$current] ?? 'Dashboard');
?>
<header class="top-header">
    <div class="header-left">
        <h2 class="header-title"><?php echo htmlspecialchars($header_title); ?></h2>
    </div>
    <div class="header-right">
        <div class="header-user-info">
            <div class="header-user-name"><?php echo htmlspecialchars($user['full_name'] ?? 'User'); ?></div>
            <div class="header-user-role"><?php echo htmlspecialchars($user['role'] ?? 'Viewer'); ?></div>
        </div>
        <a href="logout.php" class="btn btn-primary btn-sm">Logout</a>
    </div>
</header>
