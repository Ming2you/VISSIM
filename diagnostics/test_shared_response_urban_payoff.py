"""Pure source-cost fixtures. No model import, local dynamics, COM or endpoint."""
import ast
import copy
import hashlib
import math
from pathlib import Path
from types import SimpleNamespace as NS
from typing import Mapping
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'evaluation/controllers/local_signal_service.py'
VENDOR = ROOT / 'vendor/NumSim-mine/src/controllers/local_signal_plant.py'
NEW = {'_response_nonnegative', '_response_map', 'score_shared_urban_response'}
BASE_SHA = '3e1db452f2d6ee929a766a82e0c8459eca4f4e5027c3c8ba7ebc7d2384efdfa5'


def load_scorer():
    tree = ast.parse(SOURCE.read_text(encoding='utf-8'))
    body = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in NEW]
    if {n.name for n in body} != NEW: raise ValueError('Missing production scorer functions')
    scope = {'math': math, 'Mapping': Mapping}
    exec(compile(ast.Module(body=body, type_ignores=[]), str(SOURCE), 'exec'), scope)
    return scope['score_shared_urban_response']


def source_cost_terms(path, name):
    tree = ast.parse(path.read_text(encoding='utf-8'))
    function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)
    terms = sorted((n for n in ast.walk(function) if isinstance(n, ast.AugAssign)
                    and isinstance(n.target, ast.Name) and n.target.id == 'cost'), key=lambda n:n.lineno)
    return [n.value for n in terms]


def model(ramps):
    return NS(has_ramps=ramps,
        movements=['through', 'toR1', 'toR2', 'offLeft', 'offThrough'] if ramps else ['through', 'turn'],
        kind_of={'through':'internal', 'turn':'boundary_out', 'toR1':'on_ramp', 'toR2':'boundary_in',
                 'offLeft':'off_ramp', 'offThrough':'off_ramp'},
        onramp_movements={'R1':['toR1'], 'R2':['toR2']} if ramps else {},
        offramp_movements={'OR':['offLeft', 'offThrough']} if ramps else {},
        cfg=NS(network=NS(off_ramp_storage_link={'OR':'storage1'}),
               mpc=NS(protected_queue_movement='through', protected_queue_weight=.5, protected_queue_max_veh=2.)))


def rows(ramps):
    result=[]
    for index in range(2):
        row={'service_step':180+index,'stage':'after_urban_service_before_fw_landing',
             'queue_veh':{'through':3.+index, 'toR1':1., 'toR2':2.} if ramps else {'through':3.+index,'turn':2.}}
        if ramps:
            row.update(offramp_stock_veh={'OR':5.+index}, ramp_stock_veh={'R1':2.,'R2':1.},
                       accepted_to_ramp_by_movement_veh={'toR1':3.,'toR2':4.})
        result.append(row)
    return result


