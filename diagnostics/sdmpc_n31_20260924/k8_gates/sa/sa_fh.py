"""FH: FZP island transplant (K8 PREDECL §3.1 FH order 1-9 as replaced by AMENDMENT_1 r2 §3.1 steps 5-6).

Design: the transplant happens INSIDE the capture adapter process, at the one point where the merged native state and
the lane observation exist together (lane_plant_runtime.observe_state returns (merged state_json, lane observation),
configure_runtime then calls bind_current_routes, the projection, the lane plant and SA).  Every later step is the
DEPLOYED code acting on the substituted observation, in the deployed order, so the declared steps are executed by the
declared functions rather than re-implemented:

  step  declared (PREDECL §3.1, AMENDMENT_1 §3.1)                     done by
  1     open the same-T TL3 template of the arm's commit              the same replay state, tuning and code root as
                                                                      the arm's TL3 capture (sa_capture.py); with the
                                                                      transplant disabled the capture is the TL3 one
                                                                      (H-0)
  2     FW_W/FW_E cells = bin_frame(geometry, rows, road, True)        LPR.initialize on the substituted frame rows of
                                                                      the two chains (FZP seed rows, ids remapped)
  3     ports 10491/10481 = DelayedPort(cap, length, profile speed,    LPR.initialize on the substituted rows of the
        [[pos, speed, lane]], T, interval_service), mirror cap - stock two connectors (move_link + DelayedPort)
  4     FW_W exit share = FZP [T-150, T] 1132 branch passes (FD3)      observation['off_split_ratio'] of 10491 / 10479
                                                                      replaced by exits / (exits + through at the end
                                                                      of the off's from_cell), the obs150 definition
  5     islands 32/10778/129/10777/127/10695: runner queue_bins        the substituted records / link counts / stopped
        (7.0 m, stopped < 1 km/h), deployed projection operator       counts / speeds / tails / queue_bins -> the
        (10695 50/50 two-source split, its SC1001_to_SC2002 share     deployed build_local_observation_summary
        replaces the template's)
  6     re-seed in_SC1001_W (+ the 10695 share) reservations with the  the deployed seed_urban_arrival_buffer (K8-4 S5
        deployed rule incl. K8-4 S5, write storage_seed_split_by_link  rule, its storage_seed_split_by_link) and the
        for island links, pair like pair_initial_arrival_releases     deployed pairing (RS order) on the substituted
                                                                      projection
  7     SA arm: SA.initialize (FZP vehicle records + FZP route        RS hook #3 on the substituted state_json (records
        column, N13); BASE: deployed 1/14                             and the vehicle_routes built from the FZP route
                                                                      columns by bind_current_routes)
  8     entry OBS (EO 150 s bundles), gate demand = FZP link 32       sa_worker job: obs_entry (seed EO) and
        entries per 150 s (FD7)                                       gate_demand['in_SC1001_W'] (gate_rates() below)
  9     seed_from_projection                                          area_runtime.configure (RS order)
Declared differences (FD1-FD8): FD1 outside islands/chains/ports = s31 template values; FD2 entry OBS oracle; FD3 exit
share held; FD4 FZP 5 s frame (T+0.1 for the state at T); FD5 VSL 110 (sa_worker vsl110); FD6 no obs150 (obs150-derived
fields: ramp arrival shares, other off splits, link_departures_window, queue_counters, detectors stay s31); FD7 gate
demand oracle; FD8 other ports' exit shares = template values.

Two halves:
  driver side (pandas, sa_capture.py):  build_spec(...) -> fh spec JSON (rows at T+0.1, exit counts, ids)
  child side (stdlib only, sa_cap_child.py): Transplant(spec).observe_state wrapper + record (H-1/H-2/H-2b inputs)
"""
from __future__ import annotations

import copy
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

FW_CHAINS = {'FW_W': (26, 10771, 120), 'FW_E': (74, 10699, 2, 10613, 119, 10702, 24)}
PORT_LINKS = (10491, 10481)
ISLAND_LINKS = (32, 10778, 129, 10777, 127, 10695)
SUB_LINKS = tuple(sorted(set(FW_CHAINS['FW_W']) | set(FW_CHAINS['FW_E']) | set(PORT_LINKS) | set(ISLAND_LINKS)))
EXIT_OFFS = ('10491', '10479')          # OR_D_W (route decision 1132) signal / direct connectors
EXTRA_LINKS = (10479, 31, 124)          # exit share crossing, W_out observation (FH G6-6 report)
ID_OFFSET = 50_000_000
STOPPED_KPH = 1.0                       # runner B1A_STOPPED_THRESHOLD_KPH
QUEUE_BIN_M = 7.0
ENTRY_CLAMP_M = 8.0                     # runner clamps Pos in [-8, 0) to 0 (VBS B1A_ENTRY_CLAMPED)
FZP_COLS = ('NO', 'LINK', 'LANE', 'POS', 'SPEED', 'LENGTH', 'ROUTDECNO', 'ROUTENO', 'ROUTDECTYPE', 'NEXTLINK')


