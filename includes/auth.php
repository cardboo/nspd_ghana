<?php
/**
 * Session management, authentication, and CSRF protection
 */

// Configure secure session before starting
if (session_status() === PHP_SESSION_NONE) {
    $isSecure = (!empty($_SERVER['HTTPS']) && $_SERVER['HTTPS'] !== 'off');

    session_set_cookie_params([
        'lifetime' => 0,
        'path'     => '/',
        'secure'   => $isSecure,
        'httponly'  => true,
        'samesite' => 'Strict',
    ]);

    session_start();
}

/**
 * Check if user is logged in
 */
function is_logged_in() {
    return isset($_SESSION['user_id']) && isset($_SESSION['username']);
}

/**
 * Require authentication — redirect to login if not authenticated
 */
function require_auth() {
    if (!is_logged_in()) {
        header('Location: login.php');
        exit;
    }
}

/**
 * Require a specific role (or higher).
 * Role hierarchy: Administrator > Reviewer > Viewer
 */
function require_role(string $minimum_role) {
    require_auth();

    $hierarchy = [
        'Viewer'        => 1,
        'Reviewer'      => 2,
        'Administrator' => 3,
    ];

    $user_role  = $_SESSION['role'] ?? 'Viewer';
    $user_level = $hierarchy[$user_role] ?? 0;
    $required   = $hierarchy[$minimum_role] ?? 0;

    if ($user_level < $required) {
        http_response_code(403);
        die('Access denied. You do not have the required permissions.');
    }
}

/**
 * Get current user data from session
 */
function get_auth_user() {
    if (!is_logged_in()) {
        return null;
    }

    return [
        'id'        => $_SESSION['user_id'],
        'username'  => $_SESSION['username'],
        'full_name' => $_SESSION['full_name'] ?? 'User',
        'role'      => $_SESSION['role'] ?? 'Viewer',
        'email'     => $_SESSION['email'] ?? '',
    ];
}

/**
 * Authenticate user with username and password
 */
function authenticate_user($username, $password) {
    require_once __DIR__ . '/db.php';
    $pdo = get_db_connection();

    $stmt = $pdo->prepare("SELECT id, username, password_hash, full_name, role, email FROM users WHERE username = ?");
    $stmt->execute([$username]);
    $user = $stmt->fetch();

    if ($user && password_verify($password, $user['password_hash'])) {
        // Regenerate session ID to prevent session fixation
        session_regenerate_id(true);

        // Update last login
        $updateStmt = $pdo->prepare("UPDATE users SET last_login = NOW() WHERE id = ?");
        $updateStmt->execute([$user['id']]);

        // Set session variables
        $_SESSION['user_id']   = $user['id'];
        $_SESSION['username']  = $user['username'];
        $_SESSION['full_name'] = $user['full_name'];
        $_SESSION['role']      = $user['role'];
        $_SESSION['email']     = $user['email'];

        return true;
    }

    return false;
}

/**
 * Logout user
 */
function logout_user() {
    $_SESSION = [];

    if (ini_get('session.use_cookies')) {
        $params = session_get_cookie_params();
        setcookie(session_name(), '', time() - 42000,
            $params['path'], $params['domain'],
            $params['secure'], $params['httponly']
        );
    }

    session_destroy();
    header('Location: login.php');
    exit;
}

// ──────────────────────────────────────────────
// CSRF Protection
// ──────────────────────────────────────────────

/**
 * Generate or retrieve a CSRF token for the current session
 */
function csrf_token(): string {
    if (empty($_SESSION['csrf_token'])) {
        $_SESSION['csrf_token'] = bin2hex(random_bytes(32));
    }
    return $_SESSION['csrf_token'];
}

/**
 * Output a hidden input field with the CSRF token
 */
function csrf_field(): string {
    return '<input type="hidden" name="csrf_token" value="' . htmlspecialchars(csrf_token()) . '">';
}

/**
 * Validate the submitted CSRF token against the session token
 */
function validate_csrf(): bool {
    $token = $_POST['csrf_token'] ?? '';
    return hash_equals(csrf_token(), $token);
}
