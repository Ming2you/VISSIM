"""Small synthetic guards, prepared without any FZP/model/simulator execution."""
from collections import defaultdict
from copy import deepcopy
import gzip
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from diagnostics import analyze_fixed_route_arm_windows as a


class SpatialWindowTests(unittest.TestCase):
    def test_conditional_denominator_is_observed_stem_not_all_gate_outlets(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp);network=folder/'network.inpx';cache=folder/'frames.json.gz'
            network.write_text('<network><vehicleRoutingDecisionsStatic>'+''.join(
                f'<vehicleRoutingDecisionStatic no="{d}" link="{s}" pos="10"/>'
                for d,s in ((1123,52),(1124,66),(1125,46)))+'</vehicleRoutingDecisionsStatic></network>',encoding='utf-8')
            frames={750:{1:[52,1,0,50],2:[52,1,0,50]},751:{1:[52,1,20,50],2:[52,2,20,50]},
                    752:{1:[10629,1,1,50],2:[10646,1,1,50]},
                    753:{1:[10646,1,1,50],2:[120,1,1,50]},754:{1:[120,1,1,50],2:[120,1,2,50]}}
            with gzip.open(cache,'wt',encoding='utf-8') as stream:json.dump(frames,stream)
            doc={'window':[750,754],'network_path':str(network),'network_sha256':a.sha(network),
                'head_geometry':{'71':{'heads':[]}},'run':{'run':'synthetic','fzp':{
                    'selected_cache':str(cache),'selected_cache_sha256':a.sha(cache)},
                    'road_entries':[],'road_exits':[],'sg71_summary':{},'green_windows':{}}}
            mapping=[{'parent_decision':str(d),'new_route':str(r),'old_downstream_route':str(r-2),
                      'path':[str(s),str(c)],'conditional_branch_probability':'0.6' if r==4 else '0.2'}
                     for d,s,c in ((1123,52,10629),(1124,66,10633),(1125,46,10625)) for r in (4,5,6)]
            # A dynamic decision with the same number is not a static choice.
            observations=defaultdict(list,{1:[{'sec':753,'type':'DYNAMIC','decision':1123,'route':4}]})
            proof={'source_sha256':{},'missing_snapshot_seconds':[]}
            with patch.object(a,'route_observations',return_value=(observations,proof)):
                result=a.summarize_window(doc,mapping,[])
            row=result['decision_summary']['1123']
            self.assertEqual(row['observed_unique_gate_cohort'],2)
            self.assertEqual(row['all_gate_outcomes'],{'outlet:10646':2})
            self.assertEqual(row['observed_replacement_stem_entries'],1)
            self.assertEqual(row['resolved_stem_outlet_denominator'],1)
            self.assertEqual(row['physical_outlet_fractions_among_resolved_stem']['10646'],1)
            self.assertEqual(row['observed_current_newroute_counts'],{})
            self.assertTrue(result['decision_cohorts'][1]['lane_change_at_gate'])
            self.assertEqual(result['stock71']['residual'],0)

    def test_incomplete_batch_fails_before_any_native_read(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp);path=folder/'manifest.json'
            path.write_text(json.dumps({'schema':'fixed-beta300v3-three-arm-experiment/v1',
                'status':'running','completed':False,'valid':False,'source_changes':[]}),encoding='utf-8')
            with patch.object(a,'ROOT',folder), self.assertRaisesRegex(ValueError,'Completed three-arm'):
                a.qualify_batch(path)
        # Metadata-only certificate checks: no native trajectory file is opened.
        record={'header':'$VEHICLE:SIMSEC;NO','payload_sha256':'a'*64,'payload_bytes':100,
                'rows':10,'first_sec':1,'last_sec':1050,'file_sha256':'b'*64,'file_bytes':200}
        actual={**record,'path':'evaluation/runs/new/vissim_eval/result.fzp'}
        old={**record,'path':'evaluation/runs/old/vissim_eval/result.fzp'}
        proof={'schema':'fixed-beta300v3-baseline-trajectory/v1','valid':True,'terminal1050_valid':True,
               'ordered_payload_exact':True,'reference_unchanged_since_preflight':True,'different_fields':[],
               'compared_fields':['header','payload_sha256','payload_bytes','rows','first_sec','last_sec'],
               'actual':actual,'reference':old,'source_run':'old','provenance_sha256':{
                   'evaluation/runs/new/run_provenance_new.json':'c'*64,'evaluation/runs/old/run_provenance_old.json':'d'*64}}
        manifest={'arms':[{'run':'evaluation/runs/new','name':'new','baseline_trajectory_comparison':proof}],
                  'baseline_trajectory_reference':{'run':'evaluation/runs/old','source_run':'old','fzp':old['path'],
                      'fzp_sha256':'b'*64,'provenance_sha256':'d'*64}}
        self.assertEqual(a.baseline_trajectory_certificate(manifest),proof)
        for key,value in (('valid',False),('actual',{**actual,'rows':11}),('compared_fields',[]),
                          ('reference',{**old,'path':actual['path']})):
            bad=deepcopy(manifest);bad['arms'][0]['baseline_trajectory_comparison'][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):a.baseline_trajectory_certificate(bad)

    def test_duplicate_command_value_rejected(self):
        with self.assertRaisesRegex(ValueError,'repeated'):
            a.command_value(['-Network','a','-Network','b'],'-Network')


if __name__=='__main__':unittest.main()
