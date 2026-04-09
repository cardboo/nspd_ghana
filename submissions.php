<?php
require_once 'includes/auth.php';
require_auth();

require_once 'includes/db.php';
$pdo = get_db_connection();

// Get pagination variables
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

// Get total count
$count_query = "SELECT COUNT(*) as total FROM applications $where_clause";
$count_stmt = $pdo->prepare($count_query);
$count_stmt->execute($params);
$total = $count_stmt->fetch(PDO::FETCH_ASSOC)['total'];
$total_pages = ceil($total / $per_page);

// Get applications
$offset = ($page - 1) * $per_page;
$query = "SELECT id, surname, first_name, position_rank, email, submitted_at, short_courses_rmu, medicals FROM applications $where_clause ORDER BY submitted_at DESC LIMIT $per_page OFFSET $offset";
$stmt = $pdo->prepare($query);
$stmt->execute($params);
$applications = $stmt->fetchAll(PDO::FETCH_ASSOC);

// Get ranks for filter dropdown
$ranks_stmt = $pdo->prepare("SELECT DISTINCT position_rank FROM applications ORDER BY position_rank");
$ranks_stmt->execute();
$ranks = $ranks_stmt->fetchAll(PDO::FETCH_COLUMN);
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Submissions - Maritime Training Portal</title>
    <link rel="stylesheet" href="public/css/style.css">
</head>
<body>

