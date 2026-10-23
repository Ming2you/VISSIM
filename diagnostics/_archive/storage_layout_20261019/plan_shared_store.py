"""Read-only planner: keep historical paths, share immutable identical bytes."""
import collections
import hashlib
import json
import os
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
OLD = HERE.parent / 'storage_cleanup_20261019'
read = lambda p: json.loads(Path(p).read_text(encoding='utf-8-sig'))
out = HERE / 'migration_plan.json'
if out.exists():
    raise SystemExit('Inspect existing plan; do not overwrite.')
started = time.time()
groups = collections.defaultdict(list)
sources = collections.defaultdict(set)
pins = {}
errors = []
deleted = {}
def lp(p):
    value = os.path.abspath(p)
    return Path(value if value.startswith('\\\\?\\') else '\\\\?\\' + value)
for p in [OLD / 'verified_deletions.json', OLD / 'additional_outputs/verified_deletions.json']:
    for t in read(p)['targets']:
        deleted[t['path'].lower()] = t

def sha(p):
    h = hashlib.sha256()
    with lp(p).open('rb') as f:
        while b := f.read(8 * 1024 * 1024):
            h.update(b)
    return h.hexdigest()

for f in read(OLD / 'freezes.json'):
    if not f['manifest_exists']:
        continue
    tree = Path(f['tree'])
    mp = tree / 'FREEZE.json'
    data = mp.read_bytes()
    pins[str(mp)] = hashlib.sha256(data).hexdigest()
    m = json.loads(data.decode('utf-8-sig'))
    manifest_mtime = mp.stat().st_mtime_ns
    for rel, digest in m['files'].items():
        p = tree / rel
        if any(part.lower() in {'.git', '.deps', '.review-deps', '__pycache__'} for part in Path(rel).parts):
            continue
        key = (tree.drive.upper(), digest.lower())
        groups[key].append({'path': str(p), 'allowed_root': str(tree),
                            'manifest': str(mp), 'manifest_mtime_ns': manifest_mtime,
                            'evidence': 'canonical_freeze_manifest'})
        sources[key].add(str(Path(m['source']) / rel))
print(json.dumps({'stage': 'indexed_freezes', 'groups': len(groups)}), flush=True)

# Native run input copies outside freezes have no immutable manifest: hash each.
for base in [Path('D:/VISSIM_runs'), Path('E:/VISSIM_runs')]:
    count = 0
    for folder, dirs, names in os.walk(lp(base)):
        folder = folder.removeprefix('\\\\?\\')
        dirs[:] = [d for d in dirs if d.lower() not in {'frozen', '.git', '.deps', '__pycache__'}
                   and not (getattr(lp(Path(folder, d)).stat(follow_symlinks=False), 'st_file_attributes', 0) & 0x400)]
        if 'network' not in {part.lower() for part in Path(folder).parts}:
            continue
        for name in names:
            p = Path(folder, name)
            if p.suffix.lower() not in {'.inpx', '.sig', '.jpg', '.jpeg', '.png', '.bmp'}:
                continue
            try:
                before = lp(p).stat()
                if getattr(before, 'st_file_attributes', 0) & 0x400:
                    continue
                digest = sha(p)
                after = lp(p).stat()
                if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
                    raise RuntimeError('Input changed while hashing')
                groups[(base.drive.upper(), digest)].append({
                    'path': str(p), 'allowed_root': str(base / p.relative_to(base).parts[0]),
                    'evidence': 'fresh_full_file_sha256', 'bytes': after.st_size,
                    'mtime_ns': after.st_mtime_ns})
                count += 1
            except OSError as e:
                errors.append({'path': str(p), 'error': str(e)})
    print(json.dumps({'stage': 'native_networks_indexed', 'root': str(base), 'files': count}), flush=True)

