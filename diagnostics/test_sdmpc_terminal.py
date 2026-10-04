"""Terminal score scope, exact ownership and sensitivity regression checks."""
import ast
import copy
from pathlib import Path
import sys
from types import SimpleNamespace as NS
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'vendor/NumSim-mine')]
from evaluation.controllers import sdmpc_terminal as terminal
from evaluation.controllers.sdmpc import omega_costs


def fixture():
    cfg = NS(network=NS(signals=('SC1',), freeway_links=('FW_E',), ramps=('R1',),
        ramp_to_freeway={'R1': 'FW_E'}, control_area_enabled=True, control_area_beta_seconds=0,
        sdmpc_cost_ownership={'freeway:FW_E': 'FW_E', 'ramp:R1': 'FW_E',
            'movement:m': 'SC1', 'origin:FW_E': 'FW_E'}))
    spec = dict(schema=terminal.SCHEMA, design='unit test explicit PSD P',
        p_diag_h_per_veh={'SC1': .1, 'FW_E': .01, 'ramp:R1': .02, 'PASSIVE_OMEGA': .03})
    stocks = {'freeway:FW_E': dict(inside=10., outside=0.),
        'ramp:R1': dict(inside=5., outside=7.), 'movement:m': dict(inside=2., outside=99.),
        'origin:FW_E': dict(inside=0., outside=1000.), 'storage:unowned': dict(inside=3., outside=1.)}
    point = NS(objective=2., ttt=2., far=0., control_area=dict(
        near_score_veh_h=2., ttt_veh_h=2., additional_cost_veh_h=0.),
        control_area_response={'residence':[dict(dt_h=.1, inside_veh={k:v['inside'] for k,v in stocks.items()})]})
    return cfg, spec, stocks, point


