<?php
require_once 'includes/auth.php';
require_auth();
$user = get_auth_user();
$page_title = 'Overview';

require_once 'includes/db.php';
$pdo = get_db_connection();

$totalSubmissions = $pdo->query("SELECT COUNT(*) FROM applications")->fetchColumn();

$avgExp = $pdo->query("SELECT AVG(total_sea_experience_years) FROM applications")->fetchColumn();
$avgExp = number_format($avgExp ?: 0, 1);

$popularRank = $pdo->query("SELECT position_rank FROM applications GROUP BY position_rank ORDER BY COUNT(*) DESC LIMIT 1")->fetchColumn();

$recentCount = $pdo->query("SELECT COUNT(*) FROM applications WHERE submitted_at >= NOW() - INTERVAL 1 DAY")->fetchColumn();

$recentSubmissions = $pdo->query("SELECT id, surname, first_name, position_rank, total_sea_experience_years, submitted_at FROM applications ORDER BY submitted_at DESC LIMIT 5")->fetchAll();
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dashboard - NSPD Ghana</title>
    <link rel="stylesheet" href="public/css/style.css">
</head>
<body>
    <div class="app-container">
        <?php include 'includes/sidebar.php'; ?>

        <main class="main-content">
            <?php include 'includes/header.php'; ?>

            <div class="content-body">
                <div class="card-grid">
                    <div class="card">
                        <div class="card-title">Total Submissions</div>
                        <div class="card-value"><?php echo number_format($totalSubmissions); ?></div>
                        <div class="card-subtitle success">Live from database</div>
                    </div>
                    <div class="card">
                        <div class="card-title">Average Sea Exp.</div>
                        <div class="card-value"><?php echo htmlspecialchars($avgExp); ?> Years</div>
                        <div class="card-subtitle">Based on candidates</div>
                    </div>
                    <div class="card">
                        <div class="card-title">Most Common Rank</div>
                        <div class="card-value"><?php echo htmlspecialchars($popularRank ?: 'N/A'); ?></div>
                        <div class="card-subtitle primary">Most frequent application</div>
                    </div>
                    <div class="card card-accent">
                        <div class="card-title">Recent (24h)</div>
                        <div class="card-value"><?php echo number_format($recentCount); ?></div>
                        <div class="card-subtitle">New applications</div>
                    </div>
                </div>

                <div class="card">
                    <div class="card-header-row">
                        <h3 class="card-title" style="margin: 0;">Recent Submissions</h3>
                        <a href="submissions.php" class="link-primary">View All &rarr;</a>
                    </div>
                    <div class="table-container">
                        <table>
                            <thead>
                                <tr>
                                    <th>Name</th>
                                    <th>Rank</th>
                                    <th>Sea Exp.</th>
                                    <th>Submission Date</th>
                                    <th>Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                                <?php if (empty($recentSubmissions)): ?>
                                <tr>
                                    <td colspan="5" class="table-empty">No submissions yet</td>
                                </tr>
                                <?php else: ?>
                                <?php foreach ($recentSubmissions as $row): ?>
                                <tr>
                                    <td><?php echo htmlspecialchars($row['first_name'] . ' ' . $row['surname']); ?></td>
                                    <td><?php echo htmlspecialchars($row['position_rank']); ?></td>
                                    <td><?php echo htmlspecialchars($row['total_sea_experience_years']); ?> Years</td>
                                    <td><?php echo date('M d, Y', strtotime($row['submitted_at'])); ?></td>
                                    <td><a href="view-submission.php?id=<?php echo (int)$row['id']; ?>" class="link-primary">View</a></td>
                                </tr>
                                <?php endforeach; ?>
                                <?php endif; ?>
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </main>
    </div>
    <script src="public/js/sidebar.js"></script>
</body>
</html>
