"""Read-only presence audit of unresolved physical links in recorded Ver2 runs.

This diagnoses coverage, never calibrates the model or changes input/state files.
Each selected FZP is streamed once, including its raw SHA. Per-run output makes
completed work reviewable without rerunning the multi-GB scan.
"""
from collections import Counter
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NETWORK_SHA = '085a10c71874e897083c97097af8fa3f1f08da1ef7416fef2f7cfbedabdfc317'
SUPPORT = ROOT / 'diagnostics/physical_projection_support_635_proposal.json'
OUT = ROOT / 'diagnostics/unresolved_occurrence_cache'


def read(path):
    raw = path.read_bytes()
    return json.loads(raw.decode('utf-8-sig')), hashlib.sha256(raw).hexdigest()


def empty():
    return dict(vehicle_rows=0, positive_frames=0, max_stock=0, first_sec=None,
                last_sec=None, first_vehicles=[], lanes=Counter(), ids=set())


def scan_fzp(path, targets):
    stats = {x: empty() for x in targets}
    byte_targets = {x.encode(): x for x in targets}
    digest = hashlib.sha256()
    indexes = None
    last_time_token, now, first = None, None, None
    periods, frame_counts = Counter(), Counter()
    rows, frames = 0, 0
    before = path.stat()

    def close_frame():
        for key, count in frame_counts.items():
            s = stats[key]
            s['positive_frames'] += 1
            s['max_stock'] = max(s['max_stock'], count)

    with path.open('rb') as file:
        for lineno, line in enumerate(file, 1):
            digest.update(line)
            if line.startswith(b'$VEHICLE:'):
                names = [x.strip().upper() for x in line.strip().split(b':', 1)[1].split(b';')]
                required = [b'SIMSEC', b'NO', b'LANE\\LINK\\NO', b'LANE\\INDEX', b'POS', b'SPEED']
                if indexes is not None or len(names) != len(set(names)):
                    raise ValueError(f'Repeated/duplicate header: {path}')
                indexes = {x: names.index(x) for x in required}
                # This prefix fast path is explicit; changed schemas fail closed.
                if [indexes[x] for x in required[:3]] != [0, 1, 2]:
                    raise ValueError(f'Unsupported prefix schema: {path}')
                continue
            if line.startswith((b'*', b'$', b'\xef\xbb\xbf')) or not line.strip():
                continue
            if indexes is None:
                raise ValueError(f'Data before header at {path}:{lineno}')
            prefix = line.split(b';', 3)
            if len(prefix) != 4:
                raise ValueError(f'Malformed row: {path}:{lineno}')
            time_token = prefix[0].strip()
            if time_token != last_time_token:
                new_time = float(time_token)
                if now is not None:
                    if new_time <= now:
                        raise ValueError(f'Non-increasing frames: {path}:{lineno}')
                    close_frame()
                    periods[new_time - now] += 1
                    frame_counts.clear()
                now, last_time_token = new_time, time_token
                first = now if first is None else first
                frames += 1
            rows += 1
            key = byte_targets.get(prefix[2].strip())
            if key is None:
                continue
            values = line.strip().split(b';')
            if len(values) != len(names):
                raise ValueError(f'Target row column mismatch: {path}:{lineno}')
            no = values[indexes[b'NO']].strip().decode()
            s = stats[key]
            s['vehicle_rows'] += 1
            s['ids'].add(no)
            s['lanes'][values[indexes[b'LANE\\INDEX']].strip().decode()] += 1
            s['first_sec'] = now if s['first_sec'] is None else s['first_sec']
            s['last_sec'] = now
            if len(s['first_vehicles']) < 5 and no not in {x['veh_no'] for x in s['first_vehicles']}:
                s['first_vehicles'].append(dict(veh_no=no, sec=now,
                    lane=int(values[indexes[b'LANE\\INDEX']]),
                    position_m=float(values[indexes[b'POS']]), speed_kph=float(values[indexes[b'SPEED']])))
            frame_counts[key] += 1
    close_frame()
    after = path.stat()
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        raise ValueError(f'FZP changed during read: {path}')
    for s in stats.values():
        s['unique_vehicles'] = len(s.pop('ids'))
    return dict(path=path.relative_to(ROOT).as_posix(), sha256=digest.hexdigest(),
                bytes=before.st_size, vehicle_rows=rows, frames=frames, first_sec=first,
                last_sec=now, frame_step_counts=dict(periods), links=stats)


