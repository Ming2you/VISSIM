"""Names-and-sizes scan of the shared drive folder, never descending into the root sealed/ (read only).

Writes source_scan.json next to this script: file count/bytes outside sealed/, SHA256SUMS.txt count,
nested directories named 'sealed', files present on disk but absent from FILE_MANIFEST.csv.
"""
import csv, io, json, os, time

ROOT = 'Y:/99_임시휴지통/20261024'
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'source_scan.json')

with io.open(ROOT + '/FILE_MANIFEST.csv', encoding='utf-8-sig', newline='') as f:
    man = {r['path']: int(r['bytes']) for r in csv.DictReader(f)}

t0 = time.time()
files = {}
nested_sealed = []
stack = ['']
while stack:
    rel = stack.pop()
    with os.scandir(ROOT + '/' + rel if rel else ROOT) as it:
        for e in it:
            r = (rel + '/' + e.name) if rel else e.name
            if e.is_dir(follow_symlinks=False):
                if r == 'sealed':
                    continue  # root sealed/ is never entered
                if e.name.lower() == 'sealed':
                    nested_sealed.append(r)
                stack.append(r)
            else:
                files[r] = e.stat(follow_symlinks=False).st_size

sums = sorted(p for p in files if p.endswith('SHA256SUMS.txt'))
not_in_manifest = sorted(p for p in files if p not in man)
nonsealed_manifest = {p: n for p, n in man.items() if not p.startswith('sealed/')}
missing_on_source = sorted(p for p in nonsealed_manifest if p not in files)
size_diff = sorted(p for p, n in nonsealed_manifest.items() if p in files and files[p] != n)
res = {
    'scanned_at': time.strftime('%Y-%m-%d %H:%M:%S'),
    'seconds': round(time.time() - t0, 1),
    'files_outside_sealed': len(files),
    'bytes_outside_sealed': sum(files.values()),
    'sha256sums_files_outside_sealed': len(sums),
    'nested_dirs_named_sealed': nested_sealed,
    'files_not_in_manifest_count': len(not_in_manifest),
    'files_not_in_manifest_non_sha256sums': [p for p in not_in_manifest if not p.endswith('SHA256SUMS.txt')],
    'nonsealed_manifest_rows': len(nonsealed_manifest),
    'nonsealed_manifest_missing_on_source': len(missing_on_source),
    'nonsealed_manifest_size_diff_on_source': len(size_diff),
}
with io.open(OUT, 'w', encoding='utf-8') as f:
    json.dump(res, f, ensure_ascii=False, indent=1)
print(json.dumps(res, ensure_ascii=False))
