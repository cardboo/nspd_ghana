<?php
require_once 'includes/auth.php';
require_auth();
$user = get_auth_user();
$page_title = 'Submission Details';

require_once 'includes/db.php';
$pdo = get_db_connection();

// Validate ID as integer
$id = isset($_GET['id']) ? (int)$_GET['id'] : 0;

if ($id <= 0) {
    header('Location: submissions.php');
    exit;
}

// Fetch specific columns instead of SELECT *
$stmt = $pdo->prepare("
    SELECT id, surname, first_name, other_names, telephone, email,
           position_rank, short_courses_rmu, familiarisation_isps_gma,
           attachment, medicals, sea_experience, total_sea_experience_years,
           last_ship_type, submitted_at
    FROM applications WHERE id = ?
");
$stmt->execute([$id]);
$application = $stmt->fetch();

if (!$application) {
    header('Location: submissions.php');
    exit;
}

// Helper for yes/no badges
function yes_no_badge(string $value): string {
    if ($value === 'Yes') {
        return '<span class="badge badge-success-lg">&#10003; Yes</span>';
    }
    return '<span class="badge badge-danger-lg">&#10007; No</span>';
}
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>View Submission - NSPD Ghana</title>
    <link rel="stylesheet" href="public/css/style.css">
</head>
<body>
    <div class="app-container">
        <?php include 'includes/sidebar.php'; ?>

        <main class="main-content">
            <?php include 'includes/header.php'; ?>

            <div class="content-body">
                <div class="back-link">
                    <a href="submissions.php" class="link-primary">&larr; Back to Submissions</a>
                </div>

                <div class="page-header-row">
                    <h1>Submission Details</h1>
                    <div class="page-actions">
                        <?php if (in_array($user['role'], ['Administrator', 'Reviewer'])): ?>
                        <a href="api/export-pdf.php?id=<?php echo $id; ?>" class="btn btn-accent" target="_blank">Export PDF</a>
                        <?php endif; ?>
                    </div>
                </div>

                <!-- Personal Information -->
                <div class="card detail-card">
                    <h3 class="detail-section-title">Personal Information</h3>
                    <div class="detail-grid">
                        <div class="detail-item">
                            <div class="detail-label">Surname</div>
                            <div class="detail-value"><?php echo htmlspecialchars($application['surname']); ?></div>
                        </div>
                        <div class="detail-item">
                            <div class="detail-label">First Name</div>
                            <div class="detail-value"><?php echo htmlspecialchars($application['first_name']); ?></div>
                        </div>
                        <?php if (!empty($application['other_names'])): ?>
                        <div class="detail-item">
                            <div class="detail-label">Other Names</div>
                            <div class="detail-value"><?php echo htmlspecialchars($application['other_names']); ?></div>
                        </div>
                        <?php endif; ?>
                        <div class="detail-item">
                            <div class="detail-label">Telephone</div>
                            <div class="detail-value"><?php echo htmlspecialchars($application['telephone']); ?></div>
                        </div>
                        <div class="detail-item">
                            <div class="detail-label">Email</div>
                            <div class="detail-value"><?php echo htmlspecialchars($application['email']); ?></div>
                        </div>
                        <div class="detail-item">
                            <div class="detail-label">Submission Date</div>
                            <div class="detail-value"><?php echo date('F d, Y \a\t g:i A', strtotime($application['submitted_at'])); ?></div>
                        </div>
                    </div>
                </div>

                <!-- Position & Qualifications -->
                <div class="card detail-card">
                    <h3 class="detail-section-title">Position & Qualifications</h3>
                    <div class="detail-grid">
                        <div class="detail-item">
                            <div class="detail-label">Position/Rank</div>
                            <div class="detail-value text-primary"><?php echo htmlspecialchars($application['position_rank']); ?></div>
                        </div>
                        <div class="detail-item">
                            <div class="detail-label">Short Courses (RMU)</div>
                            <div class="detail-value"><?php echo yes_no_badge($application['short_courses_rmu']); ?></div>
                        </div>
                        <div class="detail-item">
                            <div class="detail-label">Familiarisation ISPS/GMA</div>
                            <div class="detail-value"><?php echo yes_no_badge($application['familiarisation_isps_gma']); ?></div>
                        </div>
                        <div class="detail-item">
                            <div class="detail-label">Attachment</div>
                            <div class="detail-value"><?php echo yes_no_badge($application['attachment'] ?? 'No'); ?></div>
                        </div>
                        <div class="detail-item">
                            <div class="detail-label">Medicals</div>
                            <div class="detail-value"><?php echo yes_no_badge($application['medicals'] ?? 'No'); ?></div>
                        </div>
                    </div>
                </div>

                <!-- Sea Experience -->
                <div class="card detail-card">
                    <h3 class="detail-section-title">Sea Experience</h3>
                    <div class="detail-grid">
                        <div class="detail-item">
                            <div class="detail-label">Has Sea Experience</div>
                            <div class="detail-value"><?php echo yes_no_badge($application['sea_experience'] ?? 'No'); ?></div>
                        </div>
                        <div class="detail-item">
                            <div class="detail-label">Total Sea Experience</div>
                            <div class="detail-value detail-value-large text-primary">
                                <?php echo htmlspecialchars($application['total_sea_experience_years']); ?> Years
                            </div>
                        </div>
                        <div class="detail-item">
                            <div class="detail-label">Sea Experience in Months</div>
                            <div class="detail-value detail-value-large text-accent">
                                <?php
                                    $totalYears = floatval($application['total_sea_experience_years'] ?? 0);
                                    echo round($totalYears * 12) . ' Months';
                                ?>
                            </div>
                        </div>
                        <?php if (!empty($application['last_ship_type'])): ?>
                        <div class="detail-item">
                            <div class="detail-label">Last Ship Type</div>
                            <div class="detail-value"><?php echo htmlspecialchars($application['last_ship_type']); ?></div>
                        </div>
                        <?php endif; ?>
                    </div>
                </div>
            </div>
        </main>
    </div>
    <script src="public/js/sidebar.js"></script>
</body>
</html>
