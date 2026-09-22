"""After all native runs: common prefixes, geometric edge costs and removals."""
from pathlib import Path
from collections import Counter,defaultdict
import hashlib,json,sys,datetime
import vsl_strength as s
c=s.c;B=s.B;O=s.O;ROOT=s.ROOT


def edge_prefix(path):
    start=path.stat();digest=hashlib.sha256();prefix={t:hashlib.sha256() for t in (2400,2550)}
    chain={r['link']:r['offset_m'] for r in c.G['chains']['FW_E']};length=c.G['bounds']['FW_E'][-1]
    seconds=Counter();extras=Counter();times=set()
    with path.open('rb') as stream:
        for raw in stream:
            digest.update(raw)
            if not raw[:1].isdigit():continue
            t=float(raw.split(b';',1)[0]);assert t.is_integer()
            if t%5:continue
            a=raw.rstrip(b'\r\n').split(b';');assert len(a)==20
            for end,h in prefix.items():
                if t<=end:h.update(b';'.join(a[:9])+b'\n')
            if not 2400<t<=3000:continue
            times.add(int(t));link=int(a[2])
            if link not in chain:continue
            x=chain[link]+float(a[4]);outside=not 0<=x<length
            for lo,hi in s.native.WINDOWS:
                if lo<t<=hi:
                    seconds[lo,hi]+=5
                    if outside:extras[lo,hi]+=5
    end=path.stat();assert (start.st_size,start.st_mtime_ns)==(end.st_size,end.st_mtime_ns)
    assert times==set(range(2405,3001,5))
    return dict(sha256=digest.hexdigest(),prefixes={str(t):h.hexdigest() for t,h in prefix.items()},
        windows={f'{a}-{b}':dict(mainline_link_ttt=seconds[a,b]/3600,excluded_edge_ttt=extras[a,b]/3600) for a,b in s.native.WINDOWS})


def main():
    comparison=c.load(O/'native_comparison.json');frozen=c.load(O/'frozen_predictions.json')
    reference=s.v.O/'upstream_native';results={};edge={};errors={};conservation=[]
    for label,file in [('none','none_summary.json'),('both100','both_zones_summary.json'),('up100','upstream_only_summary.json'),('both80','both80_summary.json'),('up80','up80_summary.json')]:
        summary=c.load((reference if label in ('none','both100','up100') else O)/file);results[label]=summary
        path=ROOT/summary['path'];audit=edge_prefix(path);assert audit['sha256']==summary['sha256']
        assert audit['prefixes']['2400']==summary['prefix_sha256'];edge[label]=audit
        for lo,hi in s.native.WINDOWS:
            value=next(r['ttt_veh_h'] for r in summary['rows'] if r['zone']=='mainline' and r['start']==lo and r['end']==hi)
            assert abs(value-audit['windows'][f'{lo}-{hi}']['mainline_link_ttt'])<1e-10
            initial=summary['initial']['before_exit_400_1305'] if lo==2400 else summary['final'][str(lo)]['before_exit_400_1305']
            final=summary['final'][str(hi)]['before_exit_400_1305']
            crossing=lambda x:next(r['crossings'] for r in summary['flows'] if r['start']==lo and r['end']==hi and r['point']==x)
            entered,left=crossing(400.),crossing(1305.38870368)
            assert initial+entered-left==final
            conservation.append(dict(arm=label,start=lo,end=hi,initial=initial,entered=entered,left=left,final=final,residual=0))
        parsed=c.load(O/(label+'_errors.json'));events=[r for file in parsed for r in file['events']]
        assert not any(file['unparsed_removal_lines'] for file in parsed)
        removed=[r for r in events if (r['kind']=='lane_change_removal' or r.get('explicitly_says_removed') is True) and 2400<float(r.get('time_sec',-1))<=3000]
        component=set(s.native.old.CHAIN)|set(s.native.old.ON)|set(s.native.old.OFF)
        inside=[r for r in removed if int(r['link']) in component]
        errors[label]=dict(east_component_removals=len(inside),all_network_removals=len(removed),
            removed_by_link=dict(Counter(r['link'] for r in removed)),
            unfinished_input_rows=[r for r in events if r['kind']=='unfinished_vehicle_input'],
            limitation='Unfinished inputs include demand after the3000s stop of the saved9001s scenario; not all are already-arrived insertion failures. Whole-network urban removals prevent an unqualified full-Omega attribution.')
    assert edge['both80']['prefixes']['2550']==edge['both100']['prefixes']['2550']
    assert edge['up80']['prefixes']['2550']==edge['up100']['prefixes']['2550']
    output=[]
    for row in comparison['compare']:
        label=row['policy'];interval='2400-2850'
        extra=edge[label]['windows'][interval]['excluded_edge_ttt']-edge['none']['windows'][interval]['excluded_edge_ttt']
        actual={k:row['actual']['delta_'+k] for k in ('mainline','on','off')};actual['mainline']-=extra
        actual['total']=sum(actual.values());pred=row['predicted']
        output.append(dict(policy=label,actual_geometric_delta=actual,predicted_common5s_delta=pred,
            error={k:pred[k]-actual[k] for k in actual},excluded_mainline_edge_delta=extra))
    s.save(O/'edge_audit.json',edge);s.save(O/'error_audit.json',errors);s.save(O/'local_conservation.json',conservation)
    s.save(O/'qualified_scope_comparison.json',dict(results=output,passed_execution_and_bookkeeping=True,
        gain_prediction_qualified=False,model_frozen_before_new_native=True,new_policy_prefix_through2550_exact=True,
        scope='Geometric east mainline + four on/four off connectors;5s right-endpoint residence, not full Omega.',
        exclusions='Negative-source-position or past-terminal-position mainline vehicles excluded to match modeled geometry; same full-link costs also retained.',
        independent_seed=False,production_adopted=False))
    print(json.dumps(dict(results=output,removals={k:(v['east_component_removals'],v['all_network_removals']) for k,v in errors.items()}),indent=2))


