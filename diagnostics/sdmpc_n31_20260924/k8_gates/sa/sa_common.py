"""K8-6 SA gate harness: shared constants, data contracts, paths and light IO (diagnostics only).

Binding text: K8_PREDECLARATION.md (3330535b) §3 as replaced/extended by AMENDMENT_1 r2 (02c7b4d4) §3.0-§3.3,
AMENDMENT_2 (06c3a73b: N-A4 report site, N-A9 BASE attribution), AMENDMENT_3 (D-K8-5); OPT1_V2_SPEC.md (7a2624a7) +
OPT1_V2_SPEC_AMENDMENT_1.md r2 (9efd3021); user decisions K8_USER_DECISIONS_20261004.md (D-K8-1: judging arm SA-F =
storage observed_full, SA-G = geometric is a REPORT arm); AMENDMENT_10 (d7bcdc9e: T20 and G-EB-11(e) compare under the
K8-2 S3 rule of sa_s3parity.py).

Nothing in this folder is runtime code; the deployed path never imports it. Heavy imports stay inside functions so that
`--help` / `--dry-run` / py_compile need only the standard library.

Data contracts (every producer writes exactly these keys; every calculator reads only these keys)
------------------------------------------------------------------------------------------------
capture.json  schema k8-sa-capture/v1   (sa_cap_child.py; one adapter process per capture)
  harness TL3|DP|FH|ROBS61, T, seed, frame_T, arm BASE|SAF|SAG, tree, tuning{path,sha256}, ok, error, error_kind,
  error_site (the child's own classification of its full traceback, sa_errors; amendment 7 §2), harness_stage_error,
  template_sha256, horizon, axes, sim_sec, forecast_len (captured forecast), forecast_long_len,
  forecast_long_prefix_equal, capture_wall_sec,
  probes_error (the probe block raised; probes then absent),
  metadata{stopline_approach_install_check, stopline_approach_initial, lane_ramp_head_service_normalisation,
           lane_plant_install_check}            (subset of the adapter's own metadata at Query construction)
  probes{...}                                   (capture_probes(): plain floats read from the captured state;
                                                 records{n127, n10777, n10695, posthead_127, n_tail129, m_other,
                                                 n_shortfall_kept, recv127, n_rehome_kept, rehome_member} = the
                                                 amendment 5 section 3 lane-stock identity terms + amendment 7 §1
                                                 N_shortfall_kept, both branches and M_other net of the (d) share
                                                 since amendment 8 §1)
  transplant{...}                               (FH only, sa_fh.TransplantRecord.as_dict(); H-2 / H-2b inputs)
summary.json  schema k8-sa-job/v1        (sa_worker.py; one fresh process per rollout job)
  job{label,harness,T,seed,frame_T,arm,entry,H,variant,mode,tree,template,forecast_long}, ok, error, error_kind,
  error_site (sa_errors on the full traceback; amendment 7 §2), wall_sec,
  objective, objective_repr, costs, costs_order, resources, T0, block_sec,
  blocks[k] = {k, t_end, w_ports{movement_w_all, gate_occ, transit_gate, port_10491, port_10481, total},
               w_ready, w_out_occ, fw_w_stock, fw_w_cell_v[31], fw_w_cell_n[31], cell9_v, origin_fw_w, ledger_ttt,
               receivers{storage: occ}, ramp_queue{RM_C10482, RM_C10490}, e_approach_queue, sa_stock{1,2,3}|None,
               port_inflow{off}, port_release{off}, w_departures{member}, w_green_sec{member},
               w_recv_limited_sec{member}, blocked_steps{off}, vmin_steps_cells_6_9, onE_threshold_steps,
               e_recv_bound_sec, sa_lane_served{1,2,3}|None}
  steps{t[], stock_<off>[], inflow_<off>[] (veh in that second), cell_v_6_9_min[]}   (per second, 10491/10481/10638)
  cap{off}, w_departures_steps{t[], veh[]}   (W member departures per response second; G-EB-5 8970.1 cut)
  samples30{t[], fw_w_v[[31]], fw_w_n[[31]]}                     (every 30 s of rollout time)
  first_block_t{off: t|None}, sa{counters, end_step_calls, step_diag_last}|None,
  tangent{axes[{index,owner,key,block,scale,green_vector}], values{index: value}, error}|None,
  probes{T3N7, T15b}|None   (job['probes'] only: captured-state tests, test_stopline_approach_captured.py)
  recorder_errors[]          (passive recorder exceptions; G-EB-5 needs [] on the judged job, amendment 6 §3)
vissim_ref.json schema k8-sa-vissim-ref/v1 (sa_vissim_ref.py; read-only FZP/EO/R-obs3 summaries)
  seeds{seed: {states{T: {...}}, spill_windows_W[[a,b]], ...}}, rules{...}
  s31 also: robs3{t}, eb_crossings_by_block{b}, eb_crossing_times[], eo_cells30_FW_W, eo_or_d_w_signal_cum{t}
tl3m/robs_validity_s<seed>.json schema k8-sa-robs-validity/v1 (sa_tl3m.py validity; K8 amendment 13)
  seed, name, status valid|invalid|not_finished|error, reasons[], checks{exit, decisions, fzp}, inputs{...}
  (valid = run exit 0, 61 decisions, FZP trajectory = the same-seed v3c3 NC FZP by the GB-6 method; invalid = the
  seed leaves the TL3m judging sample, reported; anything else -> INCOMPLETE)
"""
from __future__ import annotations

import ast
import hashlib
import json
import math
import os
import re
import sys
from pathlib import Path

SA_DIR = Path(__file__).resolve().parent
GATES_DIR = SA_DIR.parent
if str(GATES_DIR) not in sys.path:
    sys.path.insert(0, str(GATES_DIR))
import k8common as c  # noqa: E402  (configure() ran at import: K8G_ROOT / K8G_OUT defaults)
if str(SA_DIR) not in sys.path:
    sys.path.insert(0, str(SA_DIR))
import sa_errors  # noqa: E402  (the one failure classification, amendment 7 §2; stdlib only)
from sa_errors import INVARIANT_KINDS, error_kind, error_site, log_error_site  # noqa: E402,F401

# ------------------------------------------------------------------------------------------------ declared sets
SEALED_SEEDS = (37, 59, 61, 67)          # never opened (K8 PREDECL §8)
FH_SEEDS = (31, 41, 43, 47, 53)          # v3c3 NC fit seeds (PREDECL §3.1)
GRID9 = (900, 1200, 1800, 2250, 2700, 3000, 3600, 4200, 4950)   # FH / TL3 T (PREDECL §3.1)
TL3_NONEVENT = (900, 1200, 1800, 2250)   # s31 classification (PREDECL §3.1: 900-2250 non-event 4)
TL3_EVENT = (2700, 3000, 3600, 4200, 4950)
DP_T = tuple(900 + 450 * k for k in range(17))                 # R-obs3 17 states (PREDECL §0 DP)
ROBS61_T = (1,) + tuple(range(150, 9001, 150))                 # 61 R-obs3 decision states (G-EB-14)
LONG_H = {900: 24, 2700: 42, 4950: 27}                         # G-EB-5 / G-EB-7 horizons (blocks of 150 s)
LONG_JUDGED = (2700, 4950)                                      # 900 H24 is report
LONG_CHECKPOINTS = (6300, 6750)                                 # G-EB-5 FW_W stock checkpoints
DP_FULL_T = (2700, 4950)                                        # G-EB-13 / G-EB-11(d) / G-EB-10(B2)
AD_FULL = (('2700', 'REF'), ('2700', 'M2ALL'))                  # G-EB-11(e)
ARMS = ('BASE', 'SAF', 'SAG')
JUDGING_ARM = 'SAF'                                             # D-K8-1
REPORT_ARM = 'SAG'
COMPARATOR_ARM = 'BASE'                                         # amendment 5 §1: comparator only
KEYED_ARMS = ('SAF', 'SAG')                                     # G-EB-2 counts every keyed arm (amendment 5 §1)
# SA-G runs only where the original declaration put the non-judging arm (amendment 1 r2 §3.0, amendment 5 §1):
# FH event 14 states H6 and TL3 9 states H3 OBS (sag_allowed below).  sa_jobs.py refuses SA-G anywhere else.
EVENT_STATES_DECLARED = 14                                      # VISSIM event states (p4 classification)
NONEVENT_STATES_DECLARED = 31
SAG_JOBS_DECLARED = 23                                          # FH event H6 14 + TL3 OBS H3 9 (amendment 6 §3)
G13_HOOK_T = 2700                                               # G-EB-13 judged TL3 SAF hook job (amendment 6 §3)
G13_JUDGED_HOOK_JOB = 'TL3_2700_SAF_OBS_H3_HOOK'                # = job_label('TL3', 2700, 'SAF', 'OBS', 3, 'HOOK')
STORAGE_OF_ARM = {'SAF': 'observed_full', 'SAG': 'geometric'}
ENTRIES = ('OBS', 'A1')
HARNESSES = ('TL3', 'DP', 'FH', 'ROBS61')
BLOCK_SEC = 150
STEP_SEC = 1
# K8 amendment 13 (595eb450, D-K8-7): FH smoke H-5 failed -> fallback judging sample TL3m = R-obs seeds {31, 43, 47}
# x GRID9, the deployed template of each seed's own R-obs run (no transplant), OBS entry.  VISSIM classification
# p4 958275ac: events 12 (s31 5, s43 4, s47 3), non-events 15.  A seed is judged only with a valid R-obs record.
ROBS_SEED = 31                           # R-obs3: TL3 / ROBS61 folders and labels of s31 carry no seed tag (as before)
TL3M_SEEDS = (31, 43, 47)
ROBS_SEEDED_HARNESSES = ('TL3', 'ROBS61')   # captured from the R-obs run of their seed (s43 / s47: tag _s<seed>)
ROBS_NAME = 'sdmpc31_v3c3_nc_s{seed}'    # R-obs run folder name under the R-obs runs root (amendment 13)
NC_FZP_REL = 's{seed}_v3c3nc/run/vissim_eval/baseline_s{seed}_v3c3nc_001.fzp'   # under NC3 (GB-6 pair)
TL3M_EVENTS_DECLARED = {31: 5, 43: 4, 47: 3}
TL3M_NONEVENTS_DECLARED = {31: 4, 43: 5, 47: 6}
TL3M_CLASSIFICATION_SHA8 = '958275ac'    # opt1v2/out/p4_states_grid9_v3c3.json (vissim_ref.json inputs.p4)
ROBS_PRE_T = (1, 150)                    # G-EB-14: SAF failure identical to BASE -> reported (amendment 9 precedent)
VALIDITY_SCHEMA = 'k8-sa-robs-validity/v1'
VALIDITY_STATUSES = ('valid', 'invalid', 'not_finished', 'error')

