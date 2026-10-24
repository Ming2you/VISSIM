"""Preserve complete recorded1200/3300 inputs byte for byte, never overwrite."""
import hashlib
import json
import zipfile
from diagnostics.review_fixtures import ROOT

ARCHIVE = ROOT/'diagnostics/fixtures/known_wout_v1.zip'
RUN = 'codex_area_sources_beta0_s13_20260910'
FOLDER = f'evaluation/runs/{RUN}'
FILES = [f'{FOLDER}/decisions_{RUN}/{name}' for name in (
    'state_001200.json', 'state_003300.json', 'action_001050.json',
    'action_001200.json', 'action_003150.json', 'action_003300.json')]
FILES += [f'{FOLDER}/run_provenance_{RUN}.json']


def main():
    companion = ARCHIVE.with_suffix('.manifest.json')
    if ARCHIVE.exists() or companion.exists():
        raise FileExistsError('Preserve the existing archive and manifest')
    payloads = {name: (ROOT/name).read_bytes() for name in FILES}
    rows = [{'path': name, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
            for name, data in payloads.items()]
    scope = ('Complete current1200/3300 observations, preceding1050/3150 and held1200/3300 '
             'actions, and their required run provenance. Complete records permit stock, '
             'unknown-route and exclusive-owner checks without a selected-vehicle sample. '
             'No future observations/FZP or copied runtime/config implementation.')
    index = {'schema': 'portable-review-fixtures/v1', 'original_workspace_roots': [str(ROOT)],
             'files': rows, 'scope': scope}
    with zipfile.ZipFile(ARCHIVE, 'x', compression=zipfile.ZIP_DEFLATED) as bundle:
        entries = {'index.json': (json.dumps(index, ensure_ascii=False, indent=2)+'\n').encode('utf-8')}
        entries.update({'raw/'+name: data for name, data in payloads.items()})
        for name, data in entries.items():
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            bundle.writestr(info, data, compresslevel=9)
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


if __name__ == '__main__': main()
