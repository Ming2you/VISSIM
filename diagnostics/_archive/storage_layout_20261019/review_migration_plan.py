"""Validate and deduplicate the finished read-only migration plan, without data edits."""
import collections
import hashlib
import json
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
original = HERE / 'migration_plan.json'
output = HERE / 'migration_plan_reviewed.json'
if output.exists():
    raise SystemExit('Reviewed plan already exists; preserve it.')
data = json.loads(original.read_text(encoding='utf-8-sig'))
def longpath(path):
    return '\\\\?\\' + os.path.abspath(path)

# Reuse the completed full-content comparison of native FZPs.
fzp_audit=json.loads((HERE/'native_fzp_duplicate_audit.json').read_text(encoding='utf-8-sig'))
assert fzp_audit['status']=='completed'
by_digest={(Path(g['object']).drive.upper(),g['sha256']):g for g in data['groups']}
native_fzp_examined=len(fzp_audit['examined'])
native_fzp_added=0
for audited in fzp_audit['groups']:
    drive,digest,aliases=audited['drive'],audited['sha256'],audited['aliases']
    for item in aliases:
        st=os.stat(longpath(item['path']),follow_symlinks=False)
        assert st.st_size==item['bytes'] and st.st_mtime_ns//100+621355968000000000==item['last_write_utc_ticks']
    group=by_digest.get((drive,digest))
    if group is None:
        group={'sha256':digest,'object':f'{drive}/VISSIM_shared/objects/sha256/{digest[:2]}/{digest}',
               'anchor':{**aliases[0],'copy_required':False},'aliases':[]}
        data['groups'].append(group);by_digest[(drive,digest)]=group
    group['aliases'].extend(aliases)
    native_fzp_added+=len(aliases)
seen = {}
removed = 0
ext = collections.defaultdict(lambda: [0, 0])
drives = collections.defaultdict(lambda: [0, 0, 0])
normalized=[]
sharded_hash_groups=0
shard_anchor_hashes=0
for group in data['groups']:
    digest = group['sha256']
    obj = Path(group['object'])
    assert obj.drive.upper() in {'D:', 'E:'}
    assert obj.parts[1:3] == ('VISSIM_shared', 'objects')
    assert obj.name == digest and len(digest) == 64
    aliases = []
    for item in group['aliases']:
        key = os.path.normcase(os.path.abspath(item['path']))
        assert Path(item['path']).drive.lower() == obj.drive.lower()
        if key in seen:
            assert seen[key] == (digest, item['exists'], item['bytes']), key
            removed += 1
            continue
        seen[key] = (digest, item['exists'], item['bytes'])
        aliases.append(item)
    group['aliases'] = aliases
    assert group['anchor']['copy_required'] or any(
        os.path.normcase(x['path']) == os.path.normcase(group['anchor']['path']) and x['exists']
        for x in aliases)
    if len(aliases)<=1000:
        normalized.append(group)
        continue
    # These high-count groups are small signal inputs. Keep one verified
    # physical copy per 900 aliases to remain below NTFS's 1024-link limit.
    assert all(x['exists'] for x in aliases), 'A high-count missing-only group needs a separate plan.'
    assert not group['anchor']['copy_required']
    aliases.sort(key=lambda x:os.path.normcase(x['path'])!=os.path.normcase(group['anchor']['path']))
    sharded_hash_groups+=1
    for number,start in enumerate(range(0,len(aliases),900)):
        chunk=aliases[start:start+900]
        if number==0:
            anchor=group['anchor'];object_path=group['object']
        else:
            selected=chunk[0]
            st=os.stat(longpath(selected['path']))
            assert st.st_size==selected['bytes'] and st.st_mtime_ns//100+621355968000000000==selected['last_write_utc_ticks']
            h=hashlib.sha256()
            with open(longpath(selected['path']),'rb') as f:
                while block:=f.read(8*1024*1024):h.update(block)
            after=os.stat(longpath(selected['path']))
            assert h.hexdigest()==digest and st.st_mtime_ns==after.st_mtime_ns
            anchor={**selected,'copy_required':False}
            object_path=str(obj.parent/'shards'/f'{number:03d}'/digest)
            shard_anchor_hashes+=1
        normalized.append({**group,'anchor':anchor,'object':object_path,'aliases':chunk,'link_limit_shard':number})
data['groups']=normalized
for group in data['groups']:
    aliases=group['aliases'];obj=Path(group['object'])
    reclaimed = sum(x['bytes'] for x in aliases if x['exists']) - group['anchor']['bytes']
    drives[obj.drive.upper()][0] += 1
    drives[obj.drive.upper()][1] += reclaimed
    drives[obj.drive.upper()][2] += group['anchor']['bytes'] if group['anchor']['copy_required'] else 0
    suffix = Path(aliases[0]['path']).suffix.lower()
    ext[suffix][0] += len(aliases)
    ext[suffix][1] += reclaimed
data['existing_aliases'] = sum(x['exists'] for g in data['groups'] for x in g['aliases'])
data['restore_aliases'] = sum(not x['exists'] for g in data['groups'] for x in g['aliases'])
data['referenced_logical_bytes'] = sum(x['bytes'] for g in data['groups'] for x in g['aliases'])
data['potential_reclaimed_bytes'] = sum(v[1] for v in drives.values())
data['review'] = {'original_sha256': hashlib.sha256(original.read_bytes()).hexdigest(),
                  'native_fzp_equal_size_files_fully_hashed':native_fzp_examined,
                  'native_fzp_duplicate_aliases_added':native_fzp_added,
                  'hash_groups_split_for_ntfs_link_limit':sharded_hash_groups,
                  'additional_shard_anchors_fully_hashed':shard_anchor_hashes,
                  'duplicate_alias_records_removed': removed,
                  'maximum_aliases_per_object': max(len(g['aliases']) for g in data['groups']),
                  'drive_groups_net_reclaimed_copy_bytes': dict(drives),
                  'extension_aliases_net_reclaimed_bytes': dict(ext)}
output.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf8')
summary = {k: v for k, v in data.items() if k not in {'groups', 'manifest_pins', 'errors_preserved'}}
summary.update(groups=len(data['groups']), errors=len(data['errors_preserved']),
               plan_sha256=hashlib.sha256(output.read_bytes()).hexdigest())
(HERE / 'migration_review_summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf8')
print(json.dumps(summary, ensure_ascii=False, indent=2))
