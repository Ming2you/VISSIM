"""Arm tunings of the C1 P0 / probe (amendment C1 section 2.1 '팔'): base OUC (c20aff1d bytes c8e3ee2c...) plus the
top-level key c1_port holding only the arm's sub-keys (values = C1D/declared/c1_port_section.json, its key order).
OFF = the OUC bytes themselves.  Serialisation = OUC's own form (json.dumps indent 2, ensure_ascii False, + LF).

    python -B c1_arms.py            -> TOOLS/arms/<arm>.json (exclusive create) + TOOLS/arms/ARMS.json (names, keys, sha)"""
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import c1common as C  # noqa: E402

M = ('meter_neighbor_audit', 'max_leader_candidates', 'allow_zero_green', 'storage_release_guard', 'held_retention')
ARMS = {'off': (), 'omega': ('omega701',), 'm': M, 'h': ('head_service',),
        'c1': ('omega701',) + M + ('head_service',),
        'm_cap1': tuple(k for k in M if k != 'max_leader_candidates'),
        'm_noheld': tuple(k for k in M if k != 'held_retention'),
        'c1m': ('omega701',) + tuple(k for k in M if k != 'meter_neighbor_audit') + ('head_service',),
        'azg': ('allow_zero_green',), 'srg': ('storage_release_guard',), 'hr': ('held_retention',),
        'mlc': ('max_leader_candidates',)}
LABEL = {'off': 'OFF', 'omega': 'Ω', 'm': 'M', 'h': 'H', 'c1': 'C1', 'm_cap1': 'M_cap1', 'm_noheld': 'M_noheld',
         'c1m': 'C1⁻', 'azg': '{allow_zero_green}', 'srg': '{storage_release_guard}', 'hr': '{held_retention}',
         'mlc': '{max_leader_candidates}'}


def main():
    ouc_bytes = C.git_show(C.OUC_REL)
    if C.sha256_bytes(ouc_bytes) != C.OUC_SHA:
        raise SystemExit('OUC sha differs')
    ouc = json.loads(ouc_bytes)
    if C.data(ouc) != ouc_bytes:
        raise SystemExit('OUC is not in data() form')
    sec_raw = (C.DECL / 'c1_port_section.json').read_bytes()
    if C.sha256_bytes(sec_raw) != '865cc354e498f1c77894f376e249682d52ee082639eaa585ec13af5f0d059654':
        raise SystemExit('c1_port_section.json sha differs')
    section = json.loads(sec_raw)['c1_port']
    out = {'schema': 'c1-probe-arms/v1', 'base': {'name': 'config_n31_v2.json', 'sha256': C.OUC_SHA}, 'arms': {}}
    for arm, keys in ARMS.items():
        if arm == 'off':
            payload = ouc_bytes
        else:
            doc = dict(ouc)
            doc['c1_port'] = {k: section[k] for k in section if k in keys}
            if list(doc['c1_port']) != [k for k in section if k in keys] or set(doc['c1_port']) != set(keys):
                raise SystemExit('arm keys differ: ' + arm)
            payload = C.data(doc)
        digest = C.write_new(C.TOOLS / 'arms' / (arm + '.json'), payload)
        out['arms'][arm] = {'label': LABEL[arm], 'keys': list(keys), 'sha256': digest}
    C.write_new(C.TOOLS / 'arms' / 'ARMS.json', json.dumps(out, indent=1, ensure_ascii=False) + '\n')
    print('C1_ARMS ok n=%d' % len(out['arms']))


if __name__ == '__main__':
    main()
