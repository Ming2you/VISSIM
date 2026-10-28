# POST-DATA reading (written after the A0b results were seen; not part of the predeclared tools).
# Reads a few scalar fields of joint.json /selection for replay vs record, all 11 T. Descriptive only.
import json, sys
A0 = 'D:/VISSIM-merge/k8_gate_trees/codexhandoff/a0/out/a0b_hsw'
DEC = 'decisions_sdmpc31_sdmpc8100_s29'
REC = 'D:/VISSIM_handoff/20261024/raw/joint/sdmpc/' + DEC
KEYS = ('held_objective', 'warm_start_objective', 'selected_objective', 'prediction_ttt_reduction', 'sdmpc_after_pfo_rollouts', 'selection_status')
out = []
for T in range(1050, 2551, 150):
    t6 = '%06d' % T
    a = json.load(open(A0 + '/T' + t6 + '/files/sdmpc/' + DEC + '/action_' + t6 + '.joint.json', encoding='utf-8-sig'))['selection']
    b = json.load(open(REC + '/action_' + t6 + '.joint.json', encoding='utf-8-sig'))['selection']
    row = {'T': T}
    for k in KEYS:
        va, vb = a.get(k), b.get(k)
        row[k] = [va, vb, (va - vb) if isinstance(va, (int, float)) and isinstance(vb, (int, float)) and not isinstance(va, bool) else None]
    out.append(row)
json.dump(out, open(sys.argv[1], 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
for r in out:
    print(r['T'], {k: (v[2] if v[2] is not None else (v[0] == v[1])) for k, v in r.items() if k != 'T'}, 'sel', r['selected_objective'][:2])
