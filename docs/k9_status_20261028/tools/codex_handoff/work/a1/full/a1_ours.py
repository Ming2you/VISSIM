# a1_ours.py - per-link residence 0-8100 s in both integration forms (ours / codex) for A1, codex joint and LNC,
# using the scanner and integrators of omega701_recount.py (sha-checked import, functions scan_fzp / integ_ours / integ_codex).
# usage: python -B a1_ours.py [--smoke]      (--smoke: 'a1' = codex joint FZP)
# LNC is read from the existing OMEGA701 cache (cache/lnc_64cf_s29.npz), not rescanned. Read-only toward all FZP.
import hashlib, json, os, sys, time
sys.dont_write_bytecode = True
import numpy as np  # noqa: E402

SMOKE = '--smoke' in sys.argv
W0 = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/codex_handoff/work'
OM = W0 + '/omega'
OM_SHA = '5b7826f65c58a883c2dc4a3eccd6de92563bb12f812dd0d6579be8a42c92a5ac'
JOINT = 'D:/VISSIM_handoff/20261024/raw/joint/sdmpc/vissim_eval/sdmpc31_sdmpc8100_s29_001.fzp'
A1 = JOINT if SMOKE else 'D:/VISSIM_runs/20261025_codex_a1_s29/sdmpc/vissim_eval/sdmpc31_sdmpc8100_s29_001.fzp'
OUT = W0 + '/a1/full/ours_a1' + ('_smoke' if SMOKE else '') + '.json'
T_END = 8100.0


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 22), b''):
            h.update(b)
    return h.hexdigest()


if sha(OM + '/omega701_recount.py') != OM_SHA:
    raise SystemExit('omega701_recount.py sha mismatch')
sys.path.insert(0, OM)
import omega701_recount as O  # noqa: E402
print('priority', O.set_below_normal(), flush=True)
res = {'smoke': SMOKE, 'om_sha': OM_SHA, 'runs': {}}
t0 = time.time()
for tag, path in (('a1', A1), ('joint', JOINT)):
    O.acquire_lock('a1_ours_' + tag)
    try:
        arrays, meta = O.scan_fzp(path)
    finally:
        O.release_lock()
    res['runs'][tag] = {'meta': meta, 'arrays': arrays}
    print(tag, meta['rows'], meta['frames'], meta['last_sec'], round(time.time() - t0, 1), flush=True)
z = np.load(OM + '/cache/lnc_64cf_s29.npz')
res['runs']['lnc'] = {'meta': json.load(open(OM + '/cache/lnc_64cf_s29.json', encoding='utf-8')), 'arrays': {k: z[k] for k in z.files}}
out = {'smoke': SMOKE, 'om_sha': OM_SHA, 'T_end': T_END, 'runs': {}}
for tag, r in res['runs'].items():
    c = r['arrays']
    ours, im = O.integ_ours(c, T_END)
    cdx, cm = O.integ_codex(c, T_END)
    links = [str(int(x)) for x in c['links']]
    out['runs'][tag] = {'meta': {k: v for k, v in r['meta'].items() if not isinstance(v, (bytes,))}, 'ours_window': im, 'codex_window': cm,
                        'ours': {l: float(v) for l, v in zip(links, ours)}, 'codex': {l: float(v) for l, v in zip(links, cdx)}}
json.dump(out, open(OUT, 'w'), indent=0)
print('done', round(time.time() - t0, 1), {t: (round(sum(v['ours'].values()), 3), round(sum(v['codex'].values()), 3)) for t, v in out['runs'].items()})
