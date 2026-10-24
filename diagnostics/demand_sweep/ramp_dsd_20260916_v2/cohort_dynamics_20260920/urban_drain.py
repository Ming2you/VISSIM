"""Inspect10643 ->126 ->71 queue/service coupling from completed native runs.

This extracts current states and next-second flow for a bounded local model
test. It does not infer saturation from unqueued throughput, alter a signal,
or pass future observations into the450s plant.
"""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.gain_response_20260919.probe import e,H
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.state_exchange_20260920.analyze_dispersion import records
from diagnostics.validate_native_signal_record import read_ldp_frames
from diagnostics.capture_native_runtime_errors import parse_bytes
from plant.src.vissim_strict.signal_program import parse_sig
from collections import Counter
import xml.etree.ElementTree as ET
import csv
import argparse
import hashlib

HERE=Path(__file__).resolve().parent


def extract(run,start=1800,end=2850):
    # Use the actual run network and native timing; source_dsd is not a timing
    # alias. Verify every state against native LDP before using the program.
    receipt=e.load(run/'run.json');assert receipt['completed']
    network=Path(receipt['network']);root=ET.parse(network).getroot()
    sc=next(n for n in root.findall('./signalControllers/signalController') if n.get('no')=='1004')
    groups=[int(n.get('sg').split()[1]) for n in sc.findall('./scDetRecConf/signalOutputConfigurationElement')
            if n.get('configName')=='SG_BILD']
    ldp=read_ldp_frames({1004:run/'vissim_eval/baseline_1004_001.ldp'},{1004:groups},start,end)
    supply=sc.get('supplyFile2')
    sig=network.parent/supply[6:] if supply.startswith('#data#') else Path(supply)
    program=parse_sig(sig,int(sc.get('progNo')))
    signal_checks=0
    for t in range(start,end+1):
        for sg in (2,5):
            assert program.state_at(t,sg,controller_offset_sec=float(sc.get('offset')))==ldp['frames'][t][f'1004:{sg}'],(t,sg)
            signal_checks+=1
    links={int(n.get('no')):n for n in root.findall('./links/link')}
    head_positions={int(n.get('lane').split()[1]):float(n.get('pos')) for n in root.findall('./signalHeads/signalHead')
                    if n.get('lane').split()[0]=='71'}
    assert set(head_positions)==set(range(1,6))
    lengths={i:sum(((float(a.get('x'))-float(b.get('x')))**2+(float(a.get('y'))-float(b.get('y')))**2+
                   (float(a.get('zOffset','0'))-float(b.get('zOffset','0')))**2)**.5
                  for a,b in zip(list(links[i].find('./geometry/linkPolyPts')),list(links[i].find('./geometry/linkPolyPts'))[1:]))
             for i in (10643,126,71)}
    errors=parse_bytes((run/'baseline_001.err').read_bytes())
    assert not errors['unparsed_removal_lines']
    removals={r['vehicle_id']:r for r in errors['events'] if r['kind'] in
              ('lane_change_removal','route_next_link_not_found') and r['link']=='71'}
    rows=[];frame={};last=None;previous={};prior_state=None;losses=[];seen_off=set();initial_off=set()
    def state(t,current):
        c=Counter()
        for link,lane,pos,speed in current.values():
            if link==10643:
                c[f'off_lane{lane}_n']+=1;c[f'off_lane{lane}_stopped']+=int(speed<5)
                c[f'off_lane{lane}_tail30_n']+=int(pos>=lengths[10643]-30)
                c[f'off_lane{lane}_tail30_speed_sum']+=speed*int(pos>=lengths[10643]-30)
            elif link==126:c['link126_n']+=1
            elif link==71:
                g=2 if lane<=3 else 5
                c[f'urban_sg{g}_n']+=1;c[f'urban_sg{g}_stopped']+=int(speed<5)
                c[f'urban_lane{lane}_n']+=1
                c[f'urban_lane{lane}_tail30_n']+=int(pos>=head_positions[lane]-30)
                c[f'urban_lane{lane}_head_queue']+=int(pos>=head_positions[lane]-15 and speed<5)
        return {'time_s':t,**{k:c[k] for k in (
            [f'off_lane{l}_{v}' for l in (1,2) for v in ['n','stopped','tail30_n','tail30_speed_sum']]+
            ['link126_n']+[f'urban_sg{g}_{v}' for g in (2,5) for v in ['n','stopped']]+
            [f'urban_lane{l}_{v}' for l in range(1,6) for v in ['n','tail30_n','head_queue']])}}
    def process(t,current):
        nonlocal previous,prior_state
        now=state(t,current)
        seen_off.update(vid for vid,r in current.items() if r[0]==10643)
        if t==2400:initial_off.update(vid for vid,r in current.items() if r[0]==10643)
        if prior_state is not None:
            events=Counter()
            for vid,(link,lane,pos,speed) in current.items():
                old=previous.get(vid)
                if link==10643 and (old is None or old[0]!=10643):events[f'off_lane{lane}_arrivals']+=1
                if link==71 and (old is None or old[0]!=71):events[f'urban_sg{2 if lane<=3 else 5}_arrivals']+=1
                if link==71 and old and old[0]==71:
                    if (old[1]<=3)!=(lane<=3):
                        events[f'urban_exchange_to_sg{2 if lane<=3 else 5}']+=1
                    if old[2]<head_positions[old[1]] and pos>=head_positions[lane]:events[f'head_lane{lane}']+=1
            for vid,(link,lane,pos,speed) in previous.items():
                nowrow=current.get(vid)
                if link==10643 and (nowrow is None or nowrow[0]!=10643):
                    # No off-ramp deletion can be interpreted as service.
                    assert nowrow is not None and nowrow[0] in (126,10641,10700), (t,vid,nowrow)
                    events[f'off_lane{lane}_departures']+=1
                if link==71 and (nowrow is None or nowrow[0]!=71):
                    if nowrow is None:
                        warning=removals.get(vid)
                        assert warning and abs(t-warning['time_sec'])<=1,(t,vid,warning)
                        if warning['kind']=='lane_change_removal':assert abs(pos-warning['position_m'])<.1
                        events[f'urban_sg{2 if lane<=3 else 5}_removals']+=1
                        losses.append({**warning,'observed_disappearance_s':t,'last_lane':lane,
                            'fzp_absence_confirms_abnormal_loss':True,
                            'observed_on10643_since1800':vid in seen_off,'on10643_at2400':vid in initial_off})
                    else:
                        events[f'urban_sg{2 if lane<=3 else 5}_departures']+=1
                        if pos<head_positions[lane] and nowrow[0] in (10634,10635,56,47):events[f'head_lane{lane}']+=1
            row={**prior_state,'end_s':t,**{f'sg{g}_state':ldp['frames'][t][f'1004:{g}'] for g in (2,5)},
                 **{k:events[k] for k in ([f'off_lane{l}_{v}' for l in (1,2) for v in ['arrivals','departures']]+
                   [f'urban_sg{g}_{v}' for g in (2,5) for v in ['arrivals','departures','removals']]+
                   [f'urban_exchange_to_sg{g}' for g in (2,5)]+[f'head_lane{l}' for l in range(1,6)])}}
            # Off-lane transfer need not cancel individually, but total stock must.
            before_n=sum(prior_state[f'off_lane{l}_n'] for l in (1,2));after_n=sum(now[f'off_lane{l}_n'] for l in (1,2))
            assert after_n-before_n==sum(events[f'off_lane{l}_arrivals']-events[f'off_lane{l}_departures'] for l in (1,2))
            for g,other in ((2,5),(5,2)):
                assert now[f'urban_sg{g}_n']-prior_state[f'urban_sg{g}_n']==(
                    events[f'urban_sg{g}_arrivals']-events[f'urban_sg{g}_departures']+
                    events[f'urban_exchange_to_sg{g}']-events[f'urban_exchange_to_sg{other}']-events[f'urban_sg{g}_removals'])
            rows.append(row)
        previous=current;prior_state=now
    fzp=run/'vissim_eval/baseline_001.fzp';before=fzp.stat()
    for p in records(fzp):
        t=int(float(p[0]))
        if t<start:continue
        if t>end:break
        if last is not None and t!=last:
            assert t==last+1;process(last,frame);frame={}
        last=t
        # Keep next-frame presence network-wide. A short connector can be crossed
        # between samples; a missing row in a local filter is not a deletion.
        frame[int(p[1])]=(int(p[2]),int(p[3]),float(p[4]),float(p[6]))
    assert last==end;process(last,frame)
    assert len(rows)==end-start
    after=fzp.stat();assert (before.st_size,before.st_mtime_ns)==(after.st_size,after.st_mtime_ns)
    evidence={'source':str(run.relative_to(e.ROOT)),'rows':len(rows),'signal_program_native_checks':signal_checks,
        'signal_program_sha256':hashlib.sha256(sig.read_bytes()).hexdigest(),'native_ldp_pins':ldp['pins'],
        'lengths_m':lengths,'head_positions_m':head_positions,'stock_flow_checks':'Off-total and urban movement groups exact every second',
        'explicit_urban_removals':losses,'removals_are_not_service':True,
        'causality':'Row features are current states; end-second flows are validation targets, not forecast inputs.'}
    return rows,evidence


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=HERE/'urban_drain_observations_v1')
    args=parser.parse_args();out=args.output;out.mkdir(exist_ok=False)
    cases={'s23_none':HERE/'native_v1/none_s23/run','s23_vsl':H/'dsd_response_20260920/native_v2/run_retry1',
           's33_none':HERE/'native_v1/none_s33/run','s33_spread':H/'state_exchange_20260920/dispersion_seed33_v1/spread_only/run'}
    for name,run in cases.items():
        rows,evidence=extract(run)
        with (out/f'{name}.csv').open('x',encoding='utf-8',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
        e.save(out/f'{name}_evidence.json',evidence);print(name,len(rows),flush=True)


if __name__=='__main__':main()
