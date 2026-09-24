r"""Isolated input for replaying one obs150 (coupled-lane-plant/v2) decision offline (plan D1).

    make_replay_state_v2.py prepare <decisions_dir> <sim_sec> <out_dir> [--previous-sec P]
    make_replay_state_v2.py compare <out_dir> [--vsl-expected 110]

prepare
    A v2 decision reads, besides its state_<T>.json, the obs150 bundle the state pins
    (CONTRACT 4.1): frame_T and frame_{T-150}, obs150/mer_T.jsonl + the mer index entry,
    obs150/err_T.jsonl, the install record. It WRITES obs150/derived_T.json next to them
    (write_derived). Replaying in the run's own folder would therefore write into a live
    or finished run, so this links every pinned write-once file into <out_dir> (hard
    links; a sha-checked copy only across volumes), writes the mer index as the chain
    prefix that existed at T (entries <= T, the capture's own serialization), and writes
    <out_dir>/state_<T>.json equal to the original except the two directories:
      obs150.directory                    -> <out_dir>
      lane_plant_observation.directory    -> the same place under <out_dir>
    Everything else (run_provenance, network_path, detector CSV, .mer/.err sources) is
    unchanged, so the replay reads the run's own pins. The original folder is never
    renamed or written.
    Also linked, for comparison and evidence only:
      original/  action_T.{json,csv}, action_T.joint.progress.jsonl, obs150/derived_T.json
      previous/  action_P.{json,csv}, action_P.json.applied, action_P.json.sdmpc_pending,
                 action_P.decision_budget.json (whichever exist)
    The replay reads the previous action from the RUN folder, not from previous/: the
    native receipt action_P.json.applied carries the absolute path of action_P.csv and
    sdmpc.load_prices (sdmpc.py:461-470) requires it to resolve to the csv beside the
    previous action. replay_decision_n31.ps1 re-hashes the originals against previous/.
    The last check loads the new state with obs150_contract.load_bundle (every pin must
    verify inside <out_dir>) and proves the two obs150 blocks differ only in 'directory'.
    Writes <out_dir>/replay_manifest.json; last stdout line REPLAY_STATE_OK ...

compare
    After replay_decision_n31.ps1 wrote <out_dir>/replay/action_T.*, compares against
    original/: derived_T.json equal except inputs.raw_sha256 (each side's raw_sha256 must
    equal canonical_sha256 of its own obs150 block; a v2 decision always derives, so a
    missing file on either side is DIFFERENT), action CSV bytes, the control fields of
    action_T.json, the SDMPC objective/held_objective of the progress log (repr-exact;
    required on both sides when either action has metadata.sdmpc_active true, absent on
    both sides only for a decision without SDMPC), and the action contract (66 VSL rows at
    --vsl-expected, 8 meter rows). Writes <out_dir>/replay_compare.json; last line
    REPLAY_COMPARE verdict=IDENTICAL|DIFFERENT; exit 0 only when identical.
"""
from __future__ import annotations

import argparse
import copy
import csv
import io
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from n31_common import (ToolError, file_sha256, link_or_copy, long_path, oc, previous_decision_sec,  # noqa: E402
                        read_json, require, write_json)

MANIFEST_SCHEMA = 'sdmpc31-replay-state/v1'
MANIFEST_NAME = 'replay_manifest.json'
COMPARE_NAME = 'replay_compare.json'
REPLAY_SUBDIR = 'replay'
CONTROL_FIELDS = ('N_P_star', 'N_UF_star', 'ramp_metering', 'vsl', 'green_times', 'offsets',
                  'inflow_outflow_allocation')
PREVIOUS_SUFFIXES = ('.json', '.csv', '.json.applied', '.json.sdmpc_pending', '.decision_budget.json')
ORIGINAL_SUFFIXES = ('.json', '.csv', '.joint.progress.jsonl')
VSL_ROWS = 66
METER_ROWS = 8


def _rel(sim_sec, suffix):
    return f'action_{sim_sec:06d}{suffix}'


def _state_file(directory, sim_sec):
    return Path(directory) / f'state_{sim_sec:06d}.json'


def _load_state(path):
    with io.open(long_path(path), encoding='utf-8-sig') as handle:
        return json.load(handle)


def _remap(value, old_root, new_root, what):
    path = Path(value).resolve()
    try:
        relative = path.relative_to(old_root)
    except ValueError as error:
        raise ToolError(f'{what} {value} is not inside the decisions folder {old_root}') from error
    return str(new_root / relative) if str(relative) != '.' else str(new_root)


