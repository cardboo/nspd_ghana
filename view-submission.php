<?php
require_once 'includes/auth.php';
require_auth();
$user = get_auth_user();

require_once 'includes/db.php';
$pdo = get_db_connection();

// Get the application ID from the URL
$id = $_GET['id'] ?? null;

if (!$id) {
    header('Location: submissions.php');
    exit;
}

// Fetch the application data
$stmt = $pdo->prepare("SELECT * FROM applications WHERE id = ?");
$stmt->execute([$id]);
$application = $stmt->fetch();

if (!$application) {
    header('Location: submissions.php');
    exit;
}
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>View Submission - Maritime Training Portal</title>
    <link rel="stylesheet" href="public/css/style.css">
</head>
<body>
    <div class="app-container">
        <?php include 'includes/sidebar.php'; ?>

        <main class="main-content">
            <?php include 'includes/header.php'; ?>

            <div class="content-body">
                <div style="margin-bottom: 2rem;">
                    <a href="submissions.php" style="color: var(--primary-blue); font-size: 0.875rem; text-decoration: none;">← Back to Submissions</a>
                </div>

                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 2rem;">
                    <h1>Submission Details</h1>
                    <div style="display: flex; gap: 0.75rem;">
                        <a href="api/export-pdf.php?id=<?php echo htmlspecialchars($id); ?>" class="btn btn-accent" target="_blank">Export to PDF</a>
                       
                    </div>
                </div>

                <!-- Personal Information Card -->
                <div class="card" style="margin-bottom: 1.5rem;">
                    <h3 class="card-title" style="margin-bottom: 1.5rem; border-bottom: 2px solid var(--primary-blue); padding-bottom: 0.5rem;">Personal Information</h3>
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 1.5rem;">
                        <div>
                            <div style="font-size: 0.75rem; color: var(--text-muted); margin-bottom: 0.25rem;">Surname</div>
                            <div style="font-weight: 600;"><?php echo htmlspecialchars($application['surname']); ?></div>
                        </div>
                        <div>
                            <div style="font-size: 0.75rem; color: var(--text-muted); margin-bottom: 0.25rem;">First Name</div>
                            <div style="font-weight: 600;"><?php echo htmlspecialchars($application['first_name']); ?></div>
                        </div>
                        <?php if ($application['other_names']): ?>
                        <div>
                            <div style="font-size: 0.75rem; color: var(--text-muted); margin-bottom: 0.25rem;">Other Names</div>
                            <div style="font-weight: 600;"><?php echo htmlspecialchars($application['other_names']); ?></div>
                        </div>
                        <?php endif; ?>
                        <div>
                            <div style="font-size: 0.75rem; color: var(--text-muted); margin-bottom: 0.25rem;">Telephone</div>
                            <div style="font-weight: 600;"><?php echo htmlspecialchars($application['telephone']); ?></div>
                        </div>
                        <div>
                            <div style="font-size: 0.75rem; color: var(--text-muted); margin-bottom: 0.25rem;">Email</div>
                            <div style="font-weight: 600;"><?php echo htmlspecialchars($application['email']); ?></div>
                        </div>
                        <div>
                            <div style="font-size: 0.75rem; color: var(--text-muted); margin-bottom: 0.25rem;">Submission Date</div>
                            <div style="font-weight: 600;"><?php echo date('F d, Y \a\t g:i A', strtotime($application['submitted_at'])); ?></div>
                        </div>
                    </div>
                </div>

                <!-- Position & Qualifications Card -->
                <div class="card" style="margin-bottom: 1.5rem;">
                    <h3 class="card-title" style="margin-bottom: 1.5rem; border-bottom: 2px solid var(--primary-blue); padding-bottom: 0.5rem;">Position & Qualifications</h3>
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 1.5rem;">
                        <div>
                            <div style="font-size: 0.75rem; color: var(--text-muted); margin-bottom: 0.25rem;">Position/Rank</div>
                            <div style="font-weight: 600; color: var(--primary-blue);"><?php echo htmlspecialchars($application['position_rank']); ?></div>
                        </div>
                        <div>
                            <div style="font-size: 0.75rem; color: var(--text-muted); margin-bottom: 0.25rem;">Short Courses (RMU)</div>
                            <div>
                                <?php if ($application['short_courses_rmu'] == 'Yes'): ?>
                                <span style="padding: 0.3rem 0.75rem; background: #d4edda; color: #155724; border-radius: 4px; font-size: 0.875rem; font-weight: 600;">✓ Yes</span>
                                <?php else: ?>
                                <span style="padding: 0.3rem 0.75rem; background: #f8d7da; color: #721c24; border-radius: 4px; font-size: 0.875rem; font-weight: 600;">✗ No</span>
                                <?php endif; ?>
                            </div>
                        </div>
                        <div>
                            <div style="font-size: 0.75rem; color: var(--text-muted); margin-bottom: 0.25rem;">Familiarisation ISPS/GMA</div>
                            <div>
                                <?php if ($application['familiarisation_isps_gma'] == 'Yes'): ?>
                                <span style="padding: 0.3rem 0.75rem; background: #d4edda; color: #155724; border-radius: 4px; font-size: 0.875rem; font-weight: 600;">✓ Yes</span>
                                <?php else: ?>
                                <span style="padding: 0.3rem 0.75rem; background: #f8d7da; color: #721c24; border-radius: 4px; font-size: 0.875rem; font-weight: 600;">✗ No</span>
                                <?php endif; ?>
                            </div>
                        </div>
                        <div>
                            <div style="font-size: 0.75rem; color: var(--text-muted); margin-bottom: 0.25rem;">Attachment</div>
                            <div>
                                <?php if ($application['attachment'] == 'Yes'): ?>
                                <span style="padding: 0.3rem 0.75rem; background: #d4edda; color: #155724; border-radius: 4px; font-size: 0.875rem; font-weight: 600;">✓ Yes</span>
                                <?php else: ?>
                                <span style="padding: 0.3rem 0.75rem; background: #f8d7da; color: #721c24; border-radius: 4px; font-size: 0.875rem; font-weight: 600;">✗ No</span>
                                <?php endif; ?>
                            </div>
                        </div>
                        <div>
                            <div style="font-size: 0.75rem; color: var(--text-muted); margin-bottom: 0.25rem;">Medicals</div>
                            <div>
                                <?php if ($application['medicals'] == 'Yes'): ?>
                                <span style="padding: 0.3rem 0.75rem; background: #d4edda; color: #155724; border-radius: 4px; font-size: 0.875rem; font-weight: 600;">✓ Yes</span>
                                <?php else: ?>
                                <span style="padding: 0.3rem 0.75rem; background: #f8d7da; color: #721c24; border-radius: 4px; font-size: 0.875rem; font-weight: 600;">✗ No</span>
                                <?php endif; ?>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Sea Experience Card -->
                <div class="card">
                    <h3 class="card-title" style="margin-bottom: 1.5rem; border-bottom: 2px solid var(--primary-blue); padding-bottom: 0.5rem;">Sea Experience</h3>
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 1.5rem;">
                        <div>
                            <div style="font-size: 0.75rem; color: var(--text-muted); margin-bottom: 0.25rem;">Has Sea Experience</div>
                            <div>
                                <?php if ($application['sea_experience'] == 'Yes'): ?>
                                <span style="padding: 0.3rem 0.75rem; background: #d4edda; color: #155724; border-radius: 4px; font-size: 0.875rem; font-weight: 600;">✓ Yes</span>
                                <?php else: ?>
                                <span style="padding: 0.3rem 0.75rem; background: #f8d7da; color: #721c24; border-radius: 4px; font-size: 0.875rem; font-weight: 600;">✗ No</span>
                                <?php endif; ?>
                            </div>
                        </div>
                        <div>
                            <div style="font-size: 0.75rem; color: var(--text-muted); margin-bottom: 0.25rem;">Total Sea Experience</div>
                            <div style="font-weight: 600; font-size: 1.5rem; color: var(--primary-blue);">
                                <?php echo htmlspecialchars($application['total_sea_experience_years']); ?> Years
                            </div>
                        </div>
                        <div>
                            <div style="font-size: 0.75rem; color: var(--text-muted); margin-bottom: 0.25rem;">Sea Experience in Months</div>
                            <div style="font-weight: 600; font-size: 1.5rem; color: var(--accent-yellow);">
                                <?php 
                                    $totalYears = floatval($application['total_sea_experience_years'] ?? 0);
                                    $totalMonths = round($totalYears * 12);
                                    echo $totalMonths . ' Months';
                                ?>
                            </div>
                        </div>
                        <?php if ($application['last_ship_type']): ?>
                        <div>
                            <div style="font-size: 0.75rem; color: var(--text-muted); margin-bottom: 0.25rem;">Last Ship Type</div>
                            <div style="font-weight: 600;"><?php echo htmlspecialchars($application['last_ship_type']); ?></div>
                        </div>
                        <?php endif; ?>
                    </div>
                </div>

                <!-- <div style="margin-top: 2rem; display: flex; gap: 1rem;">
                    <button class="btn btn-primary">Approve Application</button>
                    <button class="btn" style="background: #dc3545; color: white; border: none;">Reject Application</button>
                    <button class="btn">Request More Info</button>
                </div> -->
            </div>
        </main>
    </div>
</body>
</html>