# ------------------------------------------------------------------------------------------------ network names
GATE = 'in_SC1001_W'
W_MEMBERS = ('SC1001_W_to_E_SC1002', 'SC1001_W_to_S_SC1003', 'SC1001_W_to_N_SC2002')
W_RAMP_MEMBERS = ('SC1001_W_to_onW', 'SC1001_W_to_onE')
W_PREFIX = 'SC1001_W_to_'
PORTS = {'10491': 'OR_D_W_storage', '10481': 'OR_D_E_storage'}
PORT_10638 = '10638'
RECEIVERS = ('SC1001_to_SC1002', 'SC1001_to_SC1003', 'SC1001_to_SC2002')
W_OUT_STORAGE = 'SC1001_W_out'
ONE_RAMPS = ('RM_C10482', 'RM_C10490')
OBS_W_LINKS = ('32', '10778', '129', '10777', '127', '10491', '10481')   # G-EB-3 (a) observed side
W_OUT_LINKS = ('31', '124')                                            # G6-6 observed W_out (u6 fzp_row)
ISLAND_LINKS = ('32', '10778', '129', '10777', '127', '10695')          # FH step 5 (amendment 1 §3.1)
PORT_LINKS = ('10491', '10481')
POSTHEAD_CONNECTORS = ('10118', '10368', '10695')
HEAD_POS_M = {1: 621.666240433568, 2: 621.5682806829368, 3: 621.461546643362}   # spec 1.9
STOPLINE_X_M = 621.6                     # a1_stopline crossing station (F1 declaration)
FW_W_CELLS = 31
CELL9 = 9                                # G-EB-4 "셀 9" (31-cell refined grid, 0-based; worker records the
                                         # OR_D_W diverge cell from the cfg and flags a mismatch)
COLLAPSE_CELLS = (6, 7, 8, 9)            # G-EB-7 "셀 6-9"
SLOW_CELLS = tuple(range(10, 31))        # G-EB-7 "셀 10-30"
X_3276_M = 3276.3077142857137            # G-EB-6 (d) station = FW_W bound 6 (EO geometry)
ONE_STATION_X10490_DEFAULT = 299.9855236542128   # evidence report.x_10490_m (N10); read from evidence when present

# ------------------------------------------------------------------------------------------------ thresholds (declared)
PORT_BLOCK_MARGIN_VEH = 1.0              # N9: blocked <=> port stock >= capacity - 1
G3_BIAS_MAX = 50.0                       # G-EB-3 (a)
G3_G67_BIAS_MAX = 20.0                   # G-EB-3 (b)
G3_G67_R_MIN = 0.5
G3_G66_BIAS_MAX = 5.0                    # G-EB-3 (d)
BOOT_N = 2000                            # G-EB-3 (c)
BOOT_SEED = 0
G4_ABS_MAX = 50.0                        # G-EB-4 per state (9/9)
G4_PR_MEDIAN_MAX, G4_PR_MAX_MAX = 50.0, 150.0   # report form
G4_CELL9_V_MIN = 60.0                    # TL3 non-event cell-9 speed at T+450
G5_STOCK_TOL = 150.0                     # FW_W stock checkpoints
G5_FLOW_REL = 0.15                       # 10491 period mean flow / EB discharge
G5_EO_END_S = 8970.1                     # amendment 5 §2-4: EO last complete 30 s window end (VISSIM clock)
G5_PLANT_END_S = round(G5_EO_END_S - 0.1, 1)   # the same instant on the plant clock (plant t <-> VISSIM t + 0.1)
G5_ORIGIN_MAX = 100.0
G5_10638_BLOCK_SHARE = 0.5               # D-EB-7 demotion trigger
G6_B_MAX_STATES = 6                      # of the 31 VISSIM non-event states (0.2)      FH: report since amendment 13
G6_E_MIN_HITS = 7                        # of the 14 VISSIM event states                FH: report since amendment 13
G6_B_SHARE = 0.2                         # amendment 13 TL3m (b): <= 0.2 x non-event states (15 -> 3)
G6_E_SHARE = 0.5                         # amendment 13 TL3m (e): >= half the event states (12 -> 6; 7/14 rate)
TL3M_G6_B_MAX = 3                        # full TL3m sample (amendment 13 text)
TL3M_G6_E_MIN = 6
G6_EXTENT_M = 500.0                      # VISSIM 127 queue range trigger
G6_SLACK_S = 30.0
G7_RATIO_SLACK = 0.05
G7_SLOW_KMH = 60.0
G8_DELTA_MAX = 3.0
G8_GREEN_S = 6.0
G11_WALL_RATIO = 1.05
G11_JSON_REL = 0.01
G11_FD_REL = 1e-6
G11_STATE_ERROR = 1e-8
MASS_TOL = 1e-9
H1_COUNT_TOL, H1_LANE_Q_TOL, H1_MIN_STATES = 1.0, 2.0, 8
H3_TOL, H3_MIN_STATES = 2.0, 8
H5_RANGE_MAX, H5_MIN_STATES = 5.0, 40
H5_RECV_SHARE = 0.10                     # W member receiving-limited seconds / green seconds
H5_EXCLUDE_MAX = 5                       # N5: <= 5/45 else G-EB-3 fails
PERSIST_REF_45 = 16.73                   # reference only (spec 1.7), never a threshold