class TerminalTests(unittest.TestCase):
    def test_disabled_preserves_point(self):
        cfg, _, stocks, point = fixture(); before = copy.deepcopy(vars(point))
        terminal.apply(point, NS(stocks=stocks), cfg)
        self.assertEqual(before, vars(point))
        self.assertEqual(omega_costs(point, cfg)[1]['total_veh_h'], 2.)

    def test_scope_and_once_only_partition(self):
        cfg, spec, stocks, point = fixture()
        terminal.configure({'adapter': {'sdmpc_terminal_cost': spec}}, cfg)
        terminal.apply(point, NS(stocks=stocks), cfg)
        self.assertEqual(point.ttt, 2.)
        self.assertAlmostEqual(point.objective, 4.17)
        local, partition = omega_costs(point, cfg)
        self.assertAlmostEqual(local['FW_E']['cost'], 3.)
        self.assertAlmostEqual(partition['costs']['PASSIVE_OMEGA'], .57)
        self.assertAlmostEqual(partition['total_veh_h'], point.objective)
        self.assertEqual(point.control_area['terminal_cost']['inside_veh'], 20.)
        terminal.validate_score(point.control_area, point.objective, cfg)

    def test_same_total_inventory_different_locations_has_explicit_value(self):
        cfg, spec, stocks, _ = fixture()
        terminal.configure({'adapter': {'sdmpc_terminal_cost': spec}}, cfg)
        first = terminal.evaluate(stocks, cfg)
        stocks['ramp:R1']['inside'] -= 1
        stocks['freeway:FW_E']['inside'] += 1
        second = terminal.evaluate(stocks, cfg)
        self.assertEqual(first['inside_veh'], second['inside_veh'])
        self.assertAlmostEqual(second['total_veh_h']-first['total_veh_h'], .03)

    def test_missing_negative_or_nonfinite_P_fails(self):
        cfg, spec, _, _ = fixture()
        for bad in (-1., float('inf'), float('nan'), True):
            trial = copy.deepcopy(spec); trial['p_diag_h_per_veh']['FW_E'] = bad
            with self.assertRaises(ValueError):
                terminal.configure({'adapter': {'sdmpc_terminal_cost': trial}}, cfg)
        del spec['p_diag_h_per_veh']['ramp:R1']
        with self.assertRaises(ValueError):
            terminal.configure({'adapter': {'sdmpc_terminal_cost': spec}}, cfg)

    def test_tampered_or_unconfigured_receipt_fails(self):
        cfg, spec, stocks, point = fixture()
        terminal.configure({'adapter': {'sdmpc_terminal_cost': spec}}, cfg)
        terminal.apply(point, NS(stocks=stocks), cfg)
        for field in ('total_veh_h', 'inside_veh', 'specification_sha256'):
            trial = copy.deepcopy(point.control_area)
            trial['terminal_cost'][field] = 99
            with self.assertRaises(ValueError): terminal.validate_score(trial, point.objective, cfg)
        terminal.configure({}, cfg)
        with self.assertRaises(ValueError): terminal.validate_score(point.control_area, point.objective, cfg)

    def test_final_command_boundary_accepts_only_its_configured_P(self):
        from diagnostics.test_joint_leader_result import fixture as joint_fixture
        from evaluation.controllers.area_leader_objective import validate_joint_leader_result
        response = joint_fixture(); score = response['final_score']
        control = response['game']['control']
        ramps = tuple(control.ramp_metering)
        cfg = NS(network=NS(signals=tuple('SC'+str(i) for i in range(1,18)),
            freeway_links=('FW_E','FW_W'), ramps=ramps,
            ramp_to_freeway={r: 'FW_E' if r.endswith('E') else 'FW_W' for r in ramps},
            control_area_enabled=True, control_area_beta_seconds=0, sdmpc_cost_ownership={}))
        spec = dict(schema=terminal.SCHEMA, design='transport fixture',
                    p_diag_h_per_veh=dict.fromkeys(terminal.group_owners(cfg), .01))
        terminal.configure({'adapter': {'sdmpc_terminal_cost': spec}}, cfg)
        point = NS(objective=8., far=0., control_area=dict(score['control_area'],
            near_score_veh_h=8., beta_seconds=0.))
        terminal.apply(point, NS(stocks={'ramp:'+ramps[0]: dict(inside=10.,outside=0.)}), cfg)
        score.update(objective_veh_h=point.objective, control_area=point.control_area)
        result = validate_joint_leader_result(response, target_np_veh=340., target_nuf_veh_h=7200., cfg=cfg)
        self.assertEqual(result['objective_value'], 9.)
        cfg.network.sdmpc_terminal_cost['p_diag_h_per_veh']['ramp:'+ramps[0]] = .02
        with self.assertRaises(ValueError):
            validate_joint_leader_result(response, target_np_veh=340., target_nuf_veh_h=7200., cfg=cfg)

    def test_real_tangent_instrumentation_preserves_terminal_gradient(self):
        from evaluation.controllers.sdmpc_tangent_runtime import Transform, namespace
        from evaluation.controllers import sdmpc_dual as ad
        code = ast.fix_missing_locations(Transform().visit(ast.parse(Path(terminal.__file__).read_text())))
        env = dict(__name__='terminal_instrumentation_test', **namespace())
        exec(compile(code, terminal.__file__, 'exec'), env)
        cfg, spec, stocks, point = fixture()
        terminal.configure({'adapter': {'sdmpc_terminal_cost': spec}}, cfg)
        stocks['freeway:FW_E']['inside'] = ad.Dual(10., {0: 1.}, ad.Trace([.001]))
        result = env['evaluate'](stocks, cfg)
        value = result['cost_by_owner_veh_h']['FW_E']
        self.assertAlmostEqual(ad.primal(value), 1.5)
        self.assertAlmostEqual(ad.derivative(value)[0], .2)

    def test_compiled_reverse_ownership_contains_external_terminal_sensitivity(self):
        from evaluation.controllers.sdmpc_tangent_runtime import Transform, namespace
        from evaluation.controllers import sdmpc_tangent_reverse as rev
        from evaluation.controllers import sdmpc as module
        import inspect
        # The same transform used by the real worker instruments arithmetic and
        # fsum. A city's control can affect another owner's terminal stock.
        env = dict(__name__='terminal_reverse_test', **namespace())
        env.update(_tangent_float=rev.float_keep, _tangent_math=rev.MathProxy())
        tree = ast.fix_missing_locations(Transform().visit(ast.parse(Path(terminal.__file__).read_text())))
        exec(compile(tree, terminal.__file__, 'exec'), env)
        cfg, spec, stocks, point = fixture()
        terminal.configure({'adapter': {'sdmpc_terminal_cost': spec}}, cfg)
        trace = rev.Trace([.001], track_stencils=False)
        stocks['freeway:FW_E']['inside'] = rev.Dual(10., {0: 1.}, trace)
        result = env['evaluate'](stocks, cfg)
        # Route the reverse scalar through the real omega_costs implementation,
        # not only the terminal helper. Original near-residence has no tangent.
        point.control_area.update(terminal_cost=result, additional_cost_veh_h=result['total_veh_h'],
            selection_score_veh_h=point.objective+result['total_veh_h'])
        point.objective += result['total_veh_h']
        source = inspect.getsource(module.omega_costs)
        ns = dict(__name__='omega_reverse_test', PASSIVE=terminal.PASSIVE, **namespace())
        ns['math'] = rev.MathProxy()
        exec(compile(ast.fix_missing_locations(Transform().visit(ast.parse(source))), '<omega-reverse>', 'exec'), ns)
        # validate_score is normally instrumented on import too.
        original = terminal.validate_score
        terminal.validate_score = env['validate_score']
        try:
            local, partition = ns['omega_costs'](point, cfg)
        finally:
            terminal.validate_score = original
        jacobian = trace.jacobian([result['cost_by_owner_veh_h']['FW_E'],
                                  local['FW_E']['cost'], partition['total_veh_h']], 1)
        for row in jacobian:
            self.assertAlmostEqual(row[0], .2)


if __name__ == '__main__':
    unittest.main()
