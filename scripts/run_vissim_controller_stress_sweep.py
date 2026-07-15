from __future__ import annotations

import argparse
import csv
import json
import queue
import subprocess
import threading
import time
from dataclasses import asdict, dataclass
from pathlib import Path


DEFAULT_NETWORK = Path("C:/Users/TRLAB/Desktop/찐찐막/Network_Vissim_Work/modi_eval_vsl_segmented.inpx")
DEFAULT_RUNNER = Path("scripts/run_stackelberg_vissim_controller.vbs")
DEFAULT_ADAPTER = Path("evaluation/controllers/vissim_stackelberg_adapter.py")
DEFAULT_CALIBRATION = Path("evaluation/calibration/vissim_network_calibration_v2_20260628.json")


@dataclass(frozen=True)
class StressScenario:
    scenario_id: str
    category: str
    demand_profile: str
    urban_volume_vph: float
    freeway_volume_vph: float


@dataclass(frozen=True)
class Case:
    case_id: str
    controller: str
    scenario: StressScenario
    sim_period_sec: int
    control_interval_sec: int
    rand_seed: int


def default_scenarios() -> list[StressScenario]:
    return [
        StressScenario("ramp_d_bias", "1_ramp_metering", "d_ramp_bias", 2200.0, 3000.0),
        StressScenario("ramp_f_bias", "1_ramp_metering", "f_ramp_bias", 2200.0, 3000.0),
        StressScenario("fw_eb_heavy", "2_vsl", "fw_eb_heavy", 1800.0, 3400.0),
        StressScenario("fw_wb_heavy", "2_vsl", "fw_wb_heavy", 1800.0, 3400.0),
        StressScenario("urban_d_heavy", "3_signal_split", "urban_d_heavy", 2400.0, 2600.0),
        StressScenario("urban_f_heavy", "3_signal_split", "urban_f_heavy", 2400.0, 2600.0),
        StressScenario("sym_high", "4_symmetric_high", "sym", 2600.0, 3400.0),
    ]


def parse_csv(text: str) -> list[str]:
    return [item.strip() for item in str(text).split(",") if item.strip()]


def parse_csv_ints(text: str) -> list[int]:
    return [int(item.strip()) for item in str(text).split(",") if item.strip()]


def selected_scenarios(selected: str) -> list[StressScenario]:
    scenarios = default_scenarios()
    if not selected:
        return scenarios
    wanted = set(parse_csv(selected))
    out = [
        item
        for item in scenarios
        if item.scenario_id in wanted or item.category in wanted or item.demand_profile in wanted
    ]
    missing = sorted(wanted - {s.scenario_id for s in out} - {s.category for s in out} - {s.demand_profile for s in out})
    if missing:
        raise ValueError(f"Unknown scenario(s): {', '.join(missing)}")
    return out


def build_cases(
    scenarios: list[StressScenario],
    controllers: list[str],
    sim_period_sec: int,
    control_interval_sec: int,
    seeds: list[int],
) -> list[Case]:
    cases: list[Case] = []
    for scenario in scenarios:
        for controller in controllers:
            for seed in seeds:
                case_id = (
                    f"{controller}_{scenario.scenario_id}"
                    f"_u{int(scenario.urban_volume_vph)}_fw{int(scenario.freeway_volume_vph)}"
                    f"_seed{int(seed)}_{int(sim_period_sec)}s"
                )
                cases.append(
                    Case(
                        case_id=case_id,
                        controller=controller,
                        scenario=scenario,
                        sim_period_sec=int(sim_period_sec),
                        control_interval_sec=int(control_interval_sec),
                        rand_seed=int(seed),
                    )
                )
    return cases


def case_paths(out_dir: Path, case: Case) -> dict[str, Path]:
    case_dir = out_dir / case.case_id
    return {
        "case_dir": case_dir,
        "state_csv": case_dir / "state.csv",
        "action_csv": case_dir / "action.csv",
        "decision_dir": case_dir / "decisions",
        "stdout": case_dir / "stdout.txt",
        "stderr": case_dir / "stderr.txt",
        "case_json": case_dir / "case.json",
    }


