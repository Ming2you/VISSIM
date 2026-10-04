"""One pass over saved one-second observations; no live COM or FZP scan."""
import ctypes
import gzip
import hashlib
import json
from collections import Counter
from pathlib import Path
import time
import xml.etree.ElementTree as ET

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
I=ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926'
PINS={}


def read(path):
    data=path.read_bytes();PINS[str(path)]=hashlib.sha256(data).hexdigest()
    return json.loads(gzip.decompress(data) if path.suffix=='.gz' else data)


def main():
    output=HERE/'audit.json';assert not output.exists()
    if hasattr(ctypes,'windll'):
        kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        kernel.GetCurrentProcess.restype=ctypes.c_void_p
        kernel.SetPriorityClass.argtypes=[ctypes.c_void_p,ctypes.c_ulong]
        if not kernel.SetPriorityClass(kernel.GetCurrentProcess(),0x4000):
            raise ctypes.WinError(ctypes.get_last_error())
    started=time.perf_counter()
    runtime=read(HERE.parent/'entry10643/native_cohorts.json')['route_runtime']
    network=ROOT/runtime['network']['path'];data=network.read_bytes()
    assert hashlib.sha256(data).hexdigest()==runtime['network']['sha256']
    PINS[str(network)]=hashlib.sha256(data).hexdigest()
    link=ET.fromstring(data).find("./links/link[@no='10681']")
    assert len(link.findall('./lanes/lane'))==2
    target=link.find('toLinkEndPt');assert target.attrib['lane']=='2 1'
    cases={}
    for seed,start,directory,prefix in [
        ('43',2250,'D:/VISSIM_runs/20260929_seed43_observation2700/nc/decisions_sdmpc31_nc2700_s43','closedloop_recorded2250_lever450_trace10681_'),
        ('47',2700,'D:/VISSIM_runs/20260928_rm_observation2700_s47_v3/hold/decisions_sdmpc31_g_2700_hold_s47','closedloop_recorded2700_select_check_trace10681_')]:
        last=None;events=[];arrivals=[];lateral=[];unresolved=[];endpoint=[];run=None
        for stamp in range(start,start+451):
            frame=read(Path(directory)/'lane_observations'/f'frame_{stamp:06d}.json')
            assert frame['complete'] is True and frame['time_s']==stamp
            if run is None:run=frame['run_id']
            assert frame['run_id']==run
            current={v[0]:v for v in frame['vehicles']};assert len(current)==len(frame['vehicles'])
            ramp={vid:v for vid,v in current.items() if v[1]==10681}
            if stamp in (start,start+150,start+300,start+450):
                endpoint.append(dict(time_sec=stamp,counts=[sum(v[2]==g for v in ramp.values()) for g in (1,2)]))
            if last is not None:
                previous={vid:v for vid,v in last.items() if v[1]==10681}
                for vid,v in previous.items():
                    w=current.get(vid)
                    if w is None:
                        unresolved.append(dict(time_sec=stamp,vehicle=vid,reason='missing_after_ramp'))
                    elif w[1]!=10681:
                        event=dict(time_sec=stamp,vehicle=vid,from_lane=v[2],to_lane=w[2],to_link=w[1],
                            from_position=v[3],to_position=w[3],from_speed=v[4],to_speed=w[4])
                        if w[1]==2:events.append(event)
                        else:unresolved.append(event)
                    elif w[2]!=v[2]:
                        lateral.append(dict(time_sec=stamp,vehicle=vid,from_lane=v[2],to_lane=w[2]))
                for vid,v in ramp.items():
                    if vid not in previous:arrivals.append(dict(time_sec=stamp,vehicle=vid,lane=v[2]))
            last=current
        windows=[]
        for k in range(3):
            left=start+150*k;right=left+150
            merges=[e for e in events if left<e['time_sec']<=right]
            incoming=[e for e in arrivals if left<e['time_sec']<=right]
            missing=[e for e in unresolved if left<e['time_sec']<=right]
            assert sum(endpoint[k]['counts'])+len(incoming)-len(merges)-len(missing)==sum(endpoint[k+1]['counts'])
            windows.append(dict(start=left,end=right,arrival=len(incoming),merge=len(merges),
                from_lane=[sum(e['from_lane']==g for e in merges) for g in (1,2)],
                to_lane=[sum(e['to_lane']==g for e in merges) for g in (1,2,3,4)],
                endpoint_lane_changes=sum(e['from_lane']!=e['to_lane'] for e in merges)))
        trace=read(I/(prefix+'lane10682_inlet_flux'+seed)/'held_actual_RM_C10681_trace.json.gz')
        receipts=[x['receipt'] for x in trace['lane_interval_receipts']];assert len(receipts)==450
        predicted=[sum(x['lane_receipts'][j]['accepted_merge_veh'] for x in receipts) for j in (0,1)]
        assert abs(sum(predicted)-sum(x['accepted_merge_veh'] for x in receipts))<1e-8
        cases[seed]=dict(windows=windows,native_from_lane=[sum(e['from_lane']==g for e in events) for g in (1,2)],
            native_to_lane=[sum(e['to_lane']==g for e in events) for g in (1,2,3,4)],
            predicted_ramp_receipts_by_lane=predicted,merge_events=events,arrivals=arrivals,lateral=lateral,
            unresolved=unresolved,endpoint=endpoint)
        print(seed,'native_from',cases[seed]['native_from_lane'],'native_to',cases[seed]['native_to_lane'],
            'predicted_port',predicted,'unresolved',len(unresolved),flush=True)
    output.write_text(json.dumps(dict(status='completed_lane_handoff_observation',cases=cases,source_pins=PINS,
        elapsed_sec=time.perf_counter()-started,new_forecasts=0,new_native=0,new_fzp=0,
        limitations=['One-second endpoint transitions bracket crossing and can include an immediate lane change.',
        'These future observations are evaluation only, never predictor lane fractions.',
        'Predicted port lane receipts were then redistributed by the REVIEW52 joint allocator; no exact outgoing joint-lane receipt was exported.']),ensure_ascii=False,indent=2)+'\n',encoding='utf8')


if __name__=='__main__':main()
