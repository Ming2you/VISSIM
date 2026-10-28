"""Stop-rule check of one finished plant job (PRE_VP section 7; booleans and reasons only, no plant value printed).

    python -B vp_jobcheck.py <job_dir> <mode A|P|S> <out.json>

Checks: probe errors / stop (S-ERR, S-R1), R1 objective bit-equal and costs <= 1e-9 (S-R1), R3 repack bit-equal
(S-R3), null ablation bit-equal (S-NULL, modes P and S), every scalar evaluation used by the tables has exactly one
hook record with 450 steps, t = T..T+449, 150 steps per block, 31 cells and no hook error (S-HOOK), plant cell
boundaries within 1 m of CELL_B (S-MAP), ablation values seen by the worker (S-REACH).  Exit 0 = no rule hit,
2 = a rule hit (the queue then writes STOP_VP)."""
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import vp_common as C  # noqa: E402
import vp_analyze as A  # noqa: E402


def main():
    jd, mode, out_path = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
    probe = C.read_json(jd / 'probe.json') or {}
    hits = []
    if not probe:
        hits.append('S-ERR: no probe.json')
    if probe.get('errors'):
        hits.append('S-ERR: probe errors %s' % probe['errors'][:2])
    if probe.get('stop'):
        hits.append('S-R1: %s' % probe['stop'])
    ck = probe.get('checks') or {}
    if ck.get('R1_objective_bit_equal') is not True or ck.get('R1_costs_within_1e-9') is not True:
        hits.append('S-R1: R1 objective %s costs %s' % (ck.get('R1_objective_bit_equal'), ck.get('R1_costs_within_1e-9')))
    if ck.get('R3_repack_bit_equal') is not True:
        hits.append('S-R3: %s' % ck.get('R3_repack_bit_equal'))
    if mode in ('P', 'S') and ck.get('null_bit_equal') is not True:
        hits.append('S-NULL: %s' % ck.get('null_bit_equal'))
    T = int(((probe.get('spec') or {}).get('state') or {}).get('T', -1))
    labels = ['R2_REC_scalar', 'EXEC_scalar']
    if mode in ('A', 'S'):
        labels += ['ARM%d_scalar' % v for v in A.ARMS]
    if mode in ('P', 'S'):
        labels += ['ABL_%s' % n for n in ['null'] + A.ABLATIONS]
    hooks = {}
    for lab in labels:
        h, why = A.hook_for(jd, probe, lab)
        ok, why2 = A.hook_ok(h, T) if h is not None else (False, why)
        hooks[lab] = {'ok': ok, 'why': why or why2}
        if not ok:
            hits.append('S-HOOK: %s %s' % (lab, why or why2))
        elif lab == 'EXEC_scalar':
            mok, mwhy = A.map_ok(h)
            if not mok:
                hits.append('S-MAP: %s' % mwhy)
        if h is not None and lab.startswith('ABL_'):
            name = lab[len('ABL_'):]
            rok, rwhy = A.reach(((probe.get('ablations') or {}).get(lab) or {}), h, name)
            hooks[lab]['reach_ok'] = rok
            if not rok:
                hits.append('S-REACH: %s %s' % (lab, rwhy))
    rec = {'schema': 'vp-jobcheck/1', 'kst': C.kst(), 'job': jd.name, 'mode': mode, 'hits': hits,
           'checks': {k: v for k, v in ck.items() if isinstance(v, bool)}, 'hooks': hooks,
           'probe_sha256': C.sha256_file(jd / 'probe.json') if (jd / 'probe.json').is_file() else None}
    C.write_json(out_path, rec)
    print('JOBCHECK %s mode=%s hits=%d' % (jd.name, mode, len(hits)))
    for h in hits:
        print('  ' + h)
    return 2 if hits else 0


if __name__ == '__main__':
    sys.exit(main())
