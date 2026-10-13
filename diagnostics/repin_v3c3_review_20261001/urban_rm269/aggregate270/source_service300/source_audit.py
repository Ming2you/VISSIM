"""Diagnose SC15 source loss from a closed positional cache and stored rollout.

Crossings are bounded observations, not a complete census or fitted saturation.
Native future data is read only for this diagnosis; predictor inputs are intact.
"""
from collections import defaultdict
import gzip
import hashlib
import json
from pathlib import Path
import pickle
import sys

HERE=Path(__file__).resolve().parent
A=HERE.parent
ROOT=HERE.parents[4]
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
from diagnostics.validate_native_signal_record import read_ldp_frames
from evaluation.controllers import route_choice_corridor as rc
from evaluation.controllers.fixed_signal_schedule import _union_green_overlap

OUT=Path('E:/VISSIM_analysis/20261010_sc15_source300')
PINS={}
NORTH={10553,10556,1220008502,10544,10545,1220011503}
SOUTH={10554,10555,1220008401,1220008402}


def pin(p):
    p=Path(p);data=p.read_bytes();PINS[str(p.resolve())]=hashlib.sha256(data).hexdigest();return data
def read(p):return json.loads(pin(p))


def crossing_witnesses(frames,source,head):
    tracks=defaultdict(list)
    for frame in frames:
        for row in frame['rows']:tracks[row[0]].append((frame['sec'],row))
    events=[];unresolved=[]
    for vehicle,track in tracks.items():
        before=[(t,v) for t,v in track if v[1]==source and v[3]<=head]
        if not before:continue
        lower,last=before[-1]
        after=[(t,v) for t,v in track if t>lower and (v[1]!=source or v[3]>head)]
        if not after:continue  # still upstream/censored is not an exit
        upper,first=after[0]
        after_links={v[1] for t,v in track if t>=upper}
        native_route=last[6] if last[5] in ('1099','1100') else ''
        north=bool(after_links&NORTH);south=bool(after_links&SOUTH)
        if upper-lower>5.00001 or (north and south):
            unresolved.append(dict(veh=vehicle,reason='wide interval or ambiguous downstream branch'));continue
        direction='north' if north else 'south' if south else 'unresolved'
        # A connector/known target proves departure; a same-source position can
        # prove head passage but an unresolved branch remains unclassified.
        if first[1]!=source and first[1] not in NORTH|SOUTH:
            unresolved.append(dict(veh=vehicle,reason='first downstream road outside verified branch'));continue
        if native_route and direction!='unresolved':
            assert native_route==('1' if direction=='north' else '2')
        events.append(dict(veh=vehicle,lower_sec=lower,upper_sec=upper,
            direction=direction,last_prehead_speed_kph=last[4]))
    return events,unresolved