def _index_prefix(decisions_dir, obs):
    """The mer index as it stood right after the capture at T: entries up to and including T."""
    path = oc.resolve({'directory': str(decisions_dir)}, oc.MER_INDEX_PATH)
    document = json.loads(path.read_text(encoding='utf-8'))
    oc.validate_mer_index(document)
    entries = [e for e in document['entries'] if e['sim_sec'] <= obs['sim_sec']]
    require(entries and entries[-1]['sim_sec'] == obs['sim_sec']
            and entries[-1]['entry_sha256'] == obs['mer']['index_sha256'],
            'mer index lacks the entry the state pins')
    prefix = {'schema': document['schema'], 'source': document['source'], 'entries': entries}
    oc.validate_mer_index(prefix)
    return oc.canonical_json_bytes(prefix) + b'\n', len(entries), len(document['entries'])


def prepare(decisions_dir, sim_sec, out_dir, previous_sec=None):
    decisions_dir = Path(decisions_dir).resolve()
    out_dir = Path(out_dir).resolve()
    source_state = _state_file(decisions_dir, sim_sec)
    require(source_state.is_file(), f'State missing: {source_state}')
    raw = _load_state(source_state)
    obs = raw.get(oc.RAW_STATE_KEY)
    require(isinstance(obs, dict), f'{source_state.name} is not an obs150 (v2) state: no "{oc.RAW_STATE_KEY}" block')
    require(raw.get('sim_sec') == sim_sec and obs.get('sim_sec') == sim_sec, 'State time differs from the request')
    oc.validate_raw(obs)
    oc.validate_lane_meta_v2(raw.get('lane_plant_observation'), raw)
    require(Path(obs['directory']).resolve() == decisions_dir,
            f'obs150.directory {obs["directory"]} is not this decisions folder')
    if sim_sec == oc.FIRST_DECISION_SEC:
        require(previous_sec is None, 't=1 has no previous decision')
    elif previous_sec is None:
        previous_sec = previous_decision_sec(sim_sec)
    oc.load_bundle(raw)                                   # every pin verifies in the source folder first
    require(not out_dir.exists(), f'Replay folder already exists (never reused): {out_dir}')
    out_dir.mkdir(parents=True)

    links = []

    def link(relative, target_rel=None, *, sha=None):
        source = oc.resolve({'directory': str(decisions_dir)}, relative)
        target = oc.resolve({'directory': str(out_dir)}, target_rel or relative)
        actual = file_sha256(source)
        require(sha is None or actual == sha, f'{relative} bytes differ from their pin')
        method = link_or_copy(source, target)
        require(file_sha256(target) == actual, f'Linked copy of {relative} differs')
        links.append({'rel': (target_rel or relative), 'source': str(source), 'sha256': actual, 'method': method})

    frames = obs['frames']
    link(frames['current']['path'], sha=frames['current']['sha256'])
    link(frames['previous']['path'], sha=frames['previous']['sha256'])
    link(obs['mer']['chunk'], sha=obs['mer']['chunk_sha256'])
    link(obs['err']['chunk'], sha=obs['err']['chunk_sha256'])
    link(obs['install_record']['path'], sha=obs['install_record']['sha256'])
    capture = oc.capture_meta_path(sim_sec)
    if oc.resolve({'directory': str(decisions_dir)}, capture).is_file():
        link(capture)
    index_bytes, kept, total = _index_prefix(decisions_dir, obs)
    index_target = oc.resolve({'directory': str(out_dir)}, oc.MER_INDEX_PATH)
    index_target.write_bytes(index_bytes)

    evidence = {'original': {}, 'previous': {}}
    for suffix in ORIGINAL_SUFFIXES:
        if (decisions_dir / _rel(sim_sec, suffix)).is_file():
            link(_rel(sim_sec, suffix), 'original/' + _rel(sim_sec, suffix))
            evidence['original'][suffix] = links[-1]
    derived_rel = oc.derived_path(sim_sec)
    if oc.resolve({'directory': str(decisions_dir)}, derived_rel).is_file():
        link(derived_rel, 'original/' + derived_rel)
        evidence['original']['derived'] = links[-1]
    if previous_sec is not None:
        require((decisions_dir / _rel(previous_sec, '.json')).is_file(),
                f'Previous action missing: {_rel(previous_sec, ".json")}')
        for suffix in PREVIOUS_SUFFIXES:
            if (decisions_dir / _rel(previous_sec, suffix)).is_file():
                link(_rel(previous_sec, suffix), 'previous/' + _rel(previous_sec, suffix))
                evidence['previous'][suffix] = links[-1]

    replay = copy.deepcopy(raw)
    replay[oc.RAW_STATE_KEY]['directory'] = str(out_dir)
    meta = replay['lane_plant_observation']
    old_meta_dir = meta['directory']
    meta['directory'] = _remap(old_meta_dir, decisions_dir, out_dir, 'lane_plant_observation.directory')
    changed = sorted(k for k in set(obs) | set(replay[oc.RAW_STATE_KEY])
                     if obs.get(k) != replay[oc.RAW_STATE_KEY].get(k))
    require(changed == ['directory'], f'Replay obs150 block differs in more than the directory: {changed}')
    replay_state = _state_file(out_dir, sim_sec)
    with io.open(long_path(replay_state), 'w', encoding='utf-8', newline='\n') as handle:
        json.dump(replay, handle, ensure_ascii=False)
    oc.load_bundle(_load_state(replay_state))              # every pin verifies inside out_dir

    manifest = {
        'schema': MANIFEST_SCHEMA, 'sim_sec': sim_sec, 'previous_sec': previous_sec,
        'source_decisions': str(decisions_dir), 'replay_dir': str(out_dir),
        'state': {'source': str(source_state), 'source_sha256': file_sha256(source_state),
                  'replay': str(replay_state), 'replay_sha256': file_sha256(replay_state)},
        'rewritten': {'obs150.directory': [obs['directory'], str(out_dir)],
                      'lane_plant_observation.directory': [old_meta_dir, meta['directory']]},
        'raw_sha256': {'source': oc.canonical_sha256(obs), 'replay': oc.canonical_sha256(replay[oc.RAW_STATE_KEY])},
        'mer_index': {'entries_kept': kept, 'entries_in_run_index': total,
                      'sha256': file_sha256(index_target)},
        'previous_action': (None if previous_sec is None else
                            {'read_from': str(decisions_dir / _rel(previous_sec, '.json')),
                             'why': 'action_P.json.applied binds the absolute path of action_P.csv (sdmpc.py:461-470)'}),
        'links': links, 'evidence': evidence,
    }
    write_json(out_dir / MANIFEST_NAME, manifest)
    print(f'REPLAY_STATE_OK out={out_dir} state={replay_state} sim_sec={sim_sec} previous={previous_sec} '
          f'links={len(links)} index_entries={kept}/{total}')
    return manifest


