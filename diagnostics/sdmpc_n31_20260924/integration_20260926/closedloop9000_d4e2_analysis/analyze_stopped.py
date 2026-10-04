"""One stopped-run audit using existing accounting and command-clock validators.

No simulation, fitting, fabricated completion receipt, or source-result edits.
The final buffered native tail is excluded; original bytes and their hashes stay
available. Both arms use the same 8100-second interval.
"""
import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT))
from diagnostics.sdmpc_n31_20260924.integration_20260926.native_pair1200 import analyze_pair as ap
from diagnostics.com_execution_equivalence import verify_pair as vp
from diagnostics.validate_native_signal_record import read_ldp_frames, check_ldp_command_clock
from evaluation.controllers.action_csv_schema import ACTION_CSV_FIELDS

END = 8100
RUNS = {'nc': Path('D:/VISSIM_runs/20260927_sd31_wiring9000/nc'),
        'sdmpc': Path('D:/VISSIM_runs/20260928_sd31_d4e2_9000/sdmpc')}
NAMES = {a: f'sdmpc31_{a}9000_s29' for a in RUNS}
OUT = HERE/'stopped_prefix8100'


def execution_prefix(arm):
    run, name = RUNS[arm], NAMES[arm]
    prov = ap.load(run/f'run_provenance_{name}.json')
    assert prov['seed'] == 29 and prov['sim_period_sec'] == 9000
    pins = {k: vp.pin(prov['files'][k]) for k in
            ('network', 'main_vbs_runner', 'generated_vbs_config', 'control_mapping', 'signal_group_plan')}
    prior = OUT/arm/'execution_prefix.json'
    if prior.exists():
        saved = ap.load(prior)
        assert saved['prefix_execution_passed'] and saved['source_pins'] == {k:prov['files'][k] for k in pins}
        for receipt in saved['byte_prefix_views']:
            assert ap.sha256(Path(receipt['source'])) == receipt['source_sha256']
            assert ap.sha256(Path(receipt['view'])) == receipt['view_sha256']
        return prov
    assert pins['signal_group_plan'] == pins['generated_vbs_config'].with_name(pins['generated_vbs_config'].stem+'_sgplan.vbs')
    runner = pins['main_vbs_runner'].read_text(encoding='utf-8-sig')
    plan = pins['signal_group_plan'].read_text(encoding='utf-8-sig')
    groups, _ = vp._plan_groups(pins['signal_group_plan'].read_bytes(), prov['env'].get('RW_MAINLINE_SG_ONLY') == '1')
    clocks = vp.native_clock_options(plan, groups)
    meters = vp.native_options(runner, pins['generated_vbs_config'].read_text(encoding='utf-8-sig'))
    timing = vp.ramp_meter_timing_authority(prov, runner)
    assert timing['amber_sec'] == 0
    mapping = ap.load(pins['control_mapping'])
    assert {str(int(r['sc_no'])) for r in mapping['signals']} == set(groups)
    assert {str(int(r['sc_no'])) for r in mapping['ramp_meters']} == set(meters)
    dsds = [int(r['dsd_no']) for s in mapping['segments'] for r in
            [*s['dsd_by_lane'].values(), *s.get('extra_dsd_controls', [])]]
    assert len(dsds) == len(set(dsds))
    log = (run/f'runlog_{name}.txt').read_bytes()
    assert prov['env']['RW_OBSERVATION_CADENCE'] == 'decision150'
    assert b'SIMRES=10 source=network' in log and b'SIGNAL_FRAME_ADVANCE=1 simres=10 ' in log
    assert f'OBS150_BUNDLE sim_sec={END} '.encode() in log
    folder = run/f'decisions_{name}'
    batches, sg_windows, vsl_windows, distributions = {}, {}, {}, {}
    for sec in [1, *range(150, END, 150)]:
        with (folder/f'action_{sec:06d}.csv').open(encoding='utf-8-sig', newline='') as f:
            reader = csv.DictReader(f); rows = list(reader)
        assert reader.fieldnames == list(ACTION_CSV_FIELDS) and rows
        assert all(None not in r and None not in r.values() for r in rows)
        assert Counter(int(r['dsd_no']) for r in rows if r['kind']=='vsl') == Counter(dsds)
        assert Counter(str(int(r['sc_no'])) for r in rows if r['kind']=='ramp_meter') == Counter({sc:1 for sc in meters})
        city = Counter(str(int(r['sc_no'])) for r in rows if r['kind']=='signal')
        if arm == 'sdmpc' and sec >= 900:
            assert city == Counter({sc:1 for sc in groups})
        if city:
            for sc, values in groups.items():
                for sg, count in values.items():
                    sg_windows.setdefault(sc+':'+sg, {'start':sec,'end':END,'zero_window':count==0})
        for sc in meters:
            sg_windows.setdefault(sc+':1', {'start':sec,'end':END})
        for row in rows:
            if row['kind'] == 'vsl':
                speed = int(float(row['speed_kph'])); distributions[str(vp.number(speed).normalize())] = speed
                for cls in (10,20,30,70):
                    key = f"{int(row['dsd_no'])}:{cls}"
                    vsl_windows.setdefault(key, {'start':sec,'end':END,'apply_seconds':[]})['apply_seconds'].append(sec)
        batches[sec] = rows
    clock = vp.CommandClock(batches, groups, meters, native_clock_plans=clocks, ramp_amber_sec=timing['amber_sec'])
    views = OUT/arm/'recorded_prefix'; views.mkdir(parents=True, exist_ok=True)
    receipts = []
    # Copy only actual bytes inside the declared prefix. Do not add terminal or
    # completion rows. The command at END would affect only the excluded future.
    for filename in ('signal_readback.csv', 'vsl_readback.csv'):
        source = folder/filename; lines = source.read_bytes().splitlines(keepends=True)
        kept = [lines[0]]
        for line in lines[1:]:
            fields = line.decode('utf-8-sig').strip().split(',')
            sec = float(fields[0])
            if sec < END or (filename=='signal_readback.csv' and sec==END and fields[-1]=='post_step'):
                assert line.endswith(b'\n'); kept.append(line)
        target = views/filename; target.write_bytes(b''.join(kept))
        receipts.append({'source':str(source),'source_sha256':ap.sha256(source),'view':str(target),'view_sha256':ap.sha256(target)})
    signals = vp.readbacks(views/'signal_readback.csv', vp.SG_FIELDS, sg_windows,
        command_check=clock.check_signal, control_interval=150, require_next_step_post=False)
    vsl = vp.readbacks(views/'vsl_readback.csv', vp.VSL_FIELDS, vsl_windows,
        command_check=clock.check_vsl, numeric=True, distribution_ids=distributions)
    network = ET.parse(pins['network']).getroot()
    expected, files = {}, {}
    for sc in sorted(set(groups)|set(meters), key=int):
        node = network.find(f'./signalControllers/signalController[@no="{sc}"]')
        conf = node.findall('./scDetRecConf/signalOutputConfigurationElement')
        assert [r.get('configName') for r in conf[:2]] == ['SIM_SEK','UML_SEK']
        addresses = [r.get('sg').split() for r in conf[2:]]
        assert all(r.get('configName')=='SG_BILD' for r in conf[2:])
        expected[int(sc)] = [int(sg) for addr,sg in addresses if addr==sc]
        owned = set(map(int, groups[sc])) if sc in groups else {1}
        assert owned <= set(expected[int(sc)]) and len(addresses)==len(expected[int(sc)])
        source = run/'vissim_eval'/f'{pins["network"].stem}_{sc}_001.ldp'
        kept = []
        for line in source.read_bytes().splitlines(keepends=True):
            if re.match(rb'\s*\d',line):
                # Native fixed-width clock remains readable even on a truncated
                # final row. The incomplete tail is outside END and never used.
                if float(line[:7]) > END:
                    break
                assert line.endswith(b'\n'), (source,'partial in requested prefix')
            kept.append(line)
        target = views/source.name; target.write_bytes(b''.join(kept)); files[int(sc)] = target
        receipts.append({'source':str(source),'source_sha256':ap.sha256(source),'view':str(target),'view_sha256':ap.sha256(target)})
    record = read_ldp_frames(files, expected, 1, END)
    assert all(n==END for n in record['file_row_count_by_sc'].values())
    controlled = {int(sc):[int(sg) for sg in groups[sc] if sc+':'+sg in sg_windows] for sc in groups}
    controlled = {sc:sgs for sc,sgs in controlled.items() if sgs}
    controlled.update({int(sc):[1] for sc in meters})
    subset = {**record,'expected_groups':controlled,
              'frames':{t:{k:v for k,v in r.items() if k in sg_windows} for t,r in record['frames'].items()}}
    comparison = check_ldp_command_clock(subset, clock, {k:w['start'] for k,w in sg_windows.items()})
    assert comparison['passed'], comparison
    result = {'scope':f'Actual recorded prefix1..{END}; not whole9000 completion',
              'prefix_execution_passed':True, 'whole9000_completed':False,
              'controlled_signal_groups':len(sg_windows), 'vsl_class_addresses':len(vsl_windows),
              'source_pins':{k:prov['files'][k] for k in pins}, 'byte_prefix_views':receipts,
              'signal_readbacks':signals, 'vsl_readbacks':vsl, 'native_ldp':comparison,
              'late_buffered_tail_excluded':True, 'lsa_com_coverage_verified':False}
    ap.save(OUT/arm/'execution_prefix.json', result)
    return prov


