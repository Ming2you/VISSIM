"""Cached SC6 service/arrival decomposition; no fit, forecast or FZP scan."""
import gzip,hashlib,importlib.util,json,pickle,sys
from collections import Counter
from pathlib import Path
import xml.etree.ElementTree as ET

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[4];A=HERE.parent;H=A.parent
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
from evaluation.controllers import signal_actuation_contract as signals
loader=importlib.util.spec_from_file_location('head_reader293',H/'sc12_source/audit.py')
head=importlib.util.module_from_spec(loader);loader.loader.exec_module(head)
head.LINKS={'SC6_S':1210018302}
PINS={}
def pin(p):
    data=Path(p).read_bytes();PINS[str(Path(p).resolve())]=hashlib.sha256(data).hexdigest();return data
def read(p):return json.loads(pin(p))
def tup(v):return tuple(tup(x) for x in v) if isinstance(v,list) else v


def phase_fraction(control,network,start,dt):
    c=network.signal_actuation_contract;raw=c['nodes']['SC6']
    values=tuple(control['green_times']['SC6_'+p] for p in signals.PHASES)
    table=signals._phase_windows(tup(raw['_segments']),tup(raw['_order']),values,
        c['amber']+c['all_red'],signals._native_payload(raw),c['amber'])
    assert raw['native_clock_basis']['kind']=='serial'
    lo,hi=table['p1'];cycle=raw['native_clock_basis']['cycle_sec']
    fraction=signals._finite_fraction(cycle,control['offsets']['SC6'],lo,hi,dt,start,start+dt)
    assert 0. <= fraction <= 1., (start,dt,fraction)
    return fraction


