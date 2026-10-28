# A0: which files of the ORIGINAL frozen tree (evidence/original_FREEZE.json) are absent from the
# handoff code subset but referenced by name from code/config text inside the subset?
import csv, json, os, re, collections
BS = chr(92)
FRZ = json.load(open('D:/VISSIM_handoff/20261024/evidence/original_FREEZE.json', encoding='utf-8'))['files']
SUB = set(r['path'] for r in csv.DictReader(open('D:/VISSIM_handoff/20261024/code/handoff/SOURCE_FILES.csv', encoding='utf-8-sig')))
CODE = 'D:/VISSIM-merge/k8_gate_trees/codexhandoff/a0/code'
missing = {p: h for p, h in FRZ.items() if p not in SUB}
by_base = collections.defaultdict(list)
for p in missing:
    by_base[p.rsplit('/', 1)[-1].lower()].append(p)
tok = re.compile(r'[A-Za-z0-9_\-./' + re.escape(BS) + r']+\.(?:json|csv|py|inpx|sig|vbs|txt|yaml|yml|pickle|pkl|npz|npy|md)', re.I)
hits = collections.defaultdict(set)
scan_roots = ['evaluation', 'plant', 'vendor', 'scripts', 'outputs', 'network', 'harness', 'tools',
              'diagnostics/repin_v3c3_review_20261001/urban_rm269', 'diagnostics/sdmpc_n31_20260924/integration_20260926/selected']
for root in scan_roots:
    for dp, dn, fn in os.walk(CODE + '/' + root):
        for f in fn:
            if not f.lower().endswith(('.py', '.json', '.vbs', '.ps1', '.csv', '.yaml', '.yml')):
                continue
            p = os.path.join(dp, f)
            if os.path.getsize(p) > 30_000_000:
                continue
            rel = os.path.relpath(p, CODE).replace(BS, '/')
            try:
                txt = open(p, encoding='utf-8', errors='ignore').read()
            except Exception:
                continue
            for t in set(tok.findall(txt)):
                b = t.replace(BS, '/').rsplit('/', 1)[-1].lower()
                if b in by_base:
                    for cand in by_base[b]:
                        tt = t.replace(BS, '/').lstrip('./')
                        exact = cand.endswith(tt) if '/' in tt else False
                        hits[cand].add((rel, t, exact))
out = []
for cand, refs in sorted(hits.items()):
    ex = any(e for _, _, e in refs)
    out.append({'missing_path': cand, 'sha256': missing[cand], 'path_suffix_match': ex,
                'referenced_from': sorted(set(r for r, _, _ in refs))[:12], 'n_refs': len(refs)})
json.dump({'freeze_files': len(FRZ), 'subset': len(SUB), 'missing_from_subset': len(missing), 'referenced_missing': out},
          open('C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/codex_handoff/work/a0/s6_missing_refs.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('freeze', len(FRZ), 'subset', len(SUB), 'missing', len(missing), 'referenced_missing', len(out), 'suffix-exact', sum(o['path_suffix_match'] for o in out))
for o in out:
    if o['path_suffix_match'] and not o['missing_path'].startswith('diagnostics/'):
        print(' ', o['missing_path'], o['referenced_from'][:4])
