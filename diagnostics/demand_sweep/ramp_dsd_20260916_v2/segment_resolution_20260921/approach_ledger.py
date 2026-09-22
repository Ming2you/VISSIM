"""Reconstruct consumed allocations after completed forecasts; no model change."""
import gzip,json
from collections import defaultdict
from pathlib import Path
import vsl_response as v
from prepare import save,table
c=v.c;f=v.f;B=v.B;ROOT=v.ROOT;O=B/'approach_resolution_v1'


def main():
    cells=[];parts=[];checks=[]
    for arm in ('none','vsl'):
        with gzip.open(O/'ar_limits'/f'limits_{arm}.json.gz','rt',encoding='utf-8') as stream:trace=json.load(stream)
        p=f.load_prediction(O/'ar_limits'/f'refined_guard1_{arm}.json')
        reference=f.load_prediction(O/'ar_baseline'/f'refined_guard1_{arm}.json')
        assert p==reference,'Read-only observer changed the entire prediction'
        bytime={(r['time_s'],r['cell'],r['group']):r for r in p['lane_groups']['FW_E']}
        assert [r['time_s'] for r in trace]==list(range(2400,2850))
        totals=defaultdict(lambda:defaultdict(float));ptotals=defaultdict(lambda:defaultdict(float))
        for row in trace:
            t=row['time_s'];s=row['cells'];phase=(t-2400)//150
            for i,m in enumerate(s['matrices']):
                calculated=[0.]*len(m)
                for k in range(len(s['before'][i+1])):
                    requested=sum(s['after_fifo'][i][g]*w[k] for g,w in enumerate(m))
                    factor=min(1.,s['receiving_after_ramp'][i+1][k]/requested) if requested else 0.
                    for g,w in enumerate(m):calculated[g]+=s['after_fifo'][i][g]*w[k]*factor
                assert max(abs(a-b) for a,b in zip(calculated,s['outgoing'][i]))<1e-9
                continuity=sum(s['end_n'][i])-sum(s['before'][i])-sum(s['incoming'][i])+sum(s['outgoing'][i])+sum(s['off_out'][i])
                assert abs(continuity)<1e-7
                for g,w in enumerate(m):
                    record=bytime[t+1,i,g]
                    assert abs(record['mainline_out_veh']-s['outgoing'][i][g])<1e-10
                    assert abs(record['n_veh']-s['end_n'][i][g])<1e-10
                    eligible=s['after_fifo'][i][g]*sum(w)
                    assert eligible-s['outgoing'][i][g]>=-1e-10
                    r=totals[phase,i,g]
                    r['initial_sending']+=s['through_requests'][i][g]
                    r['after_fifo']+=s['after_fifo'][i][g]
                    r['unconnected']+=s['after_fifo'][i][g]-eligible
                    r['receiving_lost']+=eligible-s['outgoing'][i][g]
                    r['outgoing']+=s['outgoing'][i][g]
                    r['start_stock_sum']+=s['before'][i][g]
            port=row['ports']['10643'];i=port['cell'];partition=s['partitions_before'][str(i)]
            access=c.S['off_access']['10643']['weights']
            for g in range(len(port['request_veh'])):
                pre=s['pre_through'][str(i)][g];after=pre*port['fifo'][g];actual=s['cross'][str(i)][g]
                assert pre-after>=-1e-9 and after-actual>=-1e-9
                r=ptotals[phase,g]
                r['pre_through_requested']+=pre;r['fifo_lost']+=pre-after
                r['post_receiving_lost']+=after-actual;r['pre_to_post']+=actual
                r['off_request']+=port['request_veh'][g]
                r['off_accessible_request']+=port['request_veh'][g] if access[g] else 0.
                r['off_sent']+=port['accepted_veh'][g]
                r['pre_stock_sum']+=partition['pre_n'][g]
        cells.extend(dict(arm=arm,start_s=2400+phase*150,end_s=2550+phase*150,cell=i,group=g,**dict(r)) for (phase,i,g),r in totals.items())
        parts.extend(dict(arm=arm,start_s=2400+phase*150,end_s=2550+phase*150,group=g,**dict(r)) for (phase,g),r in ptotals.items())
        checks.append(dict(arm=arm,entire_prediction_exact=True,steps=len(trace),external_cells_reconstructed=len(s['matrices'])*len(trace)))
    table(O/'ledger_cells.csv',cells);table(O/'ledger_partition10643.csv',parts)
    summary={}
    for arm in ('none','vsl'):
        summary[arm]={}
        for i in (5,6,7,8,9):
            rows=[r for r in cells if r['arm']==arm and r['cell']==i]
            summary[arm][str(i)]={k:sum(r[k] for r in rows) for k in ('initial_sending','after_fifo','unconnected','receiving_lost','outgoing')}
        rows=[r for r in parts if r['arm']==arm]
        summary[arm]['partition10643']={k:sum(r[k] for r in rows) for k in ('pre_through_requested','fifo_lost','post_receiving_lost','pre_to_post','off_request','off_accessible_request','off_sent')}
    pins=[]
    for filename,key in [('protocol.json','source_pins'),('resume_protocol.json','source_pins'),('ledger_protocol.json','sources'),('capacity_protocol.json','source_pins')]:
        for path,digest in c.load(O/filename)[key].items():
            resolved=ROOT/path
            if c.sha(resolved)!=digest:
                archive=O/('run_before_ledger.py.txt' if resolved.name=='run.py' else 'source_before_empty_check_fix.py.txt')
                assert c.sha(archive)==digest,(path,digest);resolved=archive
            pins.append(dict(protocol=filename,path=path,resolved=str(resolved.relative_to(ROOT)),sha256=digest))
    prior=c.load(B/'distribution_response_v1/completion.json')
    assert c.sha(O/'before_run.py.txt')==prior['source_pins'][str((B/'run.py').relative_to(ROOT))]
    for path,digest in c.load(B/'distribution_response_v1/verification.json')['core_hashes_unchanged'].items():assert c.sha(ROOT/path)==digest
    results=c.load(O/'results_resume.json')['results']
    assert len(results)==3 and all(z['passed'] for r in results for z in r['numerics'].values())
    assert results[0]['exact_default_arms']==list(f.ARMS)
    ablations=c.load(O/'capacity_results.json')['results']
    assert len(ablations)==3 and all(z['passed'] for r in ablations for z in r['numerics'].values())
    effective=0
    for label in ['baseline','cell7','cells5_7','no_ctm','no_operational_loss','neither','limits']:
        folder=O/('ar_'+label);spec=c.load(O/('ar_'+label+'.json'))
        receipt=c.load(folder/'refined_guard1_receipt.json')
        assert receipt['completed'] and not receipt['future_inputs'] and receipt['fit']==spec
        assert receipt['forecasts']==len(spec['arms'])
        cfgs=c.load(folder/'effective_config.json');assert [r['arm'] for r in cfgs]==spec['arms']
        for row in cfgs:
            assert row['scalar']==spec['physical_coefficients'] and row['state_response']['FW_E']==spec['state_response']
            assert row['receiving']['FW_E']==spec['hadiuzzaman'] and row['port_response']['FW_E']==spec['port_response']
            effective+=1
    assert effective==26
    save(O/'ledger_summary.json',summary)
    save(O/'verification.json',dict(checks=checks,source_pins=pins,core4_unchanged=True,
        four_original_default_predictions_exact=True,two_observed_entire_predictions_exact=True,
        forecasts_completed=26,effective_configs_checked=effective,new_native=0,qualified=False,adopted=False,all_owned_calculations_terminal=True))
    print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
