"""Wait until every FILE_MANIFEST.csv entry exists on the shared drive with the declared size (read only).

Exits with one line: UPLOAD_COMPLETE (all present, sizes equal, total stable over two polls) or
UPLOAD_TIMEOUT / UPLOAD_SIZE_MISMATCH after MAX_SEC.  Never writes to the shared drive.
"""
import csv, io, json, os, sys, time

ROOT = 'Y:/99_임시휴지통/20261024'
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'wait_upload_state.json')
POLL = int(sys.argv[1]) if len(sys.argv) > 1 else 300
MAX_SEC = int(sys.argv[2]) if len(sys.argv) > 2 else 4 * 3600

with io.open(os.path.join(ROOT, 'FILE_MANIFEST.csv'), encoding='utf-8-sig', newline='') as f:
    rows = list(csv.DictReader(f))
want = {r['path']: int(r['bytes']) for r in rows}
total = sum(want.values())

def sizes():
    found = {}
    stack = ['']
    while stack:
        rel = stack.pop()
        try:
            it = os.scandir(os.path.join(ROOT, rel) if rel else ROOT)
        except OSError:
            continue
        with it:
            for e in it:
                r = (rel + '/' + e.name) if rel else e.name
                try:
                    if e.is_dir(follow_symlinks=False):
                        stack.append(r)
                    else:
                        found[r] = e.stat(follow_symlinks=False).st_size  # cached by scandir on Windows
                except OSError:
                    pass
    return found


t0 = time.time()
prev_ok = None
while True:
    present = ok = bad = 0
    got = 0
    have = sizes()
    for rel, n in want.items():
        s = have.get(rel)
        if s is None:
            continue
        present += 1
        got += min(s, n)
        if s == n:
            ok += 1
        elif s > n:
            bad += 1
    state = {'checked': time.strftime('%Y-%m-%d %H:%M:%S'), 'files': len(want), 'present': present,
             'size_ok': ok, 'oversize': bad, 'bytes_expected': total, 'bytes_present_capped': got}
    with io.open(OUT, 'w', encoding='utf-8') as f:
        json.dump(state, f, indent=1)
    if ok == len(want) and prev_ok == len(want):
        print('UPLOAD_COMPLETE %s files=%d bytes=%d' % (state['checked'], ok, total))
        sys.exit(0)
    prev_ok = ok
    if bad:
        print('UPLOAD_SIZE_MISMATCH %s oversize=%d' % (state['checked'], bad))
        sys.exit(0)
    if time.time() - t0 > MAX_SEC:
        print('UPLOAD_TIMEOUT %s present=%d/%d size_ok=%d bytes=%.1f/%.1f GB' % (
            state['checked'], present, len(want), ok, got / 1e9, total / 1e9))
        sys.exit(0)
    time.sleep(POLL)