def main():
    assert not (HERE/'assessment_v2.json').exists()
    # The first diagnostic incorrectly used 1s as a 10s interval denominator.
    # This checks the diagnostic helper; production already passes duration.
    assert signals._finite_fraction(150.,0.,0.,50.,10.,0.,10.)==1.
    assert abs(4400.*10./3600.-12.222222222222221)<1e-10
    prior=read(A/'sourcepath292/completion.json')
    assert prior['status']=='complete_diagnostic_not_adopted'
    assert hashlib.sha256(pin(A/'sourcepath292/assessment.json')).hexdigest()==prior['assessment_sha256']
    cfg,state,_=pickle.loads(pin(A/'citysplit287/forecast2400/initial.pickle'))
    movements=['SC6_S_SC12_to_N_SC103','SC6_S_SC12_to_E_SC104']
    sources={'movement:'+m for m in movements}
    folders={'hold':Path('E:/VISSIM_runs/20261008_urbanrm269_native2400_s29/hold/decisions_sdmpc31_g_2400_hold_s29'),
             'city':Path('E:/VISSIM_runs/20261010_urbanrm269_cityonly289_s29/selected/decisions_sdmpc31_g_2400_selected_s29')}
    controls={arm:[read((H/'selection2400_discrete/hold' if arm=='hold' else A/'citysplit287/forecast2400/city_only')/f'action_{t:06}.json')
                   for t in (2400,2550,2700)] for arm in folders}
    network=ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926/selected/network/native_seed29.inpx'
    tree=ET.fromstring(pin(network))
    positions={int(h.get('lane').split()[1]):float(h.get('pos')) for h in tree.findall('./signalHeads/signalHead')
               if h.get('lane').split()[0]=='1210018302' and h.get('sg').split()[0]=='6'}
    initial=read(folders['hold']/'state_002400.json')['vehicle_records']['records']
    assert initial==read(folders['city']/'state_002400.json')['vehicle_records']['records']
    before={r['veh_no']:r for r in initial if r['link_no']==1210018302
            and r['lane_no'] in (1,2,3) and r['position_m']<=positions[r['lane_no']]}
    native={}
    for arm,folder in folders.items():
        blocks=[]
        for end in (2550,2700,2850):
            counts,events=head.heads_and_entries(folder,end)
            rows=[(lane,veh,t) for lane,veh,t in events['SC6_S'] if lane in (1,2,3)]
            full=sum(x['crossings'] for x in counts['SC6_S']['rows'] if x['lane'] in (1,2,3))
            missing=full-len(rows);assert missing>=0
            early=[(l,v,t) for l,v,t in rows if end-150<=t<end-130]
            blocks.append(dict(start_sec=end-150,count=full,known_events=len(rows),unresolved=missing,
                first20_known=len(early),first20_count_bounds=[len(early),len(early)+missing],
                first20_from_current_last_link=sum(v in before for _,v,_ in early),
                first20_from_current_stopped=sum(v in before and before[v]['stopped'] for _,v,_ in early),
                current_last_link_crossing_first150=sum(v in before for _,v,_ in rows)))
        native[arm]=blocks
    PINS.update(head.PINS)
    versions={'baseline':{'hold':A/'matched280/authority/hold.response.json.gz',
                          'city':A/'citysplit287/forecast2400/city_only.response.json.gz'},
              'path292':{arm:A/'sourcepath292/forecast2400_r3'/f'{arm}.response.json.gz' for arm in folders}}
    model={}
    for version,paths in versions.items():
        model[version]={}
        for arm,path in paths.items():
            response=json.loads(gzip.decompress(pin(path)))
            resources={(x['resource'],x['start_sec'],x['kind']):x for x in response['resource_allocations']
                if x['resource'] in movements and x['kind'] in ('urban_movement_stock','urban_movement_intended_limit')}
            blocks=[]
            for i,start in enumerate((2400,2550,2700)):
                metrics=dict(service_opportunity=0.,not_ready_opportunity=0.,other_request_loss=0.,receiving_loss=0.,
                             accepted=0.,first20_accepted=0.,ready_green_sec=0.,empty_green_sec=0.)
                initial_ready={};ticks=[]
                for t in range(start,start+150,10):
                    fraction=phase_fraction(controls[arm][i],cfg.network,t,10)
                    tick=dict(sec=t,green_sec=fraction*10,ready=0.,accepted=0.)
                    for m in movements:
                        stock=resources[m,t,'urban_movement_stock'];req=resources[m,t,'urban_movement_intended_limit']
                        q=stock['available_veh'];wanted=req['available_veh'];got=req['accepted_total_veh']
                        cap=cfg.network.movement_capacity_by_movement_veh_h[m]*fraction*10/3600
                        assert -1e-8<=got<=wanted+1e-8 and wanted<=min(q,cap)+1e-7,(version,arm,m,t,q,wanted,cap)
                        metrics['service_opportunity']+=cap
                        metrics['not_ready_opportunity']+=max(0.,cap-q)
                        metrics['other_request_loss']+=min(q,cap)-wanted
                        metrics['receiving_loss']+=wanted-got
                        metrics['accepted']+=got
                        if t<start+20:metrics['first20_accepted']+=got
                        if t==start:initial_ready[m]=q
                        tick['ready']+=q;tick['accepted']+=got
                    if tick['ready']<=1e-8:metrics['empty_green_sec']+=fraction*10
                    else:metrics['ready_green_sec']+=fraction*10
                    ticks.append(tick)
                assert abs(metrics['service_opportunity']-metrics['not_ready_opportunity']-
                    metrics['other_request_loss']-metrics['receiving_loss']-metrics['accepted'])<1e-7
                measured=native[arm][i]['count']
                if i==0:
                    expected=4400.*({'hold':68.,'city':64.}[arm])/3600.
                    assert abs(metrics['service_opportunity']-expected)<1e-8
                metrics['native_minus_model']=measured-metrics['accepted']
                metrics['native_minus_saturated_model_ceiling']=measured-metrics['service_opportunity']
                blocks.append(dict(start_sec=start,metrics=metrics,initial_ready=initial_ready,ticks=ticks))
            model[version][arm]=blocks
    # Reuse old initial-cohort experiment: do not call the same candidate new.
    pin(H/'sc6_initial_cohort/README.md');pin(H/'arrival_head/README.md')
    pin(H.parent/'upstream_worklog/02_urban_b2/diag_c3_r2/U7.md')
    report=dict(status='completed_cached_service_arrival_decomposition',previous_goal_turn='no_progress_status_restatement',
        supersedes_invalid='assessment.json: 10s green fraction normalized by 1s; service budgets and decomposition invalid',
        native=native,model=model,current_last_link_p1=dict(vehicles=len(before),
            stopped=sum(r['stopped'] for r in before.values()),lanes=dict(Counter(r['lane_no'] for r in before.values())),
            model_ready=sum(state.urban_movement_queue[m] for m in movements)),
        new_predictions=0,new_native=0,new_fzp_reads=0,production_changes=0,fits=0,
        limitations=['Native first20 missing event times are bounded, not invented.',
          'Per-tick ready stock is a model queue operand, not total physical approach stock.',
          'Lost opportunity identities freeze observed model operands and are not a counterfactual gain estimate.',
          'Current physical stopped count is not automatically all ready at a point stopline.',
          'Sourcepath292 and baseline share initialization; earlier last-link-only initialization candidate was already rejected.'],
        source_pins=PINS,goal_complete=False)
    PINS[str(Path(__file__).resolve())]=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    (HERE/'assessment_v2.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print('INITIAL',report['current_last_link_p1'])
    print('NATIVE_FIRST20',{a:[r['first20_count_bounds'] for r in rows] for a,rows in native.items()})
    for v,arms in model.items():
        for arm,rows in arms.items():print(v,arm,[{k:round(r['metrics'][k],4) for k in
            ('accepted','first20_accepted','service_opportunity','not_ready_opportunity','other_request_loss','receiving_loss')} for r in rows])


if __name__=='__main__':main()
