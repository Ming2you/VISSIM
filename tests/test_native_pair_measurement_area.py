"""Final native comparison must retain the requested approach-inclusive area."""
import json
from pathlib import Path

import pytest

from diagnostics.sdmpc_n31_20260924.integration_20260926.native_pair1200.analyze_pair import measurement_area
from diagnostics.sdmpc_n31_20260924.integration_20260926.native_pair1200.analyze_pair import closed_loop_analysis_end, traffic_events_through
from scripts.measure_control_area import Frame, Vehicle, measure_frames

ROOT = Path(__file__).resolve().parents[1]
AREA = ROOT/'diagnostics/repin_v3c3_review_20261001/urban_area263/approaches_only/membership.json'


def test_701_area_pins_and_revised_builder_are_verified():
    _, membership, receipt = measurement_area(AREA)
    assert receipt['inside_links'] == 701 and receipt['same_area_for_both_arms']
    assert membership['66'] and not membership['38'] and not membership['67']
    assert str((ROOT/'diagnostics/build_control_area_membership.py').resolve()) in receipt['current_source_pins']


def test_approach_wait_is_counted_but_internal_transition_is_not_an_exit():
    _, membership, _ = measurement_area(AREA)
    frames = [Frame(5, {'1': Vehicle('66', 10, 0)}),
              Frame(10, {'1': Vehicle('10633', 1, 10)}),
              Frame(15, {'1': Vehicle('68', 5, 10)})]
    metrics, _ = measure_frames(frames, membership, {}, end_sec=15, simulation_step_sec=.1)
    assert metrics['ttt_veh_h'] == pytest.approx(12.5/3600)
    assert metrics['ttd_observed_exit_events'] == 0
    assert metrics['censored_last_observed_inside_vehicles'] == 1


@pytest.mark.parametrize('section', ['network', 'previous_membership', 'area_revision_sources'])
def test_changed_pin_is_rejected(tmp_path, section):
    document = json.loads(AREA.read_bytes())
    pin = document[section][0] if isinstance(document[section], list) else document[section]
    pin['sha256'] = '0'*64
    candidate = tmp_path/'area.json'
    candidate.write_text(json.dumps(document), encoding='utf-8')
    with pytest.raises(AssertionError):
        measurement_area(candidate)


def test_8100_analysis_does_not_relabel_the_9000_recording():
    assert closed_loop_analysis_end(9000, 8100) == 8100
    assert closed_loop_analysis_end(9000, None) == 9000
    assert closed_loop_analysis_end(8100, None) == 8100


def test_8100_control_can_reuse_only_a_sufficient_completed_nc_identity(tmp_path):
    from diagnostics.sdmpc_n31_20260924.integration_20260926.native_pair1200.analyze_pair import completed_nc_identity
    p=tmp_path/'run_provenance_sdmpc31_nc9000_s29.json'
    p.write_text(json.dumps(dict(sim_period_sec=9000,seed=29,name='sdmpc31_nc9000_s29')),encoding='utf-8')
    assert completed_nc_identity(tmp_path,8100)==('sdmpc31_nc9000_s29',9000)
    p.write_text(json.dumps(dict(sim_period_sec=7500,seed=29,name='sdmpc31_nc7500_s29')),encoding='utf-8')
    with pytest.raises(AssertionError):completed_nc_identity(tmp_path,8100)


@pytest.mark.parametrize('end', [900, 8101, 9150])
def test_invalid_analysis_window_is_rejected(end):
    with pytest.raises(ValueError):
        closed_loop_analysis_end(9000, end)


def test_later_removals_and_terminal_uninserted_counts_are_not_8100_data():
    events = [{'kind': 'lane_change_removal', 'time_sec': 8100, 'vehicle_id': 1},
              {'kind': 'lane_change_removal', 'time_sec': 8100.1, 'vehicle_id': 2},
              {'kind': 'unfinished_vehicle_input', 'remaining_vehicles': 99}]
    assert traffic_events_through(events, 8100) == events[:1]


def test_vehicle_still_inside_at_cutoff_is_not_a_later_exit():
    from itertools import takewhile
    frames = [Frame(8090.1, {'1': Vehicle('inside', 10, 0)}),
              Frame(8095.1, {'1': Vehicle('inside', 10, 0)}),
              Frame(8100.1, {'1': Vehicle('outside', 1, 10)})]
    metrics, rows = measure_frames(takewhile(lambda f: f.time_sec <= 8100, frames),
        {'inside': True, 'outside': False}, {}, end_sec=8100, simulation_step_sec=.1)
    assert metrics['ttd_observed_plus_terminal_events'] == 0
    assert metrics['censored_last_observed_inside_vehicles'] == 1
    assert metrics['ttt_censored_tail_extrapolation_veh_h'] == pytest.approx(4.9/3600)
    assert rows[-1]['sim_sec'] == 8100


