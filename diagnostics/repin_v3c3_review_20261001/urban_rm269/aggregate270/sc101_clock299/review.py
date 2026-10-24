"""Review completed source-specific delay forecasts against preserved298."""
import gzip
import hashlib
import json
from pathlib import Path
from collections import Counter

HERE=Path(__file__).resolve().parent
read=lambda p:json.loads(Path(p).read_bytes())
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
MOV='movement:SC101_S_SC1_to_N_SC2005'


def main():
    out=HERE/'comparison.json'
    assert not out.exists()
    current=read(HERE/'forecast2400/summary.json')
    previous=read(HERE.parent/'combined298/forecast2400/summary.json')
    truth=read(HERE/'assessment.json')
    assert current['status']=='complete' and current['forecasts']==2
    for p,h in current['source_pins'].items():assert sha(p)==h,p
    pins={str(p):sha(p) for p in [HERE/'forecast2400/summary.json',HERE.parent/'combined298/forecast2400/summary.json',HERE/'assessment.json',Path(__file__)]}
    arms={}
    for arm in ('hold','city'):
        new=current['results'][arm];old=previous['results'][arm]
        assert new['writer_three_blocks'] and new['conservation_states']==4 and new['resource_max_exceedance']<1e-7
        assert new['shared_constraints']['feasible']
        responses={}
        for label,folder in (('new',HERE),('old',HERE.parent/'combined298')):
            p=folder/'forecast2400'/f'{arm}.response.json.gz';pins[str(p)]=sha(p)
            responses[label]=json.loads(gzip.decompress(p.read_bytes()))
            assert responses[label]['model_constraint_coverage']['complete']
        groups={}
        for name,r in responses.items():
            q=[x for x in r['transfers'] if x['source']==MOV and x['target']!=MOV]
            groups[name]=dict(counts=[sum(x['vehicles'] for x in q if start<=x['start_sec']<start+150) for start in (2400,2550,2700)],
                head_time_cost=-sum(x['vehicles']*(2850-x['start_sec'])/3600 for x in q))
        native=[b['count'] for b in truth['native'][arm]['blocks']]
        for name in groups:
            groups[name]['head_mae']=sum(abs(x-y) for x,y in zip(groups[name]['counts'],native))/3
        # Actual side-entry acceptance has its own upstream service/storage proof;
        # this compares the recorded accepted flow rather than assuming it fixed.
        incoming={}
        for name,r in responses.items():
            incoming[name]=Counter()
            for t in r['transfers']:
                if t['source'] in ('storage:native_1086_choice','storage:native_1087_choice') and t['target']=='storage:SC1_to_SC101':
                    incoming[name][t['source'],t['start_sec']]+=t['vehicles']
        difference=max((abs(incoming['new'][k]-incoming['old'][k]) for k in incoming['new'].keys()|incoming['old'].keys()),default=0.)
        receipt=HERE/'forecast2400'/f'{arm}.side_receipts.json';pins[str(receipt)]=sha(receipt)
        rr=read(receipt)
        assert rr and {r['decision'] for r in rr}=={'1099','1100'}
        arms[arm]=dict(old_omega=old['omega_ttt_veh_h'],new_omega=new['omega_ttt_veh_h'],heads=groups,native_head_counts=native,
            side_entry_accepted_max_delta=difference,side_delays=dict(new=sorted(set(r['delay_sec'] for r in rr)),
                original=sorted(set(r['old_delay_sec'] for r in rr))),
            resource_max_exceedance=new['resource_max_exceedance'],shared=new['shared_constraints'],
            endpoint_wall_sec=new['wall_sec'])
    delta=arms['city']['new_omega']-arms['hold']['new_omega']
    original=arms['city']['old_omega']-arms['hold']['old_omega']
    report=dict(status='complete_geometry_candidate_not_gain_qualified',arms=arms,
        old_city_minus_hold_veh_h=original,new_city_minus_hold_veh_h=delta,
        native_city_minus_hold_veh_h=5.28666666666649,
        gain_direction_correct=delta>0,
        head_timing_gain={v:arms['city']['heads'][v]['head_time_cost']-arms['hold']['heads'][v]['head_time_cost'] for v in ('old','new')},
        initial_state_error=current['initial_state_error'],source_pins=pins,
        budget_used=dict(fixed450=2,optimizer=0,ad=0,native=0,fzp=0,new_fits=0,production_changes=0),goal_complete=False,
        limitations=['Only transport after future accepted side entries changes; existing initial corridor reservations remain untouched.',
            'Current mean-speed travel omits lateral gap and queue-tail geometry; source SC15 service and actual receiving are retained.',
            'Physical geometry alignment alone does not certify whole-Omega control gains.',
            'No new coefficient fit, full optimizer, AD, heldout or native run was executed.'])
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print('GAIN',original,delta,'native',report['native_city_minus_hold_veh_h'])
    for a,b in arms.items():print(a,b['heads'],b['side_delays'],'accepted_delta',b['side_entry_accepted_max_delta'])


if __name__=='__main__':main()
