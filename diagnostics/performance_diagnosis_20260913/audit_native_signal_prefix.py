"""Read-only V3 LDP prefix check using existing parsers and CommandClock.

No model/COM/FZP calls, modified source provenance, or completion receipt.
Use a fresh --output-prefix to rerun without overwriting prior evidence.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import re
import sys
from time import perf_counter
import traceback
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from diagnostics.com_execution_equivalence import verify_pair as verify
from diagnostics.com_execution_equivalence.command_clock import CommandClock, native_options, native_clock_options
from diagnostics.validate_native_signal_record import read_ldp_frames, check_ldp_command_clock, parse_ldp_columns
from evaluation.controllers.action_csv_schema import ACTION_CSV_FIELDS

RUN = 'codex_fid_cl9000_s13_v3'


def derive_exact_prefix(files_by_sc, expected, end, directory, record_pin):
    """Copy one exact initial byte slice per file, after all strict parsers pass."""
    directory = directory.resolve()
    verify.require(directory.is_relative_to(ROOT / 'diagnostics/performance_diagnosis_20260913'),
                   'Derived output must stay inside this diagnosis directory')
    verify.require(not directory.exists(), 'Derived prefix directory already exists')
    planned = []
    for sc, source_path in sorted(files_by_sc.items()):
        original = record_pin(source_path)
        offset, boundaries, complete_times = 0, [], []
        width = 12 + len(expected[sc])
        for line in original.splitlines(keepends=True):
            offset += len(line)
            body = line.rstrip(b'\r\n')  # Inspection only; saved bytes are never rebuilt.
            if len(body) != width or not re.match(rb'^\s*\d', body):
                continue
            second = verify.integer(body[:7].decode('ascii'))
            complete_times.append((offset, second))
            if second == end:
                verify.require(line.endswith(b'\n'), 'Target row has no complete line terminator')
                boundaries.append(offset)
        verify.require(len(boundaries) == 1, 'Missing/duplicate complete target row; no safe prefix boundary')
        boundary = boundaries[0]
        verify.require(not any(second <= end for stop, second in complete_times if stop > boundary),
                       'A discarded complete row belongs to the requested prefix')
        prefix = original[:boundary]
        # The existing parser rejects any missing, malformed, reordered or
        # mismatching-address row before/at the boundary. No line is filtered.
        parsed = parse_ldp_columns(prefix, sc, expected[sc], 1, end)
        verify.require(parsed['file_row_count'] == end, 'Prefix includes extra rows')
        planned.append((sc, source_path, original, prefix))
    total = sum(len(prefix) for _, _, _, prefix in planned)
    verify.require(total <= 8 * 1024 * 1024, 'Derived LDP copy exceeds this bounded diagnostic size limit')
    directory.mkdir(parents=True, exist_ok=False)
    rows, derived_files = [], {}
    for sc, source_path, original, prefix in planned:
        target = directory / source_path.name
        with target.open('xb') as handle:
            handle.write(prefix)
        copied = target.read_bytes()
        verify.require(copied == prefix == original[:len(copied)], 'Derived copy is not an exact source byte prefix')
        verify.require(source_path.read_bytes() == original, 'Original LDP changed during derivation')
        rows.append({'sc_no': sc, 'source_path': str(source_path),
            'source_sha256': hashlib.sha256(original).hexdigest(), 'source_bytes': len(original),
            'derived_path': str(target), 'derived_sha256': hashlib.sha256(copied).hexdigest(),
            'derived_bytes': len(copied), 'source_prefix_end_byte_exclusive': len(copied),
            'source_prefix_equals_derived_bytes': True, 'original_bytes_unchanged': True,
            'discarded_suffix_bytes': len(original) - len(copied),
            'discarded_suffix_sha256': hashlib.sha256(original[len(copied):]).hexdigest(),
            'strict_original_parser_rows': end})
        derived_files[sc] = target
    manifest = {'schema': 'exact-native-ldp-byte-prefix/v1', 'run': RUN,
        'first_sec': 1, 'last_sec': end, 'original_requested_end_sec': 8850,
        'excluded_requested_time_range_sec': [end + 1, 8850],
        'excluded_requested_time_count': 8850 - end, 'files': rows,
        'file_count': len(rows), 'derived_total_bytes': total,
        'record_values_changed': False, 'rows_added': False, 'interior_rows_removed': False,
        'scope': 'Exact initial source bytes through the unique complete target row; original files remain unchanged'}
    manifest_path = directory / 'manifest.json'
    with manifest_path.open('x', encoding='utf-8', newline='\n') as handle:
        json.dump(manifest, handle, ensure_ascii=False, indent=2); handle.write('\n')
    return derived_files, manifest_path, manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-prefix', type=Path,
                        default=Path(__file__).with_name('native_signal_prefix'))
    parser.add_argument('--end', type=int, choices=(8741, 8850), default=8850,
                        help='Explicit diagnostic window; strict parsing still checks bytes outside it')
    parser.add_argument('--reuse-vsl-audit', type=Path,
                        help='Reuse a pinned prior PASS for identical run, CSVs and 8700-second apply schedule')
    parser.add_argument('--derive-exact-prefix', type=Path,
                        help='Explicit separate directory for exact source byte prefixes; allowed only with --end 8741')
    args = parser.parse_args()
    output = [args.output_prefix.with_suffix(s) for s in ('.json', '.md')]
    if any(p.exists() for p in output):
        raise FileExistsError('Use a fresh --output-prefix; prior evidence is preserved')
    if args.derive_exact_prefix is not None and args.end != 8741:
        raise ValueError('The explicitly approved derived-prefix endpoint is 8741 only')
    tick = perf_counter()
    run = ROOT / 'evaluation/runs' / RUN
    folder = run / ('decisions_' + RUN)
    first_sec, last_sec, last_command = 1, args.end, 8700
    result = {
        'schema': 'interrupted-run-native-signal-prefix/v1', 'run': RUN,
        'audit_finished': False, 'native_signal_prefix_passed': False,
        'prefix_execution_evidence_passed': False,
        'full_run_completed': False, 'full_native_execution_certified': False,
        'process_exit_verified': False, 'completion_receipt_verified': False,
        'window': {'first_sec': first_sec, 'last_sec': last_sec, 'last_command_sec': last_command},
        'requested_prefix_end_sec': 8850,
        'candidate_common_complete_end_sec': last_sec,
        'verified_through_sec': None,
        'requested_tail_beyond_candidate_window_sec': 8850 - last_sec,
        'checks': {}, 'source_pins': {},
        'native_lsa_com_coverage': {'passed': None, 'status': 'not_assessed_not_certified',
            'scope': 'LSA COM-transition coverage remains separate; an LDP pass does not repair missing LSA coverage'},
        'limitations': [
            'Interrupted 1..8850 prefix only; original requested SimPeriod=9000 is not changed.',
            'LDP t uses the existing post-step command clock at t-1; no action_008850 is invented.',
            'Before each first controlled application, LDP is native evidence without a fabricated control expectation.',
            'Signal first/changed immediate setter readbacks are not audited here; LDP is actual sampled state evidence.',
            'VSL checks setter-time class distribution IDs only, not observed vehicle speed or every-second reads.',
            'No FZP, physical model, live native run, state reconstruction, or causal performance claim.',
        ],
    }
    checks = result['checks']
    stage = 'sources'

    def pin(path, expected=None):
        path = Path(path).resolve(strict=True)
        before = path.stat()
        data = path.read_bytes()
        after = path.stat()
        verify.require((before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns),
                       'File changed while reading: ' + str(path))
        digest = hashlib.sha256(data).hexdigest()
        verify.require(expected is None or digest == expected, 'Original source SHA mismatch: ' + str(path))
        result['source_pins'][str(path)] = {'bytes': len(data), 'sha256': digest, 'expected_sha256': expected}
        return data

    def source(item):
        path = verify.path(item['path'])
        pin(path, item['sha256'])
        return path

    try:
        pp = run / ('run_provenance_' + RUN + '.json')
        prov = json.loads(pin(pp).decode('utf-8-sig'))
        verify.require(prov['name'] == RUN and prov['run_id'] and prov['seed'] == 13
                       and prov['sim_period_sec'] == 9000 and prov['control_interval_sec'] == 150,
                       'Wrong original run identity/period/cadence')
        result['run_id'] = prov['run_id']
        result['original_requested_sim_period_sec'] = prov['sim_period_sec']
        result['completion_receipt_present'] = (run / 'completion_receipt.json').exists()
        files = {key: source(prov['files'][key]) for key in (
            'network', 'main_vbs_runner', 'generated_vbs_config', 'signal_group_plan',
            'control_mapping', 'tuning', 'network_recording_proof')}
        config, plan = files['generated_vbs_config'], files['signal_group_plan']
        verify.require(plan == config.with_name(config.stem + '_sgplan.vbs'),
                       'Original pinned plan is not the actual config sibling')
        vbs_text = files['main_vbs_runner'].read_text(encoding='utf-8-sig')
        plan_text = plan.read_text(encoding='utf-8-sig')
        groups, excluded = verify._plan_groups(plan.read_bytes(), prov['env'].get('RW_MAINLINE_SG_ONLY') == '1')
        native_clocks = native_clock_options(plan_text, groups)
        meters = native_options(vbs_text, config.read_text(encoding='utf-8-sig'))
        timing = verify.ramp_meter_timing_authority(prov, vbs_text)
        mapping = json.loads(files['control_mapping'].read_text(encoding='utf-8-sig'))
        verify.require(not (set(groups) & set(meters)), 'Urban/meter SC overlap')
        verify.require({str(verify.integer(r['sc_no'])) for r in mapping['signals']} == set(groups),
                       'Original mapping/plan SC mismatch')
        verify.require(Counter(str(verify.integer(r['sc_no'])) for r in mapping['ramp_meters'])
                       == Counter({sc: 1 for sc in meters}), 'Original meter ownership mismatch')
        expected = {int(sc): [int(sg) for sg in sgs] for sc, sgs in groups.items()}
        expected.update({int(sc): [1] for sc in meters})
        network = ET.parse(files['network']).getroot()
        recording = network.find('./evaluation/scDetRec')
        verify.require(recording is not None and recording.get('writeFile') == 'true',
                       'Actual network has native recording disabled')
        for sc, sgs in expected.items():
            node = network.find(f'./signalControllers/signalController[@no="{sc}"]')
            verify.require(node is not None, 'Recorded controller missing from original loaded network')
            columns = node.findall('./scDetRecConf/signalOutputConfigurationElement')
            verify.require([c.get('configName') for c in columns[:2]] == ['SIM_SEK', 'UML_SEK']
                           and len(columns) == len(sgs) + 2
                           and all(c.get('configName') == 'SG_BILD' for c in columns[2:])
                           and Counter(c.get('sg') for c in columns[2:]) == Counter(f'{sc} {sg}' for sg in sgs),
                           'Original recording columns do not match pinned owned SGs')
        checks[stage] = {'passed': True, 'urban_controllers': len(groups), 'meter_controllers': len(meters),
                         'recorded_groups': sum(map(len, expected.values())), 'ramp_meter_timing': timing,
                         'excluded_midblock_groups': excluded, 'original_manifest_unchanged': True}

        stage = 'commands'
        csv_files = list(folder.glob('action_*.csv'))
        times = [verify.integer(p.stem.split('_')[1]) for p in csv_files]
        required_times = {1, *range(150, last_command + 1, 150)}
        verify.require(len(times) == len(set(times)) and set(times) == required_times,
                       'Missing/extra original prefix action CSV time')
        dsds = [verify.integer(r['dsd_no']) for segment in mapping['segments']
                for r in [*segment['dsd_by_lane'].values(), *segment.get('extra_dsd_controls', [])]]
        verify.require(len(dsds) == len(set(dsds)) == 66, 'Expected exact 66 original VSL addresses')
        batches, first_control, vsl_windows, distributions = {}, {}, {}, {}
        command_counts = []
        city_started = False
        for t in sorted(times):
            path = folder / f'action_{t:06d}.csv'
            pin(path)
            with path.open(encoding='utf-8-sig', newline='') as handle:
                reader = csv.DictReader(handle); rows = list(reader)
            verify.require(reader.fieldnames == list(ACTION_CSV_FIELDS) and rows
                           and all(None not in r and None not in r.values() for r in rows), 'Malformed actual action CSV')
            verify.require(Counter(verify.integer(r['dsd_no']) for r in rows if r['kind'] == 'vsl') == Counter(dsds),
                           'Missing/extra VSL address in actual CSV')
            verify.require(Counter(str(verify.integer(r['sc_no'])) for r in rows if r['kind'] == 'ramp_meter')
                           == Counter({sc: 1 for sc in meters}), 'Missing/extra actual meter row')
            city = Counter(str(verify.integer(r['sc_no'])) for r in rows if r['kind'] == 'signal')
            verify.require(not city_started or bool(city), 'Urban control disappeared from later CSV')
            if city:
                verify.require(city == Counter({sc: 1 for sc in groups}), 'Partial actual urban batch')
                city_started = True
                for sc, sgs in groups.items():
                    for sg in sgs: first_control.setdefault(sc + ':' + sg, t)
            for sc in meters: first_control.setdefault(sc + ':1', t)
            for r in rows:
                if r['kind'] != 'vsl': continue
                speed = verify.integer(r['speed_kph'])
                distributions[str(verify.number(speed).normalize())] = speed
                for cls in (10, 20, 30, 70):
                    key = str(verify.integer(r['dsd_no'])) + ':' + str(cls)
                    vsl_windows.setdefault(key, {'start': t, 'end': last_command, 'apply_seconds': []})['apply_seconds'].append(t)
            batches[t] = rows
            command_counts.append({'sim_sec': t, 'rows': len(rows), 'kinds': dict(Counter(r['kind'] for r in rows))})
        clock = CommandClock(batches, groups, meters, native_clock_plans=native_clocks,
                             ramp_amber_sec=timing['amber_sec'])
        checks[stage] = {'passed': True, 'command_count': len(times), 'first_command_sec': min(times),
                         'last_command_sec': max(times), 'first_control_sec_by_group': first_control,
                         'vsl_class_addresses': len(vsl_windows), 'commands': command_counts,
                         'terminal_command_invented': False}

        stage = 'native_ldp_prefix'
        print(json.dumps({'stage': stage, 'controllers': len(expected), 'seconds': last_sec}), flush=True)
        ldp_paths = list((run / 'vissim_eval').glob('*.ldp'))
        stem = files['network'].stem
        files_by_sc = {}
        for sc in expected:
            matches = [p for p in ldp_paths if p.name == f'{stem}_{sc}_001.ldp']
            verify.require(len(matches) == 1 and matches[0].resolve().is_relative_to(run),
                           'Missing/ambiguous original LDP controller ' + str(sc))
            files_by_sc[sc] = matches[0]
        # Pin every selected file even if the existing parser rejects the first.
        # This inventory diagnoses truncation only; it never repairs or strips
        # bytes passed to the original strict state parser below.
        inventory = {}
        for sc, path in files_by_sc.items():
            raw = pin(path)
            numeric = [line for line in raw.splitlines() if re.match(rb'^\s*\d', line)]
            width = 12 + len(expected[sc])
            complete = [line for line in numeric if len(line) == width]
            seconds = [verify.integer(line[:7].decode('ascii')) for line in complete]
            inventory[sc] = {'path': str(path), 'expected_row_width': width,
                'complete_width_numeric_rows': len(complete),
                'first_complete_width_second': min(seconds) if seconds else None,
                'last_complete_width_second': max(seconds) if seconds else None,
                'incomplete_width_numeric_rows': len(numeric) - len(complete),
                'last_numeric_line_hex': numeric[-1].hex() if numeric else None,
                'missing_requested_seconds_from_complete_width_rows': len(set(range(1, last_sec + 1)) - set(seconds)),
                'scope': 'Byte-width/time inventory only; no independent SG-state certification'}
        result['ldp_file_inventory'] = inventory
        try:
            if args.derive_exact_prefix is not None:
                files_by_sc, manifest_path, manifest = derive_exact_prefix(
                    files_by_sc, expected, last_sec, args.derive_exact_prefix, pin)
                pin(manifest_path)
                result['exact_prefix_derivation'] = {'manifest_path': str(manifest_path),
                    'manifest_sha256': result['source_pins'][str(manifest_path)]['sha256'],
                    'file_count': manifest['file_count'], 'derived_total_bytes': manifest['derived_total_bytes'],
                    'excluded_requested_time_range_sec': manifest['excluded_requested_time_range_sec'],
                    'excluded_requested_time_count': manifest['excluded_requested_time_count'],
                    'all_source_prefix_equals_derived': all(x['source_prefix_equals_derived_bytes'] for x in manifest['files']),
                    'all_original_bytes_unchanged': all(x['original_bytes_unchanged'] for x in manifest['files'])}
            record = read_ldp_frames(files_by_sc, expected, first_sec, last_sec)
            comparison = check_ldp_command_clock(record, clock, first_control)
            native_precontrol = comparison.pop('pre_control_native_frames')
            comparison['pre_control_native_frame_count'] = len(native_precontrol)
            comparison['pre_control_native_sample_count'] = sum(map(len, native_precontrol.values()))
            checks[stage] = {**{k: v for k, v in record.items() if k != 'frames'},
                             'passed': comparison['passed'], 'command_clock': comparison,
                             'excluded_unassessed_ldp_files': [str(p) for p in ldp_paths
                                if p.name not in {v.name for v in files_by_sc.values()}],
                             'reads_exact_derived_prefixes': args.derive_exact_prefix is not None}
            result['native_signal_prefix_passed'] = comparison['passed']
            if comparison['passed']:
                result['verified_through_sec'] = last_sec
        except Exception as exc:
            checks[stage] = {'passed': False, 'exception_type': type(exc).__name__, 'message': str(exc),
                             'traceback': traceback.format_exc()}
            result['failure_stage'] = stage

        stage = 'vsl_apply_readbacks'
        vsl_path = folder / 'vsl_readback.csv'
        if args.reuse_vsl_audit is not None:
            reused = json.loads(pin(args.reuse_vsl_audit).decode('utf-8-sig'))
            actual = reused['checks']['vsl_apply_readbacks']
            verify.require(reused['run'] == RUN and reused['run_id'] == prov['run_id']
                           and reused['window']['last_command_sec'] == last_command
                           and actual['passed'] is True and actual['rows'] == len(dsds) * 4 * len(times),
                           'Prior VSL PASS identity/count/schedule mismatch')
            for t in times:
                key = str((folder / f'action_{t:06d}.csv').resolve())
                verify.require(reused['source_pins'][key]['sha256'] == result['source_pins'][key]['sha256'],
                               'Prior VSL audit used different actual command bytes')
            pin(vsl_path, reused['source_pins'][str(vsl_path.resolve())]['sha256'])
            checks[stage] = {**actual, 'reused_from': str(args.reuse_vsl_audit.resolve()),
                             'reused_without_repeating_readback_validation': True}
            result['prior_requested_8850_verdict'] = {
                'path': str(args.reuse_vsl_audit.resolve()),
                'requested_end_sec': reused['window']['last_sec'],
                'native_signal_prefix_passed': reused['native_signal_prefix_passed'],
                'failure': reused['checks'].get('native_ldp_prefix'),
            }
        elif vsl_path.is_file():
            pin(vsl_path)
            actual = verify.readbacks(vsl_path, verify.VSL_FIELDS, vsl_windows,
                command_check=clock.check_vsl, numeric=True, distribution_ids=distributions)
            checks[stage] = {k: v for k, v in actual.items() if k not in ('transitions', 'setter_immediate_writes')}
            checks[stage].update(expected_setter_rows=len(dsds) * 4 * len(times),
                                 each_second_readbacks_requested=False,
                                 classes=[10, 20, 30, 70], command_count=len(times))
        else:
            checks[stage] = {'passed': None, 'status': 'missing_actual_vsl_readback_file'}
        result['prefix_execution_evidence_passed'] = (result['native_signal_prefix_passed'] is True
                                                     and checks[stage]['passed'] is True)
    except Exception as exc:
        checks[stage] = {'passed': False, 'exception_type': type(exc).__name__, 'message': str(exc),
                         'traceback': traceback.format_exc()}
        result['failure_stage'] = stage
        result['prefix_execution_evidence_passed'] = False
    finally:
        result['native_lsa_com_coverage']['files_observed_without_assessing_coverage'] = [
            {'path': str(p), 'bytes': p.stat().st_size} for p in (run / 'vissim_eval').glob('*.lsa')]
        result['audit_finished'] = True
        result['audit_wall_sec'] = perf_counter() - tick
        result['script_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        result['verifier_source_pins'] = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in [
            ROOT / 'diagnostics/com_execution_equivalence/verify_pair.py',
            ROOT / 'diagnostics/com_execution_equivalence/command_clock.py',
            ROOT / 'diagnostics/validate_native_signal_record.py']}
        output[0].parent.mkdir(parents=True, exist_ok=True)
        with output[0].open('x', encoding='utf-8', newline='\n') as handle:
            json.dump(result, handle, ensure_ascii=False, indent=2, allow_nan=False); handle.write('\n')
        native = checks.get('native_ldp_prefix', {})
        comp = native.get('command_clock', {})
        vsl = checks.get('vsl_apply_readbacks', {})
        lines = ['# V3 중단 구간 native 신호 검사', '',
            f'대상 `{RUN}`: 원본 요청 종료9000초, 원래 prefix 요청8850초, 이번 관측 검사1–{last_sec}초, 실제 마지막 명령8700초.', '',
            f"- LDP prefix 상태/명령 시계 일치: **{result['native_signal_prefix_passed']}**. 검사 sample {comp.get('compared_samples')}, mismatch {len(comp.get('mismatches', [])) if comp else None}.",
            f"- 실제 VSL 적용 readback: **{vsl.get('passed')}**; {vsl.get('rows')}행 / 예상 {vsl.get('expected_setter_rows')}행. 66 DSD ×4차종 ×59개 실제 명령 시각만 검사했다. 매초 검사를 추가하지 않았다.",
            '- 전체9000초 완료·전체 native 실행·process 종료 인증은 모두 false다. 원본 provenance의 SimPeriod·state·receipt를 변경하거나8850초 명령을 만들지 않았다.',
            '- LDP8850초는 기존 t−1 명령 시계로8849초에 유지 중인8700초 명령을 검증한다. 도시 제어 이전 native 상태는 기록 범위 확인만 하며 임의의 제어 기대값과 비교하지 않는다.',
            '- LSA 파일 존재와 COM 전환 coverage는 다르다. LSA coverage는 미평가/미인증으로 남기며 LDP 통과로 결측을 채우지 않았다. 별도의 신호 first/changed immediate readback 검사는 이 결과에 포함하지 않는다.',
            f"- LDP 원본의 완전한 고정폭 행 마지막 시각 분포: {dict(Counter(v['last_complete_width_second'] for v in result.get('ldp_file_inventory', {}).values()))}. 원본과 parser는 수정하지 않았다.",
            f"- 별도 exact byte-prefix 파생: {result.get('exact_prefix_derivation')}. 파생 시에도 헤더와 타깃 행까지 모든 원본 byte를 보존하며 중간 행 제거·값 보정은 없다. 이전8850초 실패는 그대로 유지한다.",
            f"- 실제 명령 일치 검증 완료 끝시각: {result['verified_through_sec']}. 이번 후보 창 이후8850초까지 {8850-last_sec}초가 남는다. Parser 실패 시8741초까지도 검증됐다고 선언하지 않는다.",
            f"- 분석 소요 {result['audit_wall_sec']:.3f}초. 실패 stage: {result.get('failure_stage')}. 모든 실패 상세·원본 SHA는 JSON에 보존했다.", '',
            '재현: `python -B diagnostics/performance_diagnosis_20260913/audit_native_signal_prefix.py --output-prefix diagnostics/performance_diagnosis_20260913/recheck/native_signal_prefix`.',
            '원본 런의 LDP·명령 CSV·VSL readback 및 provenance에 지정된 원본 파일이 필요하다. 기존 출력은 덮어쓰지 않는다.', '']
        with output[1].open('x', encoding='utf-8', newline='\n') as handle:
            handle.write('\n'.join(lines))
        print(json.dumps({'output': str(output[0]), 'native_signal_prefix_passed': result['native_signal_prefix_passed'],
                          'vsl_apply_readbacks_passed': vsl.get('passed'), 'full_native_execution_certified': False,
                          'failure_stage': result.get('failure_stage'), 'wall_sec': result['audit_wall_sec']}, ensure_ascii=False))
    return 0 if result['prefix_execution_evidence_passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
