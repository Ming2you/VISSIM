"""Archive the four required shared-service inputs exactly; never overwrite."""
import hashlib
import json
import zipfile
from diagnostics.review_fixtures import ROOT

ARCHIVE = ROOT/'diagnostics/fixtures/shared_service_v1.zip'
RUN = 'codex_area_sources_beta0_s13_20260910'
FOLDER = f'evaluation/runs/{RUN}'
FILES = [f'{FOLDER}/decisions_{RUN}/{name}' for name in (
    'state_000900.json', 'action_000750.json', 'action_000900.json')]
FILES += [f'{FOLDER}/run_provenance_{RUN}.json']


def main():
    companion = ARCHIVE.with_suffix('.manifest.json')
    if ARCHIVE.exists() or companion.exists():
        raise FileExistsError('Preserve the existing fixture archive and manifest')
    payloads = {name: (ROOT/name).read_bytes() for name in FILES}
    rows = [{'path': name, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
            for name, data in payloads.items()]
    scope = ('Exact source-run900 state, preceding750 action, selected900 action, and the run '
             'manifest actually read by native_internal_input.configure. Other historical '
             'paths in action diagnostics are provenance only, not replay dependencies. '
             'Production/runtime/config files remain checkout inputs, not archive copies.')
    index = {'schema': 'portable-review-fixtures/v1', 'original_workspace_roots': [str(ROOT)],
             'files': rows, 'scope': scope}
    with zipfile.ZipFile(ARCHIVE, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as bundle:
        for name, data in {'index.json': (json.dumps(index, ensure_ascii=False, indent=2)+'\n').encode('utf-8'),
                           **{'raw/'+name: data for name, data in payloads.items()}}.items():
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            bundle.writestr(info, data)
    with zipfile.ZipFile(ARCHIVE) as bundle:
        if bundle.testzip() is not None:
            raise ValueError('Archive CRC failed')
        for name, data in payloads.items():
            if bundle.read('raw/'+name) != data:
                raise ValueError('Archive raw-byte mismatch: '+name)
    result = {'archive': ARCHIVE.name, 'bytes': ARCHIVE.stat().st_size,
              'sha256': hashlib.sha256(ARCHIVE.read_bytes()).hexdigest(),
              'files': rows, 'scope': scope, 'crc_and_raw_byte_comparison': 'PASS'}
    companion.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
