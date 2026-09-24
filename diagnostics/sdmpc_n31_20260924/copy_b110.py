"""C1: byte copies of the chosen b110 calibration artifacts into this worktree.

Plant choice (evidence/PLANT_CHOICE_20260924.md): boundary family, baseline FD,
no FD refit. Files keep their B110-relative paths so the reference config's
freeway.segment_params and the freeze code pins resolve unchanged.

Checks (plan C1):
- parameters.json sha == freeze.json parameters_sha256
- geometry.json geometry_profile relocates into this worktree
  (canonical_harness.resolve_geometry_profile) with its pinned sha
- the reference config's segment_params path is the copied file

Run from the worktree root:  python -B diagnostics/sdmpc_n31_20260924/copy_b110.py [--check]
The source workspace is read only. An existing destination must be identical.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SOURCE_ROOT = Path(r'D:\VISSIM-merge\sim3')
WORKSPACE = 'diagnostics/demand_sweep/user_native_20260914/metanet_calibration_v1/res10_b110_20260923'
FILES = (
    WORKSPACE + '/train_s31_v2nc/boundary_literature_v1/boundary_config.json',
    WORKSPACE + '/train_s31_v2nc/boundary_literature_v1/boundary_fit/parameters.json',
    WORKSPACE + '/train_s31_v2nc/boundary_literature_v1/boundary_fit/freeze.json',
    WORKSPACE + '/train_s31_v2nc/free_speed_b110/segment_params.json',
    WORKSPACE + '/observations/s31_v2nc_observations/geometry.json',
)
BOUNDARY_CONFIG, PARAMETERS, FREEZE, SEGMENT_PARAMS, GEOMETRY = FILES
RECEIPT = Path(__file__).resolve().parent / 'b110_copy_receipt.json'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def check(root=ROOT):
    from diagnostics.demand_sweep.user_native_20260914.metanet_calibration_v1.canonical_harness import resolve_geometry_profile
    freeze = json.loads((root / FREEZE).read_text(encoding='utf-8-sig'))
    if sha(root / PARAMETERS) != freeze['parameters_sha256']:
        raise ValueError('parameters.json differs from its freeze pin')
    pinned = {k.replace('\\', '/'): v for k, v in freeze['code_pins'].items()}
    if pinned.get(SEGMENT_PARAMS) != sha(root / SEGMENT_PARAMS):
        raise ValueError('segment_params.json differs from its freeze code pin')
    geometry = json.loads((root / GEOMETRY).read_text(encoding='utf-8-sig'))
    profile = resolve_geometry_profile(geometry['geometry_profile'], repository_root=root)
    config = json.loads((root / BOUNDARY_CONFIG).read_text(encoding='utf-8-sig'))
    if config['freeway']['segment_params'] != SEGMENT_PARAMS:
        raise ValueError('Boundary config does not use the copied b110 segment params')
    refined = geometry['refined_partition']
    parts = str(refined['path']).replace('\\', '/').split('/')
    local = root.joinpath(*parts[parts.index('diagnostics'):])
    if sha(local) != refined['sha256']:
        raise ValueError('Refined partition named by the calibration geometry differs in this worktree')
    return {'geometry_profile': str(profile.relative_to(root)).replace('\\', '/'),
            'refined_partition': str(local.relative_to(root)).replace('\\', '/'),
            'parameters_sha256': freeze['parameters_sha256']}


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--check', action='store_true', help='verify existing copies only')
    parser.add_argument('--source-root', type=Path, default=SOURCE_ROOT)
    args = parser.parse_args()
    rows = []
    for rel in FILES:
        src, dst = args.source_root / rel, ROOT / rel
        data = src.read_bytes()
        if dst.exists():
            if dst.read_bytes() != data:
                raise SystemExit('Destination differs from the B110 source: ' + rel)
        elif args.check:
            raise SystemExit('Missing copy: ' + rel)
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(data)
        rows.append({'path': rel, 'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data),
                     'source': str(src)})
    receipt = {'schema': 'sdmpc31-b110-copy/v1', 'plant_choice': 'boundary family, baseline FD (no FD refit)',
               'files': rows, 'checks': check()}
    text = json.dumps(receipt, indent=2, ensure_ascii=False) + '\n'
    if args.check:
        if RECEIPT.read_text(encoding='utf-8') != text:
            raise SystemExit('Copy receipt differs')
    else:
        RECEIPT.write_bytes(text.encode('utf-8'))
    print('B110_COPY_OK files=%d' % len(rows))


if __name__ == '__main__':
    main()
