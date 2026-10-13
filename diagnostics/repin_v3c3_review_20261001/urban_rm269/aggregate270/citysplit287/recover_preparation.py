"""Preserve the failed preparation and replace only its exact duplicate bytes.

No simulation, no old-run cleanup, and no source-command changes.
"""
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
I = ROOT / 'diagnostics/sdmpc_n31_20260924/integration_20260926'
FAILED = I / 'native_urbanrm269_cityonly287_2400/selected/commands'
BASE = I / 'native_urbanrm269_10681only_2400/selected/commands'
NATIVE = Path('E:/VISSIM_runs/20261008_urbanrm269_native2400_s29/hold/decisions_sdmpc31_g_2400_hold_s29')


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    receipt = HERE / 'preparation_disk_failure.json'
    assert not receipt.exists(), 'Already recovered; never repeat cleanup automatically'
    assert FAILED.resolve().is_relative_to(ROOT.resolve())
    assert not (FAILED.parent.parent / 'protocol.json').exists()
    records = []
    for path in sorted(FAILED.iterdir()):
        assert path.is_file() and not path.is_symlink()
        assert path.suffix in ('.csv', '.json') and path.stem.startswith('action_')
        assert int(path.stem[7:]) < 2400
        backing = BASE / path.name
        native = NATIVE / path.name
        digest = sha(path)
        assert digest == sha(backing) == sha(native), 'Preserve incomplete/nonmatching file'
        assert path.stat().st_dev == backing.stat().st_dev
        records.append(dict(path=str(path), backing=str(backing), native=str(native),
                            sha256=digest, size=path.stat().st_size))
    report = dict(status='verified_duplicates_ready',
                  failure='WinError112 while preparing prefix; no native attempt',
                  timestamp_utc=datetime.now(timezone.utc).isoformat(),
                  original_prepare_sha256=sha(HERE / 'prepare_native.py'),
                  files=records, native_runs=0)
    receipt.write_text(json.dumps(report, indent=2) + '\n', encoding='utf8')
    for record in records:
        path, backing = Path(record['path']), Path(record['backing'])
        assert path.resolve().parent == FAILED.resolve()
        assert sha(path) == record['sha256'] == sha(backing)
        # Both independent originals remain, and the prepared name retains exact bytes.
        path.unlink()
        os.link(backing, path)
        assert os.path.samefile(path, backing) and sha(path) == record['sha256']
    report.update(status='failed_preparation_preserved_exact_bytes_as_hardlinks',
                  reclaimed_duplicate_bytes=sum(r['size'] for r in records))
    receipt.write_text(json.dumps(report, indent=2) + '\n', encoding='utf8')
    print('RECOVERED_OWN_DUPLICATES', report['reclaimed_duplicate_bytes'], flush=True)


if __name__ == '__main__':
    main()
