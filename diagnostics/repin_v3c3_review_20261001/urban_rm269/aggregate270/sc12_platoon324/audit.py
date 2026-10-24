"""Current-source and fixed-signal timing audit; reuse completed observations.

No simulation, FZP, optimization, future-input calibration or model mutation.
"""
from pathlib import Path
from collections import Counter
import gzip, hashlib, json, pickle, xml.etree.ElementTree as ET

from diagnostics.repin_v3c3_review_20261001.urban_rm269.sc12_source import audit as heads
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.city_loss322.audit import RUNS, green_seconds
from plant.src.vissim_strict.signal_program import parse_sig
from evaluation.controllers.fixed_signal_schedule import _union_green_overlap

HERE=Path(__file__).resolve().parent
A=HERE.parent
ROOT=HERE.parents[4]
SOURCE='SC6_to_SC12'
PRE={1220018202,10208,1210018202}
POST={1220018201,1220015000}
MOVS=('SC12_N_SC6_to_S_SC16','SC12_N_SC6_to_W_SC11','SC12_N_SC6_to_E_SC106')
MODEL=Path('E:/VISSIM_analysis/20261010_sc16_aggregate323/forecast2400')
PINS={}

def data(path):
    path=Path(path);b=path.read_bytes()
    PINS[str(path.resolve())]=hashlib.sha256(b).hexdigest()
    return b

def read(path):
    b=data(path)
    return json.loads(gzip.decompress(b) if str(path).endswith('.gz') else b)

