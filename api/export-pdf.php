<?php
require_once '../includes/auth.php';
require_auth();
require_role('Reviewer');

require_once '../includes/db.php';
$pdo = get_db_connection();

require_once '../vendor/autoload.php';

// Validate ID
$id = isset($_GET['id']) ? (int)$_GET['id'] : 0;
if ($id <= 0) {
    http_response_code(400);
    die('Valid application ID is required');
}

// Fetch specific columns
$stmt = $pdo->prepare("
    SELECT id, surname, first_name, other_names, telephone, email,
           position_rank, short_courses_rmu, familiarisation_isps_gma,
           attachment, medicals, sea_experience, total_sea_experience_years,
           last_ship_type, submitted_at
    FROM applications WHERE id = ?
");
$stmt->execute([$id]);
$app = $stmt->fetch();

if (!$app) {
    http_response_code(404);
    die('Application not found');
}

// Sanitize
$e = fn($v) => htmlspecialchars((string)($v ?? ''));

$surname     = $e($app['surname']);
$firstName   = $e($app['first_name']);
$otherNames  = $e($app['other_names']);
$telephone   = $e($app['telephone']);
$email       = $e($app['email']);
$rank        = $e($app['position_rank']);
$lastShip    = $e($app['last_ship_type']);
$submittedAt = date('F d, Y \a\t g:i A', strtotime($app['submitted_at']));
$generatedAt = date('F d, Y \a\t g:i A');

// Sea experience
$years = 0;
$months = 0;
if (!empty($app['total_sea_experience_years'])) {
    $total = (float)$app['total_sea_experience_years'];
    $years = floor($total);
    $months = round(($total - $years) * 12);
    if ($months === 12) { $years++; $months = 0; }
}

// Badge helper
$badge = function ($value) {
    if ($value === 'Yes') {
        return '<span style="background:#d4edda;color:#155724;padding:4px 8px;border-radius:3px;">&#10003; Yes</span>';
    }
    return '<span style="background:#f8d7da;color:#721c24;padding:4px 8px;border-radius:3px;">&#10007; No</span>';
};

$shortCoursesBadge = $badge($app['short_courses_rmu']);
$ispsBadge         = $badge($app['familiarisation_isps_gma']);
$attachmentBadge   = $badge($app['attachment'] ?? 'No');
$medicalsBadge     = $badge($app['medicals'] ?? 'No');
$experienceBadge   = $badge($app['sea_experience'] ?? 'No');

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

<h1>NSPD Ghana - Submission Details Report</h1>

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
Generated on $generatedAt | Application ID: $id | NSPD Ghana
</div>
HTML;

$pdf = new TCPDF();
$pdf->SetMargins(15, 15, 15);
$pdf->SetAutoPageBreak(true, 15);
$pdf->AddPage();
$pdf->writeHTML($html, true, false, true, false, '');
$pdf->Output("submission_$id.pdf", 'D');
exit;