def test_stopped_prefix_readback_preserves_all_in_window_requirements(tmp_path):
    from diagnostics.com_execution_equivalence.verify_pair import readbacks, SG_FIELDS
    p=tmp_path/'signal.csv'
    rows=[','.join(SG_FIELDS),'1,1,1,RED,RED,1,immediate',
          '150,1,1,RED,RED,1,post_step','151,1,1,GREEN,GREEN,1,immediate']
    p.write_text('\n'.join(rows)+'\n',encoding='utf-8')
    expected={'1:1':{'start':1,'end':150}}
    checked=[]
    result=readbacks(p,SG_FIELDS,expected,command_check=lambda r: checked.append(r),
                    control_interval=150,require_next_step_post=False,through_sec=150)
    assert result['passed'] and [int(r['sim_sec']) for r in checked]==[1,150]
    with pytest.raises(ValueError,match='outside declared'):
        readbacks(p,SG_FIELDS,expected,command_check=lambda r: None,control_interval=150,
                  require_next_step_post=False)
    p.write_text('\n'.join([rows[0],rows[1],rows[3]])+'\n',encoding='utf-8')
    with pytest.raises(ValueError,match='post-step readback missing'):
        readbacks(p,SG_FIELDS,expected,command_check=lambda r: None,control_interval=150,
                  require_next_step_post=False,through_sec=150)


def test_stopped_prefix_vsl_missing_apply_is_failure(tmp_path):
    from diagnostics.com_execution_equivalence.verify_pair import readbacks, VSL_FIELDS
    p=tmp_path/'vsl.csv'
    rows=[','.join(VSL_FIELDS)]
    for t in (1,300):
        rows += [f'{t},1,{cls},90,90,1,immediate' for cls in (10,20,30,70)]
    p.write_text('\n'.join(rows)+'\n',encoding='utf-8')
    expected={f'1:{cls}':dict(start=1,end=150,apply_seconds=[1,150]) for cls in (10,20,30,70)}
    with pytest.raises(ValueError,match='Missing/duplicate VSL'):
        readbacks(p,VSL_FIELDS,expected,command_check=lambda r:None,numeric=True,
                  distribution_ids={'9E+1':90},through_sec=150)


def test_prefix_requires_actual_decision_receipts_without_faking_terminal_counters(tmp_path):
    from diagnostics.com_execution_equivalence.verify_pair import decision_recovery_evidence
    prov={'control_interval_sec':150,'sim_period_sec':9000,'env':{}}
    lines=[b'CONTROLLER_DECISION sim_sec=1 wall_sec=1 result=exit=0 stdout={}',
           b'CONTROLLER_DECISION sim_sec=150 wall_sec=1 result=exit=0 stdout={}']
    out=decision_recovery_evidence(tmp_path,'sdmpc',prov,lines,through_sec=150)
    assert out['passed'] and not out['terminal_counters_available']
    with pytest.raises(ValueError,match='counter'):
        decision_recovery_evidence(tmp_path,'sdmpc',prov,lines)
    with pytest.raises(ValueError,match='do not cover'):
        decision_recovery_evidence(tmp_path,'sdmpc',prov,lines[:1],through_sec=150)
    lines[-1]=lines[-1].replace(b'exit=0',b'exit=1')
    with pytest.raises(ValueError,match='not all accounted'):
        decision_recovery_evidence(tmp_path,'sdmpc',prov,lines,through_sec=150)


@pytest.mark.parametrize('fault',[None,'live','area','truncated','changed','wrong_run'])
def test_explicit_user_stop_must_have_closed_owners_and_cover_cutoff(tmp_path,monkeypatch,fault):
    from diagnostics.com_execution_equivalence import verify_pair as v
    run=tmp_path/'sdmpc';(run/'vissim_eval').mkdir(parents=True)
    fzp=run/'vissim_eval/run_001.fzp'
    fzp.write_bytes(b'8545.10;1;66;1\n' if fault!='truncated' else b'8000.1;1;66;1\n')
    (tmp_path/'STOP').write_text('USER_STOP_requested',encoding='utf-8')
    receipt=dict(run=str(tmp_path),status='user_stopped_all_owned_closed',
        native9000_complete=False,analysis_end_sec=8100,remaining_owned=[],vissim_still_present=False,
        exclusive_file_open_passed=True,owned_controller_tree=[dict(ProcessId=123,CreationDate='2026-10-07')],
        vissim=dict(pid=124,created_at='2026-10-07'),fzp_after=[dict(FullName=str(fzp),Length=fzp.stat().st_size)])
    if fault=='area':receipt['analysis_end_sec']=9000
    if fault=='changed':receipt['fzp_after'][0]['Length']+=1
    if fault=='wrong_run':receipt['run']=str(run)
    rp=tmp_path/'user_stop.json';rp.write_text(json.dumps(receipt),encoding='utf-8')
    def closed(pids):
        assert pids==[123,124]
        if fault=='live':raise ValueError('live owner')
    monkeypatch.setattr(v,'_require_closed_windows_pids',closed)
    if fault:
        with pytest.raises(ValueError):v.user_stop_evidence(run,8100,rp)
    else:
        out=v.user_stop_evidence(run,8100,rp)
        assert out['passed'] and out['normal_run_completed'] is False


def test_windows_process_closure_rejects_live_owner_and_accepts_signaled_handle():
    import os, subprocess, sys
    from diagnostics.com_execution_equivalence.verify_pair import _require_closed_windows_pids
    if sys.platform!='win32':pytest.skip('Windows native process ownership')
    with pytest.raises(ValueError,match='live'):
        _require_closed_windows_pids([os.getpid()])
    child=subprocess.Popen([sys.executable,'-c','pass'],creationflags=subprocess.CREATE_NO_WINDOW)
    assert child.wait(timeout=10)==0
    _require_closed_windows_pids([child.pid])
