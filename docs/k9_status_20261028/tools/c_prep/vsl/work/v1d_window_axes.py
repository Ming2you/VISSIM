# V1d (VSL_OFFLINE, data-after declaration): count coordinate kinds and written VSL in codex window/off
# decision JSONs at T=1800 (read only) - checks whether a fixed VSL schedule leaves any VSL axis.
import json, collections
for arm in ('window', 'off'):
    o = json.load(open(f'D:/VISSIM_handoff/20261024/raw/{arm}/sdmpc/decisions_sdmpc31_sdmpc8100_s29/action_001800.json', encoding='utf-8'))
    j = o['metadata'].get('joint_leader_selection') or {}
    print(arm, 'coord kinds', dict(collections.Counter(c['kind'] for c in j.get('coordinates', []))),
          'policy fixed_vsl', json.dumps((j.get('policy') or {}).get('fixed_vsl'))[:300],
          'written FW_E__seg13', (o.get('vsl') or {}).get('FW_E__seg13'), 'grad vsl rows', sum(1 for g in j.get('gradient_rows', []) if g.get('kind') == 'vsl'))
