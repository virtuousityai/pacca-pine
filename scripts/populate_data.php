#!/usr/bin/env php
<?php
/**
 * Pacca PINE - Synthetic Data Population Script
 *
 * Creates:
 * - 100 clinic facilities
 * - 500 providers with varied specialties
 * - Appointments from today through July 31, 2026
 * - 30 internal messages
 * - 5 procedure providers
 *
 * Run inside Docker: php /var/www/localhost/htdocs/openemr/scripts/populate_data.php
 */

$host = getenv('MYSQL_HOST') ?: 'mysql';
$user = getenv('MYSQL_ROOT_USER') ?: 'root';
$pass = getenv('MYSQL_ROOT_PASS') ?: 'root';
$db   = getenv('MYSQL_DATABASE') ?: 'openemr';

$pdo = new PDO("mysql:host=$host;dbname=$db;charset=utf8mb4", $user, $pass, [
    PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
]);

echo "Connected to database.\n";

// ──────────────────────────────────────────────────────────────────
// HELPERS
// ──────────────────────────────────────────────────────────────────

function uuid_bytes() {
    return random_bytes(16);
}

$specialties = [
    'Family Medicine', 'Internal Medicine', 'Pediatrics', 'Cardiology',
    'Dermatology', 'Emergency Medicine', 'Endocrinology', 'Gastroenterology',
    'General Surgery', 'Geriatrics', 'Hematology', 'Infectious Disease',
    'Nephrology', 'Neurology', 'Obstetrics & Gynecology', 'Oncology',
    'Ophthalmology', 'Orthopedics', 'Otolaryngology', 'Pathology',
    'Physical Medicine', 'Psychiatry', 'Pulmonology', 'Radiology',
    'Rheumatology', 'Sports Medicine', 'Urology', 'Allergy & Immunology',
    'Anesthesiology', 'Pain Management', 'Plastic Surgery', 'Podiatry',
    'Vascular Surgery', 'Neonatology', 'Palliative Care', 'Urgent Care'
];

$titles = ['Dr.', 'Dr.', 'Dr.', 'Dr.', 'NP', 'PA', 'DO'];

$first_names = [
    'James','Mary','Robert','Patricia','John','Jennifer','Michael','Linda','David','Elizabeth',
    'William','Barbara','Richard','Susan','Joseph','Jessica','Thomas','Sarah','Christopher','Karen',
    'Charles','Lisa','Daniel','Nancy','Matthew','Betty','Anthony','Margaret','Mark','Sandra',
    'Donald','Ashley','Steven','Dorothy','Paul','Kimberly','Andrew','Emily','Joshua','Donna',
    'Kenneth','Michelle','Kevin','Carol','Brian','Amanda','George','Melissa','Timothy','Deborah',
    'Ronald','Stephanie','Edward','Rebecca','Jason','Sharon','Jeffrey','Laura','Ryan','Cynthia',
    'Jacob','Kathleen','Gary','Amy','Nicholas','Angela','Eric','Shirley','Jonathan','Anna',
    'Stephen','Brenda','Larry','Pamela','Justin','Emma','Scott','Nicole','Brandon','Helen',
    'Benjamin','Samantha','Samuel','Katherine','Raymond','Christine','Gregory','Debra','Frank','Rachel',
    'Alexander','Carolyn','Patrick','Janet','Jack','Catherine','Dennis','Maria','Jerry','Heather',
    'Priya','Raj','Wei','Mei','Omar','Fatima','Hiroshi','Yuki','Carlos','Sofia',
    'Ahmed','Aisha','Sanjay','Anita','Min','Jin','Luis','Isabella','Pedro','Valentina',
    'Amit','Deepa','Hassan','Layla','Kenji','Sakura','Diego','Camila','Tariq','Nadia',
    'Ravi','Sunita','Chen','Xiao','Miguel','Lucia','Ali','Sara','Takeshi','Hana',
    'Vikram','Priti','Mohammed','Zara','Koji','Aya','Fernando','Elena','Yusuf','Leila',
];

