# Restore files that the original frozen tree had (evidence/original_FREEZE.json) but the handoff
# code subset lacks. Bytes are accepted ONLY if sha256 equals the freeze record.
# Sources are read-only: GWT8 working tree, git blobs of D:/VISSIM-merge/repo (raw and CRLF variants).
import hashlib, json, os, subprocess, sys
A0 = 'D:/VISSIM-merge/k8_gate_trees/codexhandoff/a0'
REC = A0 + '/RESTORED_FILES.json'
FRZ = json.load(open('D:/VISSIM_handoff/20261024/evidence/original_FREEZE.json', encoding='utf-8'))['files']
TREES = ['D:/VISSIM-merge/sim3-n31-k8']
COMMITS = ['ca181e843058872ac4726758625e5c4057daba5f', '886a014a303dd155e05cc33041796822abbc29b0']
REPO = 'D:/VISSIM-merge/repo'
rec = json.load(open(REC, encoding='utf-8')) if os.path.exists(REC) else []
done = {r['path'] for r in rec}
for rel in sys.argv[1:]:
    rel = rel.replace(chr(92), '/')
    if rel in done:
        print('already', rel)
        continue
    want = FRZ.get(rel)
    if want is None:
        print('NOT_IN_FREEZE', rel)
        continue
    got = None
    for t in TREES:
        p = t + '/' + rel
        if os.path.isfile(p):
            b = open(p, 'rb').read()
            if hashlib.sha256(b).hexdigest() == want:
                got = (b, 'tree:' + p)
                break
    if got is None:
        for c in COMMITS:
            r = subprocess.run(['git', '-C', REPO, 'show', c + ':' + rel], capture_output=True)
            if r.returncode != 0:
                continue
            for variant, b in (('raw', r.stdout), ('crlf', r.stdout.replace(b'\r\n', b'\n').replace(b'\n', b'\r\n'))):
                if hashlib.sha256(b).hexdigest() == want:
                    got = (b, 'git:%s:%s' % (c[:8], variant))
                    break
            if got:
                break
    if got is None:
        print('NO_MATCHING_BYTES', rel, want)
        continue
    dst = A0 + '/code/' + rel
    if os.path.exists(dst):
        print('EXISTS_IN_A0', rel)
        continue
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    open(dst, 'wb').write(got[0])
    rec.append({'path': rel, 'sha256': want, 'bytes': len(got[0]), 'source': got[1]})
    print('restored', rel, want[:12], got[1])
json.dump(rec, open(REC, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