# ---------------------------------------------------------------- compare
def _progress_objective(path):
    """(objective, held_objective) of the last sdmpc_completed record, or None."""
    if not Path(path).is_file():
        return None
    for line in reversed(Path(path).read_text(encoding='utf-8').splitlines()):
        try:
            record = json.loads(line)
        except ValueError:
            continue
        if (record.get('stage') or record.get('event')) == 'sdmpc_completed':
            return {'objective': record.get('objective'), 'held_objective': record.get('held_objective')}
    return None


def _json_diff(a, b, path='', out=None, limit=40):
    out = [] if out is None else out
    if len(out) >= limit:
        return out
    if isinstance(a, dict) and isinstance(b, dict):
        for key in sorted(set(a) | set(b), key=str):
            if key not in a or key not in b:
                out.append(f'{path}/{key}: only in {"replay" if key in b else "original"}')
            else:
                _json_diff(a[key], b[key], f'{path}/{key}', out, limit)
    elif isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        for i, (x, y) in enumerate(zip(a, b)):
            _json_diff(x, y, f'{path}[{i}]', out, limit)
    elif a != b or type(a) is not type(b):
        out.append(f'{path}: {a!r:.80} != {b!r:.80}')
    return out


def action_contract(csv_path, vsl_expected):
    with open(csv_path, newline='', encoding='utf-8-sig') as handle:
        rows = list(csv.DictReader(handle))
    vsl = [r for r in rows if r.get('kind') == 'vsl']
    meters = [r for r in rows if r.get('kind') == 'ramp_meter']
    speeds = sorted({float(r['speed_kph']) for r in vsl})
    ok = len(vsl) == VSL_ROWS and len(meters) == METER_ROWS and (vsl_expected is None or speeds == [vsl_expected])
    return {'ok': ok, 'vsl_rows': len(vsl), 'vsl_speeds': speeds, 'vsl_expected': vsl_expected,
            'meter_rows': len(meters)}


