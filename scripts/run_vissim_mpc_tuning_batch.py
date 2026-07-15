from __future__ import annotations

import argparse
import concurrent.futures as futures
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
DEFAULT_CALIBRATION = Path("evaluation/calibration/vissim_calibrated_overrides_vector_20260626.json")
DEFAULT_TUNING_DIR = Path("evaluation/configs/mpc_tuning")


@dataclass(frozen=True)
class Case:
    case_id: str
    tuning_name: str
    tuning_json: str
    demand_profile: str
    sim_period_sec: int
    urban_volume_vph: float
    freeway_volume_vph: float
    control_interval_sec: int
    rand_seed: int


def parse_csv_numbers(text: str, cast=float) -> list:
    out = []
    for token in str(text).split(","):
        token = token.strip()
        if not token:
            continue
        out.append(cast(token))
    return out


def tuning_files(tuning_dir: Path, selected: str = "") -> list[Path]:
    files = sorted(path for path in tuning_dir.glob("*.json") if path.is_file())
    if not selected:
        return files
    wanted = {item.strip() for item in selected.split(",") if item.strip()}
    out = []
    for path in files:
        stem = path.stem
        name = ""
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            name = str(raw.get("name", ""))
        except (OSError, json.JSONDecodeError):
            pass
        if stem in wanted or name in wanted:
            out.append(path)
    missing = sorted(wanted - {p.stem for p in out})
    missing = [m for m in missing if m not in {json.loads(p.read_text(encoding="utf-8")).get("name", "") for p in out}]
    if missing:
        raise ValueError(f"Unknown tuning profile(s): {', '.join(missing)}")
    return out


def case_profile(
    profile: str,
    tuning_dir: Path,
    selected_tunings: str,
    selected_demand_profiles: str,
    sim_period_sec: int | None,
    urban_volume_vph: float,
    freeway_volume_vph: float,
    control_interval_sec: int,
    seeds: list[int],
) -> list[Case]:
    files = tuning_files(tuning_dir, selected_tunings)
    if profile == "smoke" and not selected_tunings:
        files = [tuning_dir / "00_calibrated_base.json"]
    demand_profiles = ["sym"]
    if selected_demand_profiles:
        demand_profiles = [item.strip() for item in selected_demand_profiles.split(",") if item.strip()]
    elif profile in ("asym-smoke", "asym-grid"):
        demand_profiles = [
            "fw_eb_heavy",
            "fw_wb_heavy",
            "d_ramp_bias",
            "f_ramp_bias",
            "urban_west_heavy",
            "urban_east_heavy",
            "urban_north_heavy",
            "urban_d_heavy",
            "urban_f_heavy",
        ]
    if profile == "smoke":
        period = int(sim_period_sec or 300)
        seed_list = [seeds[0] if seeds else 13]
    elif profile in ("grid-smoke", "asym-smoke"):
        period = int(sim_period_sec or 300)
        seed_list = [seeds[0] if seeds else 13]
    elif profile in ("grid", "asym-grid"):
        period = int(sim_period_sec or 600)
        seed_list = seeds or [13, 29]
    else:
        raise ValueError(f"Unknown profile: {profile}")

    cases: list[Case] = []
    for tuning_path in files:
        if not tuning_path.exists():
            raise FileNotFoundError(tuning_path)
        tuning = json.loads(tuning_path.read_text(encoding="utf-8"))
        name = str(tuning.get("name", tuning_path.stem))
        for demand_profile in demand_profiles:
            for seed in seed_list:
                case_id = (
                    f"mpc_{name}_{demand_profile}_u{int(urban_volume_vph)}_fw{int(freeway_volume_vph)}"
                    f"_seed{int(seed)}_{period}s"
                )
                cases.append(
                    Case(
                        case_id=case_id,
                        tuning_name=name,
                        tuning_json=str(tuning_path),
                        demand_profile=demand_profile,
                        sim_period_sec=period,
                        urban_volume_vph=float(urban_volume_vph),
                        freeway_volume_vph=float(freeway_volume_vph),
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
        "action_csv": case_dir / "actions.csv",
        "decision_dir": case_dir / "decisions",
        "stdout": case_dir / "stdout.txt",
        "stderr": case_dir / "stderr.txt",
        "case_json": case_dir / "case.json",
    }


def run_case(
    case: Case,
    network: Path,
    runner: Path,
    adapter: Path,
    calibration: Path,
    out_dir: Path,
    startup_delay_sec: float,
    case_timeout_sec: float,
    startup_timeout_sec: float,
    reset_vissim_on_startup_timeout: bool,
) -> dict[str, object]:
    paths = case_paths(out_dir, case)
    paths["case_dir"].mkdir(parents=True, exist_ok=True)
    paths["decision_dir"].mkdir(parents=True, exist_ok=True)
    paths["case_json"].write_text(json.dumps(asdict(case), ensure_ascii=False, indent=2), encoding="utf-8")

    if startup_delay_sec > 0.0:
        time.sleep(float(startup_delay_sec))

    cmd = [
        "cscript.exe",
        "//nologo",
        str(runner.resolve()),
        str(network),
        str(paths["state_csv"]),
        str(paths["action_csv"]),
        str(paths["decision_dir"]),
        str(case.sim_period_sec),
        str(case.urban_volume_vph),
        str(case.freeway_volume_vph),
        str(case.control_interval_sec),
        str(case.rand_seed),
        str(adapter.resolve()),
        str(calibration.resolve()),
        str(Path(case.tuning_json).resolve()),
        str(case.demand_profile),
    ]
    started = time.perf_counter()
    timeout = float(case_timeout_sec) if case_timeout_sec and case_timeout_sec > 0 else None
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
            if (
                "RUN_SINGLE_STEP" in line
                or "CONTROLLER_DECISION" in line
                or "STAGE=SIM_DONE" in line
            ):
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
        "tuning_name": case.tuning_name,
        "demand_profile": case.demand_profile,
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
        "urban_volume_vph": case.urban_volume_vph,
        "freeway_volume_vph": case.freeway_volume_vph,
        "control_interval_sec": case.control_interval_sec,
        "rand_seed": case.rand_seed,
        "tuning_json": case.tuning_json,
        "state_csv": str(paths["state_csv"]),
        "action_csv": str(paths["action_csv"]),
        "decision_dir": str(paths["decision_dir"]),
        "stdout": str(paths["stdout"]),
        "stderr": str(paths["stderr"]),
    }