$last_names = [
    'Smith','Johnson','Williams','Brown','Jones','Garcia','Miller','Davis','Rodriguez','Martinez',
    'Hernandez','Lopez','Gonzalez','Wilson','Anderson','Thomas','Taylor','Moore','Jackson','Martin',
    'Lee','Perez','Thompson','White','Harris','Sanchez','Clark','Ramirez','Lewis','Robinson',
    'Walker','Young','Allen','King','Wright','Scott','Torres','Nguyen','Hill','Flores',
    'Green','Adams','Nelson','Baker','Hall','Rivera','Campbell','Mitchell','Carter','Roberts',
    'Patel','Shah','Kim','Park','Chen','Wang','Liu','Zhang','Singh','Kumar',
    'Tanaka','Nakamura','Sato','Yamamoto','Watanabe','Mueller','Schmidt','Fischer','Weber','Wagner',
    'Johansson','Eriksson','Larsson','Nilsson','Petrov','Ivanov','Popov','Sokolov','Morales','Reyes',
    'Cruz','Ortiz','Gutierrez','Chavez','Ramos','Vargas','Castillo','Jimenez','Romero','Diaz',
    'Ali','Ahmed','Hassan','Khan','Rahman','Okafor','Mensah','Nkosi','Adeyemi','Ibrahim',
];

$clinic_prefixes = [
    'Pacca PINE', 'Alpine', 'Evergreen', 'Summit', 'Pinecrest', 'Sierra',
    'Redwood', 'Cedar', 'Juniper', 'Aspen', 'Birchwood', 'Oakdale',
    'Maplewood', 'Willow Creek', 'Lakeside', 'Riverside', 'Valley View',
    'Mountain View', 'Sunridge', 'Horizon', 'Meadowbrook', 'Crestview',
    'Clearwater', 'Stonebridge', 'Harbor', 'Beacon', 'Crossroads', 'Compass',
    'Northstar', 'Trailhead', 'Canyon', 'Bluebird', 'Foxwood', 'Serenity'
];

$clinic_suffixes = [
    'Medical Center', 'Health Clinic', 'Family Practice', 'Wellness Center',
    'Care Center', 'Health Partners', 'Medical Group', 'Primary Care',
    'Community Health', 'Healthcare', 'Medical Associates', 'Health Hub'
];

$cities = [
    ['San Francisco','CA','94102'],['Los Angeles','CA','90001'],['New York','NY','10001'],
    ['Chicago','IL','60601'],['Houston','TX','77001'],['Phoenix','AZ','85001'],
    ['Philadelphia','PA','19101'],['San Antonio','TX','78201'],['San Diego','CA','92101'],
    ['Dallas','TX','75201'],['Austin','TX','78701'],['Jacksonville','FL','32099'],
    ['Columbus','OH','43085'],['Charlotte','NC','28201'],['Indianapolis','IN','46201'],
    ['Denver','CO','80201'],['Seattle','WA','98101'],['Nashville','TN','37201'],
    ['Portland','OR','97201'],['Las Vegas','NV','89101'],['Atlanta','GA','30301'],
    ['Miami','FL','33101'],['Minneapolis','MN','55401'],['Tampa','FL','33601'],
    ['Boston','MA','02101'],['Raleigh','NC','27601'],['Salt Lake City','UT','84101'],
    ['Pittsburgh','PA','15201'],['Cincinnati','OH','45201'],['Kansas City','MO','64101'],
];

$facility_colors = [
    '#8b6cc1','#6aab7b','#7eb8da','#f2c078','#e09891','#5a9e8e',
    '#d4615e','#6b4fa0','#b8a4d8','#93d3a2','#ffb347','#87ceeb',
];

$streets = [
    '100 Main St','250 Oak Ave','500 Elm Blvd','123 Pine Rd','789 Cedar Ln',
    '456 Maple Dr','321 Birch Way','654 Walnut St','987 Spruce Ave','135 Ash Blvd',
    '246 Cherry Ln','357 Poplar Dr','468 Willow Ct','579 Cypress Rd','680 Sequoia Way',
];

$phone_area = ['415','310','212','312','713','602','215','210','619','214',
               '512','904','614','704','317','303','206','615','503','702'];

// ──────────────────────────────────────────────────────────────────
// 1. CREATE 100 CLINIC FACILITIES
// ──────────────────────────────────────────────────────────────────
echo "\n=== Creating 100 Clinic Facilities ===\n";

$facilityIds = [];
$stmt = $pdo->prepare("INSERT INTO facility (uuid, name, phone, street, city, state, postal_code, country_code, service_location, billing_location, color, primary_business_entity, inactive, organization_type) VALUES (?, ?, ?, ?, ?, ?, ?, 'US', 1, 1, ?, 0, 0, 'prov')");

