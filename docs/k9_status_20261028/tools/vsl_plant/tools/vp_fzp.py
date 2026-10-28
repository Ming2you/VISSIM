"""FZP sources and FZP scan jobs for PRE_VP (light; reads run records only, never an FZP).

    python -B vp_fzp.py sources <out.json>      enumerate the 12 FZP (arms NC3, VSL, V-A, B x three seeds)
    python -B vp_fzp.py jobs <sources.json> <jobs.json>

Seeds: NC3 / VSL run.json `seed`, B / V-A run_provenance `seed` (never a folder name).  Labels: <arm>_v3c3-s<seed>.
Scanners (read only, run through vp_pinned.py by sha):
  vsl_cell_scan.py (fa5aeafd...): 31 cells x 60 s windows x lanes over the whole run -> GT/out/fzp_cell/<label>.json.
      NC3 and VSL outputs already exist (vsl_v3c3/out/cell, D-K9-95 work) and are reused by sha when their `fzp`
      field is the same file; B and V-A are scanned new.
  o2_fzp_cells.py (cff42e34...): 31 cells per 5 s frame, t in [1700, 7700] s, V-A only -> GT/out/fzp_frames/<label>.json.
"""
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import vp_common as C  # noqa: E402

EXISTING_CELL = C.SP / 'vsl_v3c3' / 'out' / 'cell'
FRAME_LO, FRAME_HI = 1700.0, 7700.0


DECLARED = {'NC3': ['s31_v3c3nc', 's41_v3c3nc', 's43_v3c3nc'], 'VSL': ['s31', 's41', 's43'],
            'B': ['s31', 's41', 's43'],
            'VA': ['sdmpc31_v3c3_k92va_s31', 'sdmpc31_v3c3_k92va_s41', 'sdmpc31_v3c3_k92va_s43']}


def sources():
    """Only the declared folders are opened (no directory glob: sealed / blind seeds are never touched)."""
    rows = []
    for name in DECLARED['NC3']:
        d = C.RUN_ROOTS['nc3'] / name
        C.blind_guard(d)
        rec = d / 'run' / 'run.json'
        fzp = sorted((d / 'run' / 'vissim_eval').glob('*.fzp'))
        rows.append(('NC3', C.read_json(rec)['seed'], rec, fzp))
    for name in DECLARED['VSL']:
        d = C.RUN_ROOTS['vsl'] / name
        C.blind_guard(d)
        rec = d / 'run' / 'run.json'
        fzp = sorted((d / 'run' / 'vissim_eval').glob('*.fzp'))
        rows.append(('VSL', C.read_json(rec)['seed'], rec, fzp))
    for name in DECLARED['B']:
        run = C.RUN_ROOTS['b'] / name / 'sdmpc'
        C.blind_guard(run)
        seed, prov, _ = C.provenance_seed(run)
        fzp = sorted((run / 'vissim_eval').glob('*.fzp'))
        rows.append(('B', seed, prov, fzp))
    for name in DECLARED['VA']:
        d = C.RUN_ROOTS['va'] / name
        C.blind_guard(d)
        seed, prov, _ = C.provenance_seed(d)
        fzp = sorted((d / 'vissim_eval').glob('*.fzp'))
        rows.append(('VA', seed, prov, fzp))
    existing = {}
    for p in sorted(EXISTING_CELL.glob('*.json')):
        doc = C.read_json(p) or {}
        existing[str(Path(doc.get('fzp', '')).resolve()).lower()] = (p, doc.get('fzp_sha256'))
    out = []
    for arm, seed, rec, fzp in rows:
        if seed not in (31, 41, 43):
            continue
        if len(fzp) != 1:
            raise SystemExit('expected one FZP for %s seed %d, found %d' % (arm, seed, len(fzp)))
        label = '%s_v3c3-s%d' % (arm, seed)
        key = str(fzp[0].resolve()).lower()
        row = {'arm': arm, 'seed': seed, 'label': label, 'record': str(rec), 'record_sha256': C.sha256_file(rec),
               'fzp': str(fzp[0]), 'fzp_bytes': fzp[0].stat().st_size}
        if key in existing:
            p, fsha = existing[key]
            row.update(cell_scan_reuse=str(p), cell_scan_sha256=C.sha256_file(p), fzp_sha256_from_scan=fsha)
        else:
            row['cell_scan_out'] = str(C.OUT / 'fzp_cell' / (label + '.json'))
        if arm == 'VA':
            row['frame_scan_out'] = str(C.OUT / 'fzp_frames' / (label + '.json'))
        out.append(row)
    if len(out) != 12 or sorted({(r['arm'], r['seed']) for r in out}) != sorted(
            (a, s) for a in ('B', 'NC3', 'VA', 'VSL') for s in (31, 41, 43)):
        raise SystemExit('FZP source set is not 4 arms x 3 seeds: %s' % [(r['arm'], r['seed']) for r in out])
    return {'schema': 'vp-fzp-sources/1', 'made_kst': C.kst(), 'frame_window': [FRAME_LO, FRAME_HI], 'sources': out}


def jobs(src, name='fzp'):
    js = []
    for r in src['sources']:
        if 'cell_scan_out' in r:
            js.append({'tag': 'cell_' + r['label'], 'kind': 'py',
                       'args': [str(C.TOOLS / 'vp_pinned.py'), C.CELL_SCAN_SHA, str(C.CELL_SCAN), r['label'], r['fzp'],
                                str(Path(r['cell_scan_out']).parent)]})
        if 'frame_scan_out' in r:
            js.append({'tag': 'frames_' + r['label'], 'kind': 'py',
                       'args': [str(C.TOOLS / 'vp_pinned.py'), C.O2_CELLS_SHA, str(C.O2_CELLS), r['label'], r['fzp'],
                                str(Path(r['frame_scan_out']).parent), str(FRAME_LO), str(FRAME_HI)]})
    return {'name': name, 'jobs': js}


if __name__ == '__main__':
    if sys.argv[1] == 'sources':
        C.write_json(sys.argv[2], sources())
        print('VP_FZP_SOURCES written')
    elif sys.argv[1] == 'jobs':
        C.write_json(sys.argv[3], jobs(C.read_json(sys.argv[2])))
        print('VP_FZP_JOBS written')