# =============================================================================================== driver side
def _nullable(v):
    try:
        import pandas as pd
        if v is None or pd.isna(v):
            return None
    except Exception:
        if v is None:
            return None
    return v


def frame_rows(df, t, links):
    """FZP rows at frame t (exact SIMSEC match) on `links` as plain lists in FZP_COLS order."""
    sub = df[(df.SIMSEC == t) & df.LINK.isin(list(links))]
    out = []
    for r in sub.itertuples(index=False):
        out.append([int(r.NO), int(r.LINK), int(r.LANE), float(r.POS), float(r.SPEED), float(r.LENGTH),
                    _nullable(r.ROUTDECNO), _nullable(r.ROUTENO),
                    (None if _nullable(r.ROUTDECTYPE) in (None, 'nan', '') else str(r.ROUTDECTYPE)),
                    _nullable(r.NEXTLINK)])
    for row in out:
        for i in (6, 7, 9):
            if row[i] is not None:
                row[i] = float(row[i])
    return out


def chain_pos(road, link, pos, chains):
    for c in chains[road]:
        if int(c['link']) == int(link):
            return float(c['offset_m']) + float(pos)
    return None


def exit_counts(df, T, geometry, offs=EXIT_OFFS, road='FW_W'):
    """FD3: per off connector c, in frames (T-150, T]: n_exit = vehicles first seen on c whose previous frame was on
    the road chain (or unseen); n_through = chain crossings of the station at the END of c's from_cell (obs150
    off_split definition, obs150_observation.py:346).  ratio = n_exit / (n_exit + n_through)."""
    chains = geometry['chains']
    bounds = geometry['bounds'][road]
    offrow = {str(b['connector']): b for b in geometry['boundaries'] if b.get('kind') == 'offramp'}
    lo, hi = T - 150.0 + 0.1, T + 0.1          # transitions (t-5 -> t) for frames t in (lo, hi]
    chain_links = {int(c['link']) for c in chains[road]}
    out = {}
    for off in offs:
        out[off] = {'n_exit': 0, 'n_through': 0, 'station_m': float(bounds[int(offrow[off]['from_cell']) + 1]),
                    'from_cell': int(offrow[off]['from_cell']), 'window': [lo, hi]}
    prev, prev_t = {}, None
    for t in sorted(x for x in set(df.SIMSEC.tolist()) if lo - 5.0 - 1e-6 <= x <= hi + 1e-6):
        cur = {}
        for r in df[df.SIMSEC == t].itertuples(index=False):
            cur[int(r.NO)] = (int(r.LINK), float(r.POS))
        if prev_t is None or t - prev_t > 5.0 + 1e-6:
            prev = {}                               # no contiguous predecessor frame: count nothing for t
        if prev_t is not None and t - prev_t <= 5.0 + 1e-6 and lo + 1e-6 < t <= hi + 1e-6:
            for vid, (link, p) in cur.items():
                was = prev.get(vid)
                for off in offs:
                    if link == int(off) and (was is None or was[0] != int(off)):
                        if was is None or was[0] in chain_links:
                            out[off]['n_exit'] += 1
                if link in chain_links and was is not None and was[0] in chain_links:
                    x0 = chain_pos(road, was[0], was[1], chains)
                    x1 = chain_pos(road, link, p, chains)
                    for off in offs:
                        s = out[off]['station_m']
                        if x0 is not None and x1 is not None and x0 < s <= x1:
                            out[off]['n_through'] += 1
        prev, prev_t = cur, t
    for off, row in out.items():
        tot = row['n_exit'] + row['n_through']
        row['ratio'] = row['n_exit'] / tot if tot else None
    return out


def gate_rates(ext_df, T, H, link=32, block=150.0):
    """FD7: FZP link-32 entries per 150 s block (first frame of a vehicle on 32 within the block) in veh/h."""
    seen = {}
    d = ext_df[ext_df.LINK == link]
    for r in d.sort_values('SIMSEC').itertuples(index=False):
        seen.setdefault(int(r.NO), float(r.SIMSEC))
    rates = []
    for k in range(int(H)):
        a, b = T + block * k + 0.1, T + block * (k + 1) + 0.1
        n = sum(1 for t in seen.values() if a < t <= b + 1e-9)
        rates.append(n * 3600.0 / block)
    return rates