def scan_snapshots(run, targets, run_id):
    rows, skipped = [], []
    for path in sorted(run.glob('decisions*/state_*.json')):
        raw, digest = read(path)
        envelope = raw.get('vehicle_records', {})
        records = envelope.get('records')
        if envelope.get('complete') is not True or not isinstance(records, list):
            skipped.append(path.relative_to(ROOT).as_posix())
            continue
        if raw.get('run_provenance', {}).get('run_id') != run_id:
            raise ValueError(f'Wrong snapshot run: {path}')
        if any(envelope.get(k) != len(records) for k in ('record_count', 'collection_count_before', 'collection_count_after')):
            raise ValueError(f'Incomplete record count: {path}')
        if raw['total_vehicles'] != len(records):
            raise ValueError(f'Full snapshot total mismatch: {path}')
        counts = Counter(str(int(r['link_no'])) for r in records)
        positive = {key: counts[key] for key in targets if counts[key]}
        rows.append(dict(path=path.relative_to(ROOT).as_posix(), sha256=digest,
                         sec=raw['sim_sec'], total_vehicles=len(records), positive=positive,
                         records=[r for r in records if str(int(r['link_no'])) in positive]))
    return dict(snapshots=rows, incomplete_snapshots_skipped=skipped)


def main():
    support, support_sha = read(SUPPORT)
    targets = sorted(support['full_area_coverage_audit']['unresolved_physical_links'], key=int)
    OUT.mkdir(exist_ok=True)
    result = dict(schema='unresolved-presence-audit-v1', network_sha256=NETWORK_SHA,
                  support_sha256=support_sha, unresolved_links=targets, runs=[], excluded=[])
    for run in sorted((ROOT / 'evaluation/runs').glob('codex_*')):
        manifest_path = run / f'run_provenance_{run.name}.json'
        if not manifest_path.exists():
            continue
        manifest, manifest_sha = read(manifest_path)
        if manifest.get('files', {}).get('network', {}).get('sha256') != NETWORK_SHA:
            result['excluded'].append(dict(run=run.name, reason='Different/unverified network hash'))
            continue
        item = dict(run=run.name, run_id=manifest['run_id'], controller=manifest['controller'],
                    manifest_path=manifest_path.relative_to(ROOT).as_posix(), manifest_sha256=manifest_sha,
                    declared_resolution_sec=manifest.get('env', {}).get('RW_VEHREC_RESOLUTION'),
                    requested_end_sec=manifest.get('sim_period_sec'))
        item.update(scan_snapshots(run, targets, manifest['run_id']))
        fzps = list(run.glob('vissim_eval/*.fzp'))
        if item['declared_resolution_sec'] == '1' and fzps:
            if len(fzps) != 1:
                raise ValueError(f'FZP selection ambiguous: {run}')
            item['fzp'] = scan_fzp(fzps[0], targets)
            if set(item['fzp']['frame_step_counts']) != {1.0}:
                raise ValueError(f'Declared one-second FZP has other intervals: {run}')
            item['completed_recording'] = item['fzp']['last_sec'] == item['requested_end_sec']
            metrics_path = run / 'analysis/area_metrics.json'
            if metrics_path.exists():
                metrics, _ = read(metrics_path)
                recorded = metrics['provenance']['fzp']['sha256']
                if recorded != item['fzp']['sha256']:
                    raise ValueError(f'Previously measured raw SHA differs: {run}')
                item['prior_measurement_sha_matches'] = True
        else:
            item['fzp_skipped_reason'] = 'No declared one-second recording; complete decision snapshots audited only'
        path = OUT / f'{run.name}.json'
        if path.exists():
            raise FileExistsError(path)
        path.write_text(json.dumps(item, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
        result['runs'].append(item)
        positive = sorted({k for row in item['snapshots'] for k in row['positive']} |
                          {k for k, v in item.get('fzp', {}).get('links', {}).items() if v['vehicle_rows']}, key=int)
        print(run.name, 'positive', positive, flush=True)
    result['limitations'] = [
        'Presence-only audit. Different control experiments are not pooled as causal performance evidence.',
        'Zero sampled occupancy is not proof a physical link is unreachable; short passages can occur between samples.',
        'Whole-link support remains unresolved where route/cohort identity is ambiguous; no stock aliases or model events are synthesized.',
        'Partial beta recordings are explicitly censored at their recorded end; future control-run observations are never used as model input.'
    ]
    destination = ROOT / 'diagnostics/unresolved_positive_occurrence_audit.json'
    if destination.exists():
        raise FileExistsError(destination)
    destination.write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