# Harness operationalisations that the declaration leaves open.  Fixed here, in code, BEFORE any gate output exists
# (the gate run must not edit them; a change is a new tool commit, amendment 2 N-A8).  The final report lists them.
# K8_PREDECLARATION_AMENDMENT_5 (sha 342e6d62) §2 confirmed the 13 items of 2929816 with the corrections below
# (items 2, 4, 10) and §1 fixed the judging-arm principle; still before any SA gate / smoke / capture output.
OPERATIONALISATIONS = {
    'judging arm': 'every G-EB-* judged item is computed on the judging arm SAF only (PREDECL §3.3, D-K8-1); BASE '
                   'enters only as the comparator (paired increments G-EB-3(c), wall ratio G-EB-11(a)); SAG results '
                   'are report items only; completeness is checked per judging arm: a missing or failed SAF input '
                   '-> INCOMPLETE, never PASS (amendment 5 §1)',
    'G-EB-2 arms': 'the one exception: invariant violations are counted over every keyed arm (SAF and SAG), since an '
                   'invariant violation is an arm-independent code defect (amendment 5 §1, review N-10)',
    'G-EB-2 complete': 'judged only when every declared key-on run is present (amendment 6 §3, review N-r2-3): the '
                       'jobs = every SAF job of every sa_jobs.py family at its defaults + the SAG 23 (FH event H6 14 '
                       '+ TL3 OBS H3 9) + G13_JUDGED_HOOK_JOB (sa_jobs.declared_keyed), the captures = their template '
                       'folders + ROBS61 61 SAF; a missing summary.json or capture(_failed).json -> INCOMPLETE; an '
                       'invariant violation (invariant / route / stocks raised in runtime code; SAF captures also '
                       'init) in any keyed arm fails; an SAF run that failed in runtime code otherwise or an SAF job '
                       'without SA.end_step fails; an SAF failure without a runtime traceback (failure '
                       'classification) is unreadable -> INCOMPLETE (amendment 7 §2)',
    'G-EB-2 SAG': 'SAG (report arm, D-K8-1) rows fail G-EB-2 only for an invariant / route / stocks violation raised '
                  'in runtime code (amendment 5 §1: the G-EB-2 exception is invariant violations only); any other SAG '
                  'failure (other, init, config, no runtime traceback, killed, input absent) and an SAG job without '
                  'SA.end_step are REPORTED (item sag_reported, not judged) and do not hold G-EB-2: an SAG label or '
                  'capture folder with an attempt record counts as present (amendment 7 §2, review N-r4-3); an SAG '
                  'job that sa_jobs never started counts as present and reported when its capture folder holds an '
                  'attempt record: a failed capture (capture.json ok false, or capture_failed.json incl. killed) or an '
                  'ok capture whose own record cannot serve the job (forecast_long_len < H or not prefix-equal) '
                  '(sag_capture_attempt, amendment 8 §2, review N-r6-2); an SAG job whose capture inputs are all there '
                  'but which has not run, or whose ok capture misses a file, stays absent',
    'failure classification': 'one table, sa_errors.py (amendment 7 §2, review N-r4-2): kind = first of '
                              'StoplineInvariantError invariant, StoplineRouteError route, StoplineInitError init, '
                              'StoplineConfigError config, assert_stocks stocks, Ledger stocks, else other; site = the '
                              'innermost project frame of the traceback the CHILD recorded (worker summary.json, '
                              'capture child record; computed by the child on its full traceback, re-derived from the '
                              'recorded text when absent): runtime = evaluation/, vendor/ and the diagnostics/ modules '
                              'the runtime imports, harness = k8_gates/ (worker, capture child, FH transplant, hook '
                              'sites; the capture child marks its own post-template stage harness_stage_error); an SAF '
                              'run FAILS only with site runtime; killed / parent-only record / input absent / time-out '
                              '/ probe or harness exception / no traceback -> INCOMPLETE (rerun); full adapter runs: '
                              'run.json exit 0 with an action JSON = finished, else the site of the traceback that '
                              'ends adapter_log.txt (sa_errors.log_error_site)',
    'G-EB-1 runs': 'amendment 7 §2: each compared pair (DP template, TL3 summary, full 2700 run) needs both runs '
                   'finished: absent, killed, input absent or failed without a runtime traceback on either side -> '
                   'INCOMPLETE; both finished and exactly one failed (runtime traceback) -> FAIL; both failed -> '
                   'INCOMPLETE (equality not readable); unit_T11 = G-EB-9 rule (a missing DP row or a row count != 17 '
                   '-> INCOMPLETE, review B-r5-1)',
    'capture records': 'a folder with capture.json is a capture; a capture_failed.json next to it is stale and is '
                       'ignored (sa_capture.py moves an earlier capture_failed.json aside before a new attempt); a '
                       'capture_failed.json without the child record (schema %s, written by sa_cap_child.py) is '
                       '"killed" (the process died or was stopped before its handler) = unreadable -> INCOMPLETE in '
                       'G-EB-2 and G-EB-14 (i) and an absent capture for every reader (review r3 B-r3-3)'
                       % 'k8-sa-capture/v1',
    'job inputs': 'sa_jobs.py starts no worker while the job\'s capture inputs are missing (capture.json of a '
                  'successful capture, template.pickle, and when H exceeds the captured forecast length '
                  'forecast_long.pickle with capture.json forecast_long_len >= H and forecast_long_prefix_equal true, '
                  'amendment 7 §4 / review N-r5-2): the label stays absent (SA_JOB_SKIP_NO_CAPTURE) -> INCOMPLETE; a '
                  'summary whose run ended '
                  'on FileNotFoundError of its own template / forecast_long (sc.job_input_absent) read no SA code: '
                  'G-EB-2 counts it unreadable (any arm) and every other reader as an absent job -> INCOMPLETE, never '
                  'FAIL; sa_jobs.py moves it to stale_input_absent_<k>.json (hook/ to stale_hook_<k>/) and reruns '
                  'the job once the inputs exist (review r4 B-r4-1)',
    'SAG scope': 'SAG jobs only at the declared places: FH event 14 states H6 and TL3 9 states H3 OBS; never long, '
                 'c11, tan, DP, A1 or the smoke families (sa_jobs.py refuses; amendment 5 §1, review N-7)',
    'G-EB-3(c)': 'per port (10491, 10481) separately; increment = |model-obs|(SAF) - |model-obs|(BASE) per state '
                 '(amendment 13: the TL3m states are judged, the FH states reported); '
                 'two-sided percentile 95 % CI, lower bound = 2.5th percentile; iid = states resampled with '
                 'replacement, cluster = seeds resampled with replacement (all states of a drawn seed); '
                 'numpy.random.default_rng(0), 2000 draws each; pass <=> all four lower bounds <= 0 (amendment 5 '
                 '§2-1 confirmed)',
    'G-EB-4 cell9': 'plant FW_W cell index 9 (0-based, 31-cell grid) at the block-3 end; worker records '
                    'off_ramp_segment_index of OR_D_W for audit',
    'G-EB-5 10491 flow': 'period mean of the plant 10491 port INFLOW (landing) vs VISSIM EO crossings of '
                         'OR_D_W_signal (the connector entry); BOTH sides cut at [T, 8970.1 s] = the EO last complete '
                         '30 s window (amendment 5 §2-4, review B-2): VISSIM = cum(min(T+H*150, 8970)+0.1) - '
                         'cum(T+0.1), plant = inflow of the steps ending in (T, min(T+H*150, 8970)], both divided by '
                         'the cut duration; no 9000.1 key is looked up; release reported over the full horizon',
    'G-EB-5 EB discharge': 'plant departures of the three W stop-line members vs VISSIM 127 head crossings '
                           '(a1_stopline station 621.6 m) of seed 31, same period with the same end rule as the '
                           '10491 flow (cut at 8970.1 s; per-second departures vs crossing frame times)',
    'G-EB-5 series': 'a judged job counts only when its plant per-second record is complete (amendment 6 §3, review '
                     'N-r2-5): steps.t holds every 1 s step of (T, end] (count = end - T, t = T+1 ... end), t '
                     'strictly increasing over the whole record, inflow_10491 as long as t, the W departure series '
                     '(seconds with a W member departure only, so sparse by construction) strictly increasing, and '
                     'recorder_errors == [] (absent -> not verified); otherwise every item of that job INCOMPLETE',
    'G-EB-6 blocked': 'a step end with port stock >= capacity - 1 (N9); first time = that step end',
    'G-EB-6(a)': 'judged on SAF: 10481 blocked steps summed over all 27 TL3m H3 jobs and all 12 TL3m VISSIM event '
                 'state H6 jobs = 0 (amendment 13; the FH form -- 45 H3 + 14 event H6 -- is reported); any of those '
                 'SAF jobs missing or failed -> INCOMPLETE; BASE and SAG values reported (amendment 5 §1, review B-1)',
    'G-EB-6(c) window': 'event states: the H6 job horizon; VISSIM side = first 5 s frame >= T with '
                        '621.6 - min POS(127, v < 5 km/h) >= 500 m (a1_stopline q127 extent); never -> +inf',
    'G-EB-6(e) window': '[T, T+450] of the H3 job',
    'G-EB-7 collapse': 'a 150 s block with any step where a cell 6..9 speed <= net.v_min + 1e-9',
    'G-EB-7 slow ratio': 'per (block, cell 10..30): VISSIM block speed = mean of EO cells_30s v_kmh over the 5 '
                         'snapshots with speed_eligible_n_ge5; plant = mean of its 30 s samples at the same times; '
                         'pairs where VISSIM has no eligible snapshot are dropped from both; non-event blocks = '
                         'blocks not overlapping a VISSIM s31 FW_W spill window (F1 §6)',
    'G-EB-8 tangent': 'surrogate reverse AD job (deployed mode) on the REFERENCE action, FW_W(T+450) directional '
                      'derivative by a forward sweep of the tape per green axis of SC1001; judged value = the '
                      'p3 axis summed over the three blocks (a uniform p3 shift, like C11), block-0 value reported. '
                      'p4 has no axis of its own: the SDMPC green axis of SC1001 is the balanced (+p3, -p4) pair '
                      '(the last live phase is the balancing phase), so the N6 dFW_W/dg_p4 report is written as '
                      '"no axis" and the p3 axes\' green_vector is reported instead (amendment 5 §2-10, review N-5)',
    'H-5 exclusion': 'center-frame (frame_T = T) H-5 job of the judging arm, block 1: '
                     'sum_m receiving-limited seconds / sum_m green seconds over the three W members > 0.10; '
                     'at most 5 of 45 excluded (amendment 1 N5); amendment 13: FH only, so since the FH G-EB-3 '
                     'values are reports the exclusion list and N5 are reported with them and not applied to TL3m',
    'G-EB-13 classes': 'module:function table CLASSIFY in sa_hookcount.py',
    'G-EB-13 complete': 'judged runs = the full 2700 and 4950 SAF hook runs + the fixed TL3 2700 SAF hook job '
                        'TL3_2700_SAF_OBS_H3_HOOK (sa_jobs.py tl3 --hooks --T 2700 --arms SAF) + every other TL3 SAF '
                        'hook job present, all by the same criterion (plant reads 0); a judged run absent or with no '
                        'SA hook record (sa_files 0) is counted INCOMPLETE, never skipped (amendment 6 §3, review '
                        'N-r2-2; amendment 5 §4)',
    'G-EB-13 instrument': 'a judged run counts only with a valid instrument (review r3 B-r3-4: a read never counted '
                          'cannot make plant reads 0): SA hook hook_errors = 0 and patch_errors = 0, the SA hook '
                          'error list empty, no setup / chain error file, the patch list holding '
                          'urban_queue_model._movement_capacity_flow, and for every plant module (PLANT_MODULES of '
                          'sa_hookcount.py) whose source in the code root has capacity token lines a line patch with '
                          'that many lines (sa_hookcount.py records the expectation); and (amendment 7 §3) the same '
                          'run\'s chained S3 / site hook files with hook_errors = patch_errors = 0 and no errors, and '
                          'every hook file (hook_*.json and sahook_*.json) a final record; otherwise INCOMPLETE. '
                          'Plant reads > 0 still fail',
    'G-EB-13 positive control': 'amendment 7 §3: G-EB-13 is judged only when BASE full 2700 and 4950 (key absent) '
                                'show W member capacity plant reads > 0 (the instrument does catch them); a BASE run '
                                'absent or with 0 plant reads -> INCOMPLETE',
    'G-EB-11(d) instrument': 'amendment 7 §3 (reviews B-r5-2, N-r4-1, N-r5-3): per full 2700 / 4950 SAF run, the S3 '
                             'count is valid (>= 31 sites, no anchor mismatch, every site patched; else INCOMPLETE) '
                             'and an observed exact != 0 S3 event or a dropped fold tangent fails; otherwise PASS needs '
                             'the run instrument of G-EB-13 (S3 hook_errors = patch_errors = 0 and no errors, fold '
                             'hook errors 0, stopline_approach patched, every hook file final, no setup error), the '
                             'run finished (run.json exit 0 with an action JSON) and fold-site ev_unevaluated = 0 '
                             '(events never measured); else INCOMPLETE',
    'G-EB-11(e) S3 rule': 'AMENDMENT_10 §1-§3 (sa_s3parity.py): the ad_full job routes '
                          'sdmpc_tangent_state.state_error (unchanged) through sa_s3parity.compare; a flow_counts key '
                          'only the tangent run has, with primal exactly 0.0, created by a ModelAreaLedger.transfer '
                          'call admitted only by the K8-2 S3 gate (amount primal 0.0 with tape; site CAO:608, the one '
                          'of the six S3 sites on the ledger write path; this tree resolves the six by their exact '
                          'K8-2 text) with no stopline_approach frame on the stack is set aside and counted (per site '
                          'and per emitting frame); transfer rows already compare grouped (absent = 0) and are only '
                          'counted; an SA-created S3 call (sa_created > 0), a key outside the rule or a comparator '
                          'error fails; a summary without the s3_parity record, not installed or with 0 compares '
                          'through the wrapper is INCOMPLETE',
    'G-EB-13 run complete': 'a judged run counts only when it ran to its end (review r4 B-r4-2: the hook writes its '
                            'final record at exit, so a run that stopped before its rollout also shows "patched, '
                            '0 errors, 0 plant reads"): a full decision needs full/<tree>/<T>_SAF_<hooks-tag>/run.json '
                            'with exit 0 and action_json_bytes > 0; a hook job needs summary.json with ok true and '
                            'sa.end_step_calls > 0; otherwise INCOMPLETE. Plant reads > 0 still fail',
    'G-EB-14 harness': 'T9b (deployed captured template) and T9c (scratch projection with 10695 in the support table, '
                       '+-1e-9) are judged items read from --unit-log rows of test_stopline_approach_captured.py by '
                       'the unit-log rule, and only when the capture provenance lines of the logs (capture root, tree, '
                       'template sha256) name <out>/sa/cap/<tree> and equal its capture.json for TL3 BASE (T9b) and '
                       'TL3 BASE + T9C BASE (T9c); any provenance line of another root or sha -> INCOMPLETE '
                       '(amendment 6 §1; amendment 5 §4, review B-4); T9b / T9c equivalence asserts are outside subTest',
    'G-EB-14 capture rows': 'review r4 B-r4-3: (i) a capture record without its metadata block (the capture child '
                            'found no adapter main frame) cannot be read -> INCOMPLETE; metadata without '
                            'stopline_approach_install_check is an initialization failure (FAIL); a failed capture '
                            'fails (i) only with a runtime traceback (amendment 7 §2), else INCOMPLETE; (ii)(iii) a '
                            'row is judged only with the capture probes (present, no probes_error), '
                            'metadata.stopline_approach_initial.posthead_veh, posthead_receiver_shortfall_veh and '
                            'posthead_rehome_shortfall_veh and probes.records.n10695 -- no default 0 is read; otherwise '
                            'that row is INCOMPLETE; 127 receiver provenance = posthead_veh - '
                            '(posthead_receiver_shortfall_veh - posthead_rehome_shortfall_veh) (amendment 7 §1: the '
                            'share beyond the receiver room stays a 127 head ready packet); 10695 receiver share + '
                            'posthead_rehome_shortfall_veh = the 10695 count and the W member queue on 10695 = '
                            'posthead_rehome_shortfall_veh (amendment 8 §1: the 10695 share beyond the '
                            'room stays a lane 3 head ready packet, both kept shares reported together in '
                            'posthead_receiver_shortfall_veh)',
    'unit log': 'pytest 9 -v logs, --unit-log repeatable or one combined run (amendment 6 §1, reviews B-r2-1/2): rows '
                '= progress lines (a status word printed on a later line after interleaved output belongs to the '
                'last started node id); failures = short test summary lines ^(SUBFAILED|FAILED|ERROR)([...]|(...))? '
                '<nodeid> (a failed unittest subTest leaves its progress row PASSED, so the summary line is canonical) '
                '-> FAIL; the session summary N failed + N errors must be attributed to summary lines with a node id, '
                'else (or with no session summary) the items with rows in that log are INCOMPLETE; every unit item '
                '(T2, T10, T10b, T13, T9b, T9c) needs >= 1 PASSED and 0 SKIPPED, a missing row is INCOMPLETE, never '
                'FAIL; a named log file that does not exist -> INCOMPLETE',
    'H-2b lane stock': 'SA lane stock sum = N_127 + N_10777 - |A| + N_tail129 + M_other + N_shortfall_kept (+-1e-9; '
                       'each term recorded separately by the capture probe; N_shortfall_kept = the SA metadata '
                       'posthead_receiver_shortfall_veh (branches (a) and (d)), cross-checked against |A| - the 127 '
                       'receiver provenance + the W member queue read on 10695; the (d) share '
                       'posthead_rehome_shortfall_veh = that 10695 queue and M_other is read net of it; 10695 receiver '
                       'share + the 10695 queue = the 10695 count) - amendment 5 §3 replaces "N_127 + N_10777 - |A|" '
                       '(review B-3), amendment 7 §1 adds N_shortfall_kept, amendment 8 §1 its (d) share',
    'OBS entry tail': 'EO boundaries end at the last complete 30 s window (8970.1 s): a block ending later uses the '
                      'observed rate of its available part (>= 90 s); recorded as obs_entry._partial_blocks',
    'FH exit share': 'FD3 1132 branch passes = exits into 10491 / 10479 vs crossings of the through station at the end '
                     'of the off connector from_cell, frames (T-150, T] (obs150 off_split definition)',
    'H-3 arms': 'every arm with self-transplant jobs must pass (BASE and SAF by default)',
    'G-EB-3(d)': 'strict reading fixed by amendment 5 §2-2: (d) is judged (the row text "DP·TL3 판정, FH 보고" wins over '
                 'the verdict column "(a)(b)(c)"); DP 17 (A1 H1) and TL3 9 (OBS H3) judged separately, both |b| <= 5; '
                 'FH reported',
    # ---- K8 amendment 13 (595eb450, D-K8-7; tool commit K8-0h): FH smoke H-5 failed -> fallback judging on TL3m
    'TL3m sample': 'amendment 13: R-obs seeds {31, 43, 47} x GRID9 = 27 states, each seed\'s own deployed template '
                   '(sa_capture.py tl3 --robs-seed S from the replay states of R-obs run sdmpc31_v3c3_nc_s<S>, '
                   'make_replay_state_v2.prepare, no transplant), OBS entry = the seed\'s EO s<S>_v3c2nc (the FH '
                   'convention); s31 = the existing TL3 captures / jobs (no seed tag), s43 / s47 tagged _s<S>; VISSIM '
                   'side = vissim_ref.json states of the seed (x2 extract of the same-seed v3c3 NC FZP, T+150.1 and '
                   'T+0.1 frames; event / non-event from p4 958275ac: events 12 = 5/4/3, non-events 15 = 4/5/6, '
                   'checked per seed; another classification sha or count -> INCOMPLETE); a job counts only when its '
                   'summary names the expected seed; a seed is in the judging sample only with its R-obs validity '
                   'record status valid; status invalid -> the seed leaves the sample (reported); no record or '
                   'status not_finished / error -> INCOMPLETE',
    'R-obs validity': 'amendment 13 (sa_tl3m.py validity, binding): (1) run exit 0 = the last "EXIT <name> code=<n>" '
                      'line of <runs root>/wmi_<name>.log has n = 0 (no EXIT line -> not_finished, nothing in the run '
                      'folder is read); (2) 61 decisions = state_<T>.json and action_<T>.json for every T of '
                      'ROBS61_T (no other state file) and the runlog DECISIONS_OK=61, DECISIONS_FAILED=0, '
                      'STAGE=SIM_DONE; (3) FZP trajectory = the same-seed v3c3 NC FZP by the GB-6 method '
                      '(c1 header lines differ only in "* File:" / "* Date:", c2 the R-obs-only data lines before '
                      'SIMSEC 5.1 are the 0.10 s frame and the NC file has none, the rest (from the first 5.10 line) '
                      'byte-identical, c3 size difference = header difference + those 0.10 s bytes); GB-6 c4 (pairing '
                      'metrics) follows from c2 and c5 (.err) is not part of the record.  Any of (1)-(3) false on a '
                      'finished run -> invalid (the seed leaves the judging sample, reported); a missing input file '
                      '(runlog, NC FZP, wmi log) -> error (INCOMPLETE)',
    'G-EB-3 TL3m': 'amendment 13: judged on the 27 TL3m states (judging arm SAF, H3 OBS, block 1 = T+150): (a) model = '
                   'block-1 w_ports.total, observed = FZP T+150.1 counts on 32 + 10778 + 129 + 10777 + 127 + 10491 + '
                   '10481, |mean bias| <= 50 and MAE <= the FZP persistence MAE (|count(T+0.1) - count(T+150.1)|) of '
                   'the same states; (b) G6-7: block-1 w_ready vs FZP 127 stopped (< 5 km/h) at T+150.1, |b| <= 20 '
                   'and r >= 0.5; (c) the G-EB-3(c) rule on the TL3m states with BASE H3 OBS as comparator, cluster = '
                   'R-obs seed (3 clusters); (d) unchanged (DP 17 and TL3 s31 9); the H-5 pre-exclusion is FH only and '
                   'not applied; the FH 45 values of (a)(b)(c) are reported (with the H-5 list and N5)',
    'G-EB-6 TL3m': 'amendment 13, judging arm SAF: (a) 10481 blocked steps = 0 over the 27 TL3m H3 jobs and the 12 event '
                   'H6 jobs; (b) non-event states with a 10491 block in [T, T+450] (H3 job) <= floor(0.2 x n non-event) '
                   '(15 -> 3); (c) every event state whose H6 job blocks 10491: plant first block >= VISSIM 127 extent '
                   '>= 500 m first time - 30 s (never -> +inf); (e) event states with a 10491 block in [T, T+450] (H3 '
                   'job) >= ceil(0.5 x n event) (12 -> 6); harness reading: when a seed leaves the sample (invalid R-obs '
                   'run) the (b)/(e) bounds keep these declared ratios on the remaining states; the FH 45 / 14 values '
                   'are reported',
    'G-EB-14 R-obs seeds': 'amendment 13: (i) is judged per R-obs seed of the judging sample (31, 43, 47 with a valid '
                           'record) on its capturable ROBS61 states + FH 45; an SAF capture at T = 1 or 150 that failed '
                           'identically to the BASE capture of the same seed and T (both child-written failure records; '
                           'the adapter traceback action_<T>.error.txt, else the record error: same exception line and '
                           'same runtime frame path (file from its runtime folder, line, function), at least one runtime '
                           'frame) is reported and leaves the sample (amendment 9 precedent); any other failure keeps the '
                           'G-EB-14 capture-row rule; (ii)(iii) rows from every ok ROBS61 capture of a judged seed + FH',
    'G-EB-2 TL3m': 'amendment 13: the declared key-on list also holds the tl3m family SAF jobs (H3 OBS x GRID9, event '
                   'H6 OBS) of every TL3m seed whose validity record is not invalid, their template folders and the '
                   'ROBS61 61 SAF captures of those seeds; harness reading (G-EB-14 rule applied to the same capture '
                   'folders): an ROBS61 SAF capture at T = 1 / 150 that failed identically to BASE is listed as '
                   'reported (robs_identical_to_base), not as unreadable',
    'G-EB-4/5/7/8 TL3m': 'amendment 13: judged on TL3 s31 as before; G-EB-4 reports s43 / s47 from the TL3m H3 OBS jobs '
                         '(FW_W(T+450) vs the seed\'s FZP chain count); G-EB-5 / 7 / 8 s43 / s47 report rows need '
                         'long / C00 / C11 / TAN jobs and per-seed EO references that the TL3m job list does not hold: '
                         'reported as not computed',
}

