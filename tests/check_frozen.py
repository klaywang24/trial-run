"""Fail if config.yaml (the executable copy of the methodology) changed without updating FROZEN.sha256.
A rule change must be a dated `methodology:` commit that updates config.yaml, FROZEN.sha256 and ERRATA.md together."""
import hashlib, pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parents[1]
got = hashlib.sha256((ROOT / "config.yaml").read_bytes()).hexdigest()
want = (ROOT / "FROZEN.sha256").read_text().split()[0]
if got != want:
    sys.exit(f"config.yaml changed: sha256 {got} != frozen {want}. Rules are frozen; see METHODOLOGY section 9.")
print(f"config.yaml frozen ok ({got[:12]})")
