"""Command CSV clock versus actual readback, for the primary one-second pair.

No file reads, COM, simulator, or controller model. The caller supplies already
pinned commands/SG membership and source text; cadence/coverage stays in verifier.
"""
from bisect import bisect_right
from collections import Counter
from decimal import Decimal
import re

from diagnostics.live_beta0_first_interval_audit import expected_signal, expected_ramp
from evaluation.controllers.signal_timing_oracle import decisions_from_action_rows, intended_state


def require(value, message):
    if not value:
        raise ValueError(message)


def num(value):
    x = Decimal(str(value))
    require(x.is_finite(), 'Nonfinite command clock value')
    return x


def integer(value):
    x = num(value)
    require(x >= 0 and x == int(x), 'Expected nonnegative command clock integer')
    return int(x)


def native_options(vbs_text, generated_config_text):
    """Use pinned source literals, never invent a meter capacity or clearance."""
    constants = {}
    for name in ('RAMP_CYCLE_SEC', 'RAMP_AMBER_SEC', 'AMBER_SEC'):
        values = re.findall(r'^Const ' + name + r'\s*=\s*([0-9.]+)\s*$', vbs_text, re.M)
        require(len(values) == 1, 'Missing/ambiguous native constant: ' + name)
        constants[name] = num(values[0])
    # The reused exact diagnostic functions implement this existing contract.
    require(constants == {'RAMP_CYCLE_SEC': 10, 'RAMP_AMBER_SEC': 1, 'AMBER_SEC': 3},
            'Native constants differ from the reused command-state oracle')
    lists = {}
    for name in ('RW_RAMP_METER_SCS', 'RW_RAMP_METER_CAPACITIES_VPH'):
        values = re.findall(r'^' + name + r'\s*=\s*"([^"\r\n]+)"\s*$', generated_config_text, re.M)
        require(len(values) == 1, 'Missing/ambiguous native meter list: ' + name)
        lists[name] = values[0].split(',')
    scs = [str(integer(x)) for x in lists['RW_RAMP_METER_SCS']]
    caps = [num(x) for x in lists['RW_RAMP_METER_CAPACITIES_VPH']]
    require(len(scs) == len(caps) and len(scs) == len(set(scs)) and
            all(int(sc) > 0 for sc in scs) and all(cap > 0 for cap in caps), 'Invalid meter source mapping')
    return dict(zip(scs, caps))


def native_clock_options(pinned_plan_text, plan_groups):
    """Parse only the caller's SHA-verified generated sibling, never CSV intent."""
    text = re.sub(r'&\s*_\r?\n\s*', '&', pinned_plan_text)
    declarations = re.findall(r'^RW_SIGNAL_NATIVE_CLOCKS\s*=', text, re.M)
    if not declarations:
        return {}
    matches = re.findall(r'^RW_SIGNAL_NATIVE_CLOCKS\s*=\s*((?:"[^"]*"\s*&\s*)*"[^"]*")\s*$', text, re.M)
    require(len(declarations) == len(matches) == 1, 'Missing/ambiguous literal native clock config')
    value = ''.join(re.findall(r'"([^"]*)"', matches[0]))
    if not value:
        return {}
    result = {}
    for token in value.split(';'):
        parts = token.split(':')
        require(len(parts) == 5 and re.fullmatch(r'[1-9][0-9]*', parts[0]), 'Malformed native clock token')
        sc, kind, cycle, idle, mask = parts
        require(sc in plan_groups and sc not in result, 'Unknown/duplicate native clock controller')
        cycle, idle = num(cycle), num(idle)
        require(kind in ('serial', 'concurrent_p1_p2') and 0 < cycle <= 10000 and 0 <= idle <= cycle
                and re.fullmatch(r'[01]{4}', mask) and mask.count('1') >= 2, 'Invalid native clock contract')
        require(kind != 'concurrent_p1_p2' or (mask == '1101' and idle == 0), 'Invalid concurrent native clock')
        result[sc] = {'kind': kind, 'cycle_sec': cycle, 'idle_sec': idle, 'mask': mask}
    require(set(result) == set(plan_groups), 'Incomplete native clock controller cohort')
    return result