def eo_entry_rates(eo_dir, T, H, block=150.0):
    """OBS entry (TL3 OBS, FD2): EO boundaries_30s.csv source rows, cumulative crossings differenced over 150 s blocks
    (window_end_s = t + 0.1), veh/h per road."""
    import csv
    cum = defaultdict(dict)
    with open(Path(eo_dir) / 'boundaries_30s.csv', newline='', encoding='utf-8') as h:
        for row in csv.DictReader(h):
            if row['kind'] != 'source':
                continue
            cum[row['road']][round(float(row['window_end_s']), 1)] = float(row['cumulative_crossings'])
    out, partial = {}, []
    for road in ('FW_W', 'FW_E'):
        rates = []
        for k in range(int(H)):
            a, b = round(T + block * k + 0.1, 1), round(T + block * (k + 1) + 0.1, 1)
            if a not in cum[road]:
                raise ValueError(f'EO {road} lacks cumulative crossings at {a}')
            if b not in cum[road]:
                # The EO stops at its last complete 30 s window (8970.1 for the v3c2/v3c3 9000 s runs): the last
                # block's rate is the observed rate of its available part (>= 90 s), sa_common OPERATIONALISATIONS.
                e = max((t for t in cum[road] if a < t < b), default=None)
                if e is None or e - a < 90.0 - 1e-6:
                    raise ValueError(f'EO {road} lacks cumulative crossings at {b} (available part < 90 s)')
                rates.append((cum[road][e] - cum[road][a]) * 3600.0 / (e - a))
                partial.append([road, k, a, e, b])
                continue
            rates.append((cum[road][b] - cum[road][a]) * 3600.0 / block)
        out[road] = rates
    if partial:
        out['_partial_blocks'] = partial
    return out


def build_spec(seed, island_T, template_T, ext_parquet, frames_parquet, geometry_json):
    """The child-side transplant spec (plain JSON).  island rows from the x2 ext parquet (islands, ports), chain rows
    from the sa_fzp_frames parquet; exit counts from the chain + 10479/10491 rows of (T-150, T]."""
    import pandas as pd
    geometry = json.loads(Path(geometry_json).read_text(encoding='utf-8-sig'))
    ext = pd.read_parquet(ext_parquet, columns=['SIMSEC'] + list(FZP_COLS))
    frm = pd.read_parquet(frames_parquet, columns=['SIMSEC'] + list(FZP_COLS))
    t = float(island_T) + 0.1
    t_ext = min(ext.SIMSEC.unique(), key=lambda x: abs(x - t))
    t_frm = min(frm.SIMSEC.unique(), key=lambda x: abs(x - t))
    if abs(t_ext - t) > 1e-6 or abs(t_frm - t) > 1e-6:
        raise ValueError(f'FZP frame {t} missing (ext {t_ext}, frames {t_frm})')
    island = frame_rows(ext, t_ext, set(ISLAND_LINKS) | set(PORT_LINKS))
    chain = frame_rows(frm, t_frm, set(FW_CHAINS['FW_W']) | set(FW_CHAINS['FW_E']))
    ids = Counter(r[0] for r in island + chain)
    if any(n > 1 for n in ids.values()):
        raise ValueError('FZP vehicle repeated across island/chain rows')
    exits = exit_counts(frm[frm.LINK.isin(list(FW_CHAINS['FW_W']) + [10479, 10491])], float(island_T), geometry)
    return {'schema': 'k8-sa-fh-spec/v1', 'seed': int(seed), 'island_T': int(island_T), 'template_T': int(template_T),
            'frame_time': t, 'id_offset': ID_OFFSET, 'sub_links': list(SUB_LINKS), 'rows': island + chain,
            'exit_counts': exits, 'counts_by_link': dict(Counter(str(r[1]) for r in island + chain)),
            'geometry_json': str(geometry_json)}


# =============================================================================================== child side
def _record(row, off):
    pos = float(row[3])
    if pos < 0.0:
        pos = 0.0
    speed = float(row[4])
    return {'veh_no': int(row[0]) + off, 'link_no': int(row[1]), 'lane_no': int(row[2]), 'position_m': pos,
            'speed_kph': speed, 'stopped': speed < STOPPED_KPH}


def _frame_row(row, off, width):
    kind = row[8]
    if isinstance(kind, str) and kind.lower() == 'static':
        kind = 'STATIC'
    out = [int(row[0]) + off, int(row[1]), int(row[2]), max(0.0, float(row[3])), float(row[4]), float(row[5]),
           row[6], row[7], kind, row[9]]
    return out + [None] * max(0, width - len(out))


