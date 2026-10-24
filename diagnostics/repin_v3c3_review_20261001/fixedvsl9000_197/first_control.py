"""Read only the completed first command and its immediate VSL application."""
import csv
import hashlib
import io
import json
import sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
RUN=Path('D:/VISSIM_runs/20261004_sdmpc_fixed90_s29_9000')
D=RUN/'sdmpc/decisions_sdmpc31_sdmpc9000_s29'


def main():
    out=HERE/'first_control_native.json'
    assert not out.exists()
    command=D/'action_000900.csv'; raw=command.read_bytes()
    rows=list(csv.DictReader(io.StringIO(raw.decode('utf-8-sig'))))
    binding=json.loads((D/'action_000900.joint_written.json').read_bytes())
    assert binding['written_command_binding_passed']
    assert hashlib.sha256(raw).hexdigest()==binding['expected_csv_sha256']
    applied=(D/'action_000900.json.applied').read_text(encoding='utf-16').splitlines()
    assert float(applied[0])==900 and Path(applied[1]).resolve()==command.resolve()
    assert int(applied[2])==len(raw)
    speeds={int(r['dsd_no']):float(r['speed_kph']) for r in rows if r['kind']=='vsl'}
    expected={k:(90. if k in (63,64,65,66) else 110.) for k in speeds}
    assert speeds==expected and {k for k,v in speeds.items() if v==90}=={63,64,65,66}
    rb=[r for r in csv.DictReader(io.StringIO((D/'vsl_readback.csv').read_text()))
        if float(r['sim_sec'])==900]
    assert len(rb)==len(speeds)*4
    keys={(int(r['dsd_no']),int(r['veh_class_no'])) for r in rb}
    assert keys=={(k,c) for k in speeds for c in (10,20,30,70)}
    for r in rb:
        assert r['ok']=='1' and r['stage']=='immediate'
        assert float(r['requested_kph'])==float(r['readback_distribution_no'])==speeds[int(r['dsd_no'])]
    history=[json.loads(line) for line in (D/'action_000900.joint.progress.jsonl').read_text().splitlines()]
    pfo=next(r for r in history if r['stage']=='sdmpc_pfo_done')
    accepted=[r for r in history if r['stage']=='sdmpc_step_accepted']
    axes=[r['axes'] for r in history if r['stage']=='sdmpc_tangent_start']
    meters=[dict(id=r['id'],sc=r['sc_no'],green_sec=r['green_sec'],rate_vph=r['rate_vph'])
            for r in rows if r['kind']=='ramp_meter']
    assert len(meters)==8
    result=dict(status='first_control_written_and_VSL_readback_pass',decision_sec=900,
        command_sha256=hashlib.sha256(raw).hexdigest(),command_rows=len(rows),
        observed_readbacks=rb,VSL_distributions=speeds,actuator_application_receipt=True,
        pfo=pfo,sdmpc_max_iterations=2,sdmpc_accepted_iterations=len(accepted),
        sdmpc_convergence_verified=False,optimizer_axes=axes,
        ramp_commands=meters,writer_binding=True,
        scope='First900 command/application receipt and immediate all-class VSL readback only. RM/signal native LDP temporal verification and full9000 performance remain pending.',
        gain_qualified=False,completed9000=False)
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(dict(status=result['status'],DSDs=len(speeds),readbacks=len(rb),
               pfo_accepted=pfo['accepted_iterations'],sdmpc_accepted=len(accepted)))


