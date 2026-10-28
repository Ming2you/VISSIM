import json
for T in (1500, 1650, 1800):
    d = json.load(open(r'D:/VISSIM-runs-window264-s29-9000-recovery-20261007/sdmpc/decisions_sdmpc31_sdmpc9000_s29/action_%06d.json' % T, encoding='utf-8'))
    fut = d['diagnostics']['sdmpc_prediction_sequence']['future']
    b0 = (d.get('vsl') or {}).get('FW_E__seg13')
    fv = []
    for b in (fut if isinstance(fut, list) else fut.values()):
        v = b.get('vsl') if isinstance(b, dict) else None
        fv.append(v.get('FW_E__seg13') if isinstance(v, dict) else (list(b.keys())[:6] if isinstance(b, dict) else b))
    print(T, 'block0', b0, 'future', fv[:3])