for ($i = 0; $i < 100; $i++) {
    $prefix = $clinic_prefixes[$i % count($clinic_prefixes)];
    $suffix = $clinic_suffixes[$i % count($clinic_suffixes)];
    $num = ($i < count($clinic_prefixes)) ? '' : ' ' . chr(65 + intdiv($i, count($clinic_prefixes)));
    $name = "$prefix $suffix$num";

    $city = $cities[$i % count($cities)];
    $area = $phone_area[$i % count($phone_area)];
    $phone = "($area) " . rand(200,999) . '-' . str_pad(rand(0,9999), 4, '0', STR_PAD_LEFT);
    $street = ($i * 10 + rand(100,999)) . ' ' . explode(' ', $streets[$i % count($streets)], 2)[1];
    $color = $facility_colors[$i % count($facility_colors)];

    $stmt->execute([uuid_bytes(), $name, $phone, $street, $city[0], $city[1], $city[2], $color]);
    $facilityIds[] = $pdo->lastInsertId();

    if (($i + 1) % 25 == 0) echo "  Created $(" . ($i+1) . ") facilities...\n";
}
echo "  Created 100 facilities.\n";

// ──────────────────────────────────────────────────────────────────
// 2. CREATE 500 PROVIDERS
// ──────────────────────────────────────────────────────────────────
echo "\n=== Creating 500 Providers ===\n";

$providerIds = [];
$stmt = $pdo->prepare("INSERT INTO users (uuid, username, fname, lname, title, specialty, facility_id, active, authorized, npi, email, taxonomy, calendar, cal_ui) VALUES (?, ?, ?, ?, ?, ?, ?, 1, 1, ?, ?, '207Q00000X', 1, 1)");

for ($i = 0; $i < 500; $i++) {
    $fn = $first_names[$i % count($first_names)];
    $ln = $last_names[$i % count($last_names)];
    // Ensure unique names
    if ($i >= count($first_names)) {
        $fn = $first_names[rand(0, count($first_names)-1)];
    }
    $title = $titles[$i % count($titles)];
    $specialty = $specialties[$i % count($specialties)];
    $facId = $facilityIds[$i % count($facilityIds)];
    $npi = '1' . str_pad($i + 1000, 9, '0', STR_PAD_LEFT);
    $username = strtolower($fn) . '.' . strtolower($ln) . ($i >= 150 ? $i : '');
    $email = strtolower($fn) . '.' . strtolower($ln) . '@paccapine.health';

    $stmt->execute([uuid_bytes(), $username, $fn, $ln, $title, $specialty, $facId, $npi, $email]);
    $providerIds[] = $pdo->lastInsertId();

    if (($i + 1) % 100 == 0) echo "  Created " . ($i+1) . " providers...\n";
}
echo "  Created 500 providers.\n";

// ──────────────────────────────────────────────────────────────────
// 3. CREATE APPOINTMENTS (today → July 31, 2026)
// ──────────────────────────────────────────────────────────────────
echo "\n=== Creating Appointments ===\n";

// Get all patient IDs
$patientIds = $pdo->query("SELECT pid FROM patient_data")->fetchAll(PDO::FETCH_COLUMN);
$numPatients = count($patientIds);
echo "  Found $numPatients patients for scheduling.\n";

// Appointment categories to use (with their durations in seconds)
$apptCats = [
    ['id' => 5,  'name' => 'Office Visit',                'dur' => 900],
    ['id' => 9,  'name' => 'Established Patient',         'dur' => 900],
    ['id' => 10, 'name' => 'New Patient',                  'dur' => 1800],
    ['id' => 12, 'name' => 'Health and Behavioral Assess', 'dur' => 900],
    ['id' => 13, 'name' => 'Preventive Care Services',     'dur' => 900],
    ['id' => 14, 'name' => 'Ophthalmological Services',    'dur' => 900],
    ['id' => 23, 'name' => 'Urgent Care',                  'dur' => 1800],
];

// Appointment statuses for past/present/future
$pastStatuses   = ['>', '$', '>', '>', '$', '>'];  // checked out, coding done
$todayStatuses  = ['@', '<', '>', '-', '@', '<', '!', '#', '<', '>'];  // mix: arrived, in exam, checked out, none
$futureStatuses = ['-', '-', '-', '^', 'AVM', '-']; // none, pending, confirmed

// Start and end dates
$startDate = new DateTime('2026-03-28');
$endDate   = new DateTime('2026-07-31');

// Start times for appointments (8:00 AM to 5:00 PM, 15 min slots)
$slotTimes = [];
for ($h = 8; $h <= 16; $h++) {
    for ($m = 0; $m < 60; $m += 15) {
        if ($h == 16 && $m > 30) break;
        $slotTimes[] = sprintf('%02d:%02d:00', $h, $m);
    }
}

$today = new DateTime('2026-03-28');
$totalAppts = 0;
$batchSize = 5000;

