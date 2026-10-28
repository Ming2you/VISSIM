"""ReviewDeclare A30: the amendment-30 persistence VR call (section 2.3: the same VR f3fcc574, the same 21 VR states
1200 ... 7950, the same stage arguments) on v3c3-s43 instead of v3c3-s47, to see whether the VR measures every one of
these windows (the base call stopped at T = 600 < U4 T_FROM).  No v3c3-s47 data.  Output root
TK/a30review/vr_s43_21 (new).  Prints rc, seconds, the state keys present and whether each m1_T450 is an int; no
VISSIM value is printed.

    python -B rv_vr30.py <dest.json>
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

PY = r'C:\Users\TRLAB\AppData\Local\Programs\Python\Python312\python.exe'
BELOW_NORMAL = 0x00004000
TREE = Path(r'D:/VISSIM-merge/k8_gate_trees/k92b1/a27/k92t')
SA = TREE / 'diagnostics/sdmpc_n31_20260924/k8_gates/sa'
OUT = Path(r'D:/VISSIM-merge/k8_gate_trees/k92b1/a30review/vr_s43_21')
A24 = 'd46db6dc3959b19525f0fce77ead5432682e3de0ef8060cdc3da09661559aadc'
VR_STATES = (1200, 1500, 1950, 2850, 3300, 3450, 4200, 4650, 5100, 5550, 5700, 6000, 6150, 6450, 6600, 6900, 7050,
             7350, 7500, 7800, 7950)


def main():
    if OUT.exists():
        raise SystemExit('%s exists' % OUT)
    OUT.mkdir(parents=True)
    logp = OUT / 'vr.log'
    env = {k: v for k, v in os.environ.items() if not k.upper().startswith(('RW_', 'K8_', 'K8G_', 'K92A_'))}
    env.update(PYTHONHASHSEED='0', PYTHONDONTWRITEBYTECODE='1', PYTHONUTF8='1', K8G_ROOT=str(TREE), K8G_OUT=str(OUT))
    argv = [PY, '-B', str(SA / 'k92_vissim_ref.py'), '--root', str(TREE), '--out', str(OUT), '--states',
            '43:' + ','.join(str(t) for t in VR_STATES), '--gates-stage', 'k92t', '--declaration-sha', A24]
    t0 = time.time()
    with open(logp, 'w', encoding='utf-8', errors='replace') as f:
        rc = subprocess.run(argv, cwd=str(SA), env=env, stdout=f, stderr=subprocess.STDOUT,
                            creationflags=BELOW_NORMAL).returncode
    res = {'schema': 'rv30-vr/v1', 'rc': rc, 'sec': round(time.time() - t0, 1), 'states_asked': list(VR_STATES)}
    p = OUT / 'sa' / 'k92_vissim_ref.json'
    if p.is_file():
        d = json.loads(p.read_text(encoding='utf-8'))
        st = ((d.get('seeds') or {}).get('s43') or {}).get('states') or {}
        res['state_keys'] = sorted(int(k) for k in st if str(k).isdigit())
        res['all_states_present'] = res['state_keys'] == sorted(VR_STATES)
        res['m1_T450_int'] = all(isinstance((st.get(str(t)) or {}).get('m1_T450'), int) for t in VR_STATES)
    lines = [x for x in logp.read_text(encoding='utf-8', errors='replace').splitlines() if x.strip()]
    res['last_line_head'] = (lines[-1][:60] if lines else None)
    Path(sys.argv[1]).write_text(json.dumps(res, indent=1, sort_keys=True) + '\n', encoding='utf-8', newline='\n')
    print('RV30_VR ' + json.dumps({k: res.get(k) for k in ('rc', 'sec', 'all_states_present', 'm1_T450_int')}),
          flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
