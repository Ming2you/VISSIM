# v_reloc.py — VERIFY_VSL (2026-10-27 KST). Relocate text paths in OUR copy of the O1 input (state, provenance,
# .applied receipt) from the authors' work folders to ours, so the run never reads/writes the authors' folders.
# Writes only under D:/VISSIM-merge/k8_gate_trees/vsl_v3c3/verify_o1.
import sys, json
BS = '\\'
OLD_RUN = r'D:\VISSIM-merge\k8_gate_trees\vsl_v3c3\o1o2\runs\o1_b43_T001800'
NEW_RUN = r'D:\VISSIM-merge\k8_gate_trees\vsl_v3c3\verify_o1\runs\b43_T001800'
OLD_CODE = r'D:\VISSIM-merge\k8_gate_trees\vsl_v3c3\o1o2\codeB1'
NEW_CODE = r'D:\VISSIM-merge\k8_gate_trees\vsl_v3c3\verify_o1\codeB1'
SD = NEW_RUN + r'\sdmpc'
assert SD.startswith(r'D:\VISSIM-merge\k8_gate_trees\vsl_v3c3\verify_o1')
esc = lambda s: s.replace(BS, BS + BS)
rep = {}
for rel in (r'\decisions_sdmpc31_sdmpc9000_s43\state_001800.json', r'\run_provenance_sdmpc31_sdmpc9000_s43.json'):
    p = SD + rel
    raw = open(p, 'rb').read()
    bom = raw.startswith(b'\xef\xbb\xbf')
    t = raw.decode('utf-8-sig')
    n1, n2 = t.count(esc(OLD_RUN)), t.count(esc(OLD_CODE))
    t = t.replace(esc(OLD_RUN), esc(NEW_RUN)).replace(esc(OLD_CODE), esc(NEW_CODE))
    json.loads(t)
    left = t.count('o1o2' + BS + BS)
    open(p, 'wb').write((b'\xef\xbb\xbf' if bom else b'') + t.encode('utf-8'))
    rep[rel] = dict(run=n1, code=n2, left_o1o2=left)
p = SD + r'\decisions_sdmpc31_sdmpc9000_s43\action_001650.json.applied'
t = open(p, 'rb').read().decode('utf-16')
n = t.count(OLD_RUN)
t = t.replace(OLD_RUN, NEW_RUN)
open(p, 'wb').write(t.encode('utf-16'))
rep['applied'] = dict(run=n)
print(json.dumps(rep))
