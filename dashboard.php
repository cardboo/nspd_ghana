<?php
require_once 'includes/auth.php';
require_auth();
$user = get_auth_user();
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dashboard - Maritime Training Portal</title>
    <link rel="stylesheet" href="public/css/style.css">
</head>
<body>
    <div class="app-container">
        <?php include 'includes/sidebar.php'; ?>

        <main class="main-content">
            <?php include 'includes/header.php'; ?>

            <div class="content-body">
                <?php
                require_once 'includes/db.php';
                $pdo = get_db_connection();

                $totalSubmissions = $pdo->query("SELECT COUNT(*) FROM applications")->fetchColumn();

                $avgExp = $pdo->query("SELECT AVG(total_sea_experience_years) FROM applications")->fetchColumn();
                $avgExp = number_format($avgExp ?: 0, 1);

                $pendingReview = 0; // The current schema doesn't have a 'status' column, defaulting to 0 or could count empty medicals etc.

                $popularRank = $pdo->query("SELECT position_rank FROM applications GROUP BY position_rank ORDER BY COUNT(*) DESC LIMIT 1")->fetchColumn();

                // Fetch recent submissions
                $recentSubmissions = $pdo->query("SELECT id, surname, first_name, position_rank, total_sea_experience_years, submitted_at FROM applications ORDER BY submitted_at DESC LIMIT 5")->fetchAll();
                ?>
                <div class="card-grid">
                    <div class="card">
                        <div class="card-title">Total Submissions</div>
                        <div class="card-value"><?php echo number_format($totalSubmissions); ?></div>
                        <div style="font-size: 0.75rem; color: green; margin-top: 0.5rem;">Live from database</div>
                    </div>
                    <div class="card">
                        <div class="card-title">Average Sea Exp.</div>
                        <div class="card-value"><?php echo $avgExp; ?> Years</div>
                        <div style="font-size: 0.75rem; color: var(--text-muted); margin-top: 0.5rem;">Based on candidates</div>
                    </div>
                    <div class="card">
                        <div class="card-title">Latest Rank</div>
                        <div class="card-value"><?php echo $popularRank ?: 'N/A'; ?></div>
                        <div style="font-size: 0.75rem; color: var(--primary-blue); margin-top: 0.5rem;">Most frequent application</div>
                    </div>
                    <div class="card" style="border-bottom: 4px solid var(--accent-yellow);">
                        <div class="card-title">Recent (24h)</div>
                        <div class="card-value">
                            <?php 
                            echo $pdo->query("SELECT COUNT(*) FROM applications WHERE submitted_at >= NOW() - INTERVAL 1 DAY")->fetchColumn(); 
                            ?>
                        </div>
                        <div style="font-size: 0.75rem; color: var(--text-muted); margin-top: 0.5rem;">New applications</div>
                    </div>
                </div>

                <div class="card">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem;">
                        <h3 class="card-title" style="margin: 0;">Recent Submissions</h3>
                        <a href="submissions.php" style="font-size: 0.875rem; color: var(--primary-blue); font-weight: 600;">View All →</a>
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
                                <?php foreach ($recentSubmissions as $row): ?>
                                <tr>
                                    <td><?php echo htmlspecialchars($row['first_name'] . ' ' . $row['surname']); ?></td>
                                    <td><?php echo htmlspecialchars($row['position_rank']); ?></td>
                                    <td><?php echo htmlspecialchars($row['total_sea_experience_years']); ?> Years</td>
                                    <td><?php echo date('M d, Y', strtotime($row['submitted_at'])); ?></td>
                                    <td><a href="view-submission.php?id=<?php echo $row['id']; ?>" style="color: var(--primary-blue);">View</a></td>
                                </tr>
                                <?php endforeach; ?>
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </main>
    </div>
</body>
</html>
