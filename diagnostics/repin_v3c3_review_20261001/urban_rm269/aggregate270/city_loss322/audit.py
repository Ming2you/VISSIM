"""Separate retained city-loss errors; no fitting, rollout, native or FZP read."""
from collections import Counter, defaultdict
from pathlib import Path
import gzip, hashlib, json, pickle, xml.etree.ElementTree as ET

from evaluation.controllers import signal_actuation_contract as signals
from diagnostics.repin_v3c3_review_20261001.urban_rm269.sc12_source import audit as heads

HERE = Path(__file__).resolve().parent
A = HERE.parent
H = A.parent
ROOT = HERE.parents[4]
MODEL = Path('E:/VISSIM_analysis/20261010_sc109_routes321/forecast2400')
RUNS = dict(hold=Path('E:/VISSIM_runs/20261008_urbanrm269_native2400_s29/hold/decisions_sdmpc31_g_2400_hold_s29'),
            city=Path('E:/VISSIM_runs/20261010_urbanrm269_cityonly289_s29/selected/decisions_sdmpc31_g_2400_selected_s29'))
GROUPS = {
    'SC6_S': (1210018302, (1,2,3), ('SC6_S_SC12_to_N_SC103','SC6_S_SC12_to_E_SC104')),
    'SC101_S': (1220011503, (1,2,3), ('SC101_S_SC1_to_N_SC2005',)),
    'SC16_N_left': (1210012600, (4,), ('SC16_N_SC12_to_E',)),
}
PINS = {}

def data(path):
    path=Path(path); b=path.read_bytes();PINS[str(path.resolve())]=hashlib.sha256(b).hexdigest();return b

def read(path):
    b=data(path);return json.loads(gzip.decompress(b) if str(path).endswith('.gz') else b)

def tup(v):return tuple(tup(x) for x in v) if isinstance(v,list) else v

def green_seconds(control,network,movement,t,dt=10):
    m=network.urban_movements[movement];node=m['signal'];phase=m['phase'].rsplit('_',1)[1]
    c=network.signal_actuation_contract;raw=c['nodes'][node]
    values=tuple(control['green_times'][node+'_'+p] for p in signals.PHASES)
    table=signals._phase_windows(tup(raw['_segments']),tup(raw['_order']),values,
        c['amber']+c['all_red'],signals._native_payload(raw),c['amber'])
    assert raw['native_clock_basis']['kind']=='serial'
    lo,hi=table[phase]
    f=signals._finite_fraction(raw['native_clock_basis']['cycle_sec'],control['offsets'][node],lo,hi,dt,t,t+dt)
    assert 0<=f<=1
    return f*dt

