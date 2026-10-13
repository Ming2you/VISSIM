"""Post-hoc validation only; observed future lanes never enter prediction."""
from pathlib import Path
from collections import Counter
import gzip,hashlib,json
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc6_shared342 import candidate as c
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.transfer331.inputs import load

HERE=Path(__file__).resolve().parent;A=HERE.parent;OUT=HERE/'forecast2400'
read=lambda p:json.loads(gzip.decompress(Path(p).read_bytes()) if str(p).endswith('.gz') else Path(p).read_bytes())
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    assert not (HERE/'assessment.json').exists()
    from evaluation.controllers import vissim_stackelberg_adapter as adapter
    summary=read(OUT/'summary.json');assert summary['status']=='complete'
    pins=summary['source_pins'];assert all(sha(p)==h for p,h in pins.items())
    old=Path('E:/VISSIM_analysis/20261010_native_routes329/forecast2400')
    before=read(old/'hold.response.json.gz');disabled=read(OUT/'disabled_hold.response.json.gz')
    assert disabled==before,'Default-disabled response differs'
    native_folders={
        'hold':Path('E:/VISSIM_runs/20261008_urbanrm269_native2400_s29/hold/decisions_sdmpc31_g_2400_hold_s29'),
        'city':Path('E:/VISSIM_runs/20261010_urbanrm269_cityonly289_s29/selected/decisions_sdmpc31_g_2400_selected_s29')}
    evidence={};totals={};before_ttt={}
    for arm in ('hold','city','joint'):
        r=read(OUT/(arm+'.response.json.gz'));gate=read(OUT/(arm+'.gate.json'))
        deps=[sum(t['ttd_veh'] for t in r['transfers'] if t['route_key']=='movement:'+c.RIGHT and start<=t['start_sec']<start+150) for start in (2400,2550,2700)]
        assert abs(sum(deps)-sum(t['right_accepted'] for t in gate['history']))<1e-7
        totals[arm]=dict(omega_ttt=summary['results'][arm]['omega_ttt_veh_h'],right_exit_by150=deps,
            right_total=sum(deps),blocked_steps=sum(x['coverage']>0 for x in gate['history']),
            peak_lane_queue=max(x['lane_queue'] for x in gate['history']),
            shared_caps_feasible=summary['results'][arm]['shared_constraints']['feasible'])
        baseline=old/(arm+'.json') if arm!='joint' else Path('E:/VISSIM_analysis/20261010_rm_response330/forecast2400_v2/joint.json')
        before_ttt[arm]=read(baseline)['omega_ttt_veh_h'];pins[str(baseline)]=sha(baseline)
        if arm=='joint':continue
        observations=[]
        for at in (2400,2550,2700,2850):
            raw,frame,pp=load(native_folders[arm],at);pins.update(pp)
            queues=adapter._contiguous_stopline_queue(raw,per_lane=True)
            records=[v for v in raw['vehicle_records']['records'] if str(v['link_no'])==c.SOURCE]
            rows={r[0]:r for r in frame['vehicles']}
            lane_counts=Counter();stopped=Counter();front_counts=Counter()
            for v in records:
                dest=rows[v['veh_no']][9]
                key=f"lane{v['lane_no']}:next{dest}"
                lane_counts[key]+=1
                if v['stopped']:stopped[key]+=1
            for lane in range(1,6):
                n=queues.get((c.SOURCE,str(lane)),0);assert n==int(n)
                front=sorted((v for v in records if v['lane_no']==lane),key=lambda v:-v['position_m'])[:int(n)]
                for v in front:front_counts[f"lane{lane}:next{rows[v['veh_no']][9]}"]+=1
            observed=front_counts['lane1:next10200.0']
            history=gate['history']
            if at==2400:model=read(OUT/'installation.json')['initial_lane_queue']
            else:model=next(x['lane_after'] for x in history if x['step']*10==at-10)
            observations.append(dict(sec=at,all_vehicle_lane_route=dict(lane_counts),stopped_lane_route=dict(stopped),
                contiguous_lane_route=dict(front_counts),observed_lane1_through_front=observed,
                model_lane1_through_queue=model,
                lane1_stopped_positions=[dict(position_m=v['position_m'],next=rows[v['veh_no']][9]) for v in records if v['lane_no']==1 and v['stopped']]))
        evidence[arm]=observations
    changes={}
    for label,left,right in [('city_minus_hold','hold','city'),('joint_minus_city','city','joint')]:
        changes[label]=dict(before=before_ttt[right]-before_ttt[left],candidate=totals[right]['omega_ttt']-totals[left]['omega_ttt'])
    assert all(sha(p)==h for p,h in pins.items())
    result=dict(status='rejected_no_generalization_forecasts',totals=totals,deltas=changes,native_lane_validation=evidence,
        disabled_full_response_exact=True,source_pins=pins,completed_forecasts=4,skipped_followup_forecasts=2,
        native_right_exits450=dict(hold=56,city=56),native_delta_omega=dict(city_minus_hold=5.286666666666633,joint_minus_city=-1.093555555555611),
        production_adopted=False,goal_complete=False,future_lane_data_used='validation_only',
        caveats=['Contiguous front counts are150s snapshots, not a continuous causal lane history.',
                 'Model initial projection remains6.5through/.5right versus current confirmed7through; no route reassignment was introduced.',
                 'Future uniform through-lane arrivals are a diagnostic assumption, not measured lane choice.',
                 'The model rate was not refitted and future observed queues did not gate prediction.'])
    (HERE/'assessment.json').write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
    print(json.dumps(dict(totals=totals,deltas=changes,native_lanes={k:[(r['sec'],r['observed_lane1_through_front'],r['model_lane1_through_queue']) for r in v] for k,v in evidence.items()}),indent=2))

if __name__=='__main__':main()