def verify():
    """Verify the completed experiment without rerunning forecasts or native."""
    frozen=c.load(O/'frozen_predictions.json');pins=[]
    for filename in ('protocol.json','frozen_predictions.json'):
        for path,digest in c.load(O/filename)['source_pins'].items():
            resolved=ROOT/path
            if s.sha(resolved)!=digest:
                assert filename=='protocol.json' and resolved==B/'vsl_strength.py'
                resolved=O/'source_before_cost5s.py.txt'
            assert s.sha(resolved)==digest
            pins.append(dict(protocol=filename,path=path,resolved=str(resolved.relative_to(ROOT)),sha256=digest))
    older=c.load(B/'approach_resolution_v1/completion.json')['source_pins']
    assert s.sha(O/'before_run.py.txt')==older[str((B/'run.py').relative_to(ROOT))]
    core=c.load(B/'distribution_response_v1/verification.json')['core_hashes_unchanged']
    for path,digest in core.items():assert s.sha(ROOT/path)==digest
    ref_effective=c.load(s.v.O/'vr_hadi_fd_cap_r2_validation/effective_config.json')
    ref_effective={r['arm']:r for r in ref_effective}
    predictions={};configs=0;defaults=0
    for item in frozen['predictions']:
        label=item['policy'];folder=O/('vs_'+label)
        for path,digest in item['prediction_pins'].items():assert s.sha(ROOT/path)==digest
        receipt=c.load(folder/'refined_guard1_receipt.json')
        assert receipt['completed'] and receipt['forecasts']==2 and not receipt['future_inputs']
        assert receipt['runner_sha256']==s.sha(B/'run.py')
        for entry in c.load(folder/'effective_config.json'):
            assert entry==ref_effective[entry['arm']];configs+=1
        for arm in ('none','vsl'):
            p=s.f.load_prediction(folder/f'refined_guard1_{arm}.json')
            reference=s.f.load_prediction(s.v.O/'vr_hadi_fd_cap_r2_validation'/f'refined_guard1_{arm}.json')
            if arm=='none' or label=='both100':assert p==reference;defaults+=1
            for key in ('cells','flows'):
                assert [r for r in p[key] if r['road']=='FW_W']==[r for r in reference[key] if r['road']=='FW_W']
            assert c.screen(p)['passed']
            assert s.sampled_costs(p)==item['values_common5s'][arm]
            if arm=='vsl':predictions[label]=p
    prefixes=[]
    for stronger,base in (('both80','both100'),('up80','up100')):
        p,q=predictions[stronger],predictions[base]
        for key,time in (('cells','time_s'),('flows','window_end_s'),('ramps','end_sec'),('ports','time_s')):
            assert [r for r in p[key] if r[time]<=2550]==[r for r in q[key] if r[time]<=2550]
        for road in p['lane_groups']:
            assert [r for r in p['lane_groups'][road] if r['time_s']<=2550]==[r for r in q['lane_groups'][road] if r['time_s']<=2550]
        prefixes.append(dict(stronger=stronger,reference=base,state_and_flow_prefix_through2550_exact=True))
    runs=[]
    for name in ('both80','up80'):
        folder=O/name/'run';r=c.load(folder/'run.json');a=c.load(folder/'fixed_validation.json')
        assert r['completed'] and r['exit_code']==0 and not r['owned_native_alive'] and r['terminal_sec']==3000
        assert a['passed'] and not a['unrecorded_signal_groups']
        assert a['untargeted_snapshot_sha256_before']==a['untargeted_snapshot_sha256_after']
        assert datetime.datetime.fromisoformat(r['started'])>datetime.datetime.fromisoformat(frozen['frozen_at_utc'])
        runs.append(dict(policy=name,completed=True,wall_seconds=(datetime.datetime.fromisoformat(r['finished'])-datetime.datetime.fromisoformat(r['started'])).total_seconds(),
            event_readbacks=a['event_readbacks'],signal_snapshot_addresses=a['snapshot_addresses'],native_ldp_samples=a['native_ldp_sample_count'],all_owned_native_terminal=True))
    out=dict(source_pins=pins,core4_hashes_unchanged=core,effective_config_entries_checked=configs,
        existing_entire_predictions_exact=defaults,west_predictions_exact=8,model_prefixes=prefixes,
        native_runs=runs,completed_forecasts=8,new_native=2,qualified=False,production_adopted=False)
    s.save(O/'verification.json',out)
    print(json.dumps({k:v for k,v in out.items() if k not in ('source_pins','core4_hashes_unchanged')},indent=2))


if __name__=='__main__':
    {'analyze':main,'verify':verify}[sys.argv[1] if len(sys.argv)>1 else 'analyze']()
