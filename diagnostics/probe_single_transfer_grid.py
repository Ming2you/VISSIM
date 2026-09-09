"""Legacy CLI name for the installed-production single-transfer grid.

The shared driver now imports canonical code; no separate body exists here.
"""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'diagnostics')]
from probe_all_area_snapshots import main

if __name__ == '__main__':
    main()