planned = []
existing_aliases = missing_aliases = bytes_referenced = 0
for i, ((drive, digest), members) in enumerate(groups.items()):
    # Tiny per-run metadata is retained independently; large payloads and network
    # inputs are the actual storage users. Sole copies remain in their run folder.
    if len(members) < 2 and not any(x['path'].lower() in deleted for x in members):
        continue
    current = []
    missing = []
    for x in members:
        p = Path(x['path'])
        try:
            st = lp(p).stat()
            if getattr(st, 'st_file_attributes', 0) & 0x400 or st.st_nlink != 1:
                continue
            if x['evidence'] == 'canonical_freeze_manifest' and st.st_mtime_ns > x['manifest_mtime_ns']:
                continue
            if x['evidence'] == 'fresh_full_file_sha256' and (st.st_size, st.st_mtime_ns) != (x['bytes'], x['mtime_ns']):
                raise RuntimeError('Input changed after hashing')
            if st.st_size < 65536 and p.suffix.lower() not in {'.inpx', '.sig', '.jpg', '.jpeg', '.bmp'}:
                continue
            current.append({**x, 'bytes': st.st_size,
                            'last_write_utc_ticks': st.st_mtime_ns // 100 + 621355968000000000,
                            'exists': True})
        except FileNotFoundError:
            old = deleted.get(str(p).lower())
            if old and old['sha256'] == digest:
                missing.append({**x, 'bytes': old['bytes'], 'exists': False,
                                'last_write_utc_ticks': old['last_write_utc_ticks']})
        except OSError as e:
            errors.append({'path': str(p), 'error': str(e)})
    if len(current) < 2 and not missing:
        continue
    anchor = None
    # Prefer a same-volume historical copy, never hardlink a mutable worktree.
    candidates = [(x['path'], False) for x in current]
    if not current:
        candidates += [(p, True) for p in sorted(sources[(drive, digest)])]
    for p, must_copy in candidates:
        try:
            before = lp(p).stat()
            expected_size = (current or missing)[0]['bytes']
            if before.st_size != expected_size:
                continue
            actual = sha(p)
            after = lp(p).stat()
            if actual == digest and (before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns):
                anchor = {'path': p, 'copy_required': must_copy, 'bytes': after.st_size,
                          'last_write_utc_ticks': after.st_mtime_ns // 100 + 621355968000000000}
                break
        except OSError:
            continue
    if not anchor:
        errors.append({'sha256': digest, 'drive': drive, 'error': 'No matching complete anchor; untouched'})
        continue
    aliases = [x for x in current + missing if x['bytes'] == anchor['bytes']]
    store = f'{drive}/VISSIM_shared/objects/sha256/{digest[:2]}/{digest}'
    planned.append({'sha256': digest, 'object': store, 'anchor': anchor, 'aliases': aliases})
    existing_aliases += len(current)
    missing_aliases += len(missing)
    bytes_referenced += sum(x['bytes'] for x in aliases)
    if len(planned) % 100 == 0:
        print(json.dumps({'stage': 'anchors_hashed', 'groups': len(planned),
                          'existing_aliases': existing_aliases, 'restore_aliases': missing_aliases}), flush=True)

plan = {'schema': 'vissim-shared-store-migration/v1', 'status': 'planned_not_applied',
        'created_unix': time.time(), 'manifest_pins': pins, 'groups': planned,
        'errors_preserved': errors, 'allowed_store_roots': ['D:/VISSIM_shared', 'E:/VISSIM_shared'],
        'scope': 'Completed historical frozen files and native network input copies only. No worktree edits, no unique native-result deletion. Original historical paths are preserved as read-only NTFS hardlinks. Small metadata stays independent.',
        'existing_aliases': existing_aliases, 'restore_aliases': missing_aliases,
        'referenced_logical_bytes': bytes_referenced,
        'additional_object_copy_bytes': sum(g['anchor']['bytes'] for g in planned if g['anchor']['copy_required']),
        'potential_reclaimed_bytes': sum(max(0, sum(x['bytes'] for x in g['aliases'] if x['exists']) - g['anchor']['bytes']) for g in planned),
        'elapsed_sec': time.time() - started}
out.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding='utf-8')
summary = {k: v for k, v in plan.items() if k not in {'groups', 'manifest_pins', 'errors_preserved'}}
summary.update(groups=len(planned), errors=len(errors), plan_sha256=sha(out))
(HERE / 'migration_plan_summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({'complete': True, **summary}), flush=True)