def main():
    assert not (HERE/'assessment.json').exists(),'Preserve completed audit'
    proof=read(MODEL/'summary.json')
    assert proof['status']=='complete' and proof['forecasts']==2 and not proof['future_observation_inputs']
    for p,h in proof['source_pins'].items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h,p
    closure=read('E:/VISSIM_analysis/20261010_urbanrm269_cityonly289/runtime_closure.json')
    assert closure['all_owned_processes_closed'] and closure['normal_sim_done_sec']==2850
    cfg,state,_=pickle.loads(data(A/'citysplit287/forecast2400/initial.pickle'))
    rawpath=RUNS['hold']/'state_002400.json';raw=read(rawpath)
    fp=rawpath.parent/raw['obs150']['frames']['current']['path'];frame=read(fp)
    assert PINS[str(fp.resolve())]==raw['obs150']['frames']['current']['sha256']
    assert raw['vehicle_records']['complete'] and frame['complete']
    assert raw['sim_sec']==frame['time_s']==state.time_sec==2400
    for k in ('paused_at_sim_sec','capture_sim_sec_before','capture_sim_sec_after'):
        assert raw['vehicle_records'][k]==2400
    native_paths=[Path(read(folder/'state_002400.json')['network_path']) for folder in RUNS.values()]
    selected=ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926/selected/network/native_seed29.inpx'
    hashes={str(p):hashlib.sha256(data(p)).hexdigest() for p in [selected,*native_paths]}
    assert len(set(hashes.values()))==1
    root=ET.fromstring(data(selected))
    sc=root.find("./signalControllers/signalController[@no='10']")
    assert sc.get('type')=='FIXEDTIME' and sc.get('active')=='true'
    sig=selected.parent/sc.get('supplyFile2').removeprefix('#data#');data(sig)
    # The executed source uses this same fixed signal file, not only the same INPX.
    for np in native_paths:
        assert data(np.parent/sig.name)==data(sig)
    program=parse_sig(sig,int(sc.get('progNo')))
    offset=float(sc.get('offset'))
    green=[t for t in range(2400,2550) if _union_green_overlap(program,('4',),t,t+1,offset)>0]
    assert min(green)==2438
    sh=[x.attrib for x in root.findall('./signalHeads/signalHead') if x.get('sg')=='10 4']
    assert len(sh)==3 and {x['lane'].split()[0] for x in sh}=={'1210018202'}
    observed={int(v[0]):v for v in frame['vehicles']}
    records=[v for v in raw['vehicle_records']['records'] if v['link_no'] in PRE|POST]
    assert len(records)==17 and len({v['veh_no'] for v in records})==17
    pre={v['veh_no'] for v in records if v['link_no'] in PRE}
    post={v['veh_no'] for v in records if v['link_no'] in POST}
    gate_pos=min(float(x['pos']) for x in sh)
    assert all(v['position_m']<gate_pos for v in records if v['link_no']==1210018202)
    assert len(pre)==11 and len(post)==6
    known={};unknown=[]
    for v in records:
        row=observed[v['veh_no']]
        assert row[1]==v['link_no'] and row[2]==v['lane_no'] and row[3]==v['position_m']
        if row[6] is None:
            assert all(x is None for x in row[6:10]);unknown.append(v['veh_no']);continue
        assert row[6]==33 and row[8]=='STATIC'
        known[v['veh_no']]={1:'left',2:'through',3:'right'}[int(row[7])]
    assert Counter(known.values())==dict(through=12,left=2,right=1) and len(unknown)==2
    initial=state.local_observation_summary['projection_diagnostics']['physical_stock_assignment_by_link']
    owners={str(v['link_no']) for v in records}
    stock=sum(initial[k].get('storage:'+SOURCE,0) for k in owners)
    queues={m:state.urban_movement_queue[m] for m in MOVS}
    assert stock==15 and sum(queues.values())==2
    assert state.urban_arrival_buffer[SOURCE]==state.urban_storage_release_buffer[SOURCE]=={242:15.}
    current=dict(before_intermediate_signal_veh=11,after_intermediate_signal_veh=6,
        ready_veh=2,residual_veh=15,ready_movement_prior=queues,
        current_known_turn_counts=dict(Counter(known.values())),unknown_current_routes=len(unknown),
        parent_arrival_sec=2420,first_SC10_green_sec=min(green),current_pre_signal_ids=sorted(pre))
    heads.LINKS={'SC12_N':1220015000,'SC10_N':1210018202}
    result={}
    for arm,folder in RUNS.items():
        controls_dir=A.parent/'selection2400_discrete/hold' if arm=='hold' else A/'citysplit287/forecast2400/city_only'
        controls=[read(controls_dir/f'action_{t:06}.json') for t in (2400,2550,2700)]
        blocks=[];pre_events=[];post_events=[]
        for i,end in enumerate((2550,2700,2850)):
            counts,events=heads.heads_and_entries(folder,end)
            assert counts['SC10_N']['detector_count']==0 # Missing, NOT measured zero flow.
            p1=[x for x in events['SC12_N'] if x[0] in (1,2,3)]
            total=sum(x['crossings'] for x in counts['SC12_N']['rows'] if x['lane'] in (1,2,3))
            assert total==len(p1),'Do not assign unresolved crossings to a current cohort'
            pp=[dict(lane=l,veh=v,time_sec=t) for l,v,t in p1 if v in pre]
            po=[dict(lane=l,veh=v,time_sec=t) for l,v,t in p1 if v in post]
            pre_events+=pp;post_events+=po
            blocks.append(dict(start_sec=end-150,p1_count=total,pre_initial_p1=pp,post_initial_p1=po,
                predicted_p1_green=[dict(start_sec=t,green_sec=green_seconds(controls[i],cfg.network,MOVS[0],t))
                    for t in range(end-150,end,10) if green_seconds(controls[i],cfg.network,MOVS[0],t)>0]))
        response=read(MODEL/(arm+'.response.json.gz'))
        tr=[x for x in response['transfers'] if x['source'] in {'movement:'+m for m in MOVS[:2]} and x['source']!=x['target']]
        result[arm]=dict(native_blocks=blocks,model_p1_counts=[sum(x['vehicles'] for x in tr if t<=x['start_sec']<t+150) for t in (2400,2550,2700)],
            current_pre_initial_p1=pre_events,current_post_initial_p1=post_events)
    h={v['veh']:v['time_sec'] for v in result['hold']['current_pre_initial_p1']}
    c={v['veh']:v['time_sec'] for v in result['city']['current_pre_initial_p1']}
    assert set(h)==set(c)=={v for v in pre if known[v]=='through'} and len(h)==9
    delay=[dict(veh=v,hold_sec=h[v],city_sec=c[v],extra_sec=c[v]-h[v]) for v in sorted(h)]
    assert all(r['extra_sec']>80 for r in delay)
    # Future events are audit targets. They never enter a predictor or fitted rate.
    cohort_cost=sum(r['extra_sec'] for r in delay)/3600
    for p in [A/'gate296/README.md',A/'gate296/candidate.py',A/'sourcepath292/candidate.py',
              A.parent.parent/'upstream_worklog/02_urban_b2/diag_c3_r2/U7.md',
              A.parent.parent/'upstream_worklog/02_urban_b2/diag_c3_r2/C3V2_PROPOSAL.md']:
        data(p)
    PINS.update(heads.PINS);data(Path(__file__))
    report=dict(status='complete_initial_platoon_missed_green_reproduced',current=current,results=result,
        common_initial_cohort_delays=delay,cohort_head_delay_veh_h=cohort_cost,
        network_hashes=hashes,intermediate_heads=sh,source_pins=PINS,
        structural_cause='Current source reservations bypass an intervening fixed SC10/SG4 signal; known current SC12 turns are redrawn from the aggregate prior.',
        existing_gate296='Opposite direction SC12_to_SC6 SG8; new accepted traffic only. It does not cover this initial or future SC6_to_SC12 corridor.',
        limits=['The nine-vehicle head delay is a local cohort diagnostic, not the whole Omega TTT difference.',
                'SC10 has no direct head counter in these observations; zero detectors means missing, not zero flow.',
                'Fixed signal timing is read from matching executed SIG files; it is not an independent native signal-state verification.',
                'SC12 future head events and common vehicle IDs are used only to diagnose the error.',
                'No proof yet that correcting this path reverses whole-network gain; source-boundary admission differences remain separate.'],
        next_step='One aggregate SC6_to_SC12 pre-gate / fixed-SC10 queue / post-gate correction, preserving source stock ownership, known current turns and actual accepted upstream flow. Compare existing hold/city450 once before any unused-state/AD/SDMPC qualification. No beta/rate grid or native restart.',
        budget=dict(native=0,rollouts=0,optimizer=0,ad=0,fzp=0,fits=0,production_changes=0),goal_complete=False)
    (HERE/'assessment.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print('INITIAL',current)
    print('P1_NATIVE',{a:[b['p1_count'] for b in r['native_blocks']] for a,r in result.items()})
    print('P1_MODEL',{a:r['model_p1_counts'] for a,r in result.items()})
    print('NINE_CURRENT_VEHICLE_HEAD_DELAY_VEH_H',cohort_cost)

if __name__=='__main__':main()
