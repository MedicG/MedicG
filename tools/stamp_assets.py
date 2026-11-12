"""Set ?v=<content hash> on every local CSS/JS referenced by index.html.

Run after changing any file in assets/ (tests/test_assets.py fails if a stamp is stale).
Assets are then cached by browsers for a year: a new hash means a new URL."""
import hashlib, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATTERN = re.compile(r'((?:src|href)=")(assets/(?:css|js)/[^"?]+)(?:\?v=[^"]*)?(")')


def digest(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()[:10]


def stamped(html):
    return PATTERN.sub(lambda m: f"{m.group(1)}{m.group(2)}?v={digest(m.group(2))}{m.group(3)}", html)


INNER = {  # assets loaded at runtime by other assets: (file, referenced asset)
    "assets/js/growth.js": "assets/js/growth-data.js",
}


def stamp_inner(check):
    ok = True
    for holder, ref in INNER.items():
        path = ROOT / holder
        text = path.read_text(encoding="utf-8")
        new = re.sub(re.escape(ref) + r"\?v=[A-Za-z0-9]*", f"{ref}?v={digest(ref)}", text)
        if new != text:
            ok = False
            if not check:
                path.write_bytes(new.encode("utf-8"))
    return ok


def main(check=False):
    inner_ok = stamp_inner(check)
    index = ROOT / "index.html"
    html = index.read_text(encoding="utf-8")
    new = stamped(html)
    if check:
        return inner_ok and new == html
    if new != html:
        index.write_bytes(new.encode("utf-8"))
    print("index.html assets stamped")
    return True


if __name__ == "__main__":
    sys.exit(0 if main(check="--check" in sys.argv) else 1)
