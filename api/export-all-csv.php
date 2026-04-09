<?php
require_once '../includes/auth.php';
require_auth();
require_role('Reviewer');

require_once '../includes/db.php';
$pdo = get_db_connection();

// Apply same filters as submissions page
$search = $_GET['search'] ?? '';
$rank_filter = $_GET['rank'] ?? '';

$where = ["1=1"];
$params = [];

if (!empty($search)) {
    $where[] = "(surname LIKE ? OR first_name LIKE ? OR email LIKE ?)";
    $searchTerm = "%{$search}%";
    $params = array_merge($params, [$searchTerm, $searchTerm, $searchTerm]);
}

if (!empty($rank_filter)) {
    $where[] = "position_rank = ?";
    $params[] = $rank_filter;
}

$whereSql = implode(" AND ", $where);
$query = "SELECT id, surname, first_name, other_names, telephone, email,
                 position_rank, short_courses_rmu, familiarisation_isps_gma,
                 attachment, medicals, sea_experience, total_sea_experience_years,
                 last_ship_type, submitted_at
          FROM applications
          WHERE $whereSql
          ORDER BY submitted_at DESC";

$stmt = $pdo->prepare($query);
$stmt->execute($params);
$applications = $stmt->fetchAll();

if (empty($applications)) {
    http_response_code(404);
    die('No submissions found matching the criteria.');
}

// Set headers for CSV download
header('Content-Type: text/csv; charset=utf-8');
header('Content-Disposition: attachment; filename="nspd_submissions_' . date('Ymd_His') . '.csv"');

$output = fopen('php://output', 'w');

// BOM for Excel UTF-8 support
fwrite($output, "\xEF\xBB\xBF");

$headers = [
    'ID', 'Surname', 'First Name', 'Other Names', 'Telephone', 'Email',
    'Position/Rank', 'Short Courses (RMU)', 'ISPS/GMA Familiarisation',
    'Attachment', 'Medicals', 'Sea Experience', 'Total Sea Experience (Years)',
    'Last Ship Type', 'Submitted Date'
];
fputcsv($output, $headers);

foreach ($applications as $app) {
    fputcsv($output, [
        $app['id'],
        $app['surname'],
        $app['first_name'],
        $app['other_names'] ?? '',
        $app['telephone'],
        $app['email'],
        $app['position_rank'],
        $app['short_courses_rmu'],
        $app['familiarisation_isps_gma'],
        $app['attachment'] ?? '',
        $app['medicals'] ?? '',
        $app['sea_experience'] ?? '',
        $app['total_sea_experience_years'],
        $app['last_ship_type'] ?? '',
        date('F d, Y H:i:s', strtotime($app['submitted_at']))
    ]);
}

fclose($output);
exit;
