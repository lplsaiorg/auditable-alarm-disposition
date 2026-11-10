"""Run the frozen, standard-library-only paper result verifier from any directory."""
from pathlib import Path
import hashlib
import json
import runpy
import sys

if __name__ == '__main__':
    if not __debug__:
        sys.exit('Verification requires assertions. Run Python without -O or -OO.')
    saved = Path(__file__).resolve().parents[1] / 'saved_results'
    extra = json.loads((saved / 'public_additions_manifest.json').read_text(encoding='utf-8'))
    for name, expected in extra.items():
        if hashlib.sha256((saved / name).read_bytes()).hexdigest() != expected:
            sys.exit('Public additional artifact hash mismatch: ' + name)
    print(json.dumps({'additional_public_files_verified': len(extra)}))
    verifier = saved / 'verify_results_20261106_v02.py'
    runpy.run_path(str(verifier), run_name='__main__')
