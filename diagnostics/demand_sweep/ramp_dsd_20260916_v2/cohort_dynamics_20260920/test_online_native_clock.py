"""Causal timestamp guards for the existing online MPC observation path."""
from pathlib import Path
import copy
import json
import sys
import tempfile
import types
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2 import evaluate_response as e

K=Path(__file__).resolve().parent
B=K/'native_time_contract_v1'
GEOMETRY=K.parent/'controller_response_s23_v1/none/geometry.json'


def legacy():
    module=types.ModuleType('saved_online_native_clock')
    module.__file__=e.__file__
    exec(compile((B/'source_before_evaluate_response.py').read_bytes(),e.__file__,'exec'),module.__dict__)
    return module


def fixture(name,times,cutoff=150,*,base=B):
    root=base/name;root.mkdir(exist_ok=False)
    native=root/'vissim_eval';native.mkdir()
    link=e.load(GEOMETRY)['chains']['FW_E'][0]['link']
    header='$VEHICLE:SIMSEC;NO;LANE\\LINK\\NO;LANE\\INDEX;POS;SPEED\n'
    text=header+''.join(f'{t};1;{link};1;100.00;0.00\n' for t in times)
    (native/'baseline_001.fzp').write_text(text,encoding='ascii')
    snapshot(root,cutoff,link)
    return root,link


def snapshot(root,cutoff,link):
    (root/f'mpc_vehicles_{cutoff}.csv').write_text(
        f'vehicle,lane,position_m,speed_kmh\n1,{link} 1,100,0\n',encoding='ascii')


def observe(module,root,cutoff=150):
    return module.online_data(root/'unused_prepared',root,cutoff,{'geometry':str(GEOMETRY)})


class NativeClock(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='clock-',dir=B)
        self.directory=Path(self.temp.name).resolve()
        assert self.directory.parent==B.resolve()
        self.addCleanup(self.temp.cleanup)

    def fixture(self,name,times):
        return fixture(name,times,base=self.directory)

    def test_future_fractional_frame_rejected_before_rounding(self):
        root,_=self.fixture('future_rejected',[*range(1,150),150.1])
        with self.assertRaisesRegex(ValueError,'Future native frame'):observe(e,root)
        self.assertFalse((root/'mpc_observer_cache.pkl').exists())

    def test_past_fractional_phase_not_relabelled_as_integer(self):
        root,_=self.fixture('past_phase_rejected',[i+.1 for i in range(1,150)])
        with self.assertRaisesRegex(ValueError,'integer-aligned'):observe(e,root)
        self.assertFalse((root/'mpc_observer_cache.pkl').exists())

    def test_recorded_fractional_sample_rejected_without_state_write(self):
        root,_=self.fixture('recorded_phase_rejected',[1])
        (root/'vissim_eval/baseline_001.fzp').write_bytes((B/'actual_res10_sample.fzp').read_bytes())
        with self.assertRaisesRegex(ValueError,'integer-aligned'):observe(e,root)
        self.assertFalse((root/'mpc_observer_cache.pkl').exists())
        self.assertFalse((root/'mpc_observation_150.json').exists())

    def test_integer_future_still_rejected(self):
        root,_=self.fixture('integer_future_rejected',[*range(1,151),151])
        with self.assertRaisesRegex(ValueError,'Future native frame'):observe(e,root)

    def test_nonfinite_and_negative_time_rejected(self):
        for label,value in (('nan','nan'),('inf','inf'),('negative','-1')):
            root,_=self.fixture('invalid_'+label,[value])
            with self.assertRaisesRegex(ValueError,'Invalid native timestamp'):observe(e,root)

    def test_integer_default_and_second_cache_update_exact(self):
        old=legacy();pairs=[]
        for label,module in (('old_integer',old),('new_integer',e)):
            root,link=self.fixture(label,range(1,151))
            outputs=[]
            for cutoff in (150,300):
                if cutoff==300:
                    with (root/'vissim_eval/baseline_001.fzp').open('a',encoding='ascii') as f:
                        f.writelines(f'{t};1;{link};1;100.00;0.00\n' for t in range(151,301))
                    snapshot(root,cutoff,link)
                data,evidence=observe(module,root,cutoff)
                state=copy.deepcopy(data.__dict__);state.pop('folder')
                outputs.append((state,evidence,(root/'mpc_observer_cache.pkl').read_bytes()))
            pairs.append(outputs)
        self.assertEqual(pairs[0],pairs[1])


if __name__=='__main__':unittest.main()
