<?php
require_once 'includes/auth.php';
require_auth();
$user = get_auth_user();
$page_title = 'Submissions';

require_once 'includes/db.php';
$pdo = get_db_connection();

// Pagination & filters
$page = isset($_GET['page']) ? max(1, (int)$_GET['page']) : 1;
$search = isset($_GET['search']) ? trim($_GET['search']) : '';
$rank_filter = isset($_GET['rank']) ? trim($_GET['rank']) : '';
$per_page = 10;

// Build query
$where = [];
$params = [];

if ($search) {
    $where[] = "(surname LIKE ? OR first_name LIKE ? OR email LIKE ?)";
    $params[] = "%$search%";
    $params[] = "%$search%";
    $params[] = "%$search%";
}

if ($rank_filter) {
    $where[] = "position_rank = ?";
    $params[] = $rank_filter;
}

$where_clause = $where ? "WHERE " . implode(" AND ", $where) : "";

// Total count
$count_stmt = $pdo->prepare("SELECT COUNT(*) FROM applications $where_clause");
$count_stmt->execute($params);
$total = (int)$count_stmt->fetchColumn();
$total_pages = max(1, (int)ceil($total / $per_page));
$page = min($page, $total_pages);

// Fetch page
$offset = ($page - 1) * $per_page;
$query = "SELECT id, surname, first_name, position_rank, email, submitted_at, short_courses_rmu, medicals
          FROM applications $where_clause
          ORDER BY submitted_at DESC
          LIMIT ? OFFSET ?";
$stmt = $pdo->prepare($query);
$stmt->execute(array_merge($params, [$per_page, $offset]));
$applications = $stmt->fetchAll();

// Ranks for filter dropdown
$ranks = $pdo->query("SELECT DISTINCT position_rank FROM applications ORDER BY position_rank")->fetchAll(PDO::FETCH_COLUMN);
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Submissions - NSPD Ghana</title>
    <link rel="stylesheet" href="public/css/style.css">
</head>
<body>
<div class="app-container">
    <?php include 'includes/sidebar.php'; ?>

    <main class="main-content">
        <?php include 'includes/header.php'; ?>

        <div class="content-body">
            <div class="page-header-row">
                <h1>Submissions</h1>
                <?php if (in_array($user['role'], ['Administrator', 'Reviewer'])): ?>
                <a href="api/export-all-csv.php?search=<?php echo urlencode($search); ?>&rank=<?php echo urlencode($rank_filter); ?>" class="btn btn-accent" target="_blank">Export CSV</a>
                <?php endif; ?>
            </div>

            <!-- Filters -->
            <div class="card filter-card">
                <form method="GET" class="filter-form">
                    <div class="filter-group">
                        <label>Search</label>
                        <input type="text" name="search" value="<?php echo htmlspecialchars($search); ?>" placeholder="Name, email..." class="form-control">
                    </div>
                    <div class="filter-group" style="flex: 0 0 200px;">
                        <label>Rank</label>
                        <select name="rank" class="form-control">
                            <option value="">All Ranks</option>
                            <?php foreach ($ranks as $rank): ?>
                            <option value="<?php echo htmlspecialchars($rank); ?>" <?php echo $rank_filter === $rank ? 'selected' : ''; ?>><?php echo htmlspecialchars($rank); ?></option>
                            <?php endforeach; ?>
                        </select>
                    </div>
                    <div class="filter-actions">
                        <button type="submit" class="btn btn-primary">Filter</button>
                        <?php if ($search || $rank_filter): ?>
                        <a href="submissions.php" class="btn btn-secondary">Clear</a>
                        <?php endif; ?>
                    </div>
                </form>
            </div>

            <!-- Results Info -->
            <div class="results-info">
                Showing <?php echo count($applications); ?> of <?php echo $total; ?> submissions
            </div>

            <!-- Table -->
            <div class="card">
                <div class="table-container">
                    <table>
                        <thead>
                            <tr>
                                <th>Name</th>
                                <th>Rank</th>
                                <th>Email</th>
                                <th>Courses</th>
                                <th>Medicals</th>
                                <th>Date</th>
                                <th class="text-center">Action</th>
                            </tr>
                        </thead>
                        <tbody>
                            <?php if (empty($applications)): ?>
                            <tr>
                                <td colspan="7" class="table-empty">No submissions found</td>
                            </tr>
                            <?php else: ?>
                            <?php foreach ($applications as $app): ?>
                            <tr>
                                <td><?php echo htmlspecialchars($app['first_name'] . ' ' . $app['surname']); ?></td>
                                <td><strong class="text-primary"><?php echo htmlspecialchars($app['position_rank']); ?></strong></td>
                                <td class="text-sm"><?php echo htmlspecialchars($app['email']); ?></td>
                                <td>
                                    <?php if ($app['short_courses_rmu'] === 'Yes'): ?>
                                    <span class="badge badge-success">&#10003;</span>
                                    <?php else: ?>
                                    <span class="badge badge-danger">&#10007;</span>
                                    <?php endif; ?>
                                </td>
                                <td>
                                    <?php if ($app['medicals'] === 'Yes'): ?>
                                    <span class="badge badge-success">&#10003;</span>
                                    <?php else: ?>
                                    <span class="badge badge-danger">&#10007;</span>
                                    <?php endif; ?>
                                </td>
                                <td class="text-sm"><?php echo date('M d, Y', strtotime($app['submitted_at'])); ?></td>
                                <td class="text-center">
                                    <a href="view-submission.php?id=<?php echo (int)$app['id']; ?>" class="btn btn-primary btn-sm">View</a>
                                </td>
                            </tr>
                            <?php endforeach; ?>
                            <?php endif; ?>
                        </tbody>
                    </table>
                </div>
            </div>

            <!-- Pagination -->
            <?php if ($total_pages > 1): ?>
            <div class="pagination">
                <?php if ($page > 1): ?>
                    <a href="submissions.php?page=1&search=<?php echo urlencode($search); ?>&rank=<?php echo urlencode($rank_filter); ?>" class="pagination-link">First</a>
                    <a href="submissions.php?page=<?php echo $page - 1; ?>&search=<?php echo urlencode($search); ?>&rank=<?php echo urlencode($rank_filter); ?>" class="pagination-link">Prev</a>
                <?php endif; ?>

                <?php for ($i = max(1, $page - 2); $i <= min($total_pages, $page + 2); $i++): ?>
                    <a href="submissions.php?page=<?php echo $i; ?>&search=<?php echo urlencode($search); ?>&rank=<?php echo urlencode($rank_filter); ?>" class="pagination-link <?php echo $i === $page ? 'active' : ''; ?>"><?php echo $i; ?></a>
                <?php endfor; ?>

                <?php if ($page < $total_pages): ?>
                    <a href="submissions.php?page=<?php echo $page + 1; ?>&search=<?php echo urlencode($search); ?>&rank=<?php echo urlencode($rank_filter); ?>" class="pagination-link">Next</a>
                    <a href="submissions.php?page=<?php echo $total_pages; ?>&search=<?php echo urlencode($search); ?>&rank=<?php echo urlencode($rank_filter); ?>" class="pagination-link">Last</a>
                <?php endif; ?>
            </div>
            <?php endif; ?>
        </div>
    </main>
</div>
<script src="public/js/sidebar.js"></script>
</body>
</html>