def link_metrics(records):
    by = defaultdict(list)
    for r in records:
        by[str(r['link_no'])].append(r)
    out = {}
    for link, rows in by.items():
        stopped = [r for r in rows if r['stopped']]
        out[link] = dict(count=float(len(rows)), stopped=float(len(stopped)),
                         speed=math.fsum(r['speed_kph'] for r in rows) / len(rows),
                         tail=(min(r['position_m'] for r in stopped) if stopped else 0.0))
    return out


def queue_bins(records):
    bins = defaultdict(lambda: [0.0, 0.0])
    for r in records:
        key = f"{r['link_no']}|{r['lane_no']}|{int(r['position_m'] / QUEUE_BIN_M)}"
        bins[key][0] += 1.0
        if r['stopped']:
            bins[key][1] += 1.0
    return {k: [v[0], v[1]] for k, v in bins.items()}


class Transplant:
    """Child-side substitution (installed by sa_cap_child.py around lane_plant_runtime.observe_state)."""

    def __init__(self, spec, enabled=True):
        self.spec = spec
        self.enabled = enabled
        self.record = {'enabled': enabled, 'seed': spec.get('seed'), 'island_T': spec.get('island_T'),
                       'template_T': spec.get('template_T'), 'calls': 0}

    # --------------------------------------------------------------------------------------------------- substitute
    def substitute(self, context, merged, observation):
        rec = self.record
        rec['calls'] += 1
        if rec['calls'] > 1:
            raise RuntimeError('FH transplant: observe_state called twice')
        before = self._probe(merged)
        rec['before'] = before
        if not self.enabled:
            rec['after'] = before
            return merged, observation
        chains = {road: [int(c['link']) if isinstance(c, dict) else int(c) for c in rows]
                  for road, rows in context['geometry']['chains'].items()}
        for road, links in FW_CHAINS.items():
            if tuple(chains.get(road, ())) != links:
                raise RuntimeError(f'FH transplant: plant chain {road} {chains.get(road)} != {links}')
        sub = {int(x) for x in self.spec['sub_links']}
        off = int(self.spec['id_offset'])
        vr = merged['vehicle_records']
        kept = [r for r in vr['records'] if int(r['link_no']) not in sub]
        removed = Counter(str(r['link_no']) for r in vr['records'] if int(r['link_no']) in sub)
        clamped = sum(1 for row in self.spec['rows'] if float(row[3]) < 0.0)
        dropped = [row for row in self.spec['rows'] if float(row[3]) < -ENTRY_CLAMP_M]
        rows = [row for row in self.spec['rows'] if float(row[3]) >= -ENTRY_CLAMP_M]
        new = [_record(row, off) for row in rows]
        ids = {r['veh_no'] for r in kept}
        if any(r['veh_no'] in ids for r in new):
            raise RuntimeError('FH transplant: remapped FZP id collides with a kept vehicle')
        records = kept + new
        vr['records'] = records
        for key in ('record_count', 'collection_count_before', 'collection_count_after'):
            vr[key] = len(records)
        metrics = link_metrics(records)
        full = vr.get('full_network_link_counts') or {}
        fstop = vr.get('full_network_link_stopped_counts') or {}
        for link in {str(x) for x in sub}:
            m = metrics.get(link)
            if m is None:
                full.pop(link, None)
                if link in fstop:
                    fstop[link] = 0
            else:
                full[link] = int(m['count'])
                fstop[link] = int(m['stopped'])
        vr['full_network_link_counts'], vr['full_network_link_stopped_counts'] = full, fstop
        lo = merged['local_observation']
        for link in {str(x) for x in sub}:
            m = metrics.get(link)
            for key, field, empty in (('link_counts', 'count', 0.0), ('link_stopped_counts', 'stopped', 0.0),
                                      ('link_speeds_kph', 'speed', 0.0), ('link_queue_tail_pos_m', 'tail', 0.0)):
                table = lo.get(key)
                if isinstance(table, dict) and link in table:
                    table[link] = (m[field] if m is not None else empty)
        bins = lo.get('queue_bins') or {}
        for key in [k for k in bins if int(k.split('|', 1)[0]) in sub]:
            del bins[key]
        bins.update(queue_bins(new))
        lo['queue_bins'] = bins
        if isinstance(lo.get('observed_vehicle_count'), (int, float)):
            lo['observed_vehicle_count'] = lo['observed_vehicle_count'] - sum(removed.values()) + len(new)
        frame = observation['frames'][-1]
        width = max((len(r) for r in frame['vehicles']), default=15)
        frame['vehicles'] = ([r for r in frame['vehicles'] if int(r[1]) not in sub]
                             + [_frame_row(row, off, width) for row in rows])
        split = observation.get('off_split_ratio')
        exits = {}
        if isinstance(split, dict):
            for c, row in self.spec['exit_counts'].items():
                key = c if c in split else (int(c) if int(c) in split else None)
                if key is None or row['ratio'] is None:
                    exits[c] = {'replaced': False, **row}
                    continue
                exits[c] = {'replaced': True, 'template_ratio': split[key], **row}
                split[key] = float(row['ratio'])
        rec.update(removed_by_link=dict(removed), added_by_link=dict(Counter(str(r['link_no']) for r in new)),
                   clamped_entry_rows=clamped, dropped_rows=len(dropped), exit_shares=exits)
        rec['after'] = self._probe(merged)
        rec['expected_density'] = self._expected_density(context, frame['vehicles'])
        return merged, observation

    def _expected_density(self, context, vehicles):
        """H-2b target: the deployed bin_frame of the substituted frame, v2 lane profile (LPR.initialize)."""
        module = getattr(self, 'module', None)
        if module is None or not hasattr(module, 'bin_frame'):
            return None
        out = {}
        for road in FW_CHAINS:
            try:
                cells, bins, _dropped = module.bin_frame(context['geometry'], vehicles, road, drop_before_start=True)
                lanes = [cc['lane_km'] / cc['length_km'] for cc in cells]
                out[road] = [len(rows) / (cc['length_km'] * lane) for rows, cc, lane in zip(bins, cells, lanes)]
            except Exception as exc:
                out[road] = {'error': repr(exc)[:200]}
        return out

    def _probe(self, merged):
        """H-1 inputs on the (un)substituted merged state: counts and per-lane contiguous 127 queue (deployed walk)."""
        import sys
        vr = merged.get('vehicle_records') or {}
        counts = Counter(str(r['link_no']) for r in vr.get('records') or [])
        out = {'counts': {k: float(counts.get(k, 0)) for k in ('32', '10778', '129', '10777', '127', '10491', '10481',
                                                                  '10695', '31', '124')}}
        heads = {1: 621.666240433568, 2: 621.5682806829368, 3: 621.461546643362}
        out['posthead_127'] = float(sum(1 for r in vr.get('records') or []
                                        if str(r['link_no']) == '127' and r['position_m'] >= heads.get(int(r['lane_no']), 1e9)))
        walk = None
        mod = sys.modules.get('__main__')
        fn = getattr(mod, '_contiguous_stopline_queue_by_lane', None)
        if fn is not None:
            try:
                walk = {f'{k[0]}|{k[1]}': float(v) for k, v in fn(merged).items() if str(k[0]) == '127'}
            except Exception as exc:
                walk = {'error': repr(exc)[:200]}
        out['contiguous_127_by_lane'] = walk
        return out