def consecutive_controls():
    """Bounded read-only check of four already-applied decisions, not a monitor."""
    out=HERE/'four_controls_native.json'
    assert not out.exists(), 'Preserve the completed audit'
    pins={}
    def read(path):
        data=path.read_bytes()
        pins[str(path)]=hashlib.sha256(data).hexdigest()
        return data
    def table(t):
        path=D/f'action_{t:06d}.csv'
        return path,read(path)
    _,previous_raw=table(750)
    previous=list(csv.DictReader(io.StringIO(previous_raw.decode('utf-8-sig'))))
    # Read the append-only evidence once. Later run progress is not part of this audit.
    readback_raw=(D/'vsl_readback.csv').read_bytes()
    readback=list(csv.DictReader(io.StringIO(readback_raw.decode('utf-8-sig'))))
    result=[]
    for t in (900,1050,1200,1350):
        path,raw=table(t)
        rows=list(csv.DictReader(io.StringIO(raw.decode('utf-8-sig'))))
        binding=json.loads(read(D/f'action_{t:06d}.joint_written.json'))
        assert binding['prewrite_binding_passed'] and binding['written_command_binding_passed']
        assert binding['response_kind']=='validated_sdmpc'
        assert binding['expected_csv_sha256']==hashlib.sha256(raw).hexdigest()
        assert binding['ordered_row_count']==len(rows)==213
        applied=read(D/f'action_{t:06d}.json.applied').decode('utf-16').splitlines()
        assert float(applied[0])==t and Path(applied[1]).resolve()==path.resolve()
        assert int(applied[2])==len(raw)
        speeds={int(r['dsd_no']):float(r['speed_kph']) for r in rows if r['kind']=='vsl'}
        assert len(speeds)==66
        assert {k for k,v in speeds.items() if v==90}=={63,64,65,66}
        assert all(v==(90. if k in (63,64,65,66) else 110.) for k,v in speeds.items())
        rb=[r for r in readback if float(r['sim_sec'])==t]
        assert len(rb)==264
        assert {(int(r['dsd_no']),int(r['veh_class_no'])) for r in rb}=={
            (k,c) for k in speeds for c in (10,20,30,70)}
        assert all(r['ok']=='1' and r['stage']=='immediate' and
                   float(r['requested_kph'])==float(r['readback_distribution_no'])==speeds[int(r['dsd_no'])]
                   for r in rb)
        meters={r['id']:float(r['green_sec']) for r in rows if r['kind']=='ramp_meter'}
        oldmeters={r['id']:float(r['green_sec']) for r in previous if r['kind']=='ramp_meter'}
        assert len(meters)==len(oldmeters)==8 and meters.keys()==oldmeters.keys()
        change={k:meters[k]-oldmeters[k] for k in meters}
        assert max(abs(v) for v in change.values())<=2.+1e-9
        oldsignals={r['id']:r for r in previous if r['kind']=='signal'}
        signals={r['id']:r for r in rows if r['kind']=='signal'}
        assert len(signals)==17
        # Warmup deliberately leaves urban signals under native ownership.
        # No preceding CSV signal row is not evidence of a command mismatch.
        if t==900:assert not oldsignals
        else:assert len(oldsignals)==17 and signals.keys()==oldsignals.keys()
        fields=('p1_green','p2_green','p3_green','p4_green','offset')
        changed=([k for k in signals if any(signals[k][f]!=oldsignals[k][f] for f in fields)]
                 if oldsignals else None)
        progress=[json.loads(x) for x in read(D/f'action_{t:06d}.joint.progress.jsonl').decode('utf-8').splitlines()]
        pfo=next(x for x in progress if x['stage']=='sdmpc_pfo_done')
        completed=next(x for x in progress if x['stage']=='sdmpc_completed')
        axes=[x['axes'] for x in progress if x['stage']=='sdmpc_tangent_start']
        assert axes and set(axes)=={213}
        result.append(dict(time_sec=t,command_sha256=hashlib.sha256(raw).hexdigest(),
            command_rows=len(rows),applied_receipt=True,writer_binding=True,
            vsl_readback_count=len(rb),vsl_readbacks=rb,meter_green_sec=meters,
            meter_change_sec=change,changed_city_command_ids=changed,
            optimizer_axes=axes,pfo=pfo,decision_completion=completed,
            hold_fallback=False,native_signal_timing_verified=False))
        previous=rows
    ldp=[dict(path=str(p),bytes=p.stat().st_size) for p in sorted((RUN/'sdmpc/vissim_eval').glob('*.ldp'))]
    document=dict(status='FOUR_APPLIED_COMMANDS_AND_VSL_READBACK_PASS',controls=result,
        immutable_inputs_sha256=pins,readback_snapshot_sha256=hashlib.sha256(readback_raw).hexdigest(),
        readback_snapshot_bytes=len(readback_raw),ldp_file_sizes_at_audit=ldp,
        scope='900--1350 command/application receipts, fixed VSL readback, command RM trust bounds only. LDP signal transition timing remains pending. No performance or convergence claim.',
        optimizer_error_recovery_exercised_in_this_live_run=False,
        completed9000=False,gain_qualified=False)
    out.write_text(json.dumps(document,ensure_ascii=False,indent=2),encoding='utf-8')
    for r in result:
        print(json.dumps({k:r[k] for k in ('time_sec','meter_green_sec','meter_change_sec','changed_city_command_ids','decision_completion')},ensure_ascii=False))


if __name__=='__main__':
    if sys.argv[1:]==['--consecutive']:consecutive_controls()
    else:
        assert not sys.argv[1:]
        main()
