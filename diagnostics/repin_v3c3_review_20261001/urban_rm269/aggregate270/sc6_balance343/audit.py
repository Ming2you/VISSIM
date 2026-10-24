"""SC6 east service/ready balance from existing native bundles and responses.

No model forecast, fitting, native run or FZP scan. Future observations are
validation targets only; model quantities remain their autonomous values.
"""
from pathlib import Path
from collections import Counter
import gzip,hashlib,json,pickle,xml.etree.ElementTree as ET
from diagnostics.repin_v3c3_review_20261001.urban_rm269.sc12_source import audit as heads
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.transfer331.inputs import load
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.city_loss322.audit import green_seconds

HERE=Path(__file__).resolve().parent;A=HERE.parent;ROOT=HERE.parents[4]
ORIGIN='SC104_to_SC6';THROUGH='SC6_E_SC104_to_W_SC5';RIGHT='SC6_E_SC104_to_N_SC103'
MODEL=Path('E:/VISSIM_analysis/20261010_native_routes329/forecast2400')
RUNS=dict(hold=Path('E:/VISSIM_runs/20261008_urbanrm269_native2400_s29/hold/decisions_sdmpc31_g_2400_hold_s29'),
          city=Path('E:/VISSIM_runs/20261010_urbanrm269_cityonly289_s29/selected/decisions_sdmpc31_g_2400_selected_s29'))
PINS={}
def data(p):
    p=Path(p);blob=p.read_bytes();PINS[str(p.resolve())]=hashlib.sha256(blob).hexdigest();return blob
def read(p):
    blob=data(p);return json.loads(gzip.decompress(blob) if str(p).endswith('.gz') else blob)

