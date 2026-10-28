"""Verify the local copy of the codex handoff against FILE_MANIFEST.csv and the per-folder SHA256SUMS.txt files.

Read only toward the local copy root and the shared drive. Every file is hashed at most once (sha256 cache).
Rows/entries under sealed/ are skipped and never opened; sealed/ path names are never written out.
Outputs (next to this script):
  verify_manifest.json  - per-row results for every non-sealed manifest row + SHA256SUMS.txt results + summary
  verify_progress.json  - progress while running
"""
import csv, hashlib, io, json, os, sys, time

LOCAL = 'D:/VISSIM_handoff/20261024'
SHARED = 'Y:/99_임시휴지통/20261024'
HERE = os.path.dirname(os.path.abspath(__file__)).replace(chr(92), '/')
OUTDIR = HERE
if len(sys.argv) == 4:  # self-test only: synthetic local root, synthetic shared root, output dir
    LOCAL, SHARED, OUTDIR = sys.argv[1], sys.argv[2], sys.argv[3]
OUT = OUTDIR + '/verify_manifest.json'
PROG = OUTDIR + '/verify_progress.json'
CHUNK = 8 * 1024 * 1024
BS = chr(92)


def norm(p):
    p = p.replace(BS, '/')
    while p.startswith('./'):
        p = p[2:]
    return p


def is_sealed(rel):
    return rel == 'sealed' or rel.startswith('sealed/')


def sha256_file(path):
    h = hashlib.sha256()
    buf = bytearray(CHUNK)
    mv = memoryview(buf)
    n_total = 0
    with open(path, 'rb', buffering=0) as f:
        while True:
            n = f.readinto(buf)
            if not n:
                break
            h.update(mv[:n])
            n_total += n
    return h.hexdigest(), n_total


cache = {}  # rel -> (sha, bytes)
stats = {'hashed_files': 0, 'hashed_bytes': 0}


def get_hash(rel):
    if rel in cache:
        return cache[rel]
    assert not is_sealed(rel)
    d, n = sha256_file(LOCAL + '/' + rel)
    cache[rel] = (d, n)
    stats['hashed_files'] += 1
    stats['hashed_bytes'] += n
    return cache[rel]


def write_json(path, obj):
    tmp = path + '.tmp'
    with io.open(tmp, 'w', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)


t0 = time.time()
started = time.strftime('%Y-%m-%d %H:%M:%S')
last_prog = 0.0

# 0. Trust chain for the manifest itself: local vs shared bytes of the two small root files.
chain = {}
for name in ('FILE_MANIFEST.csv', 'SHA256SUMS.txt'):
    loc = sha256_file(LOCAL + '/' + name)
    shr = sha256_file(SHARED + '/' + name)
    chain[name] = {'local_sha256': loc[0], 'local_bytes': loc[1], 'shared_sha256': shr[0], 'shared_bytes': shr[1],
                   'same': loc == shr}

# 1. Manifest rows.
with io.open(LOCAL + '/FILE_MANIFEST.csv', encoding='utf-8-sig', newline='') as f:
    rows = list(csv.DictReader(f))
sealed_rows = sum(1 for r in rows if is_sealed(norm(r['path'])))
work = [r for r in rows if not is_sealed(norm(r['path']))]
results = []
counts = {'ok': 0, 'size_mismatch': 0, 'sha_mismatch': 0, 'missing': 0}
bytes_ok = 0
for i, r in enumerate(work):
    rel = norm(r['path'])
    exp_n = int(r['bytes'])
    exp_h = r['sha256'].strip().lower()
    p = LOCAL + '/' + rel
    item = {'path': rel, 'bytes_expected': exp_n, 'sha256_expected': exp_h}
    if not os.path.isfile(p):
        item['status'] = 'missing'
    else:
        st_n = os.path.getsize(p)
        item['bytes_local'] = st_n
        if st_n != exp_n:
            item['status'] = 'size_mismatch'
        else:
            d, n = get_hash(rel)
            item['sha256_local'] = d
            item['status'] = 'ok' if (d == exp_h and n == exp_n) else 'sha_mismatch'
    counts[item['status']] += 1
    if item['status'] == 'ok':
        bytes_ok += exp_n
    results.append(item)
    now = time.time()
    if now - last_prog > 20 or i == len(work) - 1:
        last_prog = now
        write_json(PROG, {'stage': 'manifest', 'done': i + 1, 'of': len(work), 'counts': counts,
                          'hashed_bytes': stats['hashed_bytes'], 'elapsed_sec': round(now - t0, 1)})
t_manifest = time.time() - t0

# 2. Per-folder SHA256SUMS.txt files in the local copy (sealed/ is not in the copy; checked below).
sealed_dir_in_copy = os.path.exists(LOCAL + '/sealed')
sums_files = []
for dp, dns, fns in os.walk(LOCAL):
    rel_dir = norm(os.path.relpath(dp, LOCAL))
    rel_dir = '' if rel_dir == '.' else rel_dir
    if is_sealed(rel_dir):
        dns[:] = []
        continue
    dns[:] = [d for d in dns if not is_sealed((rel_dir + '/' + d) if rel_dir else d)]
    if 'SHA256SUMS.txt' in fns:
        sums_files.append(((rel_dir + '/') if rel_dir else '') + 'SHA256SUMS.txt')
