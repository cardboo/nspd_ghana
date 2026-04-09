<?php
if (!isset($user)) {
    require_once 'includes/auth.php';
    $user = get_auth_user();
}
?>
<header class="top-header">
    <div class="header-left">
        <h2 style="margin: 0; font-size: 1.25rem;">Overview</h2>
    </div>
    <div class="header-right" style="display: flex; align-items: center;">
        <div style="text-align: right; margin-right: 1.5rem;">
            <div style="font-weight: 600; font-size: 0.875rem;"><?php echo htmlspecialchars($user['full_name'] ?? 'User'); ?></div>
            <div style="font-size: 0.75rem; color: var(--text-muted)"><?php echo htmlspecialchars($user['role'] ?? 'Viewer'); ?></div>
        </div>
        <a href="logout.php" class="btn btn-primary">Logout</a>
    </div>
</header>
