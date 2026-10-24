"""Archive prior proposal bytes, then reproduce only its incumbent bug.

Uses the address-only test fixture: no adapter/model import or traffic run.
Never applies a patch or overwrites completed historical evidence.
"""
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
FILES = tuple('diagnostics/' + name for name in (
    'joint_freeway_neighbors_candidate.py', 'joint_freeway_neighbors.patch',
    'test_joint_freeway_neighbors.py', 'prepare_joint_freeway_neighbors.py',
    'joint_freeway_neighbors_handoff.md', 'joint_freeway_neighbors_validation.json',
    'joint_freeway_neighbors_tests.log'))
OLD_SOURCE = '28fd5af312b30488a240295d976f787b548c9f0a66f17cc3a8466184bb3d8e6f'


def main():
    archive = ROOT / 'diagnostics/fixtures/joint_freeway_neighbors_pre_incumbent_guard_v1.zip'
    sidecar = archive.with_suffix('.manifest.json')
    output = ROOT / 'diagnostics/joint_freeway_incumbent_guard_prior_reproduction.json'
    if any(p.exists() for p in (archive, sidecar, output)):
        raise ValueError('Preserve previous archive/reproduction; no overwrite')
    raw = {name: (ROOT / name).read_bytes() for name in FILES}
    if hashlib.sha256(raw[FILES[0]]).hexdigest() != OLD_SOURCE:
        raise ValueError('Expected prior proposal source bytes')
    members = {name: {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()} for name, data in raw.items()}
    manifest = {'schema': 'fw-neighbor-prior-raw-archive/v1', 'members': members}
    payloads = {**raw, 'manifest.json': (json.dumps(manifest, indent=2, sort_keys=True) + '\n').encode()}
    with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as target:
        for name, data in sorted(payloads.items()):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            target.writestr(info, data)
    with zipfile.ZipFile(archive) as check:
        if check.testzip() is not None or set(check.namelist()) != set(payloads):
            raise AssertionError('ZIP CRC/member mismatch')
        if any(check.read(name) != data for name, data in payloads.items()):
            raise AssertionError('ZIP raw member bytes changed')
    manifest.update(archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
                    archive_bytes=archive.stat().st_size, crc_and_all_members_exact=True)
    sidecar.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8', newline='\n')
    sys.path.insert(0, str(ROOT))
    from diagnostics.test_joint_freeway_neighbors import FreewayNeighborsTests
    FreewayNeighborsTests.setUpClass()
    test = FreewayNeighborsTests(); test.setUp()
    domain = replace(test.domain(), head_values={0: (), 5: (), 10: ()}, meter_points=(), joint_pairs=())
    ramp = test.ramps()[0]
    def changed_rate(control):
        control['ramp_metering'][ramp] += 100.0
        return control
    rate_result = test.generate(domain=domain, realize=changed_rate)
    native_key = next((kind, identity) for kind, identity, owner, key in test.catalog.writes
                      if owner == 'FW_E' and key == ramp)
    def changed_schedule(control):
        control['diagnostics']['synthetic_schedule_override'] = True
        return control
    def schedule_rows(control):
        rows = test.rows(control)
        if control['diagnostics'].get('synthetic_schedule_override'):
            rows[native_key] = ('different synthetic schedule',)
        return rows
    schedule_result = test.generate(domain=domain, realize=changed_schedule, physical_rows=schedule_rows)
    test.tearDown()
    results = []
    for name, result in (('changed_realized_meter_rate', rate_result), ('same_levers_changed_own_schedule', schedule_result)):
        item = result['candidates'][0]
        lever_changed = item['control']['ramp_metering'] != test.old['ramp_metering']
        physical_changed = item['physical_rows'] != test.rows(test.old)
        if not result['incumbent_feasible'] or not physical_changed:
            raise AssertionError('Expected prior behavior did not reproduce')
        results.append({'case': name, 'incumbent_feasible': result['incumbent_feasible'],
                        'lever_changed': lever_changed, 'physical_rows_changed': physical_changed,
                        'requested_rate': test.old['ramp_metering'][ramp],
                        'returned_rate': item['control']['ramp_metering'][ramp]})
    for name, data in raw.items():
        if (ROOT / name).read_bytes() != data:
            raise AssertionError('Prior proposal was changed during reproduction')
    record = {'schema': 'fw-incumbent-prior-reproduction/v1', 'reproduced': True,
              'source_sha256': OLD_SOURCE, 'cases': results,
              'archive': str(archive.relative_to(ROOT)), 'archive_sha256': manifest['archive_sha256'],
              'prior_files_unchanged': True, 'input_unchanged': True,
              'model_imports': 0, 'model_execution': 0, 'com_execution': 0}
    output.write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps(record, indent=2))


if __name__ == '__main__':
    main()
