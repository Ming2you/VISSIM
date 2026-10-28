import csv, json, hashlib, os, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
W = "D:/VISSIM-merge/k8_gate_trees/codexhandoff/a49981ff"
G = "D:/VISSIM-merge/sim3-n31-k8"
BS = chr(92)
HERE = os.path.dirname(os.path.abspath(__file__))


def sha(p):
    try:
        return hashlib.sha256(open(p, 'rb').read()).hexdigest()[:12]
    except Exception:
        return 'MISSING'


def ispath(x):
    return isinstance(x, str) and ('/' in x or BS in x) and x.rsplit('.', 1)[-1] in ('json', 'vbs', 'inpx')


rows = list(csv.DictReader(open(os.path.join(HERE, 'cfg_leaf_diff.csv'), encoding='utf-8')))
for r in rows:
    if r['kind'] != 'diff':
        continue
    try:
        cv = json.loads(r['codex']); ov = json.loads(r['ours'])
    except Exception:
        continue
    cl = cv if isinstance(cv, list) else [cv]
    ol = ov if isinstance(ov, list) else [ov]
    if cl and all(ispath(x) for x in cl):
        cs = [sha(os.path.join(W, x.replace(BS, '/'))) for x in cl]
        os_ = [sha(os.path.join(G, x.replace(BS, '/'))) for x in ol]
        print(r['pointer'], 'SAME_BYTES' if cs == os_ else 'DIFF_BYTES', cs, os_)
