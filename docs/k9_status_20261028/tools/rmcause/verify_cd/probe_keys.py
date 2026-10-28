import json, sys
p = sys.argv[1]
j = json.load(open(p, encoding='utf-8-sig'))
targets = ('local_rows','gradient_rows','trials','candidate_rows','pfo','dual_updates','central_rows','sdmpc_state','control_sequence','neighbor','leader')
found = []
def walk(o, path, depth):
    if depth > 7: return
    if isinstance(o, dict):
        for k, v in o.items():
            if k == 'source_sha256': continue
            np_ = path + '/' + str(k)
            if any(t in str(k) for t in targets):
                ln = len(v) if hasattr(v, '__len__') and not isinstance(v, str) else ''
                found.append((np_, type(v).__name__, ln))
            walk(v, np_, depth+1)
    elif isinstance(o, list) and o and depth < 7:
        walk(o[0], path + '[0]', depth+1)
walk(j, '', 0)
for f in found[:80]: print(*f)