# GB-7' A_K8 (amendment 1 r2 §E rule 1): keys the SA diff writes.  k8_gates has no gb7_allowed.py yet (P10), so the
# list is kept here for P10 to include verbatim (amendment 5 §6 N-3 adds the resource kind stopline_lane_room).
A_K8_SA = {
    'metadata': ('stopline_approach_schema', 'stopline_approach_storage_arm', 'stopline_approach_evidence_sha256',
                 'stopline_approach_storage_veh', 'stopline_approach_install_check', 'stopline_approach_initial'),
    'diagnostics_prefix': ('stopline_',),
    'resource_summary_kinds': ('stopline_lane_room',),
    'route_key_prefixes': ('stopline_internal:',),
}


# ------------------------------------------------------------------------------------------------ paths
def sa_out() -> Path:
    return c.OUT / 'sa'


def seed_tagged(harness, seed) -> bool:
    """Whether a folder / label carries _s<seed>: FH always (island seed); TL3 / ROBS61 (amendment 13 TL3m) only for an
    R-obs seed other than R-obs3 s31, so every s31 folder and label is the one written before amendment 13."""
    if seed is None:
        return False
    if harness == 'FH':
        return True
    return harness in ROBS_SEEDED_HARNESSES and int(seed) != ROBS_SEED


