"""Pediatric growth charts: WHO formulas (Node) and head circumference in vital signs."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from medicg.clinical_docs import clean_vitals, DocsError  # noqa: E402


def main():
    out = subprocess.run(["node", str(ROOT / "tests/growth_check.cjs")], capture_output=True, text=True)
    assert out.returncode == 0, out.stderr or out.stdout
    print(out.stdout.strip())
    values = clean_vitals({"peso": "3.4", "talla": "50", "perimetroCefalico": "34,5"})
    assert values == {"peso": 3.4, "talla": 50.0, "perimetroCefalico": 34.5, "imc": 13.6}, values
    try:
        clean_vitals({"perimetroCefalico": "90"})
        raise AssertionError("out of range head circumference accepted")
    except DocsError:
        pass
    print("PASS growth: head circumference stored with vital signs")


if __name__ == "__main__":
    main()