class SharedUrbanPayoff(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.score = staticmethod(load_scorer())

    def call(self, m=None, data=None, **kwargs):
        m = m if m is not None else model(True)
        data = data if data is not None else rows(m.has_ramps)
        options={'start_step':180,'substeps':2,'dt_h':.1}
        if m.has_ramps: options.update(freeway_congestion={'R1':.25,'R2':.5},ramp_metering_weight=.2)
        options.update(kwargs)
        return self.score(m,data,**options)

    def test_01_all_existing_functions_and_installers_unchanged(self):
        with zipfile.ZipFile(ROOT/'diagnostics/shared_response_urban_payoff_v1/baseline_source.zip') as z:
            raw=z.read('local_signal_service.py')
        self.assertEqual(hashlib.sha256(raw).hexdigest(),BASE_SHA)
        baseline=ast.parse(raw); current=ast.parse(SOURCE.read_text(encoding='utf-8'))
        current.body=[n for n in current.body if not (isinstance(n,ast.FunctionDef) and n.name in NEW)]
        self.assertEqual(ast.dump(baseline),ast.dump(current))

    def test_02_ordinary_cost_equals_actual_phased_source_expression(self):
        terms=source_cost_terms(VENDOR,'rollout_local_tts_phased');self.assertEqual(len(terms),1)
        expression=compile(ast.Expression(terms[0]),str(VENDOR),'eval')
        data=rows(False);expected=0.
        for row in data:expected+=eval(expression,{'q':row['queue_veh'],'dt_h':.1})
        result=self.call(model(False),data)
        self.assertEqual(result['cost'],expected)
        self.assertEqual(result['congestion_cost'],0.)
        self.assertEqual(result['protected_queue_cost'],0.) # configured, but not part of ordinary kernel

    def test_03_ramp_terms_match_both_actual_kernel_sources_exactly(self):
        a=source_cost_terms(SOURCE,'rollout_shared_ramp')
        b=source_cost_terms(VENDOR,'rollout_local_tts_ramp_aware')
        self.assertEqual(len(a),3);self.assertEqual([ast.dump(x) for x in a],[ast.dump(x) for x in b])
        expressions=[compile(ast.Expression(x),str(SOURCE),'eval') for x in a]
        m=model(True); data=rows(True);expected=0.
        for row in data:
            scope={'q':row['queue_veh'],'occ':row['offramp_stock_veh'],'res':row['ramp_stock_veh'],'dt_h':.1,
                   'freeway_congestion':{'R1':.25,'R2':.5},'ramp_metering_weight':.2,
                   '_pq_mv':'through','_pq_w':.5,'_pq_max':2.}
            for ramp,members in m.onramp_movements.items():
                scope.update(ramp=ramp,released_total=sum(row['accepted_to_ramp_by_movement_veh'][x] for x in members))
                expected+=eval(expressions[0],scope)
            expected+=eval(expressions[1],scope);expected+=eval(expressions[2],scope)
        result=self.call(m,data)
        self.assertEqual(result['cost'],expected)
        self.assertAlmostEqual(result['congestion_cost'],1.1) # accepted vehicles; no extra dt
        self.assertAlmostEqual(result['offramp_residence_veh_h'],1.1)
        self.assertAlmostEqual(result['ramp_residence_veh_h'],.6)
        self.assertAlmostEqual(result['protected_queue_cost'],.15)

    def test_04_no_urban_to_ramp_acceptance_means_no_congestion_charge(self):
        data=rows(True)
        for row in data:row['accepted_to_ramp_by_movement_veh']={'toR1':0.,'toR2':0.}
        self.assertEqual(self.call(data=data)['congestion_cost'],0.)
        data[0]['meter_release_veh']={'R1':9.,'R2':9.}
        with self.assertRaisesRegex(ValueError,'wrong-stage'):self.call(data=data)

    def test_05_missing_extra_wrong_stage_or_noncontiguous_step_fails(self):
        for mutation in (
            lambda x:x.pop(), lambda x:x.append(copy.deepcopy(x[-1])),
            lambda x:x[1].update(service_step=180), lambda x:x[0].update(service_step=True),
            lambda x:x[0].update(stage='after_fw_landing'),lambda x:x[0].pop('ramp_stock_veh'),
            lambda x:x[0]['accepted_to_ramp_by_movement_veh'].pop('toR2'),
            lambda x:x[0]['offramp_stock_veh'].update(unrelated=0.),
        ):
            with self.subTest(mutation=mutation):
                data=rows(True);mutation(data)
                with self.assertRaises(ValueError):self.call(data=data)

    def test_06_all_operands_reject_nonfinite_negative_boolean(self):
        for field,key in (('queue_veh','through'),('offramp_stock_veh','OR'),('ramp_stock_veh','R1'),
                          ('accepted_to_ramp_by_movement_veh','toR1')):
            for bad in (math.nan,math.inf,-1.,True):
                with self.subTest(field=field,bad=bad):
                    data=rows(True);data[0][field][key]=bad
                    with self.assertRaises(ValueError):self.call(data=data)
        for opts in ({'dt_h':0.},{'dt_h':math.nan},{'substeps':0},{'substeps':True},
                     {'freeway_congestion':{'R1':math.nan,'R2':.2}},
                     {'freeway_congestion':{'R1':1.01,'R2':.2}}, {'ramp_metering_weight':math.inf}):
            with self.subTest(opts=opts),self.assertRaises(ValueError):self.call(**opts)

    def test_07_off_movement_queue_cannot_be_counted_with_or_stock(self):
        data=rows(True);data[0]['queue_veh']['offLeft']=5.
        with self.assertRaisesRegex(ValueError,'queue_veh'):self.call(data=data)

    def test_08_alias_or_stock_and_duplicate_ramp_attribution_fail(self):
        m=model(True);m.offramp_movements={'OR':['offLeft'],'OR2':['offThrough']}
        m.cfg.network.off_ramp_storage_link['OR2']='storage1'
        with self.assertRaisesRegex(ValueError,'Aliased'):self.call(m)
        m=model(True);m.onramp_movements['R2'].append('toR1')
        with self.assertRaisesRegex(ValueError,'Overlapping'):self.call(m)
        m=model(True);m.movements.append('through')
        with self.assertRaisesRegex(ValueError,'unique'):self.call(m)

    def test_09_dictionary_order_does_not_change_kernel_summation(self):
        data=rows(True);expected=self.call(data=data)
        reordered=[{k:(dict(reversed(list(v.items()))) if isinstance(v,dict) else v) for k,v in row.items()} for row in data]
        self.assertEqual(self.call(data=reordered),expected)

    def test_10_no_input_mutation_or_hidden_price_and_quantity_terms(self):
        m=model(True);data=rows(True);before=copy.deepcopy((vars(m),data))
        result=self.call(m,data)
        self.assertEqual(before,(vars(m),data))
        self.assertFalse(result['shared_flow_consistency_certified'])
        self.assertFalse(result['price_or_quantity_terms_included'])
        self.assertTrue(result['response_operands_complete'])

    def test_11_ordinary_rejects_undeclared_ramp_cost_operands(self):
        with self.assertRaisesRegex(ValueError,'no ramp congestion'):self.call(model(False),ramp_metering_weight=0.)

    def test_12_arithmetic_overflow_rejected(self):
        data=rows(True);data[0]['queue_veh']['through']=1e308
        with self.assertRaisesRegex(ValueError,'overflow'):self.call(data=data,dt_h=1e308)


if __name__=='__main__':unittest.main()
