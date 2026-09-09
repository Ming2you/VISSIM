"""Build deterministic raw historical fixtures; never alter the source runs."""
import json
from pathlib import Path
import subprocess
import zipfile
from diagnostics.review_fixtures import ROOT, ARCHIVE, sha

REFERENCES = [('6056c94', 'evaluation/controllers/vissim_stackelberg_adapter.py'),
              ('3299040', 'evaluation/controllers/vissim_stackelberg_adapter.py'),
              ('3299040', 'evaluation/controllers/projection_support.py'),
              ('3299040', 'evaluation/controllers/urban_flow_accounting.py')]


def build():
    inventory = json.loads((ROOT/'diagnostics/area_production_required_files.json').read_text(encoding='utf-8'))
    files, payloads, old_roots = [], {}, set()
    for row in inventory['historical_test_inputs']:
        data = (ROOT/row['path']).read_bytes()
        if sha(data) != row['sha256'] or len(data) != row['bytes']:
            raise ValueError(f'Archived original changed since review: {row["path"]}')
        payloads[row['path']] = data
        files.append({'path': row['path'], 'bytes': len(data), 'sha256': sha(data), 'kind': 'raw_run_file'})
        if Path(row['path']).name.startswith('run_provenance_'):
            old_roots.add(json.loads(data.decode('utf-8-sig'))['workspace_root'])
    for commit, path in REFERENCES:
        data = subprocess.check_output(['git', 'show', commit+':'+path], cwd=ROOT)
        name = 'reference_sources/'+commit+'/'+path
        payloads[name] = data
        files.append({'path': name, 'bytes': len(data), 'sha256': sha(data), 'kind': 'git_blob_reference',
                      'commit': subprocess.check_output(['git', 'rev-parse', commit], cwd=ROOT).decode().strip(),
                      'note': 'Git blob bytes for fixed OFF regression; not asserted to equal run-recorded raw filesystem source.'})
    index = {'schema': 'vissim-review-fixtures/v1', 'files': files,
             'original_workspace_roots': sorted(old_roots),
             'note': '45 original run JSON/CSV files plus four fixed historical git source blobs; no FZP or VISSIM results binary.'}
    ARCHIVE.parent.mkdir(parents=True, exist_ok=True)
    if ARCHIVE.exists():
        raise FileExistsError(f'Refusing to overwrite existing archive: {ARCHIVE}')
    def put(bundle, name, data):
        info = zipfile.ZipInfo(name, date_time=(2026, 9, 10, 0, 0, 0))
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = 0o644 << 16
        bundle.writestr(info, data, compresslevel=9)
    with zipfile.ZipFile(ARCHIVE, 'w') as bundle:
        put(bundle, 'index.json', (json.dumps(index, ensure_ascii=False, indent=2)+'\n').encode('utf-8'))
        for name, data in sorted(payloads.items()):
            put(bundle, 'raw/'+name, data)
    summary = {'archive': str(ARCHIVE.relative_to(ROOT)), 'sha256': sha(ARCHIVE.read_bytes()),
               'compressed_bytes': ARCHIVE.stat().st_size, 'raw_bytes': sum(len(v) for v in payloads.values()),
               'run_files': 45, 'reference_files': len(REFERENCES)}
    (ARCHIVE.parent/'control_area_v1.manifest.json').write_text(json.dumps(summary, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    build()
