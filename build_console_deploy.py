"""
Build deploy artifacts for the public Console GitHub Pages repo.

Outputs:
- docs/_deploy_index.html  : standalone login page (hand-authored, no injection)
- docs/_deploy_console.html: copy of api/static/console.html with a gate-check shim
                              that bounces unauthenticated visitors back to the login.
"""
import pathlib

SRC = pathlib.Path("api/static/console.html")
LOGIN_SRC = pathlib.Path("api/static/login.html")
OUT_INDEX = pathlib.Path("docs/_deploy_index.html")
OUT_CONSOLE = pathlib.Path("docs/_deploy_console.html")

# Auth shim injected at the very top of <head> in the deployed console.html.
# Runs before any other script. If session is not authenticated, redirect to login.
AUTH_SHIM = """
<script>
(function(){
  try {
    if (!sessionStorage.getItem("insynbio_gate_auth")) {
      window.location.replace("./");
    }
  } catch (e) {
    window.location.replace("./");
  }
})();
</script>
"""

# --- Build login page (index.html) ------------------------------------------
login_html = LOGIN_SRC.read_text(encoding="utf-8")
OUT_INDEX.write_text(login_html, encoding="utf-8")
print(f"Written: {OUT_INDEX} ({OUT_INDEX.stat().st_size:,} bytes)")

# --- Build console page (console.html) --------------------------------------
console_html = SRC.read_text(encoding="utf-8")

# Insert auth shim immediately after <head> (so it runs first)
head_marker = "<head>"
idx = console_html.find(head_marker)
if idx < 0:
    raise RuntimeError("Marker not found: <head>")
insert_pos = idx + len(head_marker)
console_html = console_html[:insert_pos] + "\n" + AUTH_SHIM + console_html[insert_pos:]

# Update build marker
console_html = console_html.replace(
    "<!-- AbEngineCore console UI build: api-not-configured-banner-20260426-v24 -->",
    "<!-- AbEngineCore console UI build: api-not-configured-banner-deploy-20260426-v24 -->",
)

OUT_CONSOLE.write_text(console_html, encoding="utf-8")
print(f"Written: {OUT_CONSOLE} ({OUT_CONSOLE.stat().st_size:,} bytes)")