def main():
    assert not (HERE/'source_audit.json').exists(), 'Do not repeat completed audit'
    done=read(OUT/'completion.json')
    assert done['status']=='complete_sc15_sc101_source_cache'
    cfg,_,_=pickle.loads(pin(A/'citysplit287/forecast2400/initial.pickle'))
    geometry=read(A/'sc101_clock299/source_geometry.json')
    native_head=read(A/'sc101_clock299/assessment.json')['native']
    calibration=read(ROOT/'diagnostics/native_sc15_service_calibration.json')
    pin(ROOT/'diagnostics/native_sc15_service_review.md')
    pin(A.parent.parent/'upstream_worklog/02_urban_b2/impl/STAGE3.md')
    report={}
    for arm in ('hold','city'):
        content=pin(done['arms'][arm]['cache'])
        assert hashlib.sha256(content).hexdigest()==done['arms'][arm]['cache_sha256']
        cache=json.loads(gzip.decompress(content))
        response=json.loads(gzip.decompress(pin(A/'sc101_clock299/forecast2400'/f'{arm}.response.json.gz')))
        fzp=Path(done['arms'][arm]['source']);stem=fzp.stem.removesuffix('_001')
        ldp=read_ldp_frames({15:fzp.parent/(stem+'_15_001.ldp')},{15:list(range(1,9))},2400,2850)
        for p,d in ldp['pins'].items():assert hashlib.sha256(pin(p)).hexdigest()==d['sha256']
        result={}
        for spec in rc._specs(cfg):
            decision=spec['decision']
            if decision not in geometry['sources']:continue
            geo=geometry['sources'][decision];native=spec['native_fixed_service']
            src=int(spec['decision_link']);head=native['head_position_m'];sg=native['signal_group']
            events,ambiguous=crossing_witnesses(cache['frames'],src,head)
            transfers=[t for t in response['transfers'] if t['source']=='storage:'+spec['prefix_storage']]
            sc101_events={e['veh']:e for e in native_head[arm]['events']}
            matched=[dict(**e,sc101_sec=sc101_events[e['veh']]['sec']) for e in events
                if e['direction']=='north' and e['veh'] in sc101_events]
            assert all(e['sc101_sec']>=e['lower_sec'] for e in matched)
            blocks=[]
            for start in (2400,2550,2700):
                end=start+150
                inside=[e for e in events if e['lower_sec']>=start and e['upper_sec']<=end]
                crossing_boundary=[e for e in events if e['lower_sec']<end and e['upper_sec']>start and e not in inside]
                predicted=[t for t in transfers if start<=t['start_sec']<end]
                model_green=_union_green_overlap(rc._native_program(native),(sg,),start,end,native['controller_offset_sec'])
                native_green=sum(ldp['frames'][t][f'15:{sg}']=='GREEN' for t in range(start,end))
                amount=sum(t['vehicles'] for t in predicted)
                head_cap=native['calibrated_service_veh_h']*model_green/3600
                assert abs(amount-head_cap)<1e-7, 'This source is not entirely service limited'
                blocks.append(dict(start_sec=start,native_witnessed_head_crossings_lower=len(inside),
                    native_witnessed_north_lower=sum(e['direction']=='north' for e in inside),
                    unresolved_time_boundary_count=len(crossing_boundary),model_all_branch_departures=amount,
                    model_north=sum(t['vehicles'] for t in predicted if t['target']=='storage:SC1_to_SC101'),
                    model_green_sec=model_green,native_green_sec=native_green,
                    matched_source_to_sc101_in_this_block=sum(start<=e['sc101_sec']<end for e in matched)))
            result[decision]=dict(input_no=next(iter(spec['generated_inputs'])),source_link=src,
                source_head_position_m=head,service_veh_h=native['calibrated_service_veh_h'],
                old_calibration_seed=calibration['seed'],blocks=blocks,events=events,
                unresolved=ambiguous,matched_source_to_sc101=matched)
        report[arm]=result
    pin(__file__)
    result=dict(status='complete_old_sc15_service_transfer_understates_native_source_flow',arms=report,
        source_pins=PINS,goal_complete=False,budget=dict(new_forecasts=0,new_native=0,new_coefficients=0),
        scope=['The450s source throughput lower bounds already exceed the model full head capacities.',
            'Block GREEN durations match. No source-service double-green factor was introduced by this audit.',
            'No lower-bound crossing count is labelled complete census or a saturation estimator.',
            '5s source frames end2845.1; unobserved late crossings or never-observed vehicles are not invented.',
            'Timing/branch witnesses diagnose SC15 supply, not all SC101 inflow or whole-Omega causality.',
            'Both arms retain original demand, routing, initial state and source parameters.'],
        next_step='Use past-only queued-discharge support on the current network before one source-service candidate. Do not fit the2400–2850 validation future or raise SC101 capacity again in isolation.')
    (HERE/'source_audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    for arm,rows in report.items():
        for decision,data in rows.items():
            print(arm,decision,[(b['native_witnessed_head_crossings_lower'],round(b['model_all_branch_departures'],3),
                b['native_witnessed_north_lower'],round(b['model_north'],3),b['native_green_sec']) for b in data['blocks']],
                'matched_sc101',[b['matched_source_to_sc101_in_this_block'] for b in data['blocks']])


if __name__=='__main__':main()
