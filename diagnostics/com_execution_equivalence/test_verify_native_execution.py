"""Small actual-file parsers and independently specified signal states; no model."""
import csv
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from diagnostics.com_execution_equivalence import verify_pair as v
from diagnostics.com_execution_equivalence.test_verify_pair import command, save, table, ACTION_FIELDS
from diagnostics.test_native_signal_record import ldp
from diagnostics.com_execution_equivalence.test_ramp_timing_authority import attach_timing


class SingleRunTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name); self.run = self.root/'run'; self.run.mkdir()
        self.folder = self.run/'decisions_run'; self.folder.mkdir()
        self.native = self.run/'vissim_eval'; self.native.mkdir()
        self.network = self.root/'actual_loaded.inpx'
        controllers = []
        for sc,sgs in ((2,(1,2)),(9101,(1,))):
            cols = '<signalOutputConfigurationElement configName="SIM_SEK"/><signalOutputConfigurationElement configName="UML_SEK"/>'
            cols += ''.join(f'<signalOutputConfigurationElement configName="SG_BILD" sg="{sc} {sg}"/>' for sg in sgs)
            controllers.append(f'<signalController no="{sc}"><scDetRecConf>{cols}</scDetRecConf></signalController>')
        self.network.write_text('<network><evaluation><scDetRec writeFile="true"/></evaluation><signalControllers>'+''.join(controllers)+'</signalControllers></network>')
        config = self.root/'generated.vbs'; config.write_text('RW_RAMP_METER_SCS = "9101"\nRW_RAMP_METER_CAPACITIES_VPH = "900"\n')
        plan = self.root/'generated_sgplan.vbs'; plan.write_text('RW_SIGNAL_SG_EXPECTED = "2:1:1,2:2:0"\n')
        runner = self.root/'runner.vbs'; runner.write_text('Const RAMP_CYCLE_SEC = 10\nConst RAMP_AMBER_SEC = 1\nConst AMBER_SEC = 3\n')
        mapping = self.root/'mapping.json'; save(mapping, {'signals':[{'sc_no':2}], 'ramp_meters':[{'sc_no':9101}],
            'segments':[{'dsd_by_lane':{'1':{'dsd_no':7}},'extra_dsd_controls':[]}]})
        files = {'network':self.network,'generated_vbs_config':config,'main_vbs_runner':runner,'control_mapping':mapping,'signal_group_plan':plan}
        self.prov = {'name':'run','run_id':'run-id','seed':13,'sim_period_sec':12,'control_interval_sec':6,
            'files':{k:{'path':str(p),'sha256':v.sha(p),'exists':True} for k,p in files.items()},'env':{'RW_MAINLINE_SG_ONLY':'1'}}
        self.pp = self.run/'run_provenance_run.json'; save(self.pp,self.prov)
        (self.run/'runlog_run.txt').write_text('STAGE=SIM_DONE\nSIM_SEC=12\n'+'\n'.join(k+'=0' for k in v.FAILURE_COUNTERS)+'\n')
        for t in (1,6,12):
            rows = [command('vsl',id='V',dsd_no=7,speed_kph=120 if t==1 else 80),
                    command('ramp_meter',id='M',sc_no=9101,green_sec=5,rate_vph=450)]
            if t>=6:
                rows += [command('signal',id='S',sc_no=2,p1_green=3,p2_green=0,p3_green=0,p4_green=0,offset=0),
                         command('signal_sg',id='S1',sc_no=2,dsd_no=1,p1_green=0,p2_green=3,green_sec=6,offset=0)]
            table(self.folder/f'action_{t:06d}.csv',ACTION_FIELDS,rows)
        self.sgrows = []
        for t in range(1,13):
            if t>1:
                for sc,sg in ((9101,1),*(((2,1),(2,2)) if t>6 else ())):
                    value=self.actual(sc,sg,t-1)
                    self.sgrows.append([t,sc,sg,value,value,1,'post_step'])
            for sc,sg in ((9101,1),*(((2,1),(2,2)) if t>=6 else ())):
                value=self.actual(sc,sg,t)
                self.sgrows.append([t,sc,sg,value,value,1,'immediate'])
        table(self.folder/'signal_readback.csv',v.SG_FIELDS,self.sgrows)
        self.vslrows=[[t,7,c,120 if t==1 else 80,120 if t==1 else 80,1,'immediate'] for t in (1,6,12) for c in (10,20,30,70)]
        table(self.folder/'vsl_readback.csv',v.VSL_FIELDS,self.vslrows)
        self.ldp_rows = {}
        symbol={'RED':'.','GREEN':'I','AMBER':'/'}
        for sc,sgs in ((2,(1,2)),(9101,(1,))):
            first=6 if sc==2 else 1
            rows=[(t,''.join(symbol[self.actual(sc,sg,t-1) if t>first else 'RED'] for sg in sgs)) for t in range(1,13)]
            self.ldp_rows[sc]=rows
            (self.native/f'actual_loaded_{sc}_001.ldp').write_bytes(ldp(sc,sgs,rows))
        (self.native/'actual_loaded_001.lsa').write_bytes(b'Signal Changes Protocol\n0;0;2;1;red;0;Fixed Time;0;\n')

    @staticmethod
    def actual(sc,sg,t):
        if sc==2:return 'RED' if sg==2 else ('GREEN' if t%6<3 else 'AMBER')
        return 'GREEN' if t%10<5 else ('AMBER' if t%10<6 else 'RED')

    def verify(self):
        with patch.object(v,'data_rows',side_effect=AssertionError('No FZP reads')):
            return v.verify_native_execution(self.run,12)

    def test_warmup_then_urban_native_ldp_pass_lsa_independent_fail(self):
        result=self.verify(); self.assertTrue(result['native_execution_passed'],result)
        self.assertFalse(result['native_lsa_com_coverage_passed']);self.assertFalse(result['passed'])
        self.assertFalse(result['process_exit_verified'])
        self.assertEqual(result['checks']['actual_commands']['first_control_sec_by_group'],{'9101:1':1,'2:1':6,'2:2':6})
        self.assertEqual(result['checks']['native_ldp']['sample_count'],36)
        self.assertEqual(result['checks']['actual_commands']['red_only_controlled_groups'],['2:2'])

    def test_missing_ldp_and_second_never_replaced_by_command(self):
        p=self.native/'actual_loaded_2_001.ldp'; original=p.read_bytes()
        p.unlink();self.assertFalse(self.verify()['native_execution_passed'])
        p.write_bytes(ldp(2,[1,2],self.ldp_rows[2][1:]));out=self.verify()
        self.assertFalse(out['checks']['native_ldp']['passed']);p.write_bytes(original)

    def test_zero_amber_actual_red_green_records_and_changed_write_clock(self):
        attach_timing(self.prov, self.root); save(self.pp, self.prov)
        rows = [row.copy() for row in self.sgrows]
        for row in rows:
            if row[1] == 9101 and row[3] == 'AMBER': row[3] = row[4] = 'RED'
        table(self.folder/'signal_readback.csv', v.SG_FIELDS, rows)
        meter_ldp = self.native/'actual_loaded_9101_001.ldp'
        meter_ldp.write_bytes(ldp(9101, [1], [(t, symbols.replace('/', '.')) for t, symbols in self.ldp_rows[9101]]))
        result = self.verify()
        self.assertTrue(result['native_execution_passed'], result)
        self.assertEqual(result['checks']['sources_and_terminal_log']['ramp_meter_timing']['amber_sec'], 0)
        self.assertTrue(result['checks']['actual_initial_and_changed_writes']['passed'])
        self.assertFalse(result['native_lsa_com_coverage_passed']); self.assertFalse(result['passed'])
        # Desired command rows alone cannot turn a native AMBER record into RED.
        meter_ldp.write_bytes(ldp(9101, [1], self.ldp_rows[9101]))
        self.assertFalse(self.verify()['checks']['native_ldp']['passed'])

    def test_zero_amber_missing_manifest_fails_before_native_or_command_reads(self):
        attach_timing(self.prov, self.root); self.prov.pop('ramp_meter_timing'); save(self.pp, self.prov)
        result = self.verify()
        self.assertFalse(result['checks']['sources_and_terminal_log']['passed'])
        self.assertNotIn('actual_commands', result['checks'])

    def test_red_only_and_t_minus_one_mismatch(self):
        p=self.native/'actual_loaded_2_001.ldp'
        for index,symbols in ((8,'/.'),(7,'II')):
            rows=self.ldp_rows[2].copy();rows[index]=(rows[index][0],symbols)
            p.write_bytes(ldp(2,[1,2],rows));out=self.verify()
            self.assertFalse(out['native_execution_passed']);self.assertFalse(out['checks']['native_ldp']['passed'])

    def test_ldp_past_terminal_is_not_a_completed_run_record(self):
        p=self.native/'actual_loaded_2_001.ldp'
        p.write_bytes(ldp(2,[1,2],self.ldp_rows[2]+[(13,'I.')]))
        self.assertFalse(self.verify()['checks']['native_ldp']['passed'])

    def test_missing_initial_or_changed_actual_immediate(self):
        for t,sc in ((6,2),(9,2),(5,9101)):
            rows=[r for r in self.sgrows if not (r[0]==t and r[1]==sc and r[2]==1 and r[-1]=='immediate')]
            table(self.folder/'signal_readback.csv',v.SG_FIELDS,rows)
            self.assertFalse(self.verify()['native_execution_passed'])

    def test_vsl_missing_class_wrong_distribution_or_apply(self):
        for kind in ('class','distribution','apply'):
            rows=[r.copy() for r in self.vslrows]
            if kind=='class':rows.pop(1)
            elif kind=='distribution':rows[4][4]=120
            else:rows=[r for r in rows if r[0]!=6]
            table(self.folder/'vsl_readback.csv',v.VSL_FIELDS,rows)
            self.assertFalse(self.verify()['checks']['actual_vsl_apply_readbacks']['passed'])

    def test_missing_urban_window_or_whole_command_time(self):
        p=self.folder/'action_000006.csv'
        with p.open(newline='') as stream: rows=list(csv.DictReader(stream))
        table(p,ACTION_FIELDS,[r for r in rows if r['kind']!='signal_sg'])
        self.assertFalse(self.verify()['checks']['actual_commands']['passed'])
        p.unlink();self.assertFalse(self.verify()['checks']['actual_commands']['passed'])

    def test_source_sha_and_actual_network_recording_gate(self):
        self.network.write_text(self.network.read_text().replace('writeFile="true"','writeFile="false"'))
        self.assertFalse(self.verify()['checks']['sources_and_terminal_log']['passed'])
        self.prov['files']['network']['sha256']=v.sha(self.network);save(self.pp,self.prov)
        self.assertIn('no enabled',self.verify()['checks']['sources_and_terminal_log']['error'])

    def test_missing_red_only_recording_column_fails_even_with_updated_pin(self):
        self.network.write_text(self.network.read_text().replace('<signalOutputConfigurationElement configName="SG_BILD" sg="2 2"/>',''))
        self.prov['files']['network']['sha256']=v.sha(self.network);save(self.pp,self.prov)
        self.assertFalse(self.verify()['checks']['sources_and_terminal_log']['passed'])

    def test_historical_fixture_plan_authority_and_actual_network_binding(self):
        plan=self.prov['files'].pop('signal_group_plan');save(self.pp,self.prov)
        prep={'schema':'native-all-controlled-sg-recording-fixture/v1','prepared':True,
              'network':str(self.network),'network_sha256':v.sha(self.network),'actual_plan':plan}
        save(self.root/'preflight.json',prep);self.assertTrue(self.verify()['native_execution_passed'])
        prep['network_sha256']='0'*64;save(self.root/'preflight.json',prep)
        self.assertFalse(self.verify()['checks']['sources_and_terminal_log']['passed'])

    def test_lsa_can_pass_only_with_actual_observed_transition_events(self):
        actual=self.verify()['checks']['actual_signal_readbacks']['transitions']
        body='Signal Changes Protocol\n'+''.join(f'{t};0;{key.replace(":",";")};{value};0;COM;0;\n' for t,stage,key,value in actual)
        (self.native/'actual_loaded_001.lsa').write_text(body)
        result=self.verify();self.assertTrue(result['native_lsa_com_coverage_passed'],result)
        self.assertTrue(result['passed'])


if __name__=='__main__':unittest.main()
