<?php
header('Content-Type: application/json');

require_once '../includes/auth.php';
require_once '../includes/db.php';

// Enforce authentication
if (!is_logged_in()) {
    echo json_encode(['error' => 'Unauthorized']);
    exit;
}

$pdo = get_db_connection();

// ----------------------------
// GET FILTERS
// ----------------------------
$rank      = $_GET['rank'] ?? '';
$course    = $_GET['course'] ?? '';
$medical   = $_GET['medical'] ?? '';
$ship_type = $_GET['ship_type'] ?? '';

// ----------------------------
// BUILD SHARED WHERE CLAUSE
// ----------------------------
$where = [];
$params = [];

if ($rank !== '') {
    $where[] = "position_rank = ?";
    $params[] = $rank;
}

if ($course !== '') {
    $where[] = "short_courses_rmu = ?";
    $params[] = $course;
}

if ($medical !== '') {
    $where[] = "medical_cert_status = ?";
    $params[] = $medical;
}

if ($ship_type !== '') {
    $where[] = "last_ship_type = ?";
    $params[] = $ship_type;
}

$whereSql = $where ? 'WHERE ' . implode(' AND ', $where) : '';


// ==================================================
// 1. APPLICATION TRENDS (LINE CHART)
// ==================================================
$trends_stmt = $pdo->prepare("
    SELECT DATE_FORMAT(submitted_at, '%b %Y') AS month, COUNT(*) AS count
    FROM applications
    $whereSql
    GROUP BY DATE_FORMAT(submitted_at, '%Y-%m')
    ORDER BY submitted_at ASC
    LIMIT 6
");
$trends_stmt->execute($params);

$trends_data = $trends_stmt->fetchAll();

$applicationTrends = [
    'labels' => array_column($trends_data, 'month'),
    'values' => array_map('intval', array_column($trends_data, 'count'))
];


// ==================================================
// 2. RANK DISTRIBUTION (BAR CHART)
// ==================================================
$rank_stmt = $pdo->prepare("
    SELECT position_rank, COUNT(*) AS count
    FROM applications
    $whereSql
    GROUP BY position_rank
    ORDER BY count DESC
");
$rank_stmt->execute($params);

$rank_data = $rank_stmt->fetchAll();

$rankDistribution = [
    'labels' => array_column($rank_data, 'position_rank'),
    'values' => array_map('intval', array_column($rank_data, 'count'))
];


// ==================================================
// 3. SEA EXPERIENCE DISTRIBUTION (PIE CHART)
// ==================================================
$exp_stmt = $pdo->prepare("
    SELECT
        SUM(CASE WHEN total_sea_experience_years BETWEEN 0 AND 2 THEN 1 ELSE 0 END) AS exp_0_2,
        SUM(CASE WHEN total_sea_experience_years BETWEEN 3 AND 5 THEN 1 ELSE 0 END) AS exp_3_5,
        SUM(CASE WHEN total_sea_experience_years BETWEEN 6 AND 10 THEN 1 ELSE 0 END) AS exp_6_10,
        SUM(CASE WHEN total_sea_experience_years > 10 THEN 1 ELSE 0 END) AS exp_10_plus
    FROM applications
    $whereSql
");
$exp_stmt->execute($params);
$exp = $exp_stmt->fetch(PDO::FETCH_ASSOC);

$experienceDistribution = [
    'labels' => ['0–2 years', '3–5 years', '6–10 years', '10+ years'],
    'values' => array_map('intval', array_values($exp))
];


// ==================================================
// 4. CERTIFICATION COVERAGE (DOUGHNUT CHART)
// ==================================================
$cert_stmt = $pdo->prepare("
    SELECT
        SUM(CASE WHEN short_courses_rmu IS NOT NULL AND short_courses_rmu != '' THEN 1 ELSE 0 END) AS rmu,
        SUM(CASE WHEN familiarisation_isps_gma = 'Yes' THEN 1 ELSE 0 END) AS gma,
        SUM(CASE WHEN (short_courses_rmu IS NULL OR short_courses_rmu = '') THEN 1 ELSE 0 END) AS incomplete
    FROM applications
    $whereSql
");
$cert_stmt->execute($params);
$cert = $cert_stmt->fetch(PDO::FETCH_ASSOC);

$certificationCoverage = [
    'labels' => ['RMU Short Courses', 'GMA / ISPS', 'Incomplete'],
    'values' => array_map('intval', array_values($cert))
];


// ==================================================
// 5. MEDICAL FITNESS STATUS (PIE CHART)
// ==================================================
$medical_stmt = $pdo->prepare("
    SELECT
        SUM(CASE WHEN medicals = 'Valid' THEN 1 ELSE 0 END) AS fit,
        SUM(CASE WHEN medicals != 'Valid' THEN 1 ELSE 0 END) AS unfit
    FROM applications
    $whereSql
");
$medical_stmt->execute($params);
$medical_data = $medical_stmt->fetch(PDO::FETCH_ASSOC);

$medicalStatus = [
    'labels' => ['Medically Fit', 'Not Medically Fit'],
    'values' => array_map('intval', array_values($medical_data))
];


// ==================================================
// FINAL RESPONSE
// ==================================================
echo json_encode([
    'applicationTrends'       => $applicationTrends,
    'rankDistribution'        => $rankDistribution,
    'experienceDistribution'  => $experienceDistribution,
    'certificationCoverage'   => $certificationCoverage,
    'medicalStatus'           => $medicalStatus
]);
