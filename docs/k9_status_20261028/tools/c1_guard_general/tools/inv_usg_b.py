# -*- coding: utf-8 -*-
"""inv_usg_b.py (guard/general, 2026-10-27 KST) — read-only: codex USG configure output in one B decision JSON.

Usage: python -B inv_usg_b.py <action_json> <out.json>
Extracts /metadata/joint_leader_selection/urban_storage_guard/observation (lanes, signals, policy) as written by
codex urban_storage_guard.configure (CX USG:13-99). Writes only <out.json>.
"""
import hashlib, json, os, sys
src, out = sys.argv[1], sys.argv[2]
raw = open(src, 'rb').read()
t = raw.decode('utf-8')
j = t.index('"joint_leader_selection"')
i = t.index('"urban_storage_guard": {', j)
u, _ = json.JSONDecoder().raw_decode(t, i + len('"urban_storage_guard": '))
o = u['observation']
res = {'tool': 'inv_usg_b.py', 'source_sha256': hashlib.sha256(raw).hexdigest(), 'source_name': os.path.basename(src),
       'observation_keys': sorted(o), 'policy': o.get('policy'), 'schema': o.get('schema'), 'scope': o.get('scope'),
       'observed_sec': o.get('observed_sec'), 'signals': o.get('signals'), 'lanes': o.get('lanes'),
       'blocks_len': len(u.get('blocks', []))}
tmp = out + '.tmp'
open(tmp, 'w', encoding='utf-8').write(json.dumps(res, ensure_ascii=False, indent=1, sort_keys=True))
os.replace(tmp, out)
print(len(o.get('lanes', [])), 'lanes', sorted(o.get('signals', {})))
print(hashlib.sha256(open(out, 'rb').read()).hexdigest())
