<?php
require_once '../includes/auth.php';
require_auth();

require_once '../includes/db.php';
$pdo = get_db_connection();

require_once '../vendor/autoload.php';

/* -------------------------
   Validate ID
-------------------------- */
$id = $_GET['id'] ?? null;
if (!$id) {
    die('Application ID is required');
}

/* -------------------------
   Fetch Application
-------------------------- */
$stmt = $pdo->prepare("SELECT * FROM applications WHERE id = ?");
$stmt->execute([$id]);
$app = $stmt->fetch(PDO::FETCH_ASSOC);

if (!$app) {
    die('Application not found');
}

/* -------------------------
   Sanitize Data
-------------------------- */
$e = fn($v) => htmlspecialchars((string)$v);

$surname       = $e($app['surname']);
$firstName     = $e($app['first_name']);
$otherNames    = $e($app['other_names'] ?? '');
$telephone     = $e($app['telephone']);
$email         = $e($app['email']);
$rank          = $e($app['position_rank']);
$lastShip      = $e($app['last_ship_type'] ?? '');
$submittedAt   = date('F d, Y \a\t g:i A', strtotime($app['submitted_at']));
$generatedAt   = date('F d, Y \a\t g:i A');

/* -------------------------
   Sea Experience
-------------------------- */
$years = 0;
$months = 0;
if (!empty($app['total_sea_experience_years'])) {
    $total = (float)$app['total_sea_experience_years'];
    $years = floor($total);
    $months = round(($total - $years) * 12);
    if ($months === 12) {
        $years++;
        $months = 0;
    }
}

/* -------------------------
   Badge Helper
-------------------------- */
function badge($value) {
    if ($value === 'Yes') {
        return '<span style="background:#d4edda;color:#155724;padding:4px 8px;border-radius:3px;">✓ Yes</span>';
    }
    return '<span style="background:#f8d7da;color:#721c24;padding:4px 8px;border-radius:3px;">✗ No</span>';
}

/* -------------------------
   Prepare Badge Variables
-------------------------- */
$shortCoursesBadge  = badge($app['short_courses_rmu']);
$ispsBadge          = badge($app['familiarisation_isps_gma']);
$attachmentBadge    = badge($app['attachment']);
$medicalsBadge      = badge($app['medicals']);
$experienceBadge    = badge($app['sea_experience']);

/* -------------------------
   HTML Content
-------------------------- */
$html = <<<HTML
<style>
body { font-family: helvetica, sans-serif; font-size: 11px; color: #333; }
h1 { background:#003d6b;color:#fff;padding:15px;text-align:center; }
.section { margin-top: 20px; }
.section-title { background:#0066b3;color:#fff;padding:8px;font-weight:bold; }
.grid { width:100%; margin-top:10px; border-collapse: collapse; }
.grid td { padding:6px; vertical-align:top; border: 1px solid #ccc; }
.label { font-size:10px; color:#666; font-weight:bold; }
.value { font-size:11px; }
.footer { margin-top:30px;font-size:9px;color:#888;text-align:center; }
</style>

<h1>Submission Details Report</h1>

<div class="section">
<div class="section-title">Personal Information</div>
<table class="grid">
<tr><td class="label">Surname</td><td class="value">$surname</td></tr>
<tr><td class="label">First Name</td><td class="value">$firstName</td></tr>
<tr><td class="label">Other Names</td><td class="value">$otherNames</td></tr>
<tr><td class="label">Telephone</td><td class="value">$telephone</td></tr>
<tr><td class="label">Email</td><td class="value">$email</td></tr>
<tr><td class="label">Submitted At</td><td class="value">$submittedAt</td></tr>
</table>
</div>

<div class="section">
<div class="section-title">Position & Qualifications</div>
<table class="grid">
<tr><td class="label">Rank</td><td class="value">$rank</td></tr>
<tr><td class="label">Short Courses</td><td class="value">$shortCoursesBadge</td></tr>
<tr><td class="label">ISPS/GMA</td><td class="value">$ispsBadge</td></tr>
<tr><td class="label">Attachment</td><td class="value">$attachmentBadge</td></tr>
<tr><td class="label">Medicals</td><td class="value">$medicalsBadge</td></tr>
</table>
</div>

<div class="section">
<div class="section-title">Sea Experience</div>
<table class="grid">
<tr><td class="label">Has Experience</td><td class="value">$experienceBadge</td></tr>
<tr><td class="label">Total Experience</td><td class="value">$years Year(s) $months Month(s)</td></tr>
<tr><td class="label">Last Ship Type</td><td class="value">$lastShip</td></tr>
</table>
</div>

<div class="footer">
Generated on $generatedAt | Report ID: $id
</div>
HTML;

/* -------------------------
   Generate PDF
-------------------------- */
$pdf = new TCPDF();
$pdf->SetMargins(15, 15, 15);
$pdf->SetAutoPageBreak(true, 15);
$pdf->AddPage();
$pdf->writeHTML($html, true, false, true, false, '');
$pdf->Output("submission_$id.pdf", 'D');
exit;