def cap_dir(tree, harness, T, arm, seed=None, frame_T=None) -> Path:
    tag = f'{int(T):06d}'
    if seed_tagged(harness, seed):
        tag += f'_s{int(seed)}'
    if frame_T is not None and int(frame_T) != int(T):
        tag += f'_f{int(frame_T):06d}'
    return sa_out() / 'cap' / tree / harness / tag / arm


def job_label(harness, T, arm, entry, H, *, seed=None, frame_T=None, variant='REF', mode='scalar', rep=None):
    parts = [harness, f'{int(T)}']
    if seed_tagged(harness, seed):
        parts.append(f's{int(seed)}')
    if frame_T is not None and int(frame_T) != int(T):
        parts.append(f'f{int(frame_T)}')
    parts += [arm, entry, f'H{int(H)}']
    if variant != 'REF':
        parts.append(variant)
    if mode != 'scalar':
        parts.append(mode)
    if rep:
        parts.append(f'rep{int(rep)}')
    return '_'.join(parts)


def job_dir(tree, label) -> Path:
    return sa_out() / 'jobs' / tree / label


def full_dir(tree, T, arm, tag='') -> Path:
    return sa_out() / 'full' / tree / (f'{int(T):06d}_{arm}' + (f'_{tag}' if tag else ''))


# ------------------------------------------------------------------------------------------------ amendment 13 (TL3m)
def is_robs3(seed) -> bool:
    return seed is None or int(seed) == ROBS_SEED


def robs_dir(seed=None) -> Path:
    """R-obs run folder of an R-obs seed (read only): s31 = the configured R-obs3 (--robs / K8G_ROBS), others
    sdmpc31_v3c3_nc_s<seed> next to it (amendment 13 RunsRoot)."""
    return c.ROBS if is_robs3(seed) else c.ROBS.parent / ROBS_NAME.format(seed=int(seed))


def robs_wmi_log(seed=None) -> Path:
    """The detached launcher log of the run (in the runs root, outside the run folder)."""
    d = robs_dir(seed)
    return d.parent / f'wmi_{d.name}.log'


def replay_dir(T, seed=None) -> Path:
    """Replay state of an R-obs decision: s31 <out>/replays/<T> (k8_gates/prep.py, as before), other R-obs seeds
    <out>/replays/s<seed>/<T> (sa_tl3m.py prep)."""
    return c.REPLAYS / f'{int(T):06d}' if is_robs3(seed) else c.REPLAYS / f's{int(seed)}' / f'{int(T):06d}'


def nc_fzp(seed) -> Path:
    return c.NC3 / NC_FZP_REL.format(seed=int(seed))


def validity_path(seed) -> Path:
    return sa_out() / 'tl3m' / f'robs_validity_s{int(seed)}.json'