def compare(out_dir, vsl_expected=None):
    out_dir = Path(out_dir).resolve()
    manifest = read_json(out_dir / MANIFEST_NAME)
    require(manifest.get('schema') == MANIFEST_SCHEMA, f'Not a replay folder: {out_dir}')
    t = manifest['sim_sec']
    replay_dir = out_dir / REPLAY_SUBDIR
    original = out_dir / 'original'
    checks = {}

    source_state = _load_state(manifest['state']['source'])
    replay_state = _load_state(manifest['state']['replay'])
    derived_rel = oc.derived_path(t)
    mine, theirs = out_dir / Path(*derived_rel.split('/')), original / Path(*derived_rel.split('/'))
    # prepare accepts only v2 states, and every v2 decision derives before it decides
    # (runtime_setup.configure_runtime -> lane_plant_runtime.observe_state -> write_derived, for
    # every controller): a missing derived file on either side is a difference, never 'not checked'.
    if theirs.is_file() and mine.is_file():
        a, b = json.loads(theirs.read_text(encoding='utf-8')), json.loads(mine.read_text(encoding='utf-8'))
        raw_ok = (a['inputs']['raw_sha256'] == oc.canonical_sha256(source_state[oc.RAW_STATE_KEY])
                  and b['inputs']['raw_sha256'] == oc.canonical_sha256(replay_state[oc.RAW_STATE_KEY]))
        a2, b2 = copy.deepcopy(a), copy.deepcopy(b)
        a2['inputs'].pop('raw_sha256')
        b2['inputs'].pop('raw_sha256')
        diff = _json_diff(a2, b2)
        checks['derived'] = {'ok': raw_ok and not diff, 'raw_sha256_bound': raw_ok, 'differences': diff}
    else:
        checks['derived'] = {'ok': False, 'original_present': theirs.is_file(), 'replay_present': mine.is_file(),
                             'note': f'{derived_rel} missing: a v2 decision always writes it'}

    csv_a, csv_b = original / _rel(t, '.csv'), replay_dir / _rel(t, '.csv')
    require(csv_b.is_file(), f'Replay action missing: {csv_b}')
    checks['action_csv'] = {'ok': csv_a.is_file() and csv_a.read_bytes() == csv_b.read_bytes(),
                            'original_sha256': file_sha256(csv_a) if csv_a.is_file() else None,
                            'replay_sha256': file_sha256(csv_b)}
    json_a, json_b = original / _rel(t, '.json'), replay_dir / _rel(t, '.json')
    action_a = read_json(json_a) if json_a.is_file() else None
    action_b = read_json(json_b) if json_b.is_file() else None
    if action_a is not None and action_b is not None:
        diff = _json_diff({k: action_a.get(k) for k in CONTROL_FIELDS}, {k: action_b.get(k) for k in CONTROL_FIELDS})
        checks['action_controls'] = {'ok': not diff, 'differences': diff}
    else:
        checks['action_controls'] = {'ok': False, 'note': 'action JSON missing on one side'}
    # An SDMPC decision (metadata.sdmpc_active is True, the condition of .sdmpc_pending, AD:13544)
    # always logs sdmpc_completed: its objective must be there on both sides. Only a decision that
    # ran no SDMPC (the warmup controller) has none.
    active = {side: isinstance(doc, dict) and (doc.get('metadata') or {}).get('sdmpc_active') is True
              for side, doc in (('original', action_a), ('replay', action_b))}
    required = any(active.values())
    obj_a = _progress_objective(original / _rel(t, '.joint.progress.jsonl'))
    obj_b = _progress_objective(replay_dir / _rel(t, '.joint.progress.jsonl'))
    checks['objective'] = {'ok': None if obj_a is None and obj_b is None and not required else
                           (obj_a is not None and obj_b is not None
                            and repr(obj_a['objective']) == repr(obj_b['objective'])
                            and repr(obj_a['held_objective']) == repr(obj_b['held_objective'])),
                           'sdmpc_active': active, 'required': required, 'original': obj_a, 'replay': obj_b}
    checks['action_contract'] = action_contract(csv_b, vsl_expected)
    # None is left only for the objective of a decision without SDMPC (warmup).
    verdict = 'IDENTICAL' if all(c['ok'] in (True, None) for c in checks.values()) else 'DIFFERENT'
    report = {'schema': 'sdmpc31-replay-compare/v1', 'sim_sec': t, 'verdict': verdict, 'checks': checks}
    write_json(out_dir / COMPARE_NAME, report)
    for name, check in checks.items():
        print(f'REPLAY_CHECK {name} ok={check["ok"]}')
    print(f'REPLAY_COMPARE verdict={verdict} sim_sec={t} report={out_dir / COMPARE_NAME}')
    return report


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('prepare')
    p.add_argument('decisions_dir')
    p.add_argument('sim_sec', type=int)
    p.add_argument('out_dir')
    p.add_argument('--previous-sec', type=int, default=None)
    c = sub.add_parser('compare')
    c.add_argument('out_dir')
    c.add_argument('--vsl-expected', type=float, default=None)
    c.add_argument('--tuning', default=None, help='effective tuning whose max(vsl_set) is the expected VSL')
    args = parser.parse_args(argv)
    if args.command == 'prepare':
        prepare(args.decisions_dir, args.sim_sec, args.out_dir, args.previous_sec)
        return 0
    expected = args.vsl_expected
    if expected is None and args.tuning:
        from n31_common import effective_vsl_max, load_effective_tuning
        expected = effective_vsl_max(load_effective_tuning(args.tuning)[0])
    return 0 if compare(args.out_dir, expected)['verdict'] == 'IDENTICAL' else 1


if __name__ == '__main__':
    try:
        sys.exit(main(sys.argv[1:]))
    except (ToolError, oc.ObsContractError) as error:
        print(f'REPLAY_STATE_ERROR {error}')
        sys.exit(1)