def neutralize_f17b(module, transplant):
    """K9-1-0 (K8_PREDECLARATION_AMENDMENT_19 r2 section 2.3 'FH는 FD3 유지'): wrap offramp_split_forecast.apply (the
    F17b hook right before LaneFreewayRuntime, LPR:456) so that an enabled FH capture keeps the pre-F17b E_W shares:
    the restore to k9_f17b.per_exit[o].c0 (the observation's share when the forecast was installed, i.e. after
    substitute()) followed by FD3 (10491 / 10479 = the FZP [T-150, T] shares set by substitute) and FD8 (10638 /
    10645 = the template values) leaves exactly the shares the observation already holds, so the wrapper applies
    nothing.  It checks the exits like apply() and records transplant.f17b {neutralized, forecast_not_applied, kept}."""
    def apply(observation, forecast):
        ratio = observation['off_split_ratio']
        for o in forecast:
            if o not in ratio:
                raise ValueError('freeway.offramp_split_forecast: exit %s absent from the observation' % o)
        transplant.record['f17b'] = {'neutralized': True,
                                     'forecast_not_applied': {str(o): float(s) for o, s in forecast.items()},
                                     'kept': {str(o): float(ratio[o]) for o in forecast}}
        return None
    module.apply = apply


def install(module, transplant):
    """Wrap lane_plant_runtime.observe_state (module attribute; configure_runtime looks it up at call time)."""
    original = module.observe_state
    transplant.module = module

    def observe_state(context, raw):
        merged, observation = original(context, raw)
        return transplant.substitute(context, merged, observation)
    module.observe_state = observe_state