def manifest_fields() -> list[str]:
    return [
        "case_id",
        "controller",
        "scenario_id",
        "category",
        "demand_profile",
        "returncode",
        "elapsed_sec",
        "timed_out",
        "timeout_reason",
        "case_timeout_sec",
        "startup_timeout_sec",
        "first_progress_sec",
        "last_progress_sec",
        "progress_marker_count",
        "sim_period_sec",
        "urban_volume_vph",
        "freeway_volume_vph",
        "control_interval_sec",
        "rand_seed",
        "state_csv",
        "action_csv",
        "decision_dir",
        "stdout",
        "stderr",
        "tuning_json",
    ]


def append_manifest(out_dir: Path, row: dict[str, object]) -> None:
    path = out_dir / "batch_manifest_partial.csv"
    exists = path.exists()
    with path.open("a", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=manifest_fields(), extrasaction="ignore")
        if not exists:
            writer.writeheader()
        writer.writerow(row)


def run_case(
    case: Case,
    network: Path,
    runner: Path,
    adapter: Path,
    calibration: Path,
    tuning: Path | None,
    out_dir: Path,
    timeout_sec: float,
    startup_timeout_sec: float,
    reset_vissim_on_startup_timeout: bool,
) -> dict[str, object]:
    paths = case_paths(out_dir, case)
    paths["case_dir"].mkdir(parents=True, exist_ok=True)
    paths["decision_dir"].mkdir(parents=True, exist_ok=True)
    paths["case_json"].write_text(
        json.dumps(
            {
                "case": {
                    **asdict(case),
                    "scenario": asdict(case.scenario),
                },
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    cmd = [
        "cscript.exe",
        "//nologo",
        str(runner.resolve()),
        str(network),
        str(paths["state_csv"]),
        str(paths["action_csv"]),
        str(paths["decision_dir"]),
        str(case.sim_period_sec),
        str(case.scenario.urban_volume_vph),
        str(case.scenario.freeway_volume_vph),
        str(case.control_interval_sec),
        str(case.rand_seed),
        str(adapter.resolve()),
        str(calibration.resolve()),
        str(tuning.resolve()) if tuning is not None else "__none__.json",
        str(case.scenario.demand_profile),
        str(case.controller),
    ]
    started = time.perf_counter()
    timeout = float(timeout_sec) if timeout_sec and timeout_sec > 0 else None
    startup_timeout = float(startup_timeout_sec) if startup_timeout_sec and startup_timeout_sec > 0 else 0.0
    timed_out = False
    timeout_reason = ""
    first_progress_sec = 0.0
    last_progress_sec = 0.0
    progress_marker_count = 0
    stdout_lines: list[str] = []
    stderr_lines: list[str] = []
    line_queue: "queue.Queue[tuple[str, str]]" = queue.Queue()

    def reader(stream_name: str, pipe) -> None:
        try:
            for line in iter(pipe.readline, ""):
                line_queue.put((stream_name, line))
        finally:
            try:
                pipe.close()
            except Exception:
                pass

    def progress_from_files() -> bool:
        try:
            if paths["state_csv"].exists() and paths["state_csv"].stat().st_size > 220:
                return True
            if any(paths["decision_dir"].glob("action_*.json")):
                return True
            if paths["action_csv"].exists() and paths["action_csv"].stat().st_size > 150:
                return True
        except OSError:
            return False
        return False

    def kill_process_tree(proc: subprocess.Popen) -> None:
        try:
            subprocess.run(
                ["taskkill.exe", "/PID", str(proc.pid), "/T", "/F"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=20,
            )
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
    )
    threads = [
        threading.Thread(target=reader, args=("stdout", proc.stdout), daemon=True),
        threading.Thread(target=reader, args=("stderr", proc.stderr), daemon=True),
    ]
    for thread in threads:
        thread.start()

    while proc.poll() is None:
        now = time.perf_counter()
        made_progress = False
        while True:
            try:
                stream_name, line = line_queue.get_nowait()
            except queue.Empty:
                break
            if stream_name == "stdout":
                stdout_lines.append(line)
            else:
                stderr_lines.append(line)
            if "RUN_SINGLE_STEP" in line or "CONTROLLER_DECISION" in line or "STAGE=SIM_DONE" in line:
                made_progress = True
        if progress_from_files():
            made_progress = True
        if made_progress:
            progress_marker_count += 1
            elapsed_progress = now - started
            last_progress_sec = elapsed_progress
            if first_progress_sec <= 0.0:
                first_progress_sec = elapsed_progress

        elapsed = now - started
        if first_progress_sec <= 0.0 and startup_timeout > 0.0 and elapsed > startup_timeout:
            timed_out = True
            timeout_reason = "startup_freeze_no_run_single_step"
            kill_process_tree(proc)
            if reset_vissim_on_startup_timeout:
                try:
                    subprocess.run(
                        ["taskkill.exe", "/IM", "VISSIM200.exe", "/F"],
                        capture_output=True,
                        text=True,
                        encoding="utf-8",
                        errors="replace",
                        timeout=30,
                    )
                except Exception:
                    pass
            break
        if first_progress_sec > 0.0 and timeout is not None and elapsed > timeout:
            timed_out = True
            timeout_reason = "running_timeout_after_progress"
            kill_process_tree(proc)
            break
        time.sleep(0.5)

    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        kill_process_tree(proc)
    for thread in threads:
        thread.join(timeout=2)
    while True:
        try:
            stream_name, line = line_queue.get_nowait()
        except queue.Empty:
            break
        if stream_name == "stdout":
            stdout_lines.append(line)
        else:
            stderr_lines.append(line)

    returncode = int(proc.returncode if proc.returncode is not None else 124)
    if timed_out:
        returncode = 124
    stdout = "".join(stdout_lines)
    stderr = "".join(stderr_lines)
    if timed_out:
        stderr = (stderr or "") + f"\nTIMEOUT reason={timeout_reason} startup_timeout={startup_timeout} case_timeout={timeout}\n"
    elapsed = time.perf_counter() - started
    paths["stdout"].write_text(stdout, encoding="utf-8")
    paths["stderr"].write_text(stderr, encoding="utf-8")
    return {
        "case_id": case.case_id,
        "controller": case.controller,
        "scenario_id": case.scenario.scenario_id,
        "category": case.scenario.category,
        "demand_profile": case.scenario.demand_profile,
        "returncode": returncode,
        "elapsed_sec": round(elapsed, 3),
        "timed_out": timed_out,
        "timeout_reason": timeout_reason,
        "case_timeout_sec": timeout or "",
        "startup_timeout_sec": startup_timeout,
        "first_progress_sec": round(first_progress_sec, 3) if first_progress_sec > 0.0 else "",
        "last_progress_sec": round(last_progress_sec, 3) if last_progress_sec > 0.0 else "",
        "progress_marker_count": progress_marker_count,
        "sim_period_sec": case.sim_period_sec,
        "urban_volume_vph": case.scenario.urban_volume_vph,
        "freeway_volume_vph": case.scenario.freeway_volume_vph,
        "control_interval_sec": case.control_interval_sec,
        "rand_seed": case.rand_seed,
        "state_csv": str(paths["state_csv"]),
        "action_csv": str(paths["action_csv"]),
        "decision_dir": str(paths["decision_dir"]),
        "stdout": str(paths["stdout"]),
        "stderr": str(paths["stderr"]),
        "tuning_json": str(tuning) if tuning is not None else "",
    }


def completed_case_ids(out_dir: Path) -> set[str]:
    completed: set[str] = set()
    for manifest_name in ("batch_manifest_partial.csv", "batch_manifest.csv"):
        manifest = out_dir / manifest_name
        if not manifest.exists():
            continue
        with manifest.open("r", encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                if str(row.get("returncode", "")).strip() in ("0", "0.0"):
                    completed.add(str(row.get("case_id", "")))
    return completed


def existing_success_rows(out_dir: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    seen: set[str] = set()
    for manifest_name in ("batch_manifest.csv", "batch_manifest_partial.csv"):
        manifest = out_dir / manifest_name
        if not manifest.exists():
            continue
        with manifest.open("r", encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                case_id = str(row.get("case_id", ""))
                if not case_id or case_id in seen:
                    continue
                if str(row.get("returncode", "")).strip() in ("0", "0.0"):
                    seen.add(case_id)
                    rows.append(dict(row))
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--controllers", default="no-control,wu,pfo")
    parser.add_argument("--scenarios", default="")
    parser.add_argument("--sim-period-sec", type=int, default=1200)
    parser.add_argument("--control-interval-sec", type=int, default=60)
    parser.add_argument("--seed", type=int, default=13)
    parser.add_argument(
        "--seeds",
        default="",
        help="Comma-separated random seeds. Overrides --seed when provided.",
    )
    parser.add_argument("--timeout-sec", type=float, default=420.0)
    parser.add_argument(
        "--startup-timeout-sec",
        type=float,
        default=60.0,
        help="If no RunSingleStep/controller/file progress appears within this time, reset the case as a startup freeze.",
    )
    parser.add_argument(
        "--reset-vissim-on-startup-timeout",
        action="store_true",
        help="Kill leftover VISSIM200.exe processes after a startup-freeze watchdog timeout.",
    )
    parser.add_argument(
        "--resume-existing-ok",
        action="store_true",
        help="Skip cases already recorded with returncode 0 in the output manifest.",
    )
    parser.add_argument("--network", default=str(DEFAULT_NETWORK))
    parser.add_argument("--runner", default=str(DEFAULT_RUNNER))
    parser.add_argument("--adapter", default=str(DEFAULT_ADAPTER))
    parser.add_argument("--calibration", default=str(DEFAULT_CALIBRATION))
    parser.add_argument("--tuning", default="")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    scenarios = selected_scenarios(args.scenarios)
    controllers = parse_csv(args.controllers)
    seeds = parse_csv_ints(args.seeds) if str(args.seeds).strip() else [int(args.seed)]
    cases = build_cases(
        scenarios,
        controllers,
        sim_period_sec=int(args.sim_period_sec),
        control_interval_sec=int(args.control_interval_sec),
        seeds=seeds,
    )
    previous_success_rows: list[dict[str, object]] = []
    if args.resume_existing_ok:
        done = completed_case_ids(out_dir)
        cases = [case for case in cases if case.case_id not in done]
        previous_success_rows = existing_success_rows(out_dir)
    profile = {
        "controllers": controllers,
        "scenarios": [asdict(item) for item in scenarios],
        "sim_period_sec": int(args.sim_period_sec),
        "control_interval_sec": int(args.control_interval_sec),
        "seed": int(args.seed),
        "seeds": seeds,
        "timeout_sec": float(args.timeout_sec),
        "startup_timeout_sec": float(args.startup_timeout_sec),
        "reset_vissim_on_startup_timeout": bool(args.reset_vissim_on_startup_timeout),
        "resume_existing_ok": bool(args.resume_existing_ok),
        "tuning": str(args.tuning),
        "case_count": len(cases),
    }
    (out_dir / "profile.json").write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8")
    rows: list[dict[str, object]] = list(previous_success_rows)
    for idx, case in enumerate(cases, start=1):
        print(f"[{idx}/{len(cases)}] START {case.case_id}", flush=True)
        row = run_case(
            case,
            network=Path(args.network),
            runner=Path(args.runner),
            adapter=Path(args.adapter),
            calibration=Path(args.calibration),
            tuning=Path(args.tuning) if str(args.tuning).strip() else None,
            out_dir=out_dir,
            timeout_sec=float(args.timeout_sec),
            startup_timeout_sec=float(args.startup_timeout_sec),
            reset_vissim_on_startup_timeout=bool(args.reset_vissim_on_startup_timeout),
        )
        rows.append(row)
        append_manifest(out_dir, row)
        print(
            f"[{idx}/{len(cases)}] DONE {case.case_id} rc={row['returncode']} elapsed={row['elapsed_sec']}",
            flush=True,
        )
    (out_dir / "batch_manifest.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    with (out_dir / "batch_manifest.csv").open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=manifest_fields(), extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    failed = [row for row in rows if int(float(row.get("returncode", 999))) != 0]
    status = "failed" if failed else "ok"
    print(
        json.dumps(
            {
                "status": status,
                "case_count": len(rows),
                "failed_cases": [row.get("case_id", "") for row in failed],
                "out_dir": str(out_dir),
            },
            ensure_ascii=False,
        )
    )
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