<div class="app-container">
    <?php include 'includes/sidebar.php'; ?>

    <main class="main-content">
        <?php include 'includes/header.php'; ?>

        <div class="content-body">
            <!-- Header with Export -->
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 2rem;">
                <h1>Submissions</h1>
                <a href="api/export-all-csv.php?search=<?php echo urlencode($search); ?>&rank=<?php echo urlencode($rank_filter); ?>" class="btn btn-accent" target="_blank">Export All to CSV</a>
            </div>

            <!-- Filters -->
            <div class="card" style="margin-bottom: 2rem; padding: 1.5rem;">
                <form method="GET" style="display: flex; gap: 1rem; align-items: flex-end; flex-wrap: wrap;">
                    <!-- Search -->
                    <div style="flex: 1; min-width: 200px;">
                        <label style="display: block; font-size: 0.75rem; color: var(--text-muted); margin-bottom: 0.5rem;">Search</label>
                        <input type="text" name="search" value="<?php echo htmlspecialchars($search); ?>" placeholder="Name, email, ID..." style="width: 100%; padding: 0.75rem; border: 1px solid #ddd; border-radius: 4px; font-size: 0.875rem;">
                    </div>

                    <!-- Rank Filter -->
                    <div style="flex: 0 0 200px;">
                        <label style="display: block; font-size: 0.75rem; color: var(--text-muted); margin-bottom: 0.5rem;">Rank</label>
                        <select name="rank" style="width: 100%; padding: 0.75rem; border: 1px solid #ddd; border-radius: 4px; font-size: 0.875rem;">
                            <option value="">All Ranks</option>
                            <?php foreach ($ranks as $rank): ?>
                            <option value="<?php echo htmlspecialchars($rank); ?>" <?php echo $rank_filter === $rank ? 'selected' : ''; ?>><?php echo htmlspecialchars($rank); ?></option>
                            <?php endforeach; ?>
                        </select>
                    </div>

                    <!-- Submit Button -->
                    <button type="submit" class="btn btn-primary">Filter</button>
                </form>
            </div>

            <!-- Results Info -->
            <div style="margin-bottom: 1rem; font-size: 0.875rem; color: var(--text-muted);">
                Showing <?php echo count($applications); ?> of <?php echo $total; ?> submissions
                <?php if ($search || $rank_filter): ?>
                    - <a href="submissions.php" style="color: var(--primary-blue); text-decoration: none;">Clear filters</a>
                <?php endif; ?>
            </div>

            <!-- Table -->
            <div class="card">
                <table class="submissions-table" style="width: 100%; border-collapse: collapse;">
                    <thead>
                        <tr style="border-bottom: 2px solid var(--primary-blue);">
                            <th style="padding: 1rem; text-align: left; font-weight: 600;">Name</th>
                            <th style="padding: 1rem; text-align: left; font-weight: 600;">Rank</th>
                            <th style="padding: 1rem; text-align: left; font-weight: 600;">Email</th>
                            <th style="padding: 1rem; text-align: left; font-weight: 600;">Courses</th>
                            <th style="padding: 1rem; text-align: left; font-weight: 600;">Medicals</th>
                            <th style="padding: 1rem; text-align: left; font-weight: 600;">Date</th>
                            <th style="padding: 1rem; text-align: center; font-weight: 600;">Action</th>
                        </tr>
                    </thead>
                    <tbody>
                        <?php if (count($applications) > 0): ?>
                            <?php foreach ($applications as $app): ?>
                            <tr style="border-bottom: 1px solid #eee; hover: background-color: #f9f9f9;">
                                <td style="padding: 1rem;"><?php echo htmlspecialchars($app['first_name'] . ' ' . $app['surname']); ?></td>
                                <td style="padding: 1rem;"><strong style="color: var(--primary-blue);"><?php echo htmlspecialchars($app['position_rank']); ?></strong></td>
                                <td style="padding: 1rem; font-size: 0.875rem;"><?php echo htmlspecialchars($app['email']); ?></td>
                                <td style="padding: 1rem;">
                                    <?php if ($app['short_courses_rmu'] === 'Yes'): ?>
                                    <span style="padding: 0.25rem 0.5rem; background: #d4edda; color: #155724; border-radius: 3px; font-size: 0.75rem; font-weight: 600;">✓</span>
                                    <?php else: ?>
                                    <span style="padding: 0.25rem 0.5rem; background: #f8d7da; color: #721c24; border-radius: 3px; font-size: 0.75rem; font-weight: 600;">✗</span>
                                    <?php endif; ?>
                                </td>
                                <td style="padding: 1rem;">
                                    <?php if ($app['medicals'] === 'Yes'): ?>
                                    <span style="padding: 0.25rem 0.5rem; background: #d4edda; color: #155724; border-radius: 3px; font-size: 0.75rem; font-weight: 600;">✓</span>
                                    <?php else: ?>
                                    <span style="padding: 0.25rem 0.5rem; background: #f8d7da; color: #721c24; border-radius: 3px; font-size: 0.75rem; font-weight: 600;">✗</span>
                                    <?php endif; ?>
                                </td>
                                <td style="padding: 1rem; font-size: 0.875rem;"><?php echo date('M d, Y', strtotime($app['submitted_at'])); ?></td>
                                <td style="padding: 1rem; text-align: center;">
                                    <a href="view-submission.php?id=<?php echo $app['id']; ?>" class="btn" style="padding: 0.5rem 1rem; background: var(--primary-blue); color: white; text-decoration: none; border-radius: 4px; font-size: 0.75rem;">View</a>
                                </td>
                            </tr>
                            <?php endforeach; ?>
                        <?php else: ?>
                            <tr>
                                <td colspan="7" style="padding: 2rem; text-align: center; color: var(--text-muted);">
                                    No submissions found
                                </td>
                            </tr>
                        <?php endif; ?>
                    </tbody>
                </table>
            </div>

            <!-- Pagination -->
            <?php if ($total_pages > 1): ?>
            <div style="margin-top: 2rem; display: flex; justify-content: center; align-items: center; gap: 0.5rem; flex-wrap: wrap;">
                <?php if ($page > 1): ?>
                    <a href="submissions.php?page=1&search=<?php echo urlencode($search); ?>&rank=<?php echo urlencode($rank_filter); ?>" class="btn" style="padding: 0.5rem 1rem;">First</a>
                    <a href="submissions.php?page=<?php echo $page - 1; ?>&search=<?php echo urlencode($search); ?>&rank=<?php echo urlencode($rank_filter); ?>" class="btn" style="padding: 0.5rem 1rem;">Previous</a>
                <?php endif; ?>

                <?php for ($i = max(1, $page - 2); $i <= min($total_pages, $page + 2); $i++): ?>
                    <?php if ($i == $page): ?>
                        <span style="padding: 0.5rem 1rem; background: var(--primary-blue); color: white; border-radius: 4px; font-weight: 600;"><?php echo $i; ?></span>
                    <?php else: ?>
                        <a href="submissions.php?page=<?php echo $i; ?>&search=<?php echo urlencode($search); ?>&rank=<?php echo urlencode($rank_filter); ?>" class="btn" style="padding: 0.5rem 1rem;"><?php echo $i; ?></a>
                    <?php endif; ?>
                <?php endfor; ?>

                <?php if ($page < $total_pages): ?>
                    <a href="submissions.php?page=<?php echo $page + 1; ?>&search=<?php echo urlencode($search); ?>&rank=<?php echo urlencode($rank_filter); ?>" class="btn" style="padding: 0.5rem 1rem;">Next</a>
                    <a href="submissions.php?page=<?php echo $total_pages; ?>&search=<?php echo urlencode($search); ?>&rank=<?php echo urlencode($rank_filter); ?>" class="btn" style="padding: 0.5rem 1rem;">Last</a>
                <?php endif; ?>
            </div>
            <?php endif; ?>
        </div>
    </main>
</div>

</body>
</html>