def main():
    assert (RUNS['sdmpc'].parent/'STOP').is_file()
    assert ap.load(HERE/'user_stop_receipt.json')['owned_processes_closed'] is True
    assert not (OUT/'summary.json').exists(), 'Preserve completed analysis'
    OUT.mkdir(exist_ok=True)
    ledger = ap.load(HERE.parent/'selected/scenario/control_area_membership_213a5d.json')
    for item in [ledger['network'], *ledger['sources']]:
        assert ap.sha256(ROOT/item['path'])==item['sha256']
    membership = ap.physical_membership_from_ledger(ledger); terminals = ap.terminal_lengths(ledger)
    summary = {'scope':'User-stopped native run; matched fully recorded8100s prefix', 'end_sec':END,
               'run_names':NAMES,'whole_omega_gain_qualified':False,'whole9000_completed':False,
               'native_uninserted_delay_available':False,'arms':{},'prefixes':{}}
    provenances = {}
    for arm, run in RUNS.items():
        provenances[arm] = execution_prefix(arm)
        errors, removals = [], {}
        for source in sorted(run.rglob('*.err')):
            parsed = ap.parse_bytes(source.read_bytes()); assert not parsed['unparsed_removal_lines']
            errors.append({'source':str(source),'sha256':ap.sha256(source),**parsed})
            for event in parsed['events']:
                if event['kind']=='lane_change_removal' and event['time_sec']<=END:
                    removals[str(event['vehicle_id'])] = event
        ap.save(OUT/arm/'native_errors.json', {'sources':errors,'prefix_removals':removals})
        fzp, = (run/'vissim_eval').glob('*.fzp'); before = fzp.stat()
        summary['prefixes'][arm] = ap.prefix_digest(fzp,900,recording_grid=(5,.1))
        def audited_frames():
            previous = None
            for frame in ap.read_fzp_frames(fzp):
                if frame.time_sec > END:
                    break
                if previous:
                    dt = frame.time_sec-previous.time_sec
                    for no in previous.vehicles.keys()-frame.vehicles.keys():
                        v = previous.vehicles[no]
                        if no in removals and v.link in terminals:
                            reach = v.speed_kph/3.6*dt+1.5*dt*dt+10
                            overshoot = v.speed_kph/3.6*.1+.015+10
                            assert not -overshoot <= terminals[v.link]-v.position_m <= reach, ('Removal counted as terminal TTD',no)
                previous = frame
                yield frame
        metric_path = OUT/arm/'area_metrics.json'
        if metric_path.exists():
            # Reuse the already completed matched-NC scan after a later arm's
            # readback/parser failure; native source files are closed/read-only.
            assert before.st_mtime_ns <= metric_path.stat().st_mtime_ns
            metrics = ap.load(metric_path)
            assert metrics['boundaries']['requested_end_sec'] == END
            assert (OUT/arm/'area_timeseries.csv').is_file()
        else:
            metrics, times = ap.measure_frames(audited_frames(),membership,terminals,end_sec=END,simulation_step_sec=.1)
            after = fzp.stat(); assert (before.st_size,before.st_mtime_ns)==(after.st_size,after.st_mtime_ns)
            ap.save(metric_path,metrics); ap.table(OUT/arm/'area_timeseries.csv',times)
        assert metrics['sampling']['nominal_step_sec']==5 and metrics['sampling']['missing_snapshot_gaps']==0
        summary['arms'][arm] = {'TTT_veh_h':metrics['ttt_veh_h'],
            'outside_Omega_residence_veh_h':sum(v['ttt_veh_h'] for v in metrics['physical_link_residence'].values() if not v['inside']),
            'Omega_TTD_events':metrics['ttd_observed_plus_terminal_events'],
            'Omega_end_vehicles':metrics['censored_last_observed_inside_vehicles'],
            'unresolved_Omega_disappearances':metrics['unresolved_inside_disappearances'],
            'native_removals_through_end':len(removals),'last_fzp_sec':metrics['boundaries']['last_fzp_sec'],
            'tail_hold_veh_h':metrics['ttt_censored_tail_extrapolation_veh_h'],
            'native_uninserted_delay_veh_h':None,'native_uninserted_at_end':None}
        print(json.dumps({arm:summary['arms'][arm]}),flush=True)
    for key in ('network','demand_profile','generated_vbs_config'):
        assert provenances['nc']['files'][key]['sha256']==provenances['sdmpc']['files'][key]['sha256']
    summary['paired_prefix_exact'] = summary['prefixes']['nc']==summary['prefixes']['sdmpc']
    assert summary['paired_prefix_exact']
    a,b = summary['arms']['nc'],summary['arms']['sdmpc']
    summary.update(delta_TTT_veh_h=b['TTT_veh_h']-a['TTT_veh_h'],
        delta_TTT_percent=100*(b['TTT_veh_h']/a['TTT_veh_h']-1),
        delta_outside_Omega_residence_veh_h=b['outside_Omega_residence_veh_h']-a['outside_Omega_residence_veh_h'],
        limitations=['Interrupted run has no normal completion or native total/latent cost receipt.',
          'Buffered LDP/ERR tail is truncated;8100 is used for complete command-clock verification.',
          '5s FZP residence uses4.9s terminal stock hold, not invented exits.',
          'TTD contains observed exits and physically screened terminal disappearance inference; unresolved losses are separate.',
          'Urban signals and freeway commands change together; not a single-lever causal comparison.',
          'LSA COM coverage is unverified; actual LDP and setter readbacks supply prefix execution evidence.'])
    ap.save(OUT/'sdmpc_decisions.json',ap.decision_summary(RUNS['sdmpc']/f'decisions_{NAMES["sdmpc"]}',900,END))
    ap.save(OUT/'summary.json',summary)
    ap.cached_diagnostics(RUNS['sdmpc'].parent,OUT,RUNS['nc'])
    print(json.dumps({k:v for k,v in summary.items() if k not in ('arms','prefixes','limitations')}),flush=True)


if __name__=='__main__':
    main()
