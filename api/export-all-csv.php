<?php
require_once '../includes/auth.php';
require_auth();

require_once '../includes/db.php';
$pdo = get_db_connection();

// Apply same filters as submissions page
$search = $_GET['search'] ?? '';
$rank_filter = $_GET['rank'] ?? '';

$query = "SELECT * FROM applications WHERE 1=1";
$params = [];

if (!empty($search)) {
    $query .= " AND (surname LIKE ? OR first_name LIKE ? OR email LIKE ?)";
    $searchTerm = "%{$search}%";
    $params = array_merge($params, [$searchTerm, $searchTerm, $searchTerm]);
}

if (!empty($rank_filter) && $rank_filter !== 'all') {
    $query .= " AND position_rank = ?";
    $params[] = $rank_filter;
}

$query .= " ORDER BY submitted_at DESC";

$stmt = $pdo->prepare($query);
$stmt->execute($params);
$applications = $stmt->fetchAll(PDO::FETCH_ASSOC);

// Set headers for CSV download
header('Content-Type: text/csv; charset=utf-8');
header('Content-Disposition: attachment; filename="submissions_' . date('Ymd_His') . '.csv"');

// Open output stream
$output = fopen('php://output', 'w');

// Write CSV header
$headers = [
    'ID',
    'Surname',
    'First Name',
    'Other Names',
    'Telephone',
    'Email',
    'Position/Rank',
    'Short Courses (RMU)',
    'ISPS/GMA Familiarisation',
    'Attachment',
    'Medicals',
    'Sea Experience',
    'Total Sea Experience (Years)',
    'Last Ship Type',
    'Submitted Date'
];
fputcsv($output, $headers);

// Write data rows
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
        $app['attachment'],
        $app['medicals'],
        $app['sea_experience'],
        $app['total_sea_experience_years'],
        $app['last_ship_type'] ?? '',
        date('F d, Y H:i:s', strtotime($app['submitted_at']))
    ]);
}

fclose($output);
exit;
?>
