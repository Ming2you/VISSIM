import json
for T in (1500, 1650, 1800):
    d = json.load(open(r'D:/VISSIM-runs-window264-s29-9000-recovery-20261007/sdmpc/decisions_sdmpc31_sdmpc9000_s29/action_%06d.json' % T, encoding='utf-8'))
    md = d['metadata']
    seq = md.get('sdmpc_prediction_sequence') or d.get('sdmpc_prediction_sequence')
    out = []
    if isinstance(seq, list):
        for b in seq[:3]:
            v = b.get('vsl') if isinstance(b, dict) else None
            out.append(v.get('FW_E__seg13') if isinstance(v, dict) else (type(b).__name__, list(b.keys())[:8] if isinstance(b, dict) else None))
    print(T, 'top vsl', (d.get('vsl') or {}).get('FW_E__seg13') if isinstance(d.get('vsl'), dict) else type(d.get('vsl')).__name__, 'seq', type(seq).__name__, out)