def validity_status(rec, seed):
    """(status, reason) of an R-obs validity record (amendment 13): 'valid' (in the judging sample), 'invalid' (the
    seed leaves the sample, reported) or None (no readable record of this seed, or not_finished / error ->
    INCOMPLETE)."""
    if not isinstance(rec, dict):
        return None, 'no R-obs validity record (sa_tl3m.py validity)'
    if rec.get('schema') != VALIDITY_SCHEMA or rec.get('seed') != int(seed):
        return None, 'validity record of another schema / seed'
    status = rec.get('status')
    if status == 'valid':
        return 'valid', ''
    if status == 'invalid':
        return 'invalid', '; '.join(str(r) for r in rec.get('reasons') or []) or 'invalid'
    return None, f'validity status {status!r}: ' + '; '.join(str(r) for r in rec.get('reasons') or [])


def read_validity(seed):
    try:
        return read_json(validity_path(seed))
    except ValueError:                                   # truncated record: unknown (INCOMPLETE)
        return None


def tl3m_seeds_not_invalid():
    """TL3m seeds whose runs stay on the declared lists (G-EB-2): every seed whose record is not 'invalid'."""
    return tuple(s for s in TL3M_SEEDS if validity_status(read_validity(s), s)[0] != 'invalid')


def guard_tl3m_seed(seed):
    guard_seed(seed)
    if int(seed) not in TL3M_SEEDS:
        raise SystemExit(f'seed s{seed} is not a TL3m R-obs seed {TL3M_SEEDS} (amendment 13)')


def base_env_for(seed=None, **kw):
    """c.base_env() with the provenance (run env) of the R-obs run of `seed` (amendment 13: an s43 / s47 template
    is replayed with its own run's provenance); s31 / None = the configured R-obs3, unchanged."""
    if is_robs3(seed):
        return c.base_env(**kw)
    saved = (c.R, c.OUT, c.ROBS, c.NC3)
    c.configure(root=saved[0], out=saved[1], robs=robs_dir(seed), nc3=saved[3])
    try:
        return c.base_env(**kw)
    finally:
        c.configure(root=saved[0], out=saved[1], robs=saved[2], nc3=saved[3])


def failed_capture_record(folder):
    """(record, None) of a capture folder whose capture failed with a child-written record (capture.json ok false,
    else capture_failed.json of the child), or (None, why)."""
    folder = Path(folder)
    try:
        ok = read_json(folder / 'capture.json')
    except ValueError:
        return None, 'capture.json unreadable'
    if isinstance(ok, dict):
        return (ok, None) if ok.get('ok') is False else (None, 'capture ok')
    try:
        rec = read_json(folder / 'capture_failed.json')
    except ValueError:
        return None, 'capture_failed.json unreadable'
    if not isinstance(rec, dict):
        return None, 'no capture record'
    if capture_failure_kind(rec) == 'killed':
        return None, 'killed (no child record)'
    return rec, None


def robs_identical_failure(tree, seed, T):
    """Amendment 13 G-EB-14 (amendment 9 precedent): whether the judging-arm ROBS61 capture of R-obs `seed` at T (1 or
    150 only) failed identically to the BASE capture of the same seed and T.  Each side needs a child-written failure
    record; its traceback is the adapter's decision failure report action_<T>.error.txt in the capture folder, else
    the record's error text; identical = equal sa_errors.traceback_signature (exception line + runtime frame path)
    with at least one runtime frame.  Returns a row dict with 'identical' (bool) and the reason / signature."""
    row = {'seed': int(seed), 'T': int(T), 'identical': False}
    if int(T) not in ROBS_PRE_T:
        row['reason'] = 'T not in %s' % (ROBS_PRE_T,)
        return row
    sigs = {}
    for arm in (JUDGING_ARM, COMPARATOR_ARM):
        d = cap_dir(tree, 'ROBS61', T, arm, seed=seed)
        rec, why = failed_capture_record(d)
        if rec is None:
            row['reason'] = f'{arm}: {why}'
            return row
        p = d / f'action_{int(T):06d}.error.txt'
        text = p.read_text(encoding='utf-8', errors='replace') if p.is_file() else rec.get('error')
        sig = sa_errors.traceback_signature(text)
        if sig is None or not sig[1]:
            row['reason'] = f'{arm}: no traceback with a runtime frame (action error file / record)'
            return row
        sigs[arm] = sig
    a, b = sigs[JUDGING_ARM], sigs[COMPARATOR_ARM]
    row.update(identical=a == b, exception=a[0][:300], site=list(a[1][-1]))
    if a != b:
        row.update(reason='SAF and BASE failures differ', base_exception=b[0][:300], base_site=list(b[1][-1]))
    return row


CAPTURE_SCHEMA = 'k8-sa-capture/v1'      # sa_cap_child.py record (capture.json / child-written capture_failed.json)


def capture_failure_kind(rec):
    """Kind of a capture_failed.json record (review r3 B-r3-3).  'killed' when the child never wrote its record (no
    k8-sa-capture/v1 schema, or the parent marked child_record false): the process was stopped or died before its
    handler, so the run cannot be read (INCOMPLETE, never FAIL).  Otherwise record_kind (the one table, amendment 7
    §2: a child record without error_kind is re-classified from its error, review N-r4-2)."""
    if not isinstance(rec, dict) or rec.get('schema') != CAPTURE_SCHEMA or rec.get('child_record') is False:
        return 'killed'
    return record_kind(rec)


def record_kind(rec):
    """error kind of a failed child record (sa_errors table): the child's own classification of its full traceback
    when it wrote one (error_site present), else re-derived from the recorded error text, else the recorded
    error_kind, else 'other'."""
    if 'error_site' in rec and rec.get('error_kind'):
        return rec['error_kind']
    return error_kind(rec.get('error')) or rec.get('error_kind') or 'other'


def record_site(rec):
    """'runtime' | 'harness' | None for a failed child record (amendment 7 §2): the child's error_site when recorded
    (the capture child marks its own post-template stage harness_stage_error -> 'harness'), else the innermost
    project frame of the recorded traceback text.  None = no traceback recorded."""
    if rec.get('harness_stage_error'):
        return 'harness'
    if 'error_site' in rec:
        return rec['error_site']
    return error_site(rec.get('error'))


def failed_in_runtime(rec):
    """Amendment 7 §2: a failed run counts as a FAIL only when its child recorded a traceback raised in runtime code;
    every other failure (no traceback, harness frame, killed, input absent) is INCOMPLETE."""
    return record_site(rec) == 'runtime'


def job_outcome(summary, tree):
    """Amendment 7 §2 for the comparison readers: None (no summary), 'ok', 'failed' (finished: the worker recorded a
    runtime traceback) or 'unfinished' (input absent, or failed without a runtime traceback)."""
    if summary is None:
        return None
    if job_input_absent(summary, tree) is not None:
        return 'unfinished'
    if summary.get('ok') is True:
        return 'ok'
    return 'failed' if failed_in_runtime(summary) else 'unfinished'


def capture_outcome(folder):
    """Amendment 7 §2 for a capture folder: None (no record), 'ok' (capture.json + template.pickle), 'failed' (a
    child record with a runtime traceback) or 'unfinished' (killed, no runtime traceback, or no template)."""
    folder = Path(folder)
    try:
        ok = read_json(folder / 'capture.json')
    except ValueError:
        return 'unfinished'
    if isinstance(ok, dict) and ok.get('ok') is not False:
        return 'ok' if (folder / 'template.pickle').is_file() else 'unfinished'
    try:
        fail = ok if isinstance(ok, dict) else read_json(folder / 'capture_failed.json')
    except ValueError:
        return 'unfinished'
    if fail is None:
        return None
    if capture_failure_kind(fail) == 'killed':
        return 'unfinished'
    return 'failed' if failed_in_runtime(fail) else 'unfinished'


def full_outcome(run, log_text=None):
    """Amendment 7 §2 for a full adapter run: None (no run.json), 'ok' (exit 0 with an action JSON), 'failed' (exit
    != 0 and the adapter log ends on a runtime traceback: run.json error_site, else log_error_site of the log text)
    or 'unfinished' (killed / stopped, a harness or infrastructure failure, exit 0 without an action JSON)."""
    if run is None:
        return None
    if run.get('exit') == 0:
        n = run.get('action_json_bytes')
        return 'ok' if isinstance(n, (int, float)) and not isinstance(n, bool) and n > 0 else 'unfinished'
    site = run['error_site'] if 'error_site' in run else log_error_site(log_text)
    return 'failed' if site == 'runtime' else 'unfinished'


CAPTURE_INPUT_FILES = ('template.pickle', 'forecast_long.pickle')    # what sa_worker.main reads from its capture
CAPTURE_FORECAST_H = 3        # captured (leader) forecast length assumed when capture.json has no forecast_len