sums_files.sort()
sum_counts = {'files': len(sums_files), 'entries': 0, 'ok': 0, 'size_or_sha_mismatch': 0, 'missing': 0,
              'skipped_sealed_entries': 0, 'malformed_lines': 0}
sum_results = []
for j, sf in enumerate(sums_files):
    base = sf[:-len('SHA256SUMS.txt')]
    with io.open(LOCAL + '/' + sf, encoding='utf-8-sig') as f:
        lines = f.read().splitlines()
    fres = {'file': sf, 'entries': 0, 'ok': 0, 'bad': []}
    for ln in lines:
        if not ln.strip():
            continue
        parts = ln.split(None, 1)
        if len(parts) != 2 or len(parts[0]) != 64:
            sum_counts['malformed_lines'] += 1
            fres['bad'].append({'line': ln[:200], 'status': 'malformed'})
            continue
        h, name = parts[0].lower(), parts[1].strip()
        if name.startswith('*'):
            name = name[1:]
        rel = norm(base + norm(name))
        if is_sealed(rel):
            sum_counts['skipped_sealed_entries'] += 1
            continue
        sum_counts['entries'] += 1
        fres['entries'] += 1
        if not os.path.isfile(LOCAL + '/' + rel):
            sum_counts['missing'] += 1
            fres['bad'].append({'path': rel, 'status': 'missing'})
            continue
        d, n = get_hash(rel)
        if d == h:
            sum_counts['ok'] += 1
            fres['ok'] += 1
        else:
            sum_counts['size_or_sha_mismatch'] += 1
            fres['bad'].append({'path': rel, 'status': 'sha_mismatch', 'expected': h, 'local': d})
    sum_results.append(fres)
    now = time.time()
    if now - last_prog > 20 or j == len(sums_files) - 1:
        last_prog = now
        write_json(PROG, {'stage': 'sha256sums', 'done': j + 1, 'of': len(sums_files), 'counts': sum_counts,
                          'hashed_bytes': stats['hashed_bytes'], 'elapsed_sec': round(now - t0, 1)})

# 3. Coverage: files in the local copy that neither the manifest nor any SHA256SUMS.txt entry checked.
man_set = {norm(r['path']) for r in work}
all_local = []
local_bytes = 0
for dp, dns, fns in os.walk(LOCAL):
    rel_dir = norm(os.path.relpath(dp, LOCAL))
    rel_dir = '' if rel_dir == '.' else rel_dir
    for fn in fns:
        rel = ((rel_dir + '/') if rel_dir else '') + fn
        all_local.append(rel)
        local_bytes += os.path.getsize(LOCAL + '/' + rel)
not_in_manifest = sorted(p for p in all_local if p not in man_set)
unchecked = sorted(p for p in not_in_manifest if p not in cache and not (p in chain and chain[p]['same']))

t1 = time.time()
summary = {
    'started': started,
    'finished': time.strftime('%Y-%m-%d %H:%M:%S'),
    'seconds_total': round(t1 - t0, 1),
    'seconds_manifest_stage': round(t_manifest, 1),
    'local_root': LOCAL,
    'python': sys.version.split()[0],
    'pythonhashseed': os.environ.get('PYTHONHASHSEED'),
    'manifest_rows_total': len(rows),
    'manifest_rows_sealed_skipped': sealed_rows,
    'manifest_rows_checked': len(work),
    'manifest_counts': counts,
    'manifest_bytes_expected_checked_rows': sum(int(r['bytes']) for r in work),
    'manifest_bytes_ok': bytes_ok,
    'sha256sums': sum_counts,
    'sealed_dir_present_in_copy': sealed_dir_in_copy,
    'trust_chain_root_files': chain,
    'local_files_total': len(all_local),
    'local_bytes_total': local_bytes,
    'local_files_not_in_manifest': len(not_in_manifest),
    'local_files_unchecked_by_manifest_or_sums': unchecked,
    'hashed_files': stats['hashed_files'],
    'hashed_bytes': stats['hashed_bytes'],
    'hash_MBps': round(stats['hashed_bytes'] / 1e6 / max(t1 - t0, 1e-9), 1),
    'all_nonsealed_manifest_rows_match': counts['ok'] == len(work),
}
write_json(OUT, {'summary': summary, 'manifest_results': results, 'sha256sums_results': sum_results})
write_json(PROG, {'stage': 'done', 'summary_counts': counts, 'sha256sums': sum_counts,
                  'elapsed_sec': round(t1 - t0, 1)})
print('VERIFY_DONE', json.dumps({'manifest': counts, 'sums': sum_counts, 'sec': round(t1 - t0, 1)}))