def manifest_fields() -> list[str]:
    return [
        "case_id",
        "tuning_name",
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
        "tuning_json",
        "state_csv",
        "action_csv",
        "decision_dir",
        "stdout",
        "stderr",
    ]


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


def append_manifest_row(out_dir: Path, row: dict[str, object]) -> None:
    manifest_csv = out_dir / "batch_manifest_partial.csv"
    fields = manifest_fields()
    exists = manifest_csv.exists()
    with manifest_csv.open("a", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        if not exists:
            writer.writeheader()
        writer.writerow({field: row.get(field, "") for field in fields})


def write_manifest(out_dir: Path, rows: list[dict[str, object]]) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "batch_manifest.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    fields = manifest_fields()
    with (out_dir / "batch_manifest.csv").open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows({field: row.get(field, "") for field in fields} for row in rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", choices=["smoke", "grid-smoke", "grid", "asym-smoke", "asym-grid"], default="smoke")
    parser.add_argument("--network", default=str(DEFAULT_NETWORK))
    parser.add_argument("--runner", default=str(DEFAULT_RUNNER))
    parser.add_argument("--adapter", default=str(DEFAULT_ADAPTER))
    parser.add_argument("--calibration-json", default=str(DEFAULT_CALIBRATION))
    parser.add_argument("--tuning-dir", default=str(DEFAULT_TUNING_DIR))
    parser.add_argument("--tunings", default="", help="Comma-separated tuning file stems or tuning names.")
    parser.add_argument("--demand-profiles", default="", help="Comma-separated demand profiles. Defaults to all asymmetric profiles for asym-* profiles.")
    parser.add_argument("--out-dir", default="evaluation/runs/mpc_tuning_smoke")
    parser.add_argument("--sim-period-sec", type=int, default=0)
    parser.add_argument("--urban-volume-vph", type=float, default=2600.0)
    parser.add_argument("--freeway-volume-vph", type=float, default=2400.0)
    parser.add_argument("--control-interval-sec", type=int, default=60)
    parser.add_argument("--seeds", default="13,29")
    parser.add_argument("--max-workers", type=int, default=1)
    parser.add_argument("--startup-stagger-sec", type=float, default=30.0)
    parser.add_argument("--case-timeout-sec", type=float, default=420.0)
    parser.add_argument(
        "--startup-timeout-sec",
        type=float,
        default=60.0,
        help="If no RunSingleStep/controller/file progress appears within this time, reset the case as a startup freeze.",
    )
    parser.add_argument(
        "--reset-vissim-on-startup-timeout",
        action="store_true",
        help="Kill leftover VISSIM200.exe processes after a startup-freeze watchdog timeout. Use with max-workers=1.",
    )
    parser.add_argument(
        "--resume-existing-ok",
        action="store_true",
        help="Skip cases already recorded with returncode 0 in the output manifest.",
    )
    args = parser.parse_args()

    network = Path(args.network)
    runner = Path(args.runner)
    adapter = Path(args.adapter)
    calibration = Path(args.calibration_json)
    tuning_dir = Path(args.tuning_dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    seeds = [int(value) for value in parse_csv_numbers(args.seeds, int)]
    sim_period = int(args.sim_period_sec) if int(args.sim_period_sec) > 0 else None
    cases = case_profile(
        profile=args.profile,
        tuning_dir=tuning_dir,
        selected_tunings=args.tunings,
        selected_demand_profiles=args.demand_profiles,
        sim_period_sec=sim_period,
        urban_volume_vph=float(args.urban_volume_vph),
        freeway_volume_vph=float(args.freeway_volume_vph),
        control_interval_sec=int(args.control_interval_sec),
        seeds=seeds,
    )
    previous_success_rows: list[dict[str, object]] = []
    if args.resume_existing_ok:
        done = completed_case_ids(out_dir)
        cases = [case for case in cases if case.case_id not in done]
        previous_success_rows = existing_success_rows(out_dir)
    (out_dir / "profile.json").write_text(
        json.dumps(
            {
                "profile": args.profile,
                "network": str(network),
                "runner": str(runner),
                "adapter": str(adapter),
                "calibration_json": str(calibration),
                "tuning_dir": str(tuning_dir),
                "tunings": args.tunings,
                "demand_profiles": args.demand_profiles,
                "max_workers": args.max_workers,
                "startup_stagger_sec": args.startup_stagger_sec,
                "case_timeout_sec": args.case_timeout_sec,
                "startup_timeout_sec": args.startup_timeout_sec,
                "reset_vissim_on_startup_timeout": args.reset_vissim_on_startup_timeout,
                "resume_existing_ok": args.resume_existing_ok,
                "case_count": len(cases),
                "cases": [asdict(case) for case in cases],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    rows: list[dict[str, object]] = list(previous_success_rows)
    with futures.ThreadPoolExecutor(max_workers=max(1, int(args.max_workers))) as pool:
        future_map = {}
        for idx, case in enumerate(cases):
            delay = (idx % max(1, int(args.max_workers))) * max(0.0, float(args.startup_stagger_sec))
            future_map[
                pool.submit(
                    run_case,
                    case,
                    network,
                    runner,
                    adapter,
                    calibration,
                    out_dir,
                    delay,
                    float(args.case_timeout_sec),
                    float(args.startup_timeout_sec),
                    bool(args.reset_vissim_on_startup_timeout),
                )
            ] = case
        for fut in futures.as_completed(future_map):
            row = fut.result()
            rows.append(row)
            append_manifest_row(out_dir, row)
            print(json.dumps(row, ensure_ascii=False), flush=True)

    rows.sort(key=lambda r: str(r["case_id"]))
    write_manifest(out_dir, rows)
    failed = [row for row in rows if int(row["returncode"]) != 0]
    status = "failed" if failed else "ok"
    print(
        json.dumps(
            {
                "status": status,
                "cases": len(rows),
                "failed_cases": [row["case_id"] for row in failed],
                "out_dir": str(out_dir),
            },
            ensure_ascii=False,
        ),
        flush=True,
    )
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
