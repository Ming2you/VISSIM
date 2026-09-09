# -*- coding: utf-8 -*-
"""N=21 격자에서 본선 수요 sweep 무제어 런 (2026-09-07 A단계).
왜 — METANET 동역학(tau·nu·kappa·delta_merge·phi_lane_drop) 재보정은 **21셀 관측**을 한-스텝-앞으로
대조해야 한다(2026-08-30 방식). 지금 있는 sweep 런은 8셀 config 로 돌아 state 의 freeway_segments 가 8개다.
겸사겸사 이 런들이 A단계 사다리의 무제어 기준선이 된다. x18 은 n21_nocontrol_ver2_x18_20260907 로 이미 있다.
사용: python chain_n21_sweep_20260907.py"""
import io, sys, time, shutil, subprocess
from pathlib import Path

R = Path(__file__).resolve().parents[1]
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
RUNNER = R / "scripts/run_real_world_single_watchdog_distributed_core17legs4b.ps1"
NET = R / "network/real_world_gaepo_modi/modi_eval_userfix Ver2.inpx"
CFG = R / "evaluation/configs/canon_ver2n21_20260907.json"
D21 = R / "evaluation/real_world_modi_control_ver2n21_20260907"
GATE = R / "evaluation/real_world_modi_inventory/urban_input_gate_map_ver2_20260907.csv"
PROF = R / "evaluation/configs/demand_profiles"
LOG = R / "evaluation/runs/chain_n21_20260907.log"
LEVELS = [("x15", "0.8333"), ("x12", "0.6667"), ("x08", "0.4444"), ("x04", "0.2222")]


def log(msg):
    line = "%s  %s" % (time.strftime("%m-%d %H:%M:%S"), msg)
    print(line, flush=True)
    with io.open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def main():
    for tag, mult in LEVELS:
        name = "n21_%s_nocontrol_ver2_20260907" % tag
        out = R / "evaluation/runs" / name
        if len(list(out.glob("decisions_*/action_*.json"))) >= 37:
            log("RESUME %s (완주 존재)" % name)
            continue
        if out.exists():
            shutil.rmtree(out, ignore_errors=True)
        ps = ("& '%s' -Name '%s' -OutDir '%s' -Network '%s' -Tuning '%s' -Mapping '%s' -VbsConfig '%s' "
              "-UrbanInputGateMap '%s' -Controller 'no-control' -ForceStepwise -SimPeriod 5400 "
              "-ControlIntervalSec 150 -Seed 13 -ControlStartSec 900 -WarmupController 'no-control' "
              "-StateLogIntervalSec 30 -DemandScale 1.0 -DemandProfile '%s'") % (
            RUNNER, name, out, NET, CFG, D21 / "control_mapping_ver2n21.json",
            D21 / "real_world_modi_control_config_ver2n21.vbs", GATE,
            PROF / ("ver2_fdsweep_%s_20260907.csv" % tag))
        log("START %s  본선 배율 %s" % (name, mult))
        t0 = time.time()
        with io.open(R / "evaluation/runs" / ("%s.chainlog.txt" % name), "w", encoding="utf-8") as lf:
            rc = subprocess.call(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps],
                                 stdout=lf, stderr=subprocess.STDOUT)
        n = len(list(out.glob("decisions_*/action_*.json")))
        log("DONE  %s exit=%s %.0f min 결정 %d/37" % (name, rc, (time.time() - t0) / 60, n))
        if n < 37:
            log("ERROR %s 미완주 — 체인 중단" % name)
            return
    log("N21_SWEEP_DONE")


if __name__ == "__main__":
    main()
