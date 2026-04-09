<?php
require_once 'includes/auth.php';

$error = '';

// If already logged in, redirect to dashboard
if (is_logged_in()) {
    header('Location: dashboard.php');
    exit;
}

// Handle login form submission
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $username = $_POST['username'] ?? '';
    $password = $_POST['password'] ?? '';
    
    if (authenticate_user($username, $password)) {
        header('Location: dashboard.php');
        exit;
    } else {
        $error = 'Invalid username or password';
    }
}
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Login - Maritime Training Dashboard</title>
    <link rel="stylesheet" href="public/css/style.css">
</head>
<body class="login-body">
    <div class="login-card">
        <div class="login-header">
            <h1 class="sidebar-logo">MARITIME PORT</h1>
            <p style="color: var(--text-muted)">Training Questionnaire Portal</p>
        </div>
        <?php if ($error): ?>
        <div style="padding: 0.75rem; background: #f8d7da; color: #721c24; border-radius: 4px; margin-bottom: 1rem; font-size: 0.875rem;">
            <?php echo htmlspecialchars($error); ?>
        </div>
        <?php endif; ?>
        <form method="POST">
            <div class="form-group">
                <label for="username">Username</label>
                <input type="text" id="username" name="username" class="form-control" placeholder="Enter your username" required>
            </div>
            <div class="form-group">
                <label for="password">Password</label>
                <input type="password" id="password" name="password" class="form-control" placeholder="Enter your password" required>
            </div>
            <div class="form-group">
                <button type="submit" class="btn btn-primary" style="width: 100%;">Sign In</button>
            </div>
        </form>
        <div style="text-align: center; margin-top: 1rem;">
            <a href="#" style="color: var(--primary-blue); font-size: 0.875rem;">Forgot Password?</a>
        </div>
        <div style="margin-top: 2rem; padding: 0.75rem; background: #e7f3ff; border-radius: 4px; font-size: 0.75rem;">
            <strong>Demo Credentials:</strong><br>
            Username: <code>admin</code><br>
            Password: <code>passwooord</code>
        </div>
    </div>
</body>
</html>