def main():
    assert not (HERE/'assessment.json').exists()
    for name in ('U7.md','U8.md','C3V2_PROPOSAL.md'):
        data(A.parents[1]/'upstream_worklog/02_urban_b2/diag_c3_r2'/name)
    cfg,state,_=pickle.loads(data(A/'transfer331/build2400_v2/initial.pickle'))
    root=ET.fromstring(data(ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926/selected/network/native_seed29.inpx'))
    links={n.get('no'):n for n in root.findall('./links/link')}
    geometry=[dict(h.attrib) for h in root.findall('./signalHeads/signalHead') if h.get('lane').split()[0]=='1220021201']
    assert {h['sg'] for h in geometry if int(h['lane'].split()[1])<=4}=={'6 6'}
    # The only branch reached after these four heads is through10200. Right
    # branches upstream, left uses lane5, hence head counts identify service.
    assert links['10200'].find('fromLinkEndPt').get('lane')=='1220021201 1'
    assert len(links['10200'].findall('./lanes/lane'))==4
    assert float(links['10142'].find('fromLinkEndPt').get('pos'))<min(float(h['pos']) for h in geometry)
    owned={'storage:'+ORIGIN,*('movement:'+m for m,s in cfg.network.urban_movements.items() if s.get('origin')==ORIGIN)}
    support=state.local_observation_summary['projection_diagnostics']['physical_stock_assignment_by_link']
    footprint={k for k,v in support.items() if any(v.get(owner,0)>0 for owner in owned)}
    assert all(abs(sum(v.get(owner,0) for owner in owned)-sum(v.values()))<1e-7 for k,v in support.items() if k in footprint)
    heads.LINKS={'SC6_E':1220021201}
    rate=cfg.network.movement_capacity_by_movement_veh_h[THROUGH];results={}
    for arm,folder in RUNS.items():
        response=read(MODEL/(arm+'.response.json.gz'))
        resources={(r['resource'],r['start_sec'],r['kind']):r for r in response['resource_allocations']}
        window_rows=[];states=[]
        for at in (2400,2550,2700,2850):
            raw,frame,pins=load(folder,at);PINS.update(pins)
            rows={r[0]:r for r in frame['vehicles']}
            v=[x for x in raw['vehicle_records']['records'] if str(x['link_no']) in footprint]
            stocks=Counter(str(x['link_no']) for x in v)
            source=[x for x in v if str(x['link_no'])=='1220021201']
            states.append(dict(sec=at,fixed_initial_owned_footprint_stock=len(v),by_link=dict(stocks),
                terminal_all=len(source),terminal_through=sum(rows[x['veh_no']][9]==10200. for x in source),
                terminal_stopped_through=sum(rows[x['veh_no']][9]==10200. and x['stopped'] for x in source)))
            if at==2400:continue
            start=at-150;native,events=heads.heads_and_entries(folder,at)
            rows=native['SC6_E']['rows'];rows=[r for r in rows if r['lane'] in (1,2,3,4)]
            head_flow=sum(r['crossings'] for r in rows)
            known=[r for r in events['SC6_E'] if r[0] in (1,2,3,4)]
            action_path=(A.parent/'selection2400_discrete/hold' if arm=='hold' else A/'citysplit287/forecast2400/city_only')/f'action_{start:06}.json'
            control=read(action_path);ticks=[]
            for t in range(start,at,10):
                q=resources[THROUGH,t,'urban_movement_stock']['available_veh']
                req=resources[THROUGH,t,'urban_movement_intended_limit']
                green=green_seconds(control,cfg.network,THROUGH,t);cap=rate*green/3600
                arrived=sum(r['vehicles'] for r in response['transfers'] if r['target']=='movement:'+THROUGH and r['source']!='movement:'+THROUGH and r['start_sec']==t)
                incoming=sum(r['vehicles'] for r in response['transfers'] if r['target']=='storage:'+ORIGIN and r['source']!='storage:'+ORIGIN and r['start_sec']==t)
                dep=req['accepted_total_veh']
                ticks.append(dict(sec=t,ready_before_service=q,ready_arrived=arrived,incoming_storage=incoming,green=green,cap=cap,
                    request=req['available_veh'],accepted=dep,ready_after=q-dep,starved=max(0.,cap-q),receiving_loss=req['available_veh']-dep))
            for left,right in zip(ticks,ticks[1:]):
                assert abs(left['ready_after']+right['ready_arrived']-right['ready_before_service'])<1e-7
            initial=ticks[0]['ready_before_service']-ticks[0]['ready_arrived']
            arrivals=sum(t['ready_arrived'] for t in ticks);departed=sum(t['accepted'] for t in ticks)
            assert abs(initial+arrivals-departed-ticks[-1]['ready_after'])<1e-7
            window_rows.append(dict(start_sec=start,native_through_head_count=head_flow,native_known_head_ids=len(known),
                native_unresolved_head_ids=head_flow-len(known),native_heads=rows,
                model_ready_start=initial,model_arrivals_to_ready=arrivals,model_through_departed=departed,model_ready_end=ticks[-1]['ready_after'],
                model_incoming_storage=sum(t['incoming_storage'] for t in ticks),
                model_green_sec=sum(t['green'] for t in ticks),model_cap=sum(t['cap'] for t in ticks),
                model_starved=sum(t['starved'] for t in ticks),model_receiving_loss=sum(t['receiving_loss'] for t in ticks),ticks=ticks))
        results[arm]=dict(native_snapshots=states,windows=window_rows)
    PINS.update(heads.PINS)
    assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in PINS.items())
    report=dict(status='complete_saved_balance_audit',origin=ORIGIN,through=THROUGH,rate_veh_h=rate,
        geometry=geometry,initial_footprint=sorted(footprint),results=results,source_pins=PINS,
        forecast_calls=0,native=0,fitting=0,future_inputs=False,goal_complete=False,
        limitations=['Initial owned physical footprint is fixed, not a new Omega boundary.',
          'Head counts are observed crossings; unresolved IDs remain explicit.',
          'Model service-ready queue is not defined as native stopped count.',
          'State frames are150s snapshots; within-interval queue history is not inferred.',
          'Native history after2400 is validation only.'])
    (HERE/'assessment.json').write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
    for arm,row in results.items():
        print(arm,json.dumps([dict(start_sec=w['start_sec'],native_head=w['native_through_head_count'],model_flow=w['model_through_departed'],ready_in=w['model_arrivals_to_ready'],ready_out=w['model_ready_end'],cap=w['model_cap'],green=w['model_green_sec'],starved=w['model_starved']) for w in row['windows']],indent=2))

if __name__=='__main__':main()
