"""Read-only complete LDP prefixes and already saved detector windows; no COM."""
import argparse, ctypes, ctypes.wintypes, hashlib, json, re, sys
from collections import Counter
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
sys.path.insert(0,str(ROOT))
from diagnostics.validate_native_signal_record import parse_ldp_columns

RUNS={'nc':Path('D:/VISSIM_runs/20260927_sd31_wiring9000/nc'),
      'current':Path('D:/VISSIM_runs/20261006_min2_storage90_fixed90_s29_9000/sdmpc')}
GROUPS={1001:list(range(1,9)),1004:list(range(1,9)),9106:[1],9108:[1]}
HEADS={'40_left':('1001:3',[960164]),'40_straight':('1001:8',[960165,960166]),
       '52_straight':('1004:6',[960203,960204,960205]),'52_left':('1004:1',[960206]),
       '10681_meter':('9106:1',[960217,960218]),'10484_meter':('9108:1',[960220])}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--end',type=int,default=5700)
    ap.add_argument('--stock-end',type=int,default=6000)
    ap.add_argument('--current-run',type=Path,default=RUNS['current'])
    ap.add_argument('--output',type=Path,default=HERE/'flows.json')
    args=ap.parse_args()
    assert args.end>=1050 and args.end%150==0
    assert args.stock_end>=args.end and args.stock_end%150==0
    runs=dict(RUNS,current=args.current_run)
    k=ctypes.WinDLL('kernel32',use_last_error=True)
    k.GetCurrentProcess.restype=ctypes.wintypes.HANDLE
    k.SetPriorityClass.argtypes=[ctypes.wintypes.HANDLE,ctypes.wintypes.DWORD]
    assert k.SetPriorityClass(k.GetCurrentProcess(),0x4000)
    assert not args.output.exists()
    out={}
    for arm,run in runs.items():
        name='sdmpc31_'+('nc' if arm=='nc' else 'sdmpc')+'9000_s29'
        frames={t:{} for t in range(1,args.end+1)};pins={}
        for sc,sgs in GROUPS.items():
            p=run/'vissim_eval'/f'{name}_{sc}_001.ldp'
            prefix=[]
            with p.open('rb') as stream:
                for line in stream:
                    match=re.match(rb'\s*(\d+\.\d+)',line)
                    if match and float(match.group(1))>args.end:break
                    prefix.append(line)
            data=b''.join(prefix);parsed=parse_ldp_columns(data,sc,sgs,1,args.end)
            for t,v in parsed['frames'].items():frames[t].update(v)
            pins[str(p)]={'prefix_sha256':hashlib.sha256(data).hexdigest(),'prefix_bytes':len(data)}
        windows=[];stocks={};positions={};d=run/f'decisions_{name}'
        for t in range(150,args.stock_end+1,150):
            s=json.loads((d/f'state_{t:06d}.json').read_bytes());o=s['obs150']
            assert o['window']=={'start_s':t-150,'end_s':t}
            row={'end':t}
            for label,(key,detectors) in HEADS.items():
                row[label]={'head_crossings':sum(o['detectors'][str(x)] for x in detectors),
                            'native_seconds':dict(Counter(frames[i][key] for i in range(t-149,t+1))) if t<=args.end else None}
            for label,detectors in [('10681_arrival',[960276,960277]),('10484_arrival',[960271])]:
                row[label]=sum(o['detectors'][str(x)] for x in detectors)
            windows.append(row)
            records=s['vehicle_records']['records'];stocks[t]={}
            for link in [40,31,124,10698,52,10629,68,10681,10484]:
                rows=[x for x in records if x['link_no']==link]
                stocks[t][link]={'n':len(rows),'stopped':sum(bool(x['stopped']) for x in rows)}
            if t in [2700,3600,4500,5400,6000,args.stock_end]:
                positions[t]={}
                for lane in range(1,5):
                    rows=[x for x in records if x['link_no']==40 and x['lane_no']==lane and x['stopped']]
                    positions[t][lane]={'stopped':len(rows),'min_m':min((x['position_m'] for x in rows),default=None),'max_m':max((x['position_m'] for x in rows),default=None)}
        periods={}
        boundaries=sorted({900,*[x for x in [2700,4500] if 900<x<args.end],args.end})
        intervals=list(zip(boundaries[:-1],boundaries[1:]))
        if (900,args.end) not in intervals:intervals.append((900,args.end))
        for start,end in intervals:
            ws=[w for w in windows if start<w['end']<=end];vals={}
            for label in HEADS:
                c=Counter()
                for w in ws:c.update(w[label]['native_seconds'])
                assert sum(c.values())==end-start
                vals[label]={'native_seconds':dict(c),'head_crossings':sum(w[label]['head_crossings'] for w in ws)}
            for label in ['10681_arrival','10484_arrival']: vals[label]=sum(w[label] for w in ws)
            periods[f'{start}_{end}']=vals
        out[arm]={f'native_prefix_1_{args.end}_complete':True,'prefix_pins':pins,'periods':periods,'windows':windows,'stocks':stocks,'link40_stopped_positions':positions}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    for arm,v in out.items():
        print(arm,json.dumps(v['periods'],ensure_ascii=False))
        print(arm,'positions',v['link40_stopped_positions'][args.stock_end])
        print(arm,'endstocks',v['stocks'][args.stock_end])

if __name__=='__main__':main()
