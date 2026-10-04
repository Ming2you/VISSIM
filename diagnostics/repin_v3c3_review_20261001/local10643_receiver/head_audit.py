"""Reuse native MER and signal clocks for completed evaluation windows."""
import hashlib
import json
from pathlib import Path
from evaluation.controllers import lane_plant_runtime as lpr, obs150_contract as oc
from evaluation.controllers import obs150_head_window as heads, obs150_signal_clock as signals

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]

def main():
    target=HERE/'head_audit.json'
    if target.exists():raise FileExistsError(target)
    config=json.loads((HERE.parent/'unrouted10646/candidate_config.json').read_bytes())
    context=lpr.load_sources(config['freeway']['lane_plant'])
    evidence=json.loads((HERE/'native_audit.json').read_bytes())
    result={};pins={}
    for path in evidence['source_pins']:
        p=Path(path)
        if p.name not in ('frame_002400.json','frame_002550.json','frame_002700.json',
                          'frame_002850.json','frame_003000.json','frame_003150.json'):
            continue
        case=('43nc' if 'seed43' in path else '47selected' if 'selected' in p.parts else '47hold')
        t=int(p.stem.split('_')[1])
        if case!='43nc' and t==2700:continue
        rawpath=p.parent.parent/('state_'+p.stem.split('_')[1]+'.json')
        rawbytes=rawpath.read_bytes();pins[str(rawpath)]=hashlib.sha256(rawbytes).hexdigest()
        raw=json.loads(rawbytes);obs=raw['obs150']
        bundle=oc.load_bundle(raw)
        clocks=signals.windows(obs['signal_log'],context['obs150'].sig_table,obs['window'],
            network_dir=Path(raw['network_path']).parent,programless_scs=context['obs150'].programless_scs)
        window=heads.build(raw,context['obs150'],clocks,bundle.mer_rows,bundle=bundle)
        selected=[h for h in window['heads'] if h['link']=='71']
        assert len(selected)==5 and window['clock_complete']
        assert all(h['unverified_sec']==0 for h in selected)
        result.setdefault(case,[]).append(dict(start_sec=window['start_sec'],end_sec=t,
            heads=selected,clocks={k:v for k,v in clocks.items() if k in ('1004-2','1004-5')}))
    assert {case:len(rows) for case,rows in result.items()}=={'43nc':3,'47hold':3,'47selected':3}
    pins.update({str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in context['paths'].values()})
    doc=dict(status='NATIVE_HEAD_AND_GREEN_WITNESSES_COMPLETE',cases=result,source_pins=pins,
             note='Completed native MER/head and signal clocks only; not forecast inputs or a fitted service law.')
    target.write_text(json.dumps(doc,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    for case,rows in result.items():
        print(case,[(r['start_sec'],sum(h['qualified_crossings'] for h in r['heads'] if h['lane']<=3),
            sum(h['qualified_crossings'] for h in r['heads'] if h['lane']>=4)) for r in rows])

if __name__=='__main__':main()
