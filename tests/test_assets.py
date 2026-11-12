"""Static checks: cache-busting stamps, icons, accessibility basics and security headers."""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import stamp_assets  # noqa: E402


def main():
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    assert stamp_assets.main(check=True), "Run: python3 tools/stamp_assets.py (asset versions are stale)"
    for ref in re.findall(r'(?:src|href)="(assets/(?:css|js)/[^"]+)"', html):
        assert "?v=" in ref and (ROOT / ref.split("?")[0]).exists(), ref
    icons_css = (ROOT / "assets/css/icons.css").read_text()
    sources = html + "".join(p.read_text(errors="ignore") for p in (ROOT / "assets/js").glob("*.js"))
    used = set(re.findall(r"\bti-([a-z0-9]+(?:-[a-z0-9]+)*)", sources))
    missing = sorted(n for n in used if f".ti-{n}{{" not in icons_css)
    assert not missing, f"Icons missing in icons.css (run tools/build_icons.py): {missing}"
    assert "cdn.jsdelivr.net" not in html and "tabler-icons" not in html, "icons must be self-hosted"
    assert '<meta name="description"' in html and 'lang="es"' in html
    unlabeled = [m for m in re.findall(r'<label class="field-lbl"(?![^>]*\bfor=)[^>]*>', html)]
    assert len(unlabeled) < 15, f"{len(unlabeled)} field labels without for="
    assert re.search(r'<script defer src="assets/js/app\.js', html)
    headers = {h["key"]: h["value"] for rule in json.loads((ROOT / "vercel.json").read_text())["headers"] if rule["source"] == "/(.*)" for h in rule["headers"]}
    for key in ("Strict-Transport-Security", "Content-Security-Policy", "X-Content-Type-Options", "Referrer-Policy", "Permissions-Policy", "X-Frame-Options"):
        assert key in headers, key
    csp = headers["Content-Security-Policy"]
    assert "object-src 'none'" in csp and "frame-ancestors 'none'" in csp and "camera=(self)" in headers["Permissions-Policy"]
    for host in set(re.findall(r'<(?:script|link)\b[^>]*?(?:src|href)="(https://[^/"]+)', html)):
        assert host in csp or host == "https://fonts.gstatic.com", f"{host} not allowed by the CSP"
    print("PASS assets: stamped versions, self-hosted icons, labels, deferred scripts, security headers and CSP")


if __name__ == "__main__":
    main()
