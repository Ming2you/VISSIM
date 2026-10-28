# copy every file that is new or changed in the working tree versus the pristine tree
import hashlib, os, shutil, sys
pristine, work, dst = sys.argv[1], sys.argv[2], sys.argv[3]
def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()
n = 0
for dp, dn, fn in os.walk(work):
    for f in fn:
        w = os.path.join(dp, f)
        rel = os.path.relpath(w, work)
        p = os.path.join(pristine, rel)
        if os.path.exists(p) and os.path.getsize(p) == os.path.getsize(w) and sha(p) == sha(w):
            continue
        d = os.path.join(dst, rel)
        os.makedirs(os.path.dirname(d), exist_ok=True)
        shutil.copy2(w, d)
        print(('changed' if os.path.exists(p) else 'new'), rel.replace(os.sep, '/'), os.path.getsize(w), sha(w))
        n += 1
for dp, dn, fn in os.walk(pristine):
    for f in fn:
        p = os.path.join(dp, f)
        rel = os.path.relpath(p, pristine)
        if not os.path.exists(os.path.join(work, rel)):
            print('deleted', rel.replace(os.sep, '/'))
print('collected', n)
