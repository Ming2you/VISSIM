"""Prepare one10--11 shared-lane candidate from the existing route allocator.

This isolates the first ramp group against the same aggregate model. It does
not replace, merge with, or qualify the rejected19--25 candidate.
"""
import ast
import copy
import math
from pathlib import Path
from diagnostics.repin_v3c3_review_20261001.junction_calibration125 import run as h

HERE = Path(__file__).resolve().parent


def replace_once(text, old, new):
    assert text.count(old) == 1, old[:100]
    return text.replace(old, new)


def sources():
    old = h.read(h.R/'prehead_storage171/forecast/executed_function_sources.json')
    s = old['RouteLaneRegion']
    # Remove the independent19 half-cell mechanism from this isolated region;
    # no coefficient or mechanism in the comparison aggregate model is changed.
    tree = ast.parse(s).body[0]
    lines = s.splitlines(keepends=True)
    for node in reversed(tree.body):
        if isinstance(node, ast.FunctionDef) and node.name.startswith('_split19_'):
            del lines[node.lineno-1:node.end_lineno]
    s = ''.join(lines)
    s = replace_once(s, '        self._split19_init(state,cfg,observations)\n', '')
    start = s.index('        self.split19_before =')
    end = s.index('        self.n0 =', start)
    s = s[:start]+s[end:]
    s = replace_once(s, '        self.free[19] = [max(0.,cfg.network.rho_max*half-n) for n in self.split19_n0[0]]\n', '')
    start = s.index('        through[19] =')
    end = s.index('        for off,requests', start)
    s = s[:start]+s[end:]
    start = s.index('                if i == 18:')
    end = s.index('                if g is not None:', start)
    s = s[:start]+s[end:]
    start = s.index('        for g,moved in enumerate(self.split19_inner):')
    end = s.index('        for i,rows in self.next.items():', start)
    s = s[:start]+s[end:]
    s = replace_once(s, '            if i == 19:\n                self._split19_exchange(cfg)\n                continue\n', '')
    s = replace_once(s, '        if i == 19:\n            return self._split19_speed(state,cfg,control,mn,exposure)\n', '')
    s = replace_once(s, '            if i == 20:up = self.split19_oldv[1][g]\n', '')
    start = s.index('        self.split19 = self.split19_next;')
    end = s.index('        self.assert_partition(state)', start)
    s = s[:start]+s[end:]
    assert 'split19' not in s
    s = replace_once(s, "        if self.receiving_cells not in ([], [21]):\n            raise ValueError('Diagnostic receiving scope is cell21 only')", "        if self.cells != [10,11] or self.groups != 4 or self.receiving_cells != [10,11]:\n            raise ValueError('173 requires only the declared10--11 four-lane region')")
    s = replace_once(s, '            matrix = _lateral168_matrix(self, i, ns, state.time_sec, dt*3600)', '''            matrix = []
            for g,rates in enumerate(self.rates):
                hazard = sum(rates)
                matrix.append([ns[g]*(1.-math.exp(-hazard*dt*3600))*r/hazard if hazard else 0. for r in rates])''')
    s = replace_once(s, '                    classes = {key:n*amount/ns[g] for key,n in old[g].items()}', '''                    # Exit-intent vehicles retain an accessible lane and only
                    # move toward it. Old stocks are never teleported.
                    classes = {key:n*amount/ns[g] for key,n in old[g].items()
                        if key.rsplit('|',1)[-1] != '10682' or (g > 0 and k == g-1)}
                    amount = sum(classes.values())''')
    s = replace_once(s, '        inlet = {}\n', '        inlet = {}\n        inlet_count = {}\n')
    s = replace_once(s, "            elif i == self.cells[0]-1 and physical['lane_index'] in mapping:", "            if i < self.cells[0] and physical['lane_index'] in mapping:")
    s = replace_once(s, '                g = mapping[physical[\'lane_index\']]\n', '''                from evaluation.controllers.offramp_routing import _position
                _,position,_ = _position(runtime,physical['link_no'],physical['position_m'])
                inlet_x = runtime['bounds'][road][self.cells[0]]
                if not inlet_x-500. <= position < inlet_x:
                    continue
                g = mapping[physical['lane_index']]
''')
    s = replace_once(s, '                    inlet.setdefault(target,[0.]*self.groups)[g] += value', '''                    inlet.setdefault(target,[0.]*self.groups)[g] += value*physical['speed_kph']
                    inlet_count.setdefault(target,[0.]*self.groups)[g] += value''')
    s = replace_once(s, '        self.inlet = {key:[n/sum(row) for n in row] for key,row in inlet.items() if sum(row)}', '''        self.inlet = {}
        for key,row in inlet.items():
            observed = row if sum(row) else inlet_count[key]
            self.inlet[key] = [n/sum(observed) for n in observed]
        self.inlet.setdefault('10682',[1.,0.,0.,0.])
        self.initial_inlet = copy.deepcopy(self.inlet)''')
    # Assert the change touches only the region class. The published METANET
    # expression, shared mass transport, and caller order are reused verbatim.
    ast.parse(s)
    result = dict(old, RouteLaneRegion=s)
    assert all(result[k] == v for k,v in old.items() if k != 'RouteLaneRegion')
    return result


