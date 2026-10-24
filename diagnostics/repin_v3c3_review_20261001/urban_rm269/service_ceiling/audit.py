"""Past-only phase service and startup-inclusive queued-cohort audit.

No capacity is installed by this script. The observed head discharge per whole
green is demand-limited; a queued prefix can identify a stronger achieved lower
bound, but is not proof of a constant future saturation rate.
"""
import ctypes,hashlib,importlib.util,json,sys
from collections import defaultdict
from pathlib import Path
import xml.etree.ElementTree as ET
HERE=Path(__file__).resolve().parent
H=HERE.parent
ROOT=HERE.parents[3]
sys.path[:0]=[str(ROOT),str(H)]
from evaluation.controllers import obs150_signal_clock as clock
from evaluation.controllers.obs150_observation import sig_manifest_files
loader=importlib.util.spec_from_file_location('head_reader',H/'sc12_source/audit.py')
a=importlib.util.module_from_spec(loader);loader.loader.exec_module(a)
a.LINKS={'SC12_S':1210012700,'SC101_S':1220011503}
read=a.read

def main():
    out=HERE/'assessment.json';assert not out.exists()
    kernel=ctypes.WinDLL('kernel32');kernel.GetCurrentProcess.restype=ctypes.c_void_p
    kernel.SetPriorityClass.argtypes=[ctypes.c_void_p,ctypes.c_uint32]
    assert kernel.SetPriorityClass(kernel.GetCurrentProcess(),0x4000)
    netpath=ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926/selected/network/native_seed29.inpx'
    root=ET.fromstring(a.pin(netpath))
    sig_files=sig_manifest_files(read(netpath.parent/'sig_manifest.json'))
    sig_table={}
    for controller in root.findall('./signalControllers/signalController'):
        if controller.get('no') not in ('12','101'):continue
        name=controller.get('supplyFile2').removeprefix('#data#')
        source=netpath.parent/name
        assert hashlib.sha256(a.pin(source)).hexdigest()==sig_files[name]
        sig_table[controller.get('no')]=clock.sig_program_from_file(
            controller.get('no'),source,int(controller.get('progNo')),sha256=sig_files[name])
    heads={h.get('no'):h for h in root.findall('./signalHeads/signalHead')}
    selected={g:[h for h in heads.values() if h.get('lane').split()[0]==str(link) and h.get('sg').split()[1]=='8'] for g,link in a.LINKS.items()}
    assert all(len(hs)==3 for hs in selected.values())
    rows=[]
    for end in range(1050,3301,150):
        start=end-150
        before=read(a.ORIGINAL/f'state_{start:06}.json')
        after=read(a.ORIGINAL/f'state_{end:06}.json')
        assert before['vehicle_records']['complete']
        physical,events=a.heads_and_entries(a.ORIGINAL,end)
        log=after['obs150']['signal_log']
        scoped={**log,'scs':['12','101'],'start':{k:v for k,v in log['start'].items() if k.split('-')[0] in ('12','101')},
            'events':[e for e in log['events'] if e[1] in ('12','101')]}
        # The first controlled window retains native ownership at its first slot.
        # Read its pinned program rather than inventing a COM state for that slot.
        windows=clock.windows(scoped,sig_table,after['obs150']['window'],
            network_dir=Path(after['network_path']).parent)
        local={}
        for group,hs in selected.items():
            headrows=[]
            for head in hs:
                link,lane=map(int,head.get('lane').split());pos=float(head.get('pos'));sg=head.get('sg').replace(' ','-')
                times=windows[sg];assert times['complete']
                obs=next(x for x in physical[group]['rows'] if x['head_id']==head.get('no'))
                ev=sorted([(t,v) for l,v,t in events[group] if l==lane])
                all_lane=[v for v in before['vehicle_records']['records'] if v['link_no']==link and v['lane_no']==lane and v['position_m']<=pos]
                queue=[]
                for v in sorted(all_lane,key=lambda v:-v['position_m']):
                    if not v['stopped'] or (not queue and pos-v['position_m']>30.):break
                    queue.append(v['veh_no'])
                # A green already active at the snapshot has unobserved startup.
                starts_red=not any(lo<=start<hi for lo,hi in times['green'])
                intervals=[(lo,hi) for lo,hi in times['green'] if lo>start and hi>lo]
                prefix=[];eligible=False;reason='snapshot_already_green' if not starts_red else 'no_complete_green_start'
                rate=None;lo=hi=None
                if starts_red and intervals:
                    lo,hi=intervals[0]
                    unknown=obs['crossings']-len(ev)
                    assert unknown>=0
                    reason='unresolved_head_ids' if unknown else 'insufficient_stopped_prefix'
                    if not unknown:
                        for t,v in ev:
                            if not lo<=t<hi:continue
                            if v not in queue:break
                            prefix.append((t,v))
                        if len(prefix)>=5 and prefix[-1][0]>lo:
                            rate=3600*len(prefix)/(prefix[-1][0]-lo)
                            eligible=True;reason='startup_inclusive_current_stopped_prefix'
                headrows.append(dict(head_id=head.get('no'),lane=lane,snapshot_queue_veh=len(queue),
                    green_sec=obs.get('green_sec'),qualified_crossings=obs.get('qualified_crossings'),
                    total_crossings=obs['crossings'],green_start=lo,green_end=hi,queued_prefix_veh=len(prefix),
                    prefix_last_sec=prefix[-1][0] if prefix else None,eligible=eligible,reason=reason,
                    startup_inclusive_achieved_rate_veh_h=rate,
                    queued_prefix_ids=[v for t,v in prefix]))
            eligible=all(r['eligible'] for r in headrows)
            local[group]=dict(heads=headrows,whole_green_rate_veh_h=sum(3600*r['qualified_crossings']/r['green_sec'] if r['green_sec'] else 0. for r in headrows),
                all_heads_prefix_qualified=eligible,queued_prefix_group_rate_veh_h=sum(r['startup_inclusive_achieved_rate_veh_h'] for r in headrows) if eligible else None)
        rows.append(dict(start_sec=start,end_sec=end,groups=local))
    summary={}
    for cutoff in (2400,3300):
        summary[cutoff]={}
        for group in selected:
            history=[r for r in rows if r['end_sec']<=cutoff]
            qualified=[r for r in history if r['groups'][group]['all_heads_prefix_qualified']]
            pair=[dict(ends=[x['end_sec'],y['end_sec']],min_rate_veh_h=min(x['groups'][group]['queued_prefix_group_rate_veh_h'],y['groups'][group]['queued_prefix_group_rate_veh_h'])) for x,y in zip(qualified,qualified[1:]) if x['end_sec']==y['start_sec']]
            summary[cutoff][group]=dict(qualified_windows=[r['end_sec'] for r in qualified],consecutive_qualified_pairs=pair,
                maximum_paired_achieved_support=max((p['min_rate_veh_h'] for p in pair),default=None))
    for p in (Path(__file__),ROOT/'evaluation/controllers/signal_head_observation.py',ROOT/'evaluation/controllers/head_service_resources.py',
        H.parent/'upstream_worklog/02_urban_b2/impl/STAGE3.md',H.parent/'upstream_worklog/02_urban_b2/diag_c3_r2/C3V2_PROPOSAL.md'):a.pin(p)
    report=dict(status='complete_readonly',new_model_forecasts=0,new_native=0,fzp_scans=0,source_pins=a.PINS,rows=rows,summary=summary,
        limitations=['The queued prefix method is a local diagnostic following F2 startup inclusion, not an exact reproduction of Claude multi-seed U4 calibration.',
            'Only current stopped vehicles before a known green onset qualify. A moving vehicle ends the observed queue. No unknown ID is imputed.',
            'Observed prefixes can later experience different impedances; their rates are not constant future capacity guarantees.',
            'The2400subset uses no observation after2400.3300is a separate same-seed diagnostic cutoff.'])
    out.write_text(json.dumps(report,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf8')
    print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
