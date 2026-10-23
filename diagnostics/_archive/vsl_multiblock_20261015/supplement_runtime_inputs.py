"""Add only witnessed missing runtime dependencies before any freeze/native."""
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = Path('E:/VISSIM_workspaces/vsl349_causal_20261011')
PACKAGE = Path('D:/VISSIM_packages/vsl_multizone355_20261015')
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda p: json.loads(p.read_bytes())

audit = read(HERE / 'runtime_dependency_audit.json')
assert not audit['mismatch'] and not audit['source_absent']
assert len(audit['missing']) == 3
assert not (PACKAGE / 'RUNTIME_DEPENDENCY_SUPPLEMENT.json').exists()
assert not (HERE / 'native_preparation.json').exists()
for folder in ('matched_off2250', 'matched_off2250_v2'):
    assert not (HERE / folder / 'progress.json').exists()
    assert not list((HERE / folder).glob('*_response.json.gz'))
for item in audit['missing']:
    relative = Path(item['path'])
    assert not relative.is_absolute() and '..' not in relative.parts
    source, destination = SOURCE / relative, PACKAGE / relative
    assert sha(source) == item['sha256'] and not destination.exists()
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    assert sha(destination) == item['sha256']
receipt = dict(
    status='complete', created_utc=datetime.now(timezone.utc).isoformat(),
    source=str(SOURCE), package=str(PACKAGE), files=audit['missing'],
    basis='Actual runtime reads from already completed full_selection3300; byte-identical source supplementation only',
    runtime_reads_sha256=sha(HERE / 'full_selection3300/runtime_reads.json'),
    import_provenance_sha256=sha(PACKAGE / 'IMPORT_PROVENANCE.json'),
    original_import_provenance_preserved=True, forecasts_consumed_before_repair=0,
    native_runs=0, freeze_count=0,
)
for path in (PACKAGE / 'RUNTIME_DEPENDENCY_SUPPLEMENT.json', HERE / 'runtime_dependency_supplement.json'):
    path.write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf8')
original = HERE / 'prepare_multizone_v2.py'
assert sha(original) == '7a2220f40e73fa7ccb841f68b0e292d5d864254bf423ac2cb68ae6cde8f90b58'
updated = original.read_text(encoding='utf8').replace("OUT=HERE/'matched_off2250_v2'", "OUT=HERE/'matched_off2250_v3'").replace('native_preparation_failure_v2.json', 'native_preparation_failure_v3.json')
target = HERE / 'prepare_multizone_v3.py'
assert not target.exists()
target.write_text(updated, encoding='utf8')
print(json.dumps(dict(supplemented_files=3, bytes=sum(v['bytes'] for v in audit['missing']), script=str(target), sha256=sha(target))))
