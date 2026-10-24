import copy
import csv
import json
from pathlib import Path
import tempfile
import unittest
from diagnostics.fast_fixed_profile import compile_profile, prepare, sha, SCHEMA
from diagnostics.fast_fixed_profile_verify import native_recording_grid, prefix_digest, verify
from diagnostics.test_native_signal_record import ldp


class FixedProfile(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.network = self.root/'baseline.inpx'
        classes = ''.join(f'<vehClassDesSpeedDistribution vehClass="{c}" desSpeedDistr="120"/>' for c in (10,20,30,70))
        speeds = ''.join(f'<desSpeedDistribution no="{c}"/>' for c in (80,100,120))
        self.network.write_text('<network><simulation numRuns="1" randSeed="13" simRes="1" simPeriod="9001"/>'
                                '<evaluation><scDetRec writeFile="true"/></evaluation>'
                                '<desSpeedDecisions><desSpeedDecision no="59" lane="2 1" pos="2652">'
                                f'<vehClassDesSpeedDistr>{classes}</vehClassDesSpeedDistr></desSpeedDecision></desSpeedDecisions>'
                                f'<desSpeedDistributions>{speeds}</desSpeedDistributions>'
                                '<signalControllers><signalController no="9107"><scDetRecConf><signalOutputConfigurationElement configName="SG_BILD" sg="9107 1"/></scDetRecConf><sgs><signalGroup no="1"/></sgs>'
                                '</signalController></signalControllers></network>', encoding='utf-8')
        self.profile = {'schema':SCHEMA, 'network_sha256':sha(self.network), 'seed':13,
                        'control_start_sec':1350,'terminal_sec':2250,
                        'native_off_service_anchor_green_sec':10,
                        'vsl_commands':[{'time_s':1350,'dsd_no':59,'speed_id':100},
                                        {'time_s':1500,'dsd_no':59,'speed_id':80},
                                        {'time_s':1800,'dsd_no':59,'speed_id':100},
                                        {'time_s':1950,'dsd_no':59,'speed_id':120}],
                        'meter_commands':[{'time_s':t,'sc_no':9107,'green_sec':g} for t,g in
                                          [(1350,8),(1500,6),(1650,4),(1800,6),(1950,8),(2100,10)]]}

    def test_declared_actual_green_windows_and_recovery(self):
        events, initial, proof = compile_profile(self.network,self.profile)
        meter = {r[0]:r[4] for r in events if r[1]=='meter'}
        state=None
        observed=[]
        for start, green in proof['meter_schedules'][9107]:
            total=0
            for sec in range(start,start+150):
                state=meter.get(sec,state)
                self.assertIn(state,('RED','GREEN'))
                total += state=='GREEN'
            observed.append(total)
        self.assertEqual(observed,[120,90,60,90,120,150])
        self.assertEqual(min(r[0] for r in events),1350)
        self.assertEqual([r[4] for r in initial if r[1]=='vsl'],[120]*4)
        self.assertEqual(len([r for r in events if r[1]=='vsl']),16)

    def test_simulation_period_preserves_long_native_and_only_increases_short_native(self):
        before = self.network.read_bytes()
        _, _, proof = compile_profile(self.network, self.profile)
        self.assertEqual((proof['saved_simulation_period_sec'], proof['effective_simulation_period_sec']), (9001,9001))
        self.assertEqual(self.network.read_bytes(), before)
        self.network.write_bytes(before.replace(b'simPeriod="9001"', b'simPeriod="1800"'))
        self.profile['network_sha256'] = sha(self.network)
        _, _, proof = compile_profile(self.network, self.profile)
        self.assertEqual((proof['saved_simulation_period_sec'], proof['effective_simulation_period_sec']), (1800,2251))

    def test_compiler_rejects_wrong_network_and_trust_violations(self):
        changes = [lambda p:p.update(network_sha256='0'*64),
                   lambda p:p['vsl_commands'][0].update(speed_id=80),
                   lambda p:p['meter_commands'][0].update(green_sec=4),
                   lambda p:p['meter_commands'][1].update(time_s=1350),
                   lambda p:p['meter_commands'][0].update(sc_no=1001),
                   lambda p:p['vsl_commands'][0].update(time_s=1200),
                   lambda p:p.update(native_off_service_anchor_green_sec=None)]
        for change in changes:
            p=copy.deepcopy(self.profile); change(p)
            with self.assertRaises(ValueError): compile_profile(self.network,p)

    def test_no_commands_native_traffic_snapshot_and_pins(self):
        self.profile['vsl_commands']=[]; self.profile['meter_commands']=[]
        profile=self.root/'none.json'; profile.write_text(json.dumps(self.profile))
        before=self.network.read_bytes()
        result=prepare(self.network,profile,self.root/'prepared')
        self.assertEqual(result['mode'],'fixed_profile')
        self.assertEqual(result['command_rows'],0)
        self.assertEqual(Path(result['network']).read_bytes(),before)
        self.assertEqual(self.network.read_bytes(),before)
        for path,digest in result['snapshot_sha256'].items(): self.assertEqual(sha(path),digest)

    def test_prefix_uses_every_vehicle_column_and_excludes_future(self):
        a=self.root/'a.fzp'; b=self.root/'b.fzp'
        a.write_bytes(b'Header time A\r\n1.00;1;2;3;7\r\n2.00;1;2;3;8\r\n3.00;1;2;3;9\r\n')
        b.write_bytes(b'Header time B\n1.00;1;2;3;7\n2.00;1;2;3;8\n3.00;9;9;9;9\n')
        self.assertEqual(prefix_digest(a,2),prefix_digest(b,2))
        b.write_bytes(b'1.00;1;2;3;7\n2.00;1;2;3;99\n')
        self.assertNotEqual(prefix_digest(a,2),prefix_digest(b,2))

    def test_resolution_probe_is_explicit_and_preserves_integer_event_clock(self):
        self.profile['vsl_commands'] = []; self.profile['meter_commands'] = []
        baseline = compile_profile(self.network, self.profile)
        self.assertNotIn('native_resolution_probe', baseline[2])
        self.network.write_bytes(self.network.read_bytes().replace(b'simRes="1"', b'simRes="10"'))
        self.profile['network_sha256'] = sha(self.network)
        with self.assertRaises(ValueError): compile_profile(self.network, self.profile)
        self.profile['native_resolution_probe'] = 10
        events, initial, proof = compile_profile(self.network, self.profile)
        self.assertEqual(events, [])
        self.assertEqual(initial, baseline[1])
        self.assertEqual(proof['native_resolution_probe'], 10)
        self.profile['meter_commands'] = [{'time_s':1350, 'sc_no':9107, 'green_sec':8}]
        events, _, proof = compile_profile(self.network, self.profile)
        self.assertEqual(events[:3],[[1350,'meter',9107,1,'GREEN'],[1358,'meter',9107,1,'RED'],[1360,'meter',9107,1,'GREEN']])
        self.assertIn('first affected LDP frame is t+1',proof['event_clock'])
        self.profile['meter_commands'] = []
        self.profile['native_resolution_probe'] = 1
        with self.assertRaises(ValueError): compile_profile(self.network, self.profile)

    def test_resolution_changes_no_compiled_commands_or_trust_region(self):
        original=compile_profile(self.network,self.profile)
        self.network.write_bytes(self.network.read_bytes().replace(b'simRes="1"',b'simRes="10"'))
        self.profile.update(network_sha256=sha(self.network),native_resolution_probe=10)
        changed=compile_profile(self.network,self.profile)
        self.assertEqual(original[:2],changed[:2])
        for key in ('meter_schedules','event_clock','control_start_sec','terminal_sec'):
            self.assertEqual(original[2][key],changed[2][key])
        self.profile['meter_commands'][0]['green_sec']=7
        with self.assertRaises(ValueError):compile_profile(self.network,self.profile)

    def test_fractional_native_prefix_respects_phase_and_control_cutoff(self):
        a=self.root/'a.fzp';b=self.root/'b.fzp'
        a.write_bytes(b'1.1;1;10\n2.1;1;20\n3.1;1;30\n')
        b.write_bytes(b'1.1;1;10\n2.1;1;20\n3.1;1;999\n')
        self.assertEqual(prefix_digest(a,3,recording_grid=(1,.1)),prefix_digest(b,3,recording_grid=(1,.1)))
        self.assertEqual(prefix_digest(a,3,recording_grid=(1,.1))['last_time_s'],2.1)
        with self.assertRaises(ValueError):prefix_digest(a,3)
        with self.assertRaises(ValueError):prefix_digest(a,3,recording_grid=(1,0))
        b.write_bytes(b'1.1;1;10\n3.1;1;30\n')
        with self.assertRaises(ValueError):prefix_digest(b,3,recording_grid=(1,.1))
        b.write_bytes(b'1.1;1;10\n2.2;1;20\n3.1;1;30\n')
        with self.assertRaises(ValueError):prefix_digest(b,3,recording_grid=(1,.1))

    def test_native_prewrite_clock_detects_one_second_shift(self):
        profile=self.root/'profile.json'; profile.write_text(json.dumps(self.profile))
        prepared=self.root/'prepared'; prepare(self.network,profile,prepared)
        run=self.root/'run'; (run/'vissim_eval').mkdir(parents=True)
        events,initial,proof=compile_profile(self.network,self.profile)
        (run/'readback.csv').write_text('kind,no,time_int,expected,actual\nnative_simulation,SimPeriod,,9001,9001\nfixed_simulation,SimPeriod,,9001,9001\n')
        values=[]
        for phase,time in [('initial',0),('final',2250)]:
            for _,kind,no,cls,value in initial:
                if kind=='signal': value='OFF' if phase=='initial' else 'GREEN'
                values.append([time,phase,kind,no,cls,('READ' if kind=='signal' else value),value,('' if kind=='vsl' else str(phase=='final')),1])
        for sec,kind,no,cls,value in events:
            values.append([sec,'write',kind,no,cls,value,value,('True' if kind=='meter' else ''),1])
        with (run/'fixed_readback.csv').open('w',newline='') as stream:
            writer=csv.writer(stream); writer.writerow(['time_s','phase','kind','no','veh_class','expected','actual','contr_by_com','ok']); writer.writerows(values)
        native=[]
        for t in range(1,2251):
            schedule=[r for r in self.profile['meter_commands'] if r['time_s']<t]
            symbol=' ' if not schedule else ('I' if (t-1)%10<schedule[-1]['green_sec'] else '.')
            native.append((t,symbol))
        file=run/'vissim_eval/baseline_9107_001.ldp'; file.write_bytes(ldp(9107,[1],native))
        result=verify(prepared,run)
        self.assertEqual([r['observed_green_seconds'] for r in result['actual_green_windows']],[120,90,60,90,120,150])
        wrong=list(native); wrong[1357]=(1358,'.')  # write at1358 cannot affect1358 native frame
        file.write_bytes(ldp(9107,[1],wrong))
        with self.assertRaisesRegex(ValueError,'Native meter differs'): verify(prepared,run)
        file.write_bytes(ldp(9107,[1],native[:-1]))
        with self.assertRaisesRegex(ValueError,'Missing LDP frame'): verify(prepared,run)
        (run/'readback.csv').write_text('kind,no,time_int,expected,actual\nnative_simulation,SimPeriod,,9001,9001\nfixed_simulation,SimPeriod,,9001,2251\n')
        with self.assertRaisesRegex(ValueError,'SimPeriod readback'): verify(prepared,run)

    def test_resolution_grid_requires_actual_matching_setup(self):
        setup=[{'kind':kind,'no':name,'expected':value,'actual':value} for kind,name,value in
               [('native_simulation','SimRes','10'),('native_recording','VehRecResolution','10'),
                ('native_recording','VehRecFromTime','0')]]
        self.assertEqual(tuple(map(float,native_recording_grid(setup,10))),(1,.1))
        with self.assertRaises(ValueError):native_recording_grid(setup,1)
        with self.assertRaises(ValueError):native_recording_grid(setup[:-1],10)
        wrong=copy.deepcopy(setup);wrong[1]['actual']='1'
        with self.assertRaises(ValueError):native_recording_grid(wrong,10)
        setup[1].update(expected='50',actual='50');setup[2].update(expected='4.9',actual='4.9')
        self.assertEqual(tuple(map(float,native_recording_grid(setup,10))),(5,0))

    def test_zero_event_reference_must_match_terminal_not_only_1350(self):
        self.profile['vsl_commands']=[]; self.profile['meter_commands']=[]
        profile=self.root/'profile.json'; profile.write_text(json.dumps(self.profile))
        prepared=self.root/'prepared'; prepare(self.network,profile,prepared)
        run=self.root/'run'; reference=self.root/'reference'
        for folder in (run,reference):
            (folder/'vissim_eval').mkdir(parents=True)
            (folder/'vissim_eval/baseline_9107_001.ldp').write_bytes(ldp(9107,[1],[(t,' ') for t in range(1,2251)]))
        (run/'readback.csv').write_text('kind,no,time_int,expected,actual\nnative_simulation,SimPeriod,,9001,9001\nfixed_simulation,SimPeriod,,9001,9001\n')
        _,initial,_=compile_profile(self.network,self.profile)
        with (run/'fixed_readback.csv').open('w',newline='') as stream:
            writer=csv.writer(stream); writer.writerow(['time_s','phase','kind','no','veh_class','expected','actual','contr_by_com','ok'])
            for phase,time in [('initial',0),('final',2250)]:
                for _,kind,no,cls,value in initial:
                    writer.writerow([time,phase,kind,no,cls,'READ' if kind=='signal' else value,'OFF' if kind=='signal' else value,'False' if kind=='signal' else '',1])
        own=run/'vissim_eval/baseline_001.fzp'; ref=reference/'vissim_eval/baseline_001.fzp'
        own.write_bytes(b'1.00;1;1\n1350.00;1;1\n2250.00;1;1\n')
        ref.write_bytes(b'1.00;1;1\n1350.00;1;1\n2250.00;1;2\n')
        with self.assertRaisesRegex(ValueError,'FZP warmup prefix differs'): verify(prepared,run,reference)
        ref.write_bytes(own.read_bytes())
        self.assertEqual(verify(prepared,run,reference)['paired_comparison_end_sec'],2250)


if __name__ == '__main__': unittest.main()