def main():
    assert not (HERE/'assessment.json').exists(),'Preserve completed evidence'
    assert signals._finite_fraction(150,0,0,50,10,0,10)==1
    proof=read(MODEL/'summary.json')
    assert proof['status']=='complete' and proof['forecasts']==2 and not proof['future_observation_inputs']
    for p,h in proof['source_pins'].items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h,p
    closure=read('E:/VISSIM_analysis/20261010_urbanrm269_cityonly289/runtime_closure.json')
    assert closure['all_owned_processes_closed'] and closure['normal_sim_done_sec']==2850
    for p in (H.parent/'upstream_worklog/02_urban_b2/diag_c3_r2/C3V2_PROPOSAL.md',
              H.parent/'upstream_worklog/02_urban_b2/diag_c3_r2/U7.md',
              A/'servicearrival293/assessment_v2.json', A/'sc101_service304/README.md', A/'source_boundary318/README.md'):
        data(p)
    cfg,state,_=pickle.loads(data(A/'citysplit287/forecast2400/initial.pickle'))
    rates=dict(cfg.network.movement_capacity_by_movement_veh_h)
    applied=read(MODEL/'candidate_application.json')
    rates['SC101_S_SC1_to_N_SC2005']=applied['after_veh_h']
    assert rates['SC101_S_SC1_to_N_SC2005']==5236.47858772522
    assert max(applied['support']['end_sec'])<2400
    controls={arm:[read((H/'selection2400_discrete/hold' if arm=='hold' else A/'citysplit287/forecast2400/city_only')/f'action_{t:06}.json')
                   for t in (2400,2550,2700)] for arm in RUNS}
    heads.LINKS={k:v[0] for k,v in GROUPS.items()}
    heads.LINKS.update(SC12_N=1220015000,SC12_W=1220012103,SC12_S=1210012700)
    native={};model={};witnesses={}
    for arm,folder in RUNS.items():
        native[arm]={k:[] for k in GROUPS};prior=defaultdict(list);matched=Counter();left=[]
        for end in (2250,2400,2550,2700,2850):
            counts,events=heads.heads_and_entries(folder,end)
            for label in ('SC12_N','SC12_W','SC12_S'):
                for lane,veh,t in events[label]:prior[veh].append((t,label,lane))
            for group,(_,lanes,_) in GROUPS.items():
                selected=[(l,v,t) for l,v,t in events[group] if l in lanes]
                total=sum(x['crossings'] for x in counts[group]['rows'] if x['lane'] in lanes)
                missing=total-len(selected);assert missing>=0
                native[arm][group].append(dict(start_sec=end-150,count=total,known_count=len(selected),unresolved=missing,
                    head_time_cost_known=-sum((2850-t)/3600 for _,_,t in selected)))
                if end<=2400 or group!='SC16_N_left':continue
                for lane,veh,t in selected:
                    candidates=[x for x in prior[veh] if x[0]<t]
                    src=max(candidates) if candidates else (None,'unknown',None)
                    matched[src[1]]+=1
                    left.append(dict(veh=veh,time_sec=t,prior_head=src,travel_sec=t-src[0] if src[0] is not None else None))
        witnesses[arm]=dict(matched_sources=dict(matched),left_head_events=left)
        response=read(MODEL/(arm+'.response.json.gz'))
        assert response['model_constraint_coverage']['complete']
        resources={(x['resource'],x['start_sec'],x['kind']):x for x in response['resource_allocations']}
        model[arm]={}
        for group,(_,_,movements) in GROUPS.items():
            blocks=[]
            for index,start in enumerate((2400,2550,2700)):
                sums=Counter();ticks=[]
                for t in range(start,start+150,10):
                    details={}
                    for m in movements:
                        stock=resources[m,t,'urban_movement_stock'];request=resources[m,t,'urban_movement_intended_limit']
                        q=stock['available_veh'];wanted=request['available_veh'];got=request['accepted_total_veh']
                        g=green_seconds(controls[arm][index],cfg.network,m,t);cap=rates[m]*g/3600
                        assert -1e-8<=got<=wanted+1e-8 and wanted<=min(q,cap)+1e-7,(arm,m,t,q,wanted,cap)
                        row=dict(cap=cap,ready=q,accepted=got,green_sec=g,starved=max(0,cap-q),
                            other_request_loss=min(q,cap)-wanted,receiving_loss=wanted-got)
                        details[m]=row
                        for key in ('cap','accepted','starved','other_request_loss','receiving_loss'):sums[key]+=row[key]
                    ticks.append(dict(sec=t,movements=details))
                assert abs(sums['cap']-sum(sums[k] for k in ('accepted','starved','other_request_loss','receiving_loss')))<1e-7
                blocks.append(dict(start_sec=start,**dict(sums),ticks=ticks))
            source='SC12_to_SC16' if group=='SC16_N_left' else cfg.network.urban_movements[movements[0]]['origin']
            transfers=[x for x in response['transfers'] if x['source']!=x['target']]
            incoming=Counter()
            for x in transfers:
                if x['target']=='storage:'+source:incoming[x['source'] or 'exogenous']+=x['vehicles']
            departed=[x for x in transfers if x['source'] in {'movement:'+m for m in movements}]
            model[arm][group]=dict(blocks=blocks,source_accepted=dict(incoming),
                total_accepted=sum(b['accepted'] for b in blocks),
                head_time_cost=-sum(x['vehicles']*(2850-x['start_sec'])/3600 for x in departed))
    PINS.update(heads.PINS)
    netpath=ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926/selected/network/native_seed29.inpx'
    root=ET.fromstring(data(netpath))
    rawpath=RUNS['hold']/'state_002400.json';raw=read(rawpath)
    currentpath=rawpath.parent/raw['obs150']['frames']['current']['path'];frame=read(currentpath)
    assert PINS[str(currentpath.resolve())]==raw['obs150']['frames']['current']['sha256']
    records=[v for v in raw['vehicle_records']['records'] if v['link_no']==1210012600 and v['lane_no']==4 and v['stopped']]
    head=root.find("./signalHeads/signalHead[@no='180701']")
    assert head.get('lane')=='1210012600 4' and head.get('sg')=='16 7'
    outgoing=[]
    for link in root.findall('./links/link'):
        frm=link.find('fromLinkEndPt')
        if frm is None or frm.get('lane').split()[0]!='1210012600':continue
        lo=int(frm.get('lane').split()[1]);allowed=range(lo,lo+len(link.findall('./lanes/lane')))
        if 4 in allowed:outgoing.append(link.get('no'))
    assert outgoing==['10250'] and len(records)==1
    initial=dict(native_stopped_lane4=records,exclusive_connector='10250',
        current_route_rows=[x for x in frame['vehicles'] if x[0] in {v['veh_no'] for v in records}],
        predicted_ready={m:state.urban_movement_queue[m] for m in cfg.network.urban_movements if m.startswith('SC16_N_SC12')},
        aggregate_prior={m:v['beta'] for m,v in cfg.network.urban_movements.items() if m.startswith('SC16_N_SC12')},
        initial_provenance=state.local_observation_summary['projection_diagnostics']['physical_stock_assignment_by_link']['1210012600'])
    data(Path(__file__))
    report=dict(status='complete_city_loss_operands_separated',model=model,native=native,
        sc16_initial=initial,sc16_source_witnesses=witnesses,source_pins=PINS,
        previous_goal_turn='no_progress_clock_status_only_revalidated',
        budget=dict(rollouts=0,native=0,fzp_scans=0,optimizer=0,ad=0,fits=0,production_changes=0),
        limits=['Head cost is departure timing weighted to2850, not whole Omega TTT or isolated causal benefit.',
            'Future native/head records are diagnostic targets only; source matches are lower bounds.',
            'NULL current routes do not authorize a new future route decision.',
            'SC16 unique lane supports current ready-turn ownership, not all upstream/future route proportions.',
            'Legacy rates and route supply both limit SC16; fixing initial0.8veh alone cannot explain missing26 departures.',
            'Claude v3c1 routing changes are a different network and cannot supply current beta values.',
            'Common initial state is development data; no heldout response or AD/choice qualification for latest composite.'],goal_complete=False)
    (HERE/'assessment.json').write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
    for group in GROUPS:
        for arm in RUNS:
            m=model[arm][group];n=[x['count'] for x in native[arm][group] if x['start_sec']>=2400]
            print(group,arm,'MODEL',[round(x['accepted'],3) for x in m['blocks']],'NATIVE',n,
                'CAP',[round(x['cap'],3) for x in m['blocks']], 'RECEIVING_LOSS',sum(x['receiving_loss'] for x in m['blocks']))
    print('SC16_SOURCE', {arm:v['matched_sources'] for arm,v in witnesses.items()})

if __name__=='__main__':main()
