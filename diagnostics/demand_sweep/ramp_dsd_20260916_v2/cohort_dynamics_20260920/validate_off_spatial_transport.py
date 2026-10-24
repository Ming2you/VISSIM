"""Native lane inventory/entry comparison and frozen prototype provenance."""
from pathlib import Path
import sys,hashlib,statistics,subprocess,math,argparse
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.gain_response_20260919.probe import e,ARMS

HERE=Path(__file__).resolve().parent


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--cumulative',action='store_true');args=parser.parse_args()
    out=HERE/('off_spatial_transport_cumulative_validation_v1.json' if args.cumulative else 'off_spatial_transport_validation_v1.json')
    if out.exists():raise FileExistsError(out)
    directories=['off_spatial_transport_v1','off_spatial_transport_anchor_v1','off_spatial_transport_delay_v1','off_spatial_transport_delay_anchor_v1']
    if args.cumulative:directories+=['off_spatial_transport_cumulative_v1','off_spatial_transport_cumulative_anchor_v1']
    snapshots=[HERE/'off_spatial_transport_v1/source_before_anchor/off_spatial_transport.py.txt',
               HERE/'off_spatial_transport_anchor_v1/source_before_delay/off_spatial_transport.py.txt',
               HERE/'off_spatial_transport_delay_anchor_v1/source_before_cumulative/off_spatial_transport.py.txt']
    archive={hashlib.sha256(p.read_bytes()).hexdigest():str(p.relative_to(e.ROOT)) for p in snapshots}
    checks=0;old=[];all_results={};exact=0
    for directory in directories:
        d=HERE/directory;protocol=e.load(d/'protocol.json');r=e.load(d/'result.json')
        for file,pin in protocol['pins'].items():
            if hashlib.sha256((e.ROOT/file).read_bytes()).hexdigest()!=pin:
                assert Path(file).name=='off_spatial_transport.py' and pin in archive
                old.append(dict(directory=directory,file=file,source_snapshot=archive[pin]))
            checks+=1
        all_results[directory]=r['results']
    pairs=[(directories[2],directories[0]),(directories[3],directories[1])]
    if args.cumulative:pairs+=[(directories[4],directories[0]),(directories[5],directories[1])]
    for current,previous in pairs:
        for arm in ARMS:
            assert e.load(HERE/current/f'prediction_lane_reference_{arm}.json')==e.load(HERE/previous/f'prediction_lane_reference_{arm}.json')
            exact+=1
    verified=subprocess.run([sys.executable,'-B','-X','utf8',str(e.ROOT/'scripts/verify_parameters.py'),
        str(HERE/directories[2]/'config.json')],cwd=e.ROOT,encoding='utf-8',capture_output=True)
    assert verified.returncode==0 and 'PASS' in verified.stdout
    observed={};native_balances=0
    for arm in ARMS:
        file=HERE/('off_space_wave_v2/s23_frames.json' if arm=='none' else f'off_queue_release_controlled_v1/s23_{arm}_frames.json')
        frames={r['time_s']:{vid:(l,p,v) for vid,l,p,v in r['vehicles']} for r in e.load(file)['frames']}
        lane_rows=[]
        for t in range(2400,2850,10):
            for lane in (1,2):
                arrivals=departures=transfers_in=transfers_out=0
                for sec in range(t+1,t+11):
                    a,b=frames[sec-1],frames[sec]
                    arrivals+=sum(b[v][0]==lane for v in b.keys()-a.keys())
                    departures+=sum(a[v][0]==lane for v in a.keys()-b.keys())
                    transfers_in+=sum(a[v][0]!=lane and b[v][0]==lane for v in a.keys()&b.keys())
                    transfers_out+=sum(a[v][0]==lane and b[v][0]!=lane for v in a.keys()&b.keys())
                n0=sum(r[0]==lane for r in frames[t].values());n1=sum(r[0]==lane for r in frames[t+10].values())
                assert n1-n0==arrivals-departures+transfers_in-transfers_out;native_balances+=1
                lane_rows.append(dict(time_s=t,lane=lane,start_n=n0,end_n=n1,arrivals=arrivals,departures=departures,
                    exchange_in=transfers_in,exchange_out=transfers_out,
                    entry_stopped_seconds=sum(any(l==lane and p<6 and v<5 for l,p,v in frames[sec].values()) for sec in range(t,t+10))))
        observed[arm]=lane_rows
    comparison={};model_balances=0;interface_checks=0
    for directory,models in all_results.items():
        comparison[directory]={}
        for arm in ARMS:
            pred=e.load(HERE/directory/f'prediction_spatial_{arm}.json')
            groups={(r['time_s'],r['group']):r for r in pred['lane_groups']['FW_E'] if r['cell']==8}
            ports={r['time_s']:r for r in pred['ports'] if r['connector']=='10643'}
            offers=models['spatial']['summaries'][arm]['offers'];rows=[]
            native={(r['time_s'],r['lane']):r for r in observed[arm]}
            previous=[native[2400,l]['start_n'] for l in (1,2)]
            for offer in offers:
                t=offer['time_s'];end=[]
                for g in (0,1):
                    n=native[t,g+1];admitted=groups[t+10,g]['off_out_veh'];departed=previous[g]-offer['stock'][g]
                    assert departed>=-1e-7
                    after=offer['stock'][g]+admitted;end.append(after)
                    assert abs(after-previous[g]-admitted+departed)<1e-7;model_balances+=1
                    rows.append(dict(**n,predicted_end_n=after,predicted_arrivals=admitted,predicted_departures=departed,
                        offered_arrivals=offer['new'][g]*10/3600,predicted_tail_position=offer['tail'][g]))
                assert abs(sum(end)-ports[t+10]['n_veh'])<1e-7
                previous=end
            summary={}
            for lane in (1,2):
                rs=[r for r in rows if r['lane']==lane]
                summary[str(lane)]=dict(actual_arrivals=sum(r['arrivals'] for r in rs),predicted_arrivals=sum(r['predicted_arrivals'] for r in rs),
                    actual_departures=sum(r['departures'] for r in rs),predicted_departures=sum(r['predicted_departures'] for r in rs),
                    inventory_mae_veh=statistics.mean(abs(r['predicted_end_n']-r['end_n']) for r in rs),
                    entry_count_rmse=math.sqrt(statistics.mean((r['predicted_arrivals']-r['arrivals'])**2 for r in rs)),
                    zero_offer_intervals=sum(r['offered_arrivals']<1e-8 for r in rs),
                    zero_offer_with_actual_entries=sum(r['offered_arrivals']<1e-8 and r['arrivals']>0 for r in rs),
                    actual_internal_exchange=sum(r['exchange_in']+r['exchange_out'] for r in rs))
            comparison[directory][arm]=dict(summary=summary,rows=rows)
            interface_checks+=models['spatial']['summaries'][arm]['checks']['lane_interface_checks']
            for road in pred['diagnostics']['roads']:
                assert road['continuity_residual_max_veh']<1e-7 and road['negative_density_count']==road['jam_density_exceedance_count']==0
            for row in pred['ports']+pred['ramps']:assert abs(row['conservation_residual_veh'])<1e-7
        print(directory,'NC lane2',comparison[directory]['none']['summary']['2'],flush=True)
    assert model_balances==360*len(directories) and interface_checks==360*len(directories) and native_balances==360
    e.save(out,dict(status='PROTOTYPE_CONSERVATION_PASS_GAIN_NOT_QUALIFIED',comparisons=comparison,
        source_pin_checks=checks,archived_sources=old,unchanged_lane_reference_full_json=exact,
        native_lane_balances=native_balances,model_lane_balances=model_balances,lane_interface_checks=interface_checks,
        parameter_check=dict(returncode=verified.returncode,stdout=verified.stdout,stderr=verified.stderr),
        source_pins={str(p.relative_to(e.ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),HERE/'off_spatial_transport.py']},
        caveats=['True inlet capacity is not identified from realized entries alone.',
            'Future native lane exchanges occur even though past exchange rate at initialization is zero; the bounded prototype does not predict them.',
            'Frozen urban-state anchor advances known signals only; no full urban dynamics or green/offset control response validated.',
            'Only one inspected seed/state tested. No12-state/fresh-seed/production qualification.'],
        new_native_runs=0,production_adopted=False,qualified=False))


if __name__=='__main__':main()