$stmt = $pdo->prepare("INSERT INTO openemr_postcalendar_events (uuid, pc_catid, pc_multiple, pc_aid, pc_pid, pc_title, pc_time, pc_eventDate, pc_endDate, pc_duration, pc_startTime, pc_endTime, pc_apptstatus, pc_facility, pc_eventstatus, pc_sharing) VALUES (?, ?, 0, ?, ?, ?, NOW(), ?, ?, ?, ?, ?, ?, ?, 1, 1)");

$currentDate = clone $startDate;
$pdo->beginTransaction();

while ($currentDate <= $endDate) {
    $dateStr = $currentDate->format('Y-m-d');
    $dayOfWeek = (int)$currentDate->format('w'); // 0=Sun, 6=Sat
    $isWeekend = ($dayOfWeek == 0 || $dayOfWeek == 6);
    $isPast = ($currentDate < $today);
    $isToday = ($currentDate->format('Y-m-d') === $today->format('Y-m-d'));

    // On weekends, only ~20 providers do urgent care (8 appts each)
    // On weekdays, all 500 providers with 8-12 appts
    if ($isWeekend) {
        $activeProviders = array_slice($providerIds, 0, 20);
        $apptRange = [4, 8];
    } else {
        // Use a rotating subset of ~100 providers per day for performance
        $dayIndex = ($currentDate->format('z')) % 5; // 0-4
        $startIdx = $dayIndex * 100;
        $activeProviders = array_slice($providerIds, $startIdx, 100);
        $apptRange = [8, 12];
    }

    foreach ($activeProviders as $provId) {
        $numAppts = rand($apptRange[0], $apptRange[1]);
        // Pick random time slots (no overlap)
        $availSlots = $slotTimes;
        shuffle($availSlots);
        $selectedSlots = array_slice($availSlots, 0, $numAppts);
        sort($selectedSlots);

        foreach ($selectedSlots as $startTime) {
            $cat = $isWeekend
                ? $apptCats[6]  // Urgent care on weekends
                : $apptCats[rand(0, 5)];

            $dur = $cat['dur'];
            $pid = $patientIds[rand(0, $numPatients - 1)];
            $facId = $facilityIds[rand(0, count($facilityIds) - 1)];

            // Calculate end time
            $st = DateTime::createFromFormat('H:i:s', $startTime);
            $et = clone $st;
            $et->modify('+' . ($dur / 60) . ' minutes');
            $endTime = $et->format('H:i:s');

            // Status based on date
            if ($isPast) {
                $status = $pastStatuses[rand(0, count($pastStatuses) - 1)];
            } elseif ($isToday) {
                $status = $todayStatuses[rand(0, count($todayStatuses) - 1)];
            } else {
                $status = $futureStatuses[rand(0, count($futureStatuses) - 1)];
            }

            $stmt->execute([
                uuid_bytes(),
                $cat['id'],
                $provId,
                $pid,
                $cat['name'],
                $dateStr,
                $dateStr,
                $dur,
                $startTime,
                $endTime,
                $status,
                $facId,
            ]);
            $totalAppts++;
        }
    }

    if ($totalAppts % $batchSize < 200) {
        $pdo->commit();
        $pdo->beginTransaction();
        echo "  $dateStr — $totalAppts appointments created...\n";
    }

    $currentDate->modify('+1 day');
}

$pdo->commit();
echo "  Total appointments created: $totalAppts\n";

// ──────────────────────────────────────────────────────────────────
// 4. CREATE 5 PROCEDURE PROVIDERS
// ──────────────────────────────────────────────────────────────────
echo "\n=== Creating 5 Procedure Providers ===\n";

$procProviders = [
    ['Quest Diagnostics',          '1234567890', 'Clinical Laboratory'],
    ['LabCorp',                    '0987654321', 'Clinical Laboratory'],
    ['Regional Imaging Associates','1122334455', 'Radiology'],
    ['National Pathology Group',   '5566778899', 'Pathology'],
    ['BioReference Laboratories',  '6677889900', 'Clinical Laboratory'],
];

$stmt = $pdo->prepare("INSERT INTO procedure_providers (uuid, name, npi, active, DorP, direction, protocol, notes, type) VALUES (?, ?, ?, 1, 'D', 'B', 'DL', ?, ?)");

foreach ($procProviders as $pp) {
    $stmt->execute([uuid_bytes(), $pp[0], $pp[1], "External $pp[2] provider", $pp[2]]);
    echo "  Created: {$pp[0]}\n";
}

