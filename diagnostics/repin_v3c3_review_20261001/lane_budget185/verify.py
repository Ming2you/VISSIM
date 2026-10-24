"""Independent parity and common-prefix checks for the185 lane ledger."""
from pathlib import Path
import gzip
import hashlib
import json

HERE=Path(__file__).resolve().parent
R=HERE.parent


def read(p):
    with (gzip.open(p,'rt',encoding='utf8') if p.suffix=='.gz' else p.open(encoding='utf8')) as f:return json.load(f)


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    result=read(HERE/'analysis_extended.json')
    replay=R/'phase_joint183/audit185/forecast'
    status=read(replay/'status.json');assert status==dict(status='complete',forecasts=2)
    table_checks=0
    for arm in ('release','release_vsl90'):
        a=read(replay/f'queue/s67_late_{arm}.json.gz')
        b=read(R/f'phase_joint183/queue_validation/forecast/queue/s67_late_{arm}.json.gz')
        for table in ('cells','flows','ports','ramps'):
            assert a[table]==b[table];table_checks+=1
    # Source change only allows selecting the correct existing parity target.
    new=(R/'state_lateral168/run.py').read_text(encoding='utf8')
    old=(HERE/'completed183_runner.py.txt').read_text(encoding='utf8')
    added="                    if setting183 and 'audit_reference_dir' in setting183:\n                        reference_path=Path(setting183['audit_reference_dir'])/f\"{record['case']}_{record['arm']}.json.gz\"\n"
    assert new.count(added)==1 and new.replace(added,'')==old
    data=read(R/'blocking176/release_frames.json.gz');fields={key:i for i,key in enumerate(data['fields'])}
    index=lambda t:{vid for vid,z in data['frames'][str(t)].items() if z[fields['cell']]==21 and z[fields['lane']]==1}
    entered=left=0
    for t in (2670.1,2675.1,2680.1,2685.1,2690.1,2695.1):
        a=index(t);b=index(round(t+5,1));entered+=len(b-a);left+=len(a-b)
    assert (len(index(2670.1)),entered,left,len(index(2700.1)))==(5,14,17,2)
    common=[z for z in result['summary'] if z['arm']=='release' and z['end']==2700.1]
    assert len(common)==2
    for row in common:
        native=row['truth'];model=row['predicted']
        assert native['upstream_enter']==7 and native['merge_all']==native['merge_enter']==7
        assert native['downstream_leave']==17 and native['lateral_in']==native['lateral_out']==0
        assert native['bypass_all']==native['bypass_merge']==native['unknown_in']==native['unknown_out']==0
        assert native['boundary_lane_in']==1 and native['boundary_lane_out']==0
        expected=model['start_n']+model['incoming']+model['merge']-model['outgoing']+model['lateral_net']
        assert abs(expected-model['end_n'])<1e-10
    profiles=result['reference_ramp_profiles'];assert len(profiles)==48 and result['unique_reference_states']==4
    first=[z for z in profiles if z['connector']=='10490' and z['horizon']==30]
    assert len(first)==4 and all(z['baseline']>z['actual'] for z in first)
    protocol=read(R/'phase_joint183/audit185/protocol.json')
    for p,digest in result['input_sha256'].items():assert sha(Path(p))==digest,p
    for p,digest in protocol['protected_sha256'].items():assert sha(Path(p))==digest,p
    assert sha(Path(protocol['STOP']['path']))==protocol['STOP']['sha256']
    preservation=read(replay/'preservation.json');assert preservation['hooks_restored']
    for p,digest in preservation['input_sha256'].items():assert sha(Path(p))==digest,p
    out=dict(status='verified',new_exact_physical_tables=table_checks,forecasts=2,
        executed_physics_unchanged=True,common_prefix_membership=[5,14,17,2],
        reference_profiles=48,unique_reference_states=4,pins_and_STOP=True,hooks_restored=True,
        qualification=False,adopted=False,full_goal='ACTIVE_NOT_QUALIFIED',source_sha256=sha(Path(__file__)))
    (HERE/'verification.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf8')
    print(json.dumps(out))


if __name__=='__main__':main()
