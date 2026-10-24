"""Bounded first-difference diagnostic; does not qualify or rerun native traffic."""
import hashlib
import itertools
import json
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
OLD = Path('D:/VISSIM_runs/20260930_release2670_s67/release/run/vissim_eval/release2670_s67_release_001.fzp')
NEW = Path('D:/VISSIM_runs/20261003_s67_vsl_observation2700/release/vissim_eval/sdmpc31_g_2700_release_s67_001.fzp')

def rows(path):
    with path.open('rb') as stream:
        for line in stream:
            if re.match(rb'^\d+(?:\.\d+)?;', line):
                yield line.rstrip(b'\r\n')

def header(path):
    with path.open('rb') as stream:
        for line in stream:
            if line.startswith(b'$VEHICLE:'):
                return line.decode('utf-8-sig').strip().removeprefix('$VEHICLE:').split(';')
    raise AssertionError('Missing column header')

def main():
    target = HERE/'first_prefix_difference76.json'
    assert not target.exists()
    a, b = rows(OLD), rows(NEW)
    names = header(OLD)
    assert names == header(NEW), 'Column definitions differ'
    digest = hashlib.sha256()
    for index, (left, right) in enumerate(itertools.zip_longest(a, b)):
        assert left is not None and right is not None
        if left != right:
            l, r = left.decode().split(';'), right.decode().split(';')
            changes = {name: [x, y] for name, x, y in zip(names, l, r) if x != y}
            result = dict(old=str(OLD), new=str(NEW), exact_rows_before_first_difference=index,
                          common_rows_sha256=digest.hexdigest(), columns=names,
                          first_old=l, first_new=r, changed_fields=changes,
                          subsequent_old=[x.decode() for x in itertools.islice(a, 3)],
                          subsequent_new=[x.decode() for x in itertools.islice(b, 3)],
                          scope='Stop at first unequal normalized FZP row; no whole-file reanalysis')
            target.write_text(json.dumps(result, indent=2), encoding='utf-8')
            print(json.dumps({k:result[k] for k in ('exact_rows_before_first_difference','changed_fields','first_old','first_new')}))
            return
        assert float(left.split(b';', 1)[0]) < 2700, 'Expected old-prefix mismatch not found'
        digest.update(left+b'\n')
    raise AssertionError('No difference')

def align_recording_start():
    """Compare the overlapping recorded interval to the preserved old proof."""
    target = HERE/'recording_start_alignment76.json'
    assert not target.exists()
    summary_path = HERE/'analysis/summary.json'
    summary = json.loads(summary_path.read_bytes())
    assert summary['paired_prefix_exact'] and not summary['original_initial_history_exact']
    before = NEW.stat()
    digest = hashlib.sha256(); count = 0; skipped = []; last = None; first = None
    for line in rows(NEW):
        time = float(line.split(b';', 1)[0])
        if time >= 2700:
            break
        if time < 5.1:
            skipped.append(line.decode())
            continue
        if first is None:
            first = time
        digest.update(line+b'\n'); count += 1; last = time
    after = NEW.stat()
    assert (before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns)
    overlap = dict(sha256=digest.hexdigest(), rows=count, last_time_s=last)
    assert len(skipped)==1 and float(skipped[0].split(';')[0])==0.1
    assert first==5.1 and overlap==summary['original_prefix']
    result = dict(schema='recording-start-alignment/v1', overlap_exact=True,
                  first_common_record_s=first, cutoff_s=2700, overlap=overlap,
                  extra_new_start_rows=skipped, new_fzp=str(NEW),
                  new_file_size=after.st_size, new_mtime_ns=after.st_mtime_ns,
                  analysis_summary=str(summary_path),
                  analysis_summary_sha256=hashlib.sha256(summary_path.read_bytes()).hexdigest(),
                  original_initial_history_exact=False, original_failure_preserved=True,
                  interpretation='Old starts5.1; new has one additional0.1 row. All common recorded rows are byte-exact; no old0.1 observation is claimed.',
                  old_full_prefix_rescanned=False, native_reruns=0)
    target.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result))

if __name__ == '__main__':
    align_recording_start() if '--align-recording-start' in sys.argv else main()
