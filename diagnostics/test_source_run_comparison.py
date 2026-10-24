from pathlib import Path
import csv,json,tempfile,unittest
from unittest.mock import patch
from diagnostics.live_beta0_first_interval_audit import trace_audit
from diagnostics.compare_source_run import ROOT,road_stats,cell_stats,lever_changes,signature_rows,area_actuation,passage_summary,run_path,comparison_contract,area_window_summary,apply_strict_readback

class SourceRunComparison(unittest.TestCase):
    def test_committed_four_lever_action_uses_canonical_signal_schema(self):
        from evaluation.controllers.signal_timing_oracle import decisions_from_action_rows
        path=ROOT/'diagnostics/area_production_preflight/wu-link_t900_beta0_20260909T225309161773Z/action.csv'
        with path.open(encoding='utf-8-sig',newline='') as stream:rows=list(csv.DictReader(stream))
        self.assertNotIn('cycle_sec',rows[0]);self.assertNotIn('offset_sec',rows[0])
        signature=signature_rows(rows)
        controllers=decisions_from_action_rows(rows)[0]['controllers']
        self.assertEqual(len(controllers),17)
        self.assertEqual(sum(k.startswith('vsl:') for k in signature),66)
        self.assertEqual(sum(k.startswith('ramp:') for k in signature),8)
        for sc,plan in controllers.items():
            self.assertEqual(signature['signal:'+sc]['cycle_sec'],plan['cycle_sec'])
            self.assertEqual(signature['signal:'+sc]['offset_sec'],plan['offset_sec'])
            self.assertGreater(plan['cycle_sec'],0)
        altered=[dict(r) for r in rows]
        next(r for r in altered if r['kind']=='vsl')['speed_kph']='80'
        next(r for r in altered if r['kind']=='ramp_meter')['green_sec']='0'
        axis=next(r for r in altered if r['kind']=='signal');sc=axis['sc_no']
        axis['p1_green']=str(float(axis['p1_green'])+1)
        for row in altered:
            if row['kind'] in ('signal','signal_sg') and row['sc_no']==sc:row['offset']=str(float(row['offset'])+10)
        changes=lever_changes(signature_rows(altered),signature)
        self.assertEqual({key:len(changes[key]) for key in ('VSL','RM','green','offset')},{'VSL':1,'RM':1,'green':1,'offset':1})
        self.assertFalse(changes['cycle'])
    def test_sparse_endpoint_only_readback_cannot_preserve_legacy_pass(self):
        rows=[{'sim_sec':sec,'stage':stage,'sc_no':'1','sg_no':'1','requested_state':'GREEN','readback_state':'GREEN','ok':'1'}
              for sec,stage in [('900','immediate'),('1050','post_step')]]
        self.assertTrue(trace_audit(rows,{}, {'1':5.},start=900,end=1050)['valid'])
        result={'status':'pass','failures':[]}
        apply_strict_readback(result,rows,[],{}, {'1':5.},900,1050)
        self.assertEqual(result['status'],'fail')
        self.assertFalse(result['actuation_trace']['strict_one_second_cadence']['valid'])
    def test_area_slice_preserves_canonical_boundary_events_and_closure(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'diagnostics',prefix='area_window_test_') as d:
            path=Path(d);fields=['sim_sec','interval_sec','inside_vehicles','ttt_veh_h_cumulative','observed_exit_events','terminal_exit_inferred_events','unresolved_inside_disappearances','observed_entry_events','appeared_inside_events']
            with (path/'area_timeseries.csv').open('w',newline='') as stream:
                w=csv.DictWriter(stream,fieldnames=fields);w.writeheader()
                for values in ([1,1,5,1,99,0,0,0,0],[2,1,4,2,1,0,1,1,0],[3,1,3,3,0,1,0,0,0]):w.writerow(dict(zip(fields,values)))
            result=area_window_summary(path,1,3)
            self.assertEqual(result['ttt_veh_h'],2.)
            self.assertEqual(result['ttd_observed_plus_terminal_events'],2)
            self.assertEqual(result['unresolved_inside_disappearances'],1)
            self.assertEqual(result['sampled_stock_closure_residual_veh'],0)
            with self.assertRaises(ValueError):area_window_summary(path,1.5,3)
    def test_matched_comparison_requires_known_same_seed_and_network(self):
        baseline={'manifest':{'seed':13,'network_sha256':'abc'},'last_observed_sec':5400}
        partial={'manifest':{'seed':13,'network_sha256':'abc'},'last_observed_sec':1200}
        self.assertTrue(comparison_contract(partial,baseline)['eligible_matched_comparison'])
        for manifest in ({},{'seed':14,'network_sha256':'abc'},{'seed':13,'network_sha256':'different'}):
            self.assertFalse(comparison_contract({'manifest':manifest},baseline)['eligible_matched_comparison'])
    def test_slow_onset_uses_four_consecutive_30s_samples(self):
        rows=[{'sim_sec':str(t),'link':'40','count':'5','stopped_count':'5','mean_speed_kph':'20'} for t in (30,60,90,120)]
        stats,_=road_stats(rows,[30,60,90,120],30,120,['40']);self.assertEqual(stats['40']['first_sustained_slow_sec'],30.)
        stats,_=road_stats(rows[:-1],[30,60,90,120],30,120,['40']);self.assertIsNone(stats['40']['first_sustained_slow_sec'])
        self.assertAlmostEqual(stats['40']['ttt_30s_veh_h'],5*75/3600)
    def test_zero_stock_zero_speed_does_not_create_congestion(self):
        rows=[{'sim_sec':str(t),'model_link':'FW_E','segment_index':'8','count':'0','stopped_count':'0','mean_speed_kph':'0'} for t in (30,60,90,120)]
        stats,_,_=cell_stats(rows,30,120);self.assertIsNone(stats['FW_E:8']['first_sustained_slow_sec'])
        self.assertIsNone(stats['FW_E:8']['minimum_nonempty_speed_kph'])
    def test_spatial_gap_breaks_sampled_episode(self):
        rows=[{'sim_sec':str(t),'model_link':'FW_E','segment_index':'8','count':'8','stopped_count':'5','mean_speed_kph':'10'} for t in (30,60,120,150,180)]
        stats,_,_=cell_stats(rows,30,180);self.assertFalse(stats['FW_E:8']['episodes'])
    def test_levers_separate_green_offset_and_zero_offset_is_valid(self):
        old={'signal:1':{'cycle_sec':150.,'offset_sec':145.,'p1_green':20.},'ramp:x':{'green_sec':10.},'vsl:x':{'speed_kph':100.}}
        new={'signal:1':{'cycle_sec':150.,'offset_sec':5.,'p1_green':25.},'ramp:x':{'green_sec':5.},'vsl:x':{'speed_kph':80.}}
        result=lever_changes(new,old)
        self.assertEqual({k:len(v) for k,v in result.items()},{'VSL':1,'RM':1,'green':1,'offset':1,'cycle':0})
        self.assertEqual(result['offset'][0]['wrapped_delta_sec'],10.)
        self.assertFalse(any(lever_changes(new,new).values()))
        self.assertFalse(any(lever_changes(new,None).values()))
    def test_physical_meter_encoding_is_not_called_observed_flow(self):
        result=signature_rows([{'kind':'ramp_meter','id':'meter','green_sec':'5','rate_vph':'450'}])
        self.assertEqual(result,{'ramp:meter':{'green_sec':5.}})
    def test_native_baseline_does_not_require_area_scoring_flags(self):
        result=area_actuation(Path('not-a-run'),900,1050,expected_area=False)
        self.assertEqual(result['status'],'native_baseline')
    def test_missing_intermediate_area_decision_remains_a_pending_interval(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'diagnostics',prefix='actuation_series_test_') as d:
            run=Path(d);dec=run/('decisions_'+run.name);dec.mkdir()
            for file in ('action_000900.json','action_001200.json','signal_readback.csv'):(dec/file).write_text('{}',encoding='utf-8')
            (run/f'action_{run.name}.csv').write_text('',encoding='utf-8')
            calls=[]
            def audit(run,a,b,*args):calls.append(a);return {'status':'pending' if a==1050 else 'pass','interval_sec':[a,b]}
            with patch('diagnostics.compare_source_run.read_csv_prefix',return_value=([],{})),patch('diagnostics.compare_source_run.audit_interval',side_effect=audit):result=area_actuation(run,900,1350)
            self.assertEqual(calls,[900,1050,1200]);self.assertEqual(result['status'],'pending')
    def test_final_connector_block_is_excluded_and_observed_inferred_separate(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'diagnostics',prefix='passages_test_') as d:
            path=Path(d);fields=['start_sec','end_sec','connector','source_link','target_link','departures_observed','departures_inferred','departures_total','arrival_events','mean_vehicles','mean_stopped']
            with (path/'physical_connector_passages.csv').open('w',newline='') as f:
                w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
                for a in (900,1050):w.writerow(dict(zip(fields,[a,a+150,'10682','120','121',3,2,5,6,10,8])))
            r=passage_summary(path,900,1200)['10682']
            self.assertEqual(r['departures_observed_veh'],3.);self.assertEqual(r['departures_inferred_veh'],2.);self.assertEqual(r['discharge_vph'],120.)
    def test_run_path_cannot_escape_named_runs(self):
        with self.assertRaises(ValueError):run_path('../../diagnostics')

if __name__=='__main__':unittest.main()
