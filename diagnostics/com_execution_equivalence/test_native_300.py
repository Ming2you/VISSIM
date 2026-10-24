"""Receipt-free 300s qualifier, synthetic artifacts only; no native/model access."""
import csv
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from diagnostics.com_execution_equivalence import verify_pair as v
from diagnostics.com_execution_equivalence.test_verify_pair import command, save, table, ACTION_FIELDS
from diagnostics.test_native_signal_record import ldp


class Native300Test(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.root = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)
        self.patch = patch.object(v, 'ROOT', self.root); self.patch.start(); self.addCleanup(self.patch.stop)
        self.prep = self.root / 'diagnostics/com_execution_equivalence/native_all_sg_300_v1'
        self.prep.mkdir(parents=True)
        self.source = self.root / 'network.inpx'; self.source.write_text('synthetic network')
        self.config = self.root / 'generated.vbs'
        self.config.write_text('RW_RAMP_METER_SCS = "'+','.join(str(s) for s in range(9101,9109))+'"\n'
            'RW_RAMP_METER_CAPACITIES_VPH = "'+','.join(['900']*8)+'"\n')
        self.runner = self.root / 'runner.vbs'
        self.runner.write_text('Const RAMP_CYCLE_SEC = 10\nConst RAMP_AMBER_SEC = 1\nConst AMBER_SEC = 3\n')
        self.groups = {str(sc): {str(sg): int(sg != 8 or sc > 14) for sg in range(1,9)} for sc in range(1,18)}
        self.plan = self.root / 'generated_sgplan.vbs'
        self.plan.write_text('RW_SIGNAL_SG_EXPECTED = "'+','.join(f'{sc}:{sg}:{n}' for sc,gs in self.groups.items() for sg,n in gs.items())+'"\n')
        records = [{'sc_no': int(sc), 'sg_no': int(sg), 'kind': 'urban', 'windows': n, 'red_only': n == 0}
                   for sc,gs in self.groups.items() for sg,n in gs.items()]
        records += [{'sc_no': sc, 'sg_no': 1, 'kind': 'meter', 'windows': 1, 'red_only': False} for sc in range(9101,9109)]
        self.values = {f"{r['sc_no']}:{r['sg_no']}": 'RED' if r['red_only'] else 'GREEN' for r in records}
        record_path = self.prep / 'recorded_groups.json'; save(record_path, records)
        self.mapping = self.root / 'mapping.json'
        save(self.mapping, {'segments': [{'dsd_by_lane': {'1': {'dsd_no': 7}}, 'extra_dsd_controls': [{'dsd_no': 8}]}]})
        save(self.prep / 'preflight.json', {'schema': 'native-all-controlled-sg-recording-fixture/v1', 'prepared': True,
            'network': str(self.source), 'network_sha256': v.sha(self.source),
            'actual_plan': {'path': str(self.plan), 'sha256': v.sha(self.plan), 'RW_MAINLINE_SG_ONLY': '1'},
            'recorded_groups_path': str(record_path), 'recorded_groups_sha256': v.sha(record_path)})
        self.a = self.root / 'old'; self.b = self.root / 'fast'
        self.make_run(self.a, False); self.make_run(self.b, True)

    def make_run(self, run, fast):
        run.mkdir(); folder = run / ('decisions_'+run.name); folder.mkdir()
        native = run / 'vissim_eval'; native.mkdir()
        entry = lambda p: {'path': str(p), 'exists': True, 'sha256': v.sha(p)}
        prov = {'name': run.name, 'run_id': run.name+'-uuid', 'seed': 13, 'sim_period_sec': 300,
            'control_interval_sec': 150, 'state_log_interval_sec': 1, 'demand_scale': 1,
            'controller': 'diagnostic-signal-profile', 'audit_anchors_sec': '',
            'signal_observation': {'options': {'enabled': True}},
            'files': {**{k: entry(self.source) for k in ('network','tuning','demand_profile')},
                'control_mapping': entry(self.mapping), 'main_vbs_runner': entry(self.runner), 'generated_vbs_config': entry(self.config)},
            'controller_sources': [entry(self.runner)], 'signal_programs': [entry(self.plan)],
            'env': {'RW_SIGNAL_OBSERVATION': '1', 'RW_MAINLINE_SG_ONLY': '1',
                'RW_SIGNAL_WRITE_ON_CHANGE': '1' if fast else '0', 'RW_SIGNAL_READBACK_SEC': '0' if fast else '1'}}
        save(run / ('run_provenance_'+run.name+'.json'), prov)
        (run / ('runlog_'+run.name+'.txt')).write_text('STAGE=SIM_DONE\nSIM_SEC=300\n'+'\n'.join(k+'=0' for k in v.FAILURE_COUNTERS)+'\n')
        (native/'network.fzp').write_text('* metadata '+run.name+'\n$VEHICLE:SIMSEC;NO;SPEED\n'+''.join(f'{t}.00;1;20.00\n' for t in range(1,301)))
        rows = []
        for sc,gs in self.groups.items():
            rows.append(command('signal', sc_no=sc, p1_green=150, p2_green=0, p3_green=0, p4_green=0, offset=0))
            rows += [command('signal_sg', sc_no=sc, dsd_no=sg, p1_green=0, p2_green=150, green_sec=150, offset=0) for sg,n in gs.items() if n]
        rows += [command('ramp_meter', sc_no=sc, green_sec=10, rate_vph=900) for sc in range(9101,9109)]
        rows += [command('vsl', dsd_no=dsd, speed_kph=120) for dsd in (7,8)]
        for t in (1,150,300): table(folder/f'action_{t:06d}.csv', ACTION_FIELDS, rows)
        table(folder/'vsl_readback.csv', v.VSL_FIELDS, [(t,dsd,cls,120,120,1,'immediate') for t in (1,150,300) for dsd in (7,8) for cls in (10,20,30,70)])
        def signal_rows():
            for t in range(1,301):
                stages = (['post_step'] if t > 1 and (not fast or t in (2,150,300)) else [])
                stages += ['immediate'] if not fast or t == 1 else []
                for stage in stages:
                    for key,value in self.values.items():
                        sc,sg = key.split(':'); yield (t,sc,sg,value,value,1,stage)
        table(folder/'signal_readback.csv', v.SG_FIELDS, signal_rows())
        (native/'network.lsa').write_text('Signal Changes Protocol\n'+''.join(f'1;0;{key.replace(":",";")};{value};1;COM;0;\n' for key,value in self.values.items()))
        for sc in [*map(int,self.groups),*range(9101,9109)]:
            gs = list(map(int,self.groups[str(sc)])) if str(sc) in self.groups else [1]
            symbols = ''.join('.' if self.values[f'{sc}:{sg}']=='RED' else 'I' for sg in gs)
            (native/f'network_{sc}_001.ldp').write_bytes(ldp(sc,gs,[(t,symbols) for t in range(1,301)]))
        (native/'network_99999_001.ldp').write_text('Unselected native header-only file')

    def verify(self): return v.qualify_native_300(self.a, self.b)

    def test_all144_records_pass_without_claiming_process_receipt(self):
        out = self.verify(); self.assertTrue(out['passed'], out['checks'])
        self.assertTrue(out['recorded_execution_equivalent']); self.assertFalse(out['process_exit_verified'])
        self.assertFalse(out['actual_execution_equivalent']); self.assertFalse(out['completion_receipt_verified'])
        self.assertEqual(out['checks']['native_ldp_pair']['samples'],43200)
        self.assertEqual(len(out['checks']['native_ldp_left']['excluded_unassessed_ldp_files']),1)

    def test_zero_amber_shared_authority_reaches_both_pair_clocks(self):
        from diagnostics.com_execution_equivalence.test_ramp_timing_authority import attach_timing
        for run in (self.a, self.b):
            pp = run / ('run_provenance_' + run.name + '.json'); prov = v.read(pp)
            attach_timing(prov, self.root); save(pp, prov)
        with patch.object(v, 'CommandClock', wraps=v.CommandClock) as clocks:
            result = self.verify()
        self.assertTrue(result['recorded_execution_equivalent'],
                        {key: value for key, value in result['checks'].items() if not value.get('passed')})
        self.assertEqual(len(clocks.call_args_list), 2)
        self.assertEqual([call.kwargs['ramp_amber_sec'] for call in clocks.call_args_list], [0, 0])
        self.assertEqual(result['checks']['recorded_provenance_and_terminal_logs']['ramp_meter_timing']['amber_sec'], 0)

    def test_missing_lsa_com_remains_independent_failure(self):
        (self.b/'vissim_eval/network.lsa').write_text('1;0;1;1;GREEN;1;COM;0;\n')
        out = self.verify(); self.assertTrue(out['recorded_execution_equivalent'])
        self.assertFalse(out['native_lsa_com_coverage_passed']); self.assertFalse(out['passed'])

    def test_same_missing_owned_commands_in_both_arms_rejected(self):
        for run in (self.a,self.b):
            p=run/('decisions_'+run.name)/'action_000150.csv'
            with p.open(newline='') as f: rows=list(csv.DictReader(f))
            table(p,ACTION_FIELDS,[r for r in rows if not (r['kind']=='signal' and r['sc_no']=='17')])
        self.assertFalse(self.verify()['checks']['action_csv_physical_fields']['passed'])

    def test_missing_initial_post_and_ldp_tail_fail_independently(self):
        p=self.b/'decisions_fast/signal_readback.csv'; p.write_text(p.read_text().replace('2,1,1,GREEN,GREEN,1,post_step\n',''))
        p=self.b/'vissim_eval/network_9101_001.ldp'; p.write_bytes(p.read_bytes().rsplit(b'\r\n',2)[0]+b'\r\n')
        out=self.verify()
        self.assertFalse(out['checks']['signals_right']['passed']); self.assertFalse(out['checks']['native_ldp_right']['passed'])
        self.assertFalse(out['recorded_execution_equivalent'])

    def test_missing_vsl_extra_dsd_class_is_failure(self):
        p=self.b/'decisions_fast/vsl_readback.csv'; p.write_text(p.read_text().replace('150,8,70,120,120,1,immediate\n',''))
        out=self.verify(); self.assertFalse(out['checks']['vsl_right']['passed']); self.assertFalse(out['payload_equivalent'])

    def test_wrong_network_or_terminal_fails_before_payload_reads(self):
        p=self.b/'run_provenance_fast.json'; raw=v.read(p); raw['files']['network']['sha256']='0'*64; save(p,raw)
        with patch.object(v,'fzp_comparison',side_effect=AssertionError('must not scan')):
            out=self.verify(); self.assertFalse(out['passed']); self.assertTrue(out['payload_reads_skipped'])
        p=self.a/'runlog_old.txt'; p.write_text(p.read_text().replace('SIM_SEC=300','SIM_SEC=299'))
        self.assertTrue(self.verify()['payload_reads_skipped'])

    def test_plan_tamper_and_recorded_catalog_omission_rejected(self):
        self.plan.write_text(self.plan.read_text().replace('1:1:1','1:1:0',1))
        out=self.verify(); self.assertTrue(out['payload_reads_skipped'])


if __name__ == '__main__': unittest.main()
