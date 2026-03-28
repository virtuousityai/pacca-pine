<?php

/**
 * AJAX helper for the AI Coding Agent.
 * Returns the SOAP note and active conditions for a given encounter.
 *
 * @package   OpenEMR
 * @link      https://www.open-emr.org
 * @author    Pacca PINE AI <ai@virtuosityai.com>
 * @copyright Copyright (c) 2026 Virtuosity AI
 * @license   https://github.com/openemr/openemr/blob/master/LICENSE GNU General Public License 3
 */

require_once(__DIR__ . "/../../interface/globals.php");

use OpenEMR\Common\Csrf\CsrfUtils;

header('Content-Type: application/json');

$pid = (int)($_GET['pid'] ?? 0);
$encounter = (int)($_GET['encounter'] ?? 0);

if (!$pid || !$encounter) {
    echo json_encode(['error' => 'Missing pid or encounter']);
    exit;
}

// Fetch SOAP note for this encounter
$soap = [
    'subjective' => '',
    'objective' => '',
    'assessment' => '',
    'plan' => '',
];

$soapRow = sqlQuery(
    "SELECT fs.subjective, fs.objective, fs.assessment, fs.plan
     FROM form_soap fs
     JOIN forms f ON f.form_id = fs.id AND f.formdir = 'soap' AND f.deleted = 0
     WHERE f.encounter = ? AND f.pid = ?
     ORDER BY fs.date DESC LIMIT 1",
    [$encounter, $pid]
);

if ($soapRow) {
    $soap['subjective'] = $soapRow['subjective'] ?? '';
    $soap['objective'] = $soapRow['objective'] ?? '';
    $soap['assessment'] = $soapRow['assessment'] ?? '';
    $soap['plan'] = $soapRow['plan'] ?? '';
}

// Fetch active conditions for this patient (limit to 5 to keep payload small)
$conditions = [];
$condRows = sqlStatement(
    "SELECT DISTINCT title FROM lists
     WHERE pid = ? AND type = 'medical_problem'
       AND (enddate IS NULL OR enddate = '' OR enddate >= CURDATE())
     ORDER BY title
     LIMIT 5",
    [$pid]
);
while ($row = sqlFetchArray($condRows)) {
    $conditions[] = $row['title'];
}

$soap['conditions'] = implode(', ', $conditions);

echo json_encode($soap);