def job_inputs_missing(job):
    """Review r4 B-r4-1: the capture inputs of a job that are not there (empty list = the worker can start).
    capture.json of a successful capture (readable, ok not false), template.pickle, and when the job horizon is longer
    than the captured forecast (capture.json forecast_len; without it any H > 3) forecast_long.pickle with capture.json
    forecast_long_len >= H and forecast_long_prefix_equal true (amendment 7 §4, review N-r5-2: the two checks
    sa_worker.main makes before it uses the file).  sa_jobs.run_job launches no worker while one is missing, so an
    absent or killed capture leaves the job absent (INCOMPLETE), never a failed summary."""
    cap = Path(job['template']).parent
    try:
        rec = read_json(cap / 'capture.json')
    except ValueError:                                   # truncated / unreadable record
        rec = None
    missing = []
    if not isinstance(rec, dict) or rec.get('ok') is False:
        missing.append('capture.json')
    if not Path(job['template']).is_file():
        missing.append('template.pickle')
    n = rec.get('forecast_len') if isinstance(rec, dict) else None
    short = int(n) if isinstance(n, (int, float)) and not isinstance(n, bool) else CAPTURE_FORECAST_H
    if int(job['H']) > short:
        if not Path(job['forecast_long']).is_file():
            missing.append('forecast_long.pickle')
        n_long = rec.get('forecast_long_len') if isinstance(rec, dict) else None
        if not (isinstance(n_long, (int, float)) and not isinstance(n_long, bool) and n_long >= int(job['H'])):
            missing.append('forecast_long_len >= H')
        if not (isinstance(rec, dict) and rec.get('forecast_long_prefix_equal') is True):
            missing.append('forecast_long_prefix_equal')
    return missing


CAPTURE_RECORDED_INPUTS = ('forecast_long_len >= H', 'forecast_long_prefix_equal')    # read from capture.json itself


def sag_capture_attempt(job):
    """Amendment 8 §2 (review N-r6-2): the capture attempt record of an SAG job that sa_jobs.run_job never started
    (job_inputs_missing non-empty), or None.  An attempt record is
      - a failed capture: capture.json with ok false, or capture_failed.json without an ok capture.json (a child
        record or a parent-only 'killed' record, the amendment 7 §2 attempt records of the capture folder), or
      - an ok capture whose own record cannot serve the job (only CAPTURE_RECORDED_INPUTS lacking: its forecast_long
        is shorter than H or not prefix-equal; template / forecast files present).  Review r8 N-r8-1: only when the
        record says so -- ok is true and both fields are recorded (forecast_long_len a number, forecast_long_prefix_equal
        a bool) and fail; an absent field (or an absent ok key) is not a record of failure, so the label stays absent.
    None when the inputs are complete (the job is simply not run yet), when no capture record exists, or when an ok
    capture misses a file (template.pickle / forecast_long.pickle: an unfinished folder, rerun) or a forecast field --
    those labels stay absent (INCOMPLETE).  G-EB-2 counts an SAG label with an attempt record as present and reported
    (amendment 7 §2: SAG failures do not hold G-EB-2 completeness)."""
    lacking = job_inputs_missing(job)
    if not lacking:
        return None
    cap = Path(job['template']).parent
    try:
        rec = read_json(cap / 'capture.json')
    except ValueError:                                   # truncated / unreadable record
        rec = None
    if isinstance(rec, dict) and rec.get('ok') is not False:
        n_long, prefix_equal = rec.get('forecast_long_len'), rec.get('forecast_long_prefix_equal')
        recorded = (rec.get('ok') is True and isinstance(n_long, (int, float)) and not isinstance(n_long, bool)
                    and isinstance(prefix_equal, bool))
        if recorded and set(lacking) <= set(CAPTURE_RECORDED_INPUTS):
            return 'capture.json ok, its record cannot serve the job (%s)' % ', '.join(lacking)
        return None
    if isinstance(rec, dict):
        return 'capture.json ok false (capture failed)'
    if (cap / 'capture_failed.json').is_file():
        return 'capture_failed.json (capture failed or killed)'
    return None


_FILE_NOT_FOUND = re.compile(r"^FileNotFoundError: \[Errno 2\] No such file or directory: ('.*'|\".*\")\s*$")


def _norm(path):
    return os.path.normcase(os.path.abspath(str(path)))


def job_input_absent(summary, tree):
    """Review r4 B-r4-1: the capture input path whose absence ended a failed job, else None.  The run ended on
    FileNotFoundError (its last traceback line) for the job's own template.pickle / forecast_long.pickle -- the paths
    the summary names (job.template / job.forecast_long, sa_worker.to_summary) or, for a summary without them, a
    capture input file under <out>/sa/cap/<tree>.  No SA code was read: every reader treats such a summary as an
    absent job (INCOMPLETE), never as a failure, and sa_jobs.run_job reruns the job once the inputs exist."""
    if not isinstance(summary, dict) or summary.get('ok') is not False:
        return None
    lines = [ln for ln in str(summary.get('error') or '').splitlines() if ln.strip()]
    m = _FILE_NOT_FOUND.match(lines[-1].strip()) if lines else None
    if m is None:
        return None
    paths = [m.group(1)[1:-1]]                           # the quoted text as written (a hand-made record)
    try:
        paths.insert(0, str(ast.literal_eval(m.group(1))))   # Python writes repr(filename)
    except (ValueError, SyntaxError):
        pass
    job = summary.get('job') or {}
    own = {_norm(job[k]) for k in ('template', 'forecast_long') if job.get(k)}
    root = _norm(sa_out() / 'cap' / tree) + os.sep
    for path in paths:
        if own:
            if _norm(path) in own:
                return path
        elif Path(path).name in CAPTURE_INPUT_FILES and _norm(path).startswith(root):
            return path
    return None


def job_summary(tree, label):
    """summary.json of a job for the comparison readers: None when absent or when its run ended on its own missing
    capture input (job_input_absent; not a result, review r4 B-r4-1)."""
    s = read_json(job_dir(tree, label) / 'summary.json')
    return None if s is None or job_input_absent(s, tree) is not None else s


def g5_period_end(T, H):
    """Plant-clock end of the G-EB-5 period (amendment 5 §2-4): the horizon end, cut at the EO end 8970.1 s."""
    return min(float(T) + float(H) * BLOCK_SEC, G5_PLANT_END_S)


def sag_allowed(harness, entry, H, *, event_state=None, variant='REF', mode='scalar'):
    """True only at the declared SA-G places (FH event H6, TL3 GRID9 H3 OBS; REFERENCE action, scalar); amendment
    5 §1.  Long horizons, C00/C11/C12, tangent, DP, A1 entry and the smoke families are not SA-G places."""
    if variant != 'REF' or mode != 'scalar':
        return False
    if harness == 'FH':
        return entry == 'OBS' and int(H) == 6 and event_state is True
    if harness == 'TL3':
        return entry == 'OBS' and int(H) == 3
    return False


def guard_seed(seed):
    if seed is None:
        return
    if int(seed) in SEALED_SEEDS:
        raise SystemExit(f'sealed seed s{seed} refused (K8 PREDECL §8)')
    if int(seed) not in FH_SEEDS:
        raise SystemExit(f'seed s{seed} is not a v3c3 NC fit seed {FH_SEEDS}')


# ------------------------------------------------------------------------------------------------ light IO
def sha256_file(path) -> str:
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def read_json(path, default=None):
    p = Path(path)
    if not p.is_file():
        return default
    return json.loads(p.read_text(encoding='utf-8-sig'))


def write_json(path, obj):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + '.tmp')
    tmp.write_text(json.dumps(obj, indent=1, sort_keys=False, default=_json_default, allow_nan=True), encoding='utf-8')
    os.replace(tmp, p)


def _json_default(o):
    if isinstance(o, (set, frozenset, tuple)):
        return list(o)
    if isinstance(o, Path):
        return str(o)
    v = getattr(o, 'value', None)
    if isinstance(v, (int, float)):
        return float(v)
    return repr(o)


def primal(x):
    """Plain float of a traffic value (float, forward Dual .value, reverse Dual .value); attribute reads only."""
    if x is None:
        return None
    if isinstance(x, bool):
        return float(x)
    if isinstance(x, (int, float)):
        return float(x)
    v = getattr(x, 'value', None)
    if v is None:
        v = getattr(x, '_validation_primal', None)
    return float(v) if v is not None else float('nan')


def finite(x):
    return x is not None and isinstance(x, (int, float)) and math.isfinite(x)


# ------------------------------------------------------------------------------------------------ markdown
def md_table(header, rows) -> str:
    def cell(v):
        if v is None:
            return '–'
        if isinstance(v, bool):
            return 'PASS' if v else 'FAIL'
        if isinstance(v, float):
            if not math.isfinite(v):
                return str(v)
            return f'{v:.6g}'
        return str(v).replace('|', '\\|').replace('\n', ' ')
    out = ['| ' + ' | '.join(header) + ' |', '|' + '|'.join('---' for _ in header) + '|']
    out += ['| ' + ' | '.join(cell(v) for v in r) + ' |' for r in rows]
    return '\n'.join(out)


