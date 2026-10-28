# Bulk restore: every original-freeze file under the given top folders that is missing from a0/code,
# accepted ONLY when bytes from a read-only source hash to the freeze sha256.
# Sources: GWT8 working tree; git blobs (ca181e84, 886a014a) in D:/VISSIM-merge/repo (raw + CRLF).
import hashlib, json, os, subprocess, sys
A0 = 'D:/VISSIM-merge/k8_gate_trees/codexhandoff/a0'
CODE = A0 + '/code'
REC = A0 + '/RESTORED_FILES.json'
FRZ = json.load(open('D:/VISSIM_handoff/20261024/evidence/original_FREEZE.json', encoding='utf-8'))['files']
TREE = 'D:/VISSIM-merge/sim3-n31-k8'
COMMITS = ['ca181e843058872ac4726758625e5c4057daba5f', '886a014a303dd155e05cc33041796822abbc29b0']
tops = sys.argv[1].split(',')
extra = sys.argv[2:]
rec = json.load(open(REC, encoding='utf-8')) if os.path.exists(REC) else []
done = {r['path'] for r in rec}
todo = [p for p in FRZ if (p.split('/')[0] in tops or p in extra) and not os.path.exists(CODE + '/' + p) and p not in done]
print('todo', len(todo))
git = subprocess.Popen(['git', '-C', 'D:/VISSIM-merge/repo', 'cat-file', '--batch'], stdin=subprocess.PIPE, stdout=subprocess.PIPE)


def blob(spec):
    git.stdin.write((spec + '\n').encode('utf-8'))
    git.stdin.flush()
    head = git.stdout.readline().decode('utf-8', 'replace').rstrip('\n')
    if head.endswith('missing') or ' ' not in head:
        return None
    size = int(head.split()[-1])
    data = git.stdout.read(size)
    git.stdout.read(1)
    return data


stats = {'tree': 0, 'git': 0, 'none': 0}
nomatch = []
for rel in todo:
    want = FRZ[rel]
    got = None
    p = TREE + '/' + rel
    if os.path.isfile(p) and os.path.getsize(p) < 600_000_000:
        b = open(p, 'rb').read()
        if hashlib.sha256(b).hexdigest() == want:
            got = (b, 'tree')
    if got is None:
        for c in COMMITS:
            b = blob(c + ':' + rel)
            if b is None:
                continue
            for variant, bb in (('raw', b), ('crlf', b.replace(b'\r\n', b'\n').replace(b'\n', b'\r\n'))):
                if hashlib.sha256(bb).hexdigest() == want:
                    got = (bb, 'git:%s:%s' % (c[:8], variant))
                    break
            if got:
                break
    if got is None:
        stats['none'] += 1
        nomatch.append(rel)
        continue
    dst = CODE + '/' + rel
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    open(dst, 'wb').write(got[0])
    rec.append({'path': rel, 'sha256': want, 'bytes': len(got[0]), 'source': got[1]})
    stats['tree' if got[1] == 'tree' else 'git'] += 1
git.stdin.close()
json.dump(rec, open(REC, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
json.dump(nomatch, open(A0 + '/RESTORE_NOMATCH_' + '_'.join(t.replace('/', '-') for t in tops) + '.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(stats)
print('nomatch examples', nomatch[:30])