def prepare():
    assert not (HERE/'protocol.json').exists(), 'Preserve prior attempt'
    prior = h.read(h.R/'merge_target172/protocol.json')
    path = h.F/'cohort_early/s29_none_frames.json.gz'
    data = h.read(path)
    known = h.read(h.R/'lane10682_transport/exchange_profile.json')
    assert h.sha(path) == known['sha256']
    assert data['fields'] == ['cell','speed_kmh','x_m','lane']
    frames = {float(t):{vid:[vid,r[0],r[2],r[3],r[1]] for vid,r in rows.items()}
              for t,rows in data['frames'].items()}
    counts = [[0]*4 for _ in range(4)]; exposure = [0]*4
    censored = 0
    for t,u in zip(sorted(frames),sorted(frames)[1:]):
        assert abs(u-t-5)<1e-7
        for vid,x in frames[t].items():
            if x[1] not in (10,11):continue
            y = frames[u].get(vid)
            if y is None or y[1] != x[1]:
                censored += 1;continue
            g,k = x[3]-1,y[3]-1
            assert 0<=g<4 and 0<=k<4
            exposure[g] += 1
            if k != g:counts[g][k] += 1
    rates = []
    for g,row in enumerate(counts):
        total=sum(row); assert total<exposure[g]
        hazard=-math.log1p(-total/exposure[g])/5
        rates.append([hazard*n/total if total else 0. for n in row])
    spec=dict(cells=[10,11],lanes=4,exchange_rates_per_sec=rates,
        inlet_lane_to_group={str(k+1):k for k in range(4)},off_access={'10682':0},
        ramp_access={'RM_C10639':0},congested_receiving_cells=[10,11])
    funcs=sources()
    h.save(HERE/'executed_function_sources.json',funcs)
    h.save(HERE/'spec.json',spec)
    h.save(HERE/'protocol.json',dict(previous_goal_turn='PROGRESS172 target-lane and port-state evidence',
        comparison='Matched aggregate versus10--11 only, SAME153 coefficients/current171 admission. Not a claimed incremental improvement of the19--25 candidate; combination and full runtime remain separate required gates.',
        hypothesis='Explicit target-lane destination stock and shared receiving can represent10639 queue formation without reducing every meter service rate.',
        changed='Only10--11 four-lane sending, receiving, shared ramp/mainline allocation, finite lateral transport and per-lane existing METANET. Existing FD-derived receiving envelope; no added capacity/command bonus.',
        invariants='All sources/commands/routes/FD/speed coefficients/integration/ramp head pulses/off storage and drain/VSL history/total waiting are unchanged. Initial lane stocks partition existing canonical inventory. No future native states in predictions.',
        approximation='Current500m speed-weighted inlet composition is frozen. Lateral endpoint hazards are censored approximations, not exact lane-change rates. Existing ramp-first use of shared receiving is an approximation, not a measured microscopic priority claim. Merge position insidecell10 remains cell-aggregated.',
        training=dict(seed=29,arm='early_none',window=[min(frames),max(frames)],counts=counts,exposures=exposure,censored=censored),
        validation='Four29late and four67late policies plus61hold/release recovery guard,450s each; previously inspected states, not blind holdout. No refit to these outcomes.',
        budget=dict(max_forecasts=21,coefficient_grid=0,native=0,FZP=0),
        gate='Exact disabled parity/mass/destination/storage;10639 release merge error improves without harming held-meter flow or61recovery. Record full component TTT/ramp waiting, all four East ramp flows and policy ranks. No production adoption or9000 from a local pass.',
        protected_sha256=prior['protected_sha256'], STOP=prior['STOP'],
        pins={str(path):h.sha(path),str(Path(__file__)):h.sha(__file__),str(h.ROOT/'evaluation/controllers/physical_ramp_boundary.py'):h.sha(h.ROOT/'evaluation/controllers/physical_ramp_boundary.py')}))
    h.save(HERE/'preflight.json',dict(status='source_prepared_only_runtime_preflight_pending',
        class_ast_valid=True,other_four_functions_exact171=True,spec=spec))
    print('prepared173',counts,exposure, 'bounded21 forecasts; runtime parity required')


if __name__=='__main__':prepare()
