"""Verify that all upstream files outside the documented VSM edits are intact."""
from pathlib import Path
import hashlib
import json

root = Path(__file__).resolve().parents[1]
base = json.loads((root / 'provenance/VSM_BASE.json').read_text())
expected = json.loads((root / 'provenance/VSM_UPSTREAM_FILES.json').read_text())
allowed = set(base['modified_upstream_files'])
checked = 0
for relative, sha in expected.items():
    path = root / relative
    assert path.is_file(), f'Missing upstream file: {relative}'
    if relative in allowed:
        continue
    content = path.read_bytes()
    actual = hashlib.sha1(b'blob ' + str(len(content)).encode() + b'\0' + content).hexdigest()
    assert actual == sha, f'Unexpected upstream change: {relative}'
    checked += 1
assert len(expected) == base['upstream_files']
print(f'PASS: {checked} unchanged upstream files; {len(allowed)} documented VSM integration edits')