# ================================================================================================ K8b (K8b-0)
# K8_PREDECLARATION_AMENDMENT_16 r2 (sha below) as corrected by AMENDMENT_17 (5bb43134), user decisions
# K8B_USER_DECISIONS_20261007 (D-K8b-1..4, variant A).  Harness only: the K8b runtime keys are config keys of the arm
# tunings (urban.sc1002w_saturation, urban.stopline_approach.city_arrival, urban.wout_exit_law); nothing here runs in
# the deployed path.
K8B_AMENDMENT16_SHA256 = 'e8ad8a346d93fcb23eea4428eca213163860dc02a48e4c6e022bf0180263cbc4'
K8B_AMENDMENT17_SHA256 = '5bb431346755ee45386746a0e926adba73a69e86ed3a342bdc8340a2ccc507b4'
K8B_GATES_STAGE = 'k8bt'                  # amendment 16 section 5.4: the judging stage token
K8B_KEY_PATHS = (('urban', 'stopline_approach', 'city_arrival'), ('urban', 'sc1002w_saturation'),
                 ('urban', 'wout_exit_law'))                       # P-2, P-1, P-4' + P-4b (section 2.0-1)
K8B_ARM_PATHS = (('urban', 'stopline_approach'),) + K8B_KEY_PATHS  # the four paths an arm may differ from BASE in
K8B_ARM_FILE = 'config_n31_v2_stopline_{storage}_k8b.json'         # section 4 K8b-4 (make_config_n31 output)
K8B_BASE_SHA256 = '319d07aac77472d4318ddf6266003916cb7afab98da35a06254952e393542bb8'   # section 5.2 (r2): condition
K8B_BASE_BLOB = '132620aef90d2280d54e899cc7c0dffd21c3cf19'        # git hash-object --no-filters (record)
K8B_K86H_ARM_SHA256 = {'SAF': '178de6c2c6a211eb811701455c7bfbb6b65d747b6e2698e2025c95bc766b7a6c',
                       'SAG': '26e3be09c7ddcbe2cacbf628f0407ab2c1d1d2fbc85f8c79a84693e792759f70'}   # k86h arm files
# Probe sample (D:/VISSIM-merge/k8b_probe/PROBE_SAMPLE.json sha 41aa5d87...): the only states a K8b-keyed capture /
# job / unit test may open before the judging stage (amendment 16 section 0.2: H3 24 + long starts L1 s43 2400 and
# L2 s47 4800; every other R-obs state of the judging seeds, T < 900 included, is refused).
K8B_PROBE_SAMPLE_SHA256 = '41aa5d8761b83b7cf9a32fe2a59e408eb4a23a736b374cd8d0ad4da3376dde10'
K8B_PROBE_H3 = ((31, 1050), (31, 1650), (31, 2100), (31, 2550), (31, 3300), (31, 4350), (31, 5100), (31, 6900),
                (43, 1500), (43, 2100), (43, 2550), (43, 2850), (43, 3450), (43, 3900), (43, 4650), (43, 6150),
                (47, 1500), (47, 2100), (47, 2550), (47, 2850), (47, 3450), (47, 4350), (47, 5250), (47, 5700))
K8B_PROBE_LONG = ((43, 2400), (47, 4800))
K8B_PROBE_STATES = frozenset(K8B_PROBE_H3 + K8B_PROBE_LONG)
K8B_LONG_JUDGED = frozenset((31, T) for T in LONG_H)                # 900 H24 / 2700 H42 / 4950 H27 of s31
K8B_WOUT = 'SC1001_W_out'
K8B_WOUT_RAMPS = ('RM_C10484', 'RM_C10480')                         # R_D_E, R_D_W (physical_ramp_branches names)
K8B_SC1002_W = ('SC1002_W_SC1001_to_E_SC101', 'SC1002_W_SC1001_to_S_SC105', 'SC1002_W_SC1001_to_N_SC2004')


def k8b_keys_of(doc):
    """The K8b key paths present in a tuning document (dotted names, declaration order)."""
    out = []
    for path in K8B_KEY_PATHS:
        node = doc
        for key in path:
            node = node.get(key) if isinstance(node, dict) else None
        if node is not None:
            out.append('.'.join(path))
    return out


def k8b_strip(doc):
    """A deep copy of `doc` without the three K8b key paths (section 5.2 r2 arm identity)."""
    import copy
    out = copy.deepcopy(doc)
    for path in K8B_KEY_PATHS:
        node = out
        for key in path[:-1]:
            node = node.get(key) if isinstance(node, dict) else None
        if isinstance(node, dict):
            node.pop(path[-1], None)
    return out


def k8b_judging_state(seed, T):
    """Amendment 16 sections 0.2 / 5.4: the states a K8b-keyed computation may not open before the judging stage --
    GRID9 and DP_T of every seed, the long judged starts of s31, every other R-obs decision state of the judging seeds
    31 / 43 / 47 that is not a probe sample state (T < 900 included), and any state of a non-fit or sealed seed."""
    seed, T = int(seed if seed is not None else ROBS_SEED), int(T)
    if (seed, T) in K8B_PROBE_STATES:
        return False
    if T in GRID9 or T in DP_T or (seed, T) in K8B_LONG_JUDGED:
        return True
    if seed in TL3M_SEEDS:
        return True                     # R-obs states of the judging seeds outside the probe sample (G-EB-14)
    return seed not in FH_SEEDS or seed in SEALED_SEEDS


def k8b_stage_open(args):
    """True when the caller passed --gates-stage k8bt with the amendment 16 sha (section 5.4); a wrong token or sha
    is refused (SystemExit), never ignored."""
    stage = getattr(args, 'gates_stage', None)
    sha = getattr(args, 'declaration_sha', None)
    if stage is None and sha is None:
        return False
    if stage != K8B_GATES_STAGE or sha != K8B_AMENDMENT16_SHA256:
        raise SystemExit(f'--gates-stage {stage!r} / --declaration-sha {sha!r}: the judging stage needs '
                         f'--gates-stage {K8B_GATES_STAGE} --declaration-sha {K8B_AMENDMENT16_SHA256}')
    return True


K8B_META_KEYS = ('k8b_p1', 'k8b_p2', 'k8b_p2_init', 'k8b_p4')         # capture metadata of a keyed template


def k8b_guard(tuning_path, seed, T, args, what, extra_keys=()):
    """Refuse (SystemExit, before any child starts) a K8b-keyed capture / job on a judging state outside the judging
    stage (amendment 16 sections 0.2 and 5.4).  Keyed = the tuning file carries a K8b key, or `extra_keys` is not
    empty (the job guard passes the K8b metadata keys of the template's capture record, so a keyed template is caught
    even when its tuning file is gone).  A tuning file that exists but cannot be parsed is refused; an absent file
    adds no key (the adapter cannot load it either).  Returns the keys (empty = not keyed, no check).  With the stage
    open the first keyed judging-state use is logged once to <out>/sa/k8b_judging_stage.json."""
    keys = []
    if tuning_path and Path(tuning_path).is_file():
        try:
            doc = json.loads(Path(tuning_path).read_text(encoding='utf-8-sig'))
        except (OSError, ValueError) as exc:
            raise SystemExit(f'K8b guard: tuning {tuning_path} unreadable ({exc!r}); refused')
        keys = k8b_keys_of(doc)
    keys = keys + [str(k) for k in extra_keys if str(k) not in keys]
    if not keys:
        return keys
    if k8b_judging_state(seed, T):
        if not k8b_stage_open(args):
            raise SystemExit(f'K8B_BLIND_REFUSED {what}: s{seed} T={T} is a judging state and the tuning carries '
                             f'{keys} (amendment 16 sections 0.2 / 5.4; pass --gates-stage {K8B_GATES_STAGE} '
                             f'--declaration-sha <amendment 16 sha> only in the judging stage)')
        mark = sa_out() / 'k8b_judging_stage.json'
        if not mark.is_file():
            import time
            write_json(mark, {'schema': 'k8b-judging-stage/v1', 'started': time.strftime('%Y-%m-%d %H:%M:%S'),
                              'first': {'what': what, 'seed': seed, 'T': T, 'tuning': str(tuning_path)},
                              'amendment16_sha256': K8B_AMENDMENT16_SHA256, 'root': str(c.R)})
    return keys


def add_k8b_stage_args(parser):
    g = parser.add_argument_group('K8b judging stage (amendment 16 section 5.4)')
    g.add_argument('--gates-stage', help=f'{K8B_GATES_STAGE}: allow K8b-keyed runs on judging states')
    g.add_argument('--declaration-sha', help='the amendment 16 sha256, required with --gates-stage')
    return parser


def vissim_count():
    """Number of running VISSIM processes (read only: Get-Process -Name VISSIM*; never touches them).  None when the
    query fails (an unknown count is never a clean pair, amendment 16 section 5.3.1)."""
    import subprocess
    try:
        out = subprocess.run(['powershell', '-NoProfile', '-Command',
                              '@(Get-Process -Name VISSIM* -ErrorAction SilentlyContinue).Count'],
                             capture_output=True, text=True, timeout=120)
        return int(out.stdout.strip().splitlines()[-1])
    except Exception:
        return None