class CommandClock:
    """One-second primary clock. Event-continuous calls must use another audit.

    batches maps actual application seconds to complete ordered action CSV rows.
    plan_groups is the verifier's pinned SC -> SG -> window-count dictionary.
    meter_capacities comes from native_options on pinned VBS/config source text.
    """
    def __init__(self, batches, plan_groups, meter_capacities, *, native_clock_plans=None, ramp_amber_sec=1):
        require(batches, 'No command batches for execution clock')
        require(type(ramp_amber_sec) in (int, float) and ramp_amber_sec in (0, 1),
                'Ramp amber must be numeric 0 or 1; source authority is a caller obligation')
        self.ramp_amber_sec = int(ramp_amber_sec)
        self.times = sorted(integer(t) for t in batches)
        require(len(self.times) == len(set(self.times)) and self.times[0] >= 1, 'Invalid command application times')
        self.groups = plan_groups
        self.native_clock_plans = dict(native_clock_plans or {})
        require(not self.native_clock_plans or set(self.native_clock_plans) == set(plan_groups),
                'Incomplete native clock controller cohort')
        self.snapshots = []
        self.apply_vsl = {}
        signals, ramps, vsl = {}, {}, {}
        for t in self.times:
            rows = batches[t]
            window_counts = Counter(); cycles = {}; signal_counts = Counter(); meter_counts = Counter(); vsl_counts = Counter(); axes = {}
            for row in rows:
                kind = row['kind']
                require(kind in ('signal', 'signal_sg', 'ramp_meter', 'vsl'), 'Unknown command kind')
                if kind in ('signal', 'signal_sg'):
                    sc = str(integer(row['sc_no']))
                    require(sc in plan_groups, 'Command controller absent from pinned SG plan')
                    if kind == 'signal':
                        signal_counts[sc] += 1
                        num(row['offset'])
                        for p in range(1, 5): num(row[f'p{p}_green'])
                        if sc in self.native_clock_plans:
                            axes[sc] = (tuple(num(row[f'p{p}_green']) for p in range(1, 5)), num(row['offset']))
                    else:
                        sg = str(integer(row['dsd_no']))
                        require(sg in plan_groups[sc], 'Command SG absent from pinned plan')
                        a, b, cycle, offset = (num(row[k]) for k in ('p1_green', 'p2_green', 'green_sec', 'offset'))
                        require(0 <= a < b <= cycle and cycle > 0 and 0 <= offset < cycle, 'Invalid delivered SG window')
                        window_counts[sc, sg] += 1
                        pair = (cycle, offset)
                        require(sc not in cycles or cycles[sc] == pair, 'Inconsistent delivered SC clock')
                        cycles[sc] = pair
                elif kind == 'ramp_meter':
                    sc = str(integer(row['sc_no'])); meter_counts[sc] += 1
                    require(sc in meter_capacities, 'Meter absent from pinned native mapping')
                    green, rate, cap = num(row['green_sec']), num(row['rate_vph']), num(meter_capacities[sc])
                    require(0 <= green <= 10 and 0 <= rate <= cap and cap > 0, 'Invalid meter command bounds')
                    # Same CDbl arithmetic order and half-even Round as native RampActionValid.
                    want = round(10.0 * float(rate) / float(cap))
                    require(abs(green - want) <= Decimal('0.001'), 'Meter rate/green quantization differs')
                    ramps[sc] = float(green)
                else:
                    dsd = str(integer(row['dsd_no'])); vsl_counts[dsd] += 1
                    speed = integer(row['speed_kph'])
                    require(int(dsd) > 0 and speed > 0, 'Invalid VSL command address/value')
                    vsl[dsd] = speed; self.apply_vsl[t, dsd] = speed
            require(all(n == 1 for n in signal_counts.values()) and all(n == 1 for n in meter_counts.values())
                    and all(n == 1 for n in vsl_counts.values()), 'Duplicate command address')
            require(set(cycles) == set(signal_counts), 'Urban axis/window controller set differs')
            for sc in signal_counts:
                require(all(window_counts[sc, sg] == count for sg, count in plan_groups[sc].items()),
                        'Delivered SG window count differs from pinned plan (including RED-only)')
                if sc in self.native_clock_plans:
                    spec = self.native_clock_plans[sc]
                    greens, offset = axes[sc]
                    require(all(g == 0 or 5 <= g <= 90 for g in greens)
                            and ''.join('1' if g > 0 else '0' for g in greens) == spec['mask'],
                            'Native command physical bounds or live phase mask differs')
                    if spec['kind'] == 'concurrent_p1_p2':
                        require(greens[0] + 3 <= greens[1], 'Native concurrent phase clearance conflict')
                        expected_cycle = greens[1] + greens[3] + 6
                    else:
                        expected_cycle = sum(greens) + 3 * spec['mask'].count('1') + spec['idle_sec']
                    require(expected_cycle == spec['cycle_sec'] and cycles[sc] == (expected_cycle, offset),
                            'Delivered native cycle or axis/window offset differs from pinned source')
            decisions = decisions_from_action_rows([{**r, 'sim_sec': t} for r in rows])
            if signal_counts:
                require(len(decisions) == 1, 'Expected one urban decision clock')
                signals.update(decisions[0]['controllers'])
            else: require(not decisions, 'Unexpected urban clock')
            self.snapshots.append({'signals': signals.copy(), 'ramps': ramps.copy(), 'vsl': vsl.copy()})

    def check_signal(self, row):
        sec = integer(row['sim_sec']); stage = row['stage']
        require(stage in ('immediate', 'post_step'), 'Unsupported readback stage')
        # post_step precedes the new write at t, including a decision/offset boundary.
        applied_sec = sec if stage == 'immediate' else sec - 1
        index = bisect_right(self.times, applied_sec) - 1
        require(index >= 0, 'No prior command for actual signal readback')
        snapshot = self.snapshots[index]
        sc, sg = str(integer(row['sc_no'])), str(integer(row['sg_no']))
        if sc in snapshot['ramps']:
            require(sg == '1', 'Unexpected native meter SG')
            expected = self.expected_meter_state(snapshot['ramps'][sc], applied_sec)
        else:
            require(sc in snapshot['signals'] and sg in self.groups[sc], 'No owned urban command for readback')
            expected = self.expected_urban_state(sc, snapshot['signals'][sc], sg, applied_sec)
        require(row['ok'] == '1' and row['requested_state'].strip().upper() == expected
                and row['readback_state'].strip().upper() == expected,
                f'Command clock mismatch at {sec}/{stage} {sc}:{sg}: expected {expected}')
        return expected

    def expected_meter_state(self, green, sec):
        # Preserve the historical oracle exactly when the optional policy is off.
        # New zero-amber policy changes meters only, on the same pre-step clock.
        if self.ramp_amber_sec == 1:
            return expected_ramp(green, sec)
        return 'RED' if green <= 0 else 'GREEN' if sec % 10. < green else 'RED'

    def expected_urban_state(self, sc, controller, sg, sec):
        if sc not in self.native_clock_plans:
            return expected_signal(controller, sg, sec)
        cycle = controller['cycle_sec']
        # Native COM writes at t drive the frame recorded after the next step.
        # The source clock is therefore evaluated at t+1, matching the runner's
        # explicit native-only pre-step alignment. Legacy and meter clocks stay
        # on their original timing convention.
        pos = (sec + controller['offset_sec'] + 1) % cycle
        return intended_state(controller['windows'].get(sg, []), pos, cycle, 3.)

    def check_vsl(self, row):
        sec, dsd = integer(row['sim_sec']), str(integer(row['dsd_no']))
        require(row['stage'] == 'immediate' and integer(row['veh_class_no']) in (10, 20, 30, 70), 'Invalid VSL readback stage/class')
        require((sec, dsd) in self.apply_vsl, 'No VSL application for actual readback address/time')
        expected = self.apply_vsl[sec, dsd]
        require(row['ok'] == '1' and num(row['requested_kph']) == expected
                and integer(row['readback_distribution_no']) == expected,
                f'VSL command/readback mismatch at {sec} DSD {dsd}')
        return expected