// ──────────────────────────────────────────────────────────────────
// 5. CREATE 30 INTERNAL MESSAGES
// ──────────────────────────────────────────────────────────────────
echo "\n=== Creating 30 Internal Messages ===\n";

$msgTemplates = [
    ['Lab Results Ready',        "Lab results for patient are now available. CBC shows normal values. Please review and sign off at your earliest convenience."],
    ['Referral Request',         "Requesting referral to cardiology for patient with persistent chest discomfort. EKG was normal but symptoms continue. Please advise."],
    ['Prescription Renewal',     "Patient requesting renewal of Lisinopril 10mg. Last BP reading was 128/82. Labs from last month were within normal limits."],
    ['Follow-up Reminder',       "Reminder: Patient is due for 3-month diabetes follow-up. Last A1C was 7.2%. Please schedule at your earliest convenience."],
    ['Prior Authorization',      "Prior auth needed for MRI of lumbar spine. Patient has had 6 weeks of physical therapy with no improvement. Documenting medical necessity."],
    ['Patient Callback Request', "Patient called requesting callback regarding recent test results. Preferred callback time: afternoon. Contact number on file."],
    ['Consultation Note',        "Thank you for the referral. Patient was evaluated for suspected rheumatoid arthritis. Started on Methotrexate 15mg weekly. Will follow up in 4 weeks."],
    ['Urgent: Abnormal Lab',     "URGENT: Patient's potassium level is 5.8 mEq/L. Please review immediately and advise on next steps. Patient has been notified to return to clinic."],
    ['Imaging Report',           "CT scan of abdomen/pelvis completed. Impression: No acute findings. Small hepatic cyst noted, likely benign. Recommend follow-up ultrasound in 6 months."],
    ['Care Coordination',        "Patient discharged from hospital yesterday following pneumonia admission. Needs follow-up within 7 days. Current medications updated in chart."],
    ['Medication Interaction',   "Alert: Potential drug interaction identified between newly prescribed Fluconazole and patient's current Warfarin. Please review and adjust dosing if needed."],
    ['Insurance Verification',   "Patient's insurance has changed effective March 1st. New carrier: BlueCross PPO. Policy verified and updated in system. No referral required for specialists."],
    ['Staff Meeting Reminder',   "Monthly staff meeting this Thursday at 12:30 PM in Conference Room B. Agenda: Q1 quality metrics review, new EHR features demo, and flu season prep."],
    ['Patient Education',        "New patient education materials for diabetes management have been uploaded to the shared drive. Please distribute to relevant patients during visits."],
    ['Equipment Maintenance',    "The spirometry machine in Exam Room 3 is due for calibration next week. Please route patients needing PFTs to Exam Room 1 until maintenance is complete."],
];

$msgStatuses = ['New', 'New', 'Read', 'Read', 'Done', 'New'];
$stmt = $pdo->prepare("INSERT INTO pnotes (date, body, pid, user, groupname, activity, authorized, title, assigned_to, message_status) VALUES (?, ?, ?, ?, 'Default', 1, 1, ?, ?, ?)");

for ($i = 0; $i < 30; $i++) {
    $msg = $msgTemplates[$i % count($msgTemplates)];
    $fromProvider = rand(0, min(count($providerIds)-1, 49));
    $toProvider = rand(0, min(count($providerIds)-1, 49));
    while ($toProvider == $fromProvider) $toProvider = rand(0, min(count($providerIds)-1, 49));

    // Get usernames
    $fromUser = $pdo->query("SELECT username FROM users WHERE id=" . $providerIds[$fromProvider])->fetchColumn();
    $toUser = $pdo->query("SELECT username FROM users WHERE id=" . $providerIds[$toProvider])->fetchColumn();

    $pid = $patientIds[rand(0, $numPatients - 1)];
    $daysAgo = rand(0, 14);
    $date = (new DateTime('2026-03-28'))->modify("-$daysAgo days")->format('Y-m-d H:i:s');
    $status = $msgStatuses[rand(0, count($msgStatuses) - 1)];

    $stmt->execute([$date, $msg[1], $pid, $fromUser, $msg[0], $toUser, $status]);
}
echo "  Created 30 messages.\n";

// ──────────────────────────────────────────────────────────────────
// SUMMARY
// ──────────────────────────────────────────────────────────────────
echo "\n========================================\n";
echo "Data Population Complete!\n";
echo "========================================\n";
echo "Facilities:          100\n";
echo "Providers:           500\n";
echo "Appointments:        $totalAppts\n";
echo "Procedure Providers: 5\n";
echo "Messages:            30\n";
echo "========================================\n";
