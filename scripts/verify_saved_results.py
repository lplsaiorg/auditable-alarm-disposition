"""Run the frozen, standard-library-only paper result verifier from any directory."""
from pathlib import Path
import runpy
import sys

if __name__ == '__main__':
    if not __debug__:
        sys.exit('Verification requires assertions. Run Python without -O or -OO.')
    verifier = Path(__file__).resolve().parents[1] / 'saved_results' / 'verify_results_20261106_v02.py'
    runpy.run_path(str(verifier), run_name='__main__')
