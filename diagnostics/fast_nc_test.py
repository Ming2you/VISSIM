"""Small preparation/syntax guards, no model or simulator creation."""
import math
import json
from pathlib import Path
import tempfile
import unittest
from diagnostics import fast_nc_prepare as p


class NativeInputs(unittest.TestCase):
    def test_native_preserve_snapshots_exact_input_and_assets(self):
        # This deliberately does not satisfy the legacy204-row/default NC schema.
        # Preservation must use the supplied file, not old profiles or controls.
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            source=root/'user.inpx'
            data=b'<network><simulation numRuns="1" randSeed="17" simRes="5"/><vehicleInputs><input volume="123"/></vehicleInputs><signal supplyFile2="#data#a.sig"/></network>'
            source.write_bytes(data); (root/'a.sig').write_bytes(b'user signal')
            out=root/'prepared'
            p.prepare_native_preserve(source,out,9000)
            proof=json.loads((out/'prepared.json').read_text())
            self.assertEqual((out/'network/user.inpx').read_bytes(),data)
            self.assertEqual((out/'network/a.sig').read_bytes(),b'user signal')
            self.assertEqual(source.read_bytes(),data)
            self.assertEqual(proof['seed'],17)
            self.assertFalse((out/'demand.csv').exists())
            self.assertFalse((out/'controls.csv').exists())

    def test_global_scale_one_is_exact_and_positive(self):
        self.assertEqual(p.demand_rows(p.BASE),p.demand_rows(p.BASE,global_scale=1))
        for scale in (0,-1,float('nan'),float('inf')):
            with self.assertRaises(ValueError): p.demand_rows(p.BASE,global_scale=scale)

    def test_global_scale_applies_after_absolute_override(self):
        override=[{'input_no':114,'start_sec':0,'volume_vph':125}]
        original=p.demand_rows(p.BASE,override)
        reduced=p.demand_rows(p.BASE,override,0.6)
        self.assertEqual(len(reduced),204)
        for a,b in zip(original,reduced):
            self.assertEqual(b,{**a,'volume_vph':a['volume_vph']*0.6})
        self.assertEqual(reduced[0]['volume_vph'],75)

    def test_original_204_and_74(self):
        rows=p.demand_rows(p.BASE)
        self.assertEqual(len(rows),204)
        self.assertEqual(len(p.controls()),74)
        for r in rows:
            self.assertTrue(math.isfinite(r['volume_vph']))

    def test_one_interval_override_and_unmatched_rejected(self):
        base=p.demand_rows(p.BASE)
        row=base[0]
        result=p.demand_rows(p.BASE,[{'input_no':row['input_no'],'start_sec':row['start_sec'],'volume_vph':0}])
        self.assertEqual(result[0]['volume_vph'],0)
        self.assertEqual(result[1:],base[1:])
        with self.assertRaises(ValueError):
            p.demand_rows(p.BASE,[{'input_no':999999,'start_sec':0,'volume_vph':0}])

    def test_invalid_values_and_duplicate(self):
        for v in ('nan','inf',-1):
            with self.assertRaises(ValueError): p.number(v)
        row={'input_no':114,'start_sec':0,'volume_vph':5}
        with self.assertRaises(ValueError): p.demand_rows(p.BASE,[row,row])

    def test_no_model_or_census_and_one_continuous(self):
        text=(p.ROOT/'diagnostics/fast_nc_runner.vbs').read_text()
        self.assertEqual(text.count('sim.Simulation.RunContinuous'),1)
        self.assertEqual(text.count('sim.Simulation.RunSingleStep'),1)
        self.assertNotIn('Net.Vehicles',text)
        self.assertNotIn('RunController',text)
        self.assertIn('Array(10,20,30,70)',text)
        self.assertLess(text.index('sim.Simulation.RunSingleStep'),text.index('ApplyAndCheckControls True'))


if __name__=='__main__': unittest.main()
