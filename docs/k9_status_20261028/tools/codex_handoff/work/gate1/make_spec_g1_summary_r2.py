# writes spec_g1_summary_r2.json: g1_summary.py -> g1_summary_r2.py, one change after the data (read the freeze-verify
# capture as UTF-16 when it starts with a UTF-16 BOM; Windows PowerShell 5.1 '>' writes UTF-16LE). Nothing else changes.
import json
W = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/codex_handoff/work/gate1'
old = "    t = open(fv, encoding='utf-8', errors='replace').read()"
new = ("    raw_fv = open(fv, 'rb').read()   # r2: PS 5.1 '>' writes UTF-16LE with BOM\n"
       "    t = raw_fv.decode('utf-16') if raw_fv[:2] in (b'\\xff\\xfe', b'\\xfe\\xff') else raw_fv.decode('utf-8', errors='replace')")
spec = [{'src': W + '/g1_summary.py', 'dst': W + '/g1_summary_r2.py',
         'why': 'r2 after data: freeze_verify_after.txt is UTF-16LE (PS 5.1 redirection); r1 read it as UTF-8 and missed FREEZE_VERIFIED',
         'reps': [[old, new]]}]
json.dump(spec, open(W + '/spec_g1_summary_r2.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('ok')
