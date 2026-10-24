"""Infer downstream internal faces from conserved stock and terminal flow.

No new forecasts. Cells24--30 have no side boundaries in this pinned geometry.
Native internal faces are balance-derived, not independent detector readings.
"""
import argparse,json
from pathlib import Path
from assess import ROOT,HERE,digest,read
from evaluation.controllers import offramp_routing as routing

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    target=a.out/'recovery_balance.json';assert not target.exists()
    source=a.out/'matched_assessment.json';d=read(source)
    path=ROOT/read(HERE/'legacy_urban_diagnostic_config.json')['freeway']['offramp_route_inventory']
    doc=read(path);r=routing.compile_inventory(doc,json.loads(routing._pinned(doc['mapping'])))
    assert not any(v['freeway']=='FW_E' and v['cell']>=24 for v in r['merges'].values())
    assert not any(v['freeway']=='FW_E' and v['source_cell']>=24 for v in r['branches'].values())
    report={}
    for arm,frames in d['physical31_snapshots'].items():
        rows=[]
        for i,(before,after) in enumerate(zip(frames,frames[1:])):
            item={'start_sec':before['time_sec'],'end_sec':after['time_sec']}
            for kind,flow_kind in [('actual','actual'),('predicted','predicted')]:
                n0=before[kind]['n']['FW_E'];n1=after[kind]['n']['FW_E']
                dn=[y-x for x,y in zip(n0,n1)];terminal=d['flows'][arm]['chain_end:FW_E'][flow_kind][i]
                q25=terminal+sum(dn[26:]);q23=terminal+sum(dn[24:])
                assert min(q23,q25)>=0
                stock=sum(dn[24:26]);assert abs(q23-q25-stock)<1e-8
                item[kind]=dict(through23=q23,through25=q25,stock_change24_25=stock,
                    end_stock24_25=sum(n1[24:26]),end_speed24_25=after[kind]['speed']['FW_E'][24:26])
            item['errors_model_minus_native']={k:item['predicted'][k]-item['actual'][k]
                for k in ('through23','through25','stock_change24_25','end_stock24_25')}
            rows.append(item)
        report[arm]=rows
    summary=dict(seed=d['seed'],by_arm=report,new_predictions=0,new_native=0,fits=0,
        scope=__doc__,caveats=['Native detector is1m from the terminal; inferred internal faces include that boundary-position discrepancy.',
        'Inventory changes identify incoming/outgoing imbalance, not an independent causal effect of a speed coefficient.',
        'Current FW5/U10 forecast excludes native348 urban projection recipe. No model changes selected.'],
        pins={str(p):digest(p) for p in (Path(__file__),source,path)})
    target.write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps({'seed':d['seed'],'rows':{arm:[row['errors_model_minus_native'] for row in rows] for arm,rows in report.items()}},indent=2))

if __name__=='__main__':main()
