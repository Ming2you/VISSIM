"""Close a completed migration from its journal; never change experimental data."""
import collections
import datetime
import hashlib
import gzip
import json
import os
from pathlib import Path
import shutil

A = Path(__file__).resolve().parent
B = A.parent / 'storage_cleanup_20261019'
def read(p):
    return json.loads(Path(p).read_text(encoding='utf-8-sig'))

completion = read(A/'migration_completion.json')
assert completion['status'] == 'complete'
review = read(A/'migration_review_summary.json')
assert completion['plan_sha256'].lower() == review['plan_sha256'].lower()
pending = {}
counts = collections.Counter()
backup_absence_samples=0
journal_path=A/'migration_journal.jsonl.gz' if (A/'migration_journal.jsonl.gz').exists() else A/'migration_journal.jsonl'
open_journal=gzip.open if journal_path.suffix=='.gz' else open
with open_journal(journal_path,'rt',encoding='utf-8-sig') as f:
    for line in f:
        event = json.loads(line)
        key = os.path.normcase(event['path'])
        counts[event['event']] += 1
        if event['event'] == 'prepared':
            assert key not in pending, key
            pending[key] = event['backup']
        elif event['event'] == 'linked_verified':
            backup = pending.pop(key)
            # The writer only records linked_verified after successful backup
            # removal. Audit every state transition, then sample the filesystem
            # instead of repeating half a million already completed checks.
            if counts['linked_verified']<=10 or counts['linked_verified']%10000==0:
                assert not os.path.exists('\\\\?\\'+os.path.abspath(backup)), backup
                backup_absence_samples+=1
assert not pending
assert counts['prepared'] == counts['linked_verified'] == completion['converted_copies']+completion['restored_paths']

log_path = A/'shared_package_v2.log' if (A/'shared_package_v2_launch.json').exists() else A/'shared_package.log'
log = log_path.read_text(encoding='utf-8-sig')
assert 'FREEZE_VERIFIED' in log and 'FREEZE_DONE' in log
frozen = Path([line[4:].strip() for line in log.splitlines() if line.startswith('FRZ=')][-1])
manifest = read(frozen/'FREEZE.json')
inputs = read(A/('current_runtime_inputs_v2.json' if (A/'shared_package_v2_launch.json').exists() else 'current_runtime_inputs.json'))
old = read(B/'deletion_summary.json')
baseline = {x['Name']:x['Free'] for x in old['before_drives']}
before = {x['Name']:x['Free'] for x in completion['before_drives']}
after = {d:shutil.disk_usage(d+':/').free for d in ('C','D','E')}
result = {
    'status':'completed_shared_layout_migration',
    'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'shared_stores':['D:/VISSIM_shared','E:/VISSIM_shared'],
    'objects':completion['objects'],
    'physical_duplicate_copies_removed':completion['converted_copies'],
    'historical_paths_restored_as_shared_links':completion['restored_paths'],
    'journal_entries_verified':dict(counts),
    'unresolved_journal_operations':0,
    'post_completion_backup_absence_samples':backup_absence_samples,
    'free_bytes_by_drive':after,
    'additional_free_bytes_D_E':sum(after[d]-before[d] for d in ('D','E')),
    'total_free_bytes_gained_D_E_since_cleanup_start':sum(after[d]-baseline[d] for d in ('D','E')),
    'plan':str(A/('migration_plan_reviewed.json.gz' if (A/'migration_plan_reviewed.json.gz').exists() else 'migration_plan_reviewed.json')),
    'journal':str(journal_path),
    'audit_compression':read(A/'audit_compression_complete.json') if (A/'audit_compression_complete.json').exists() else None,
    'errors_preserved_without_deletion':review['errors'],
    'immutable_runtime_package':str(frozen),
    'runtime_input_files':len(inputs['files']),
    'runtime_input_logical_bytes':inputs['bytes'],
    'runtime_manifest_sha256':hashlib.sha256((frozen/'FREEZE.json').read_bytes()).hexdigest(),
    'runtime_external_reference_pins':len(inputs['external_inputs']),
    'runtime_background_reference_limitations':inputs['preexisting_unresolved_backgrounds'],
    'future_code_installation':str(A/'code_installation.json'),
    'future_link_limit_update':str(A/'code_installation_link_limit.json'),
    'verification':'Canonical manifest verification for the new package; full anchor SHA256 and unchanged pinned target metadata before migration; NTFS file identity checked for every replacement. This is storage verification, not a new native qualification.',
    'policy':{
        'network_and_assets':'Immutable content-addressed shared objects per volume; historical paths are read-only hardlink aliases. Very widely reused small inputs use one physical object per at most 900 aliases to respect NTFS link limits.',
        'code':'Explicit pinned input selection; editable development sources stay independent.',
        'run_outputs':'Separate result directories; independent copied INPX/SIG inputs only where the runner must modify them.',
        'excluded':'Historical outputs and split handoff archives are not copied implicitly into new packages.',
        'preserved':'Unique original results/FZPs, editable workspaces, unverified copies and small metadata. No model parameters were changed.',
        'logical_size_caveat':'Adding directory sizes counts hardlink aliases repeatedly; use physical drive free space for reclaimed capacity.'},
    'native_launches':0,
    'forecasts':0,
    'processes_terminated':0,
    'calibration_goal':'unchanged, not marked complete',
}
(A/'storage_layout_complete.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({k:v for k,v in result.items() if k not in {'runtime_background_reference_limitations','policy'}},ensure_ascii=False,indent=2))
