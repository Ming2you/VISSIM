from __future__ import annotations

import argparse
import concurrent.futures as futures
import csv
import json
import queue
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, asdict
from pathlib import Path


DEFAULT_NETWORK = Path("C:/Users/TRLAB/Desktop/찐찐막/Network_Vissim_Work/modi_eval_vsl_segmented.inpx")
DEFAULT_RUNNER = Path("scripts/run_vissim_calibration_probe.vbs")


@dataclass(frozen=True)
class Case:
    case_id: str
    sim_period_sec: int
    urban_volume_vph: float
    freeway_volume_vph: float
    ramp_green_d_sec: float
    ramp_green_f_sec: float
    log_interval_sec: int
    rand_seed: int
    vsl_speed_kph: float = 120.0
    major_green_sec: float = 56.0
    minor_green_sec: float = 56.0
    route_bias: str = ""


def profile_cases(profile: str) -> list[Case]:
    if profile == "fd-smoke":
        return [
            Case(f"fd_fw{fw}_seed13", 240, 60, fw, 10, 10, 10, 13)
            for fw in (800, 1400, 2000)
        ]
    if profile == "fd":
        return [
            Case(f"fd_fw{fw}_seed{seed}", 900, 60, fw, 10, 10, 15, seed)
            for seed in (13, 29)
            for fw in (800, 1200, 1600, 2000, 2400, 2800)
        ]
    if profile == "ramp-smoke":
        return [
            Case(f"ramp_g{green}_seed13", 240, 900, 600, green, green, 10, 13)
            for green in (1, 2, 4, 6, 8, 10)
        ]
    if profile == "ramp":
        return [
            Case(f"ramp_g{green}_seed{seed}", 900, 1200, 600, green, green, 15, seed)
            for seed in (13, 29)
            for green in (1, 2, 4, 6, 8, 10)
        ]
    if profile == "ramp-d-bias":
        return [
            Case(f"rampD_bias_g{green}_seed{seed}", 900, 2400, 600, green, 10, 15, seed, route_bias="D_RAMP")
            for seed in (13, 29)
            for green in (1, 2, 4, 6, 8, 10)
        ]
    if profile == "ramp-f-bias":
        return [
            Case(f"rampF_bias_g{green}_seed{seed}", 900, 2400, 600, 10, green, 15, seed, route_bias="F_RAMP")
            for seed in (13, 29)
            for green in (1, 2, 4, 6, 8, 10)
        ]
    if profile == "signal-smoke":
        return [
            Case(f"signal_urban{urban}_seed13", 300, urban, 600, 10, 10, 10, 13)
            for urban in (800, 1600, 2400)
        ]
    if profile == "signal":
        return [
            Case(
                f"signal_mg{int(major)}_ng{int(minor)}_seed{seed}",
                900,
                3000,
                600,
                10,
                10,
                15,
                seed,
                major_green_sec=major,
                minor_green_sec=minor,
            )
            for seed in (13, 29)
            for major, minor in ((32, 32), (44, 44), (56, 56), (68, 68), (44, 68), (68, 44))
        ]
    if profile == "mfd-smoke":
        return [
            Case(f"mfd_urban{urban}_seed13", 360, urban, 1000, 10, 10, 10, 13)
            for urban in (800, 1600, 2400, 3000)
        ]
    if profile == "mfd":
        return [
            Case(f"mfd_urban{urban}_seed{seed}", 900, urban, 1000, 10, 10, 15, seed)
            for seed in (13, 29)
            for urban in (600, 1000, 1400, 1800, 2200, 2600, 3000, 3400)
        ]
    if profile == "f-ramp-bias-smoke":
        return [
            Case(f"f_ramp_bias_g{green}_seed13", 300, 1500, 600, 10, green, 10, 13, route_bias="F_RAMP")
            for green in (2, 4, 8, 10)
        ]
    if profile == "all-smoke":
        return profile_cases("fd-smoke") + profile_cases("ramp-smoke")
    raise ValueError(f"Unknown profile: {profile}")


def case_paths(out_dir: Path, case: Case) -> dict[str, Path]:
    case_dir = out_dir / case.case_id
    return {
        "case_dir": case_dir,
        "state_csv": case_dir / "state.csv",
        "segment_csv": case_dir / "segments.csv",
        "ramp_csv": case_dir / "ramps.csv",
        "signal_csv": case_dir / "signal_discharge.csv",
        "urban_csv": case_dir / "urban_production.csv",
        "stdout": case_dir / "stdout.txt",
        "stderr": case_dir / "stderr.txt",
        "case_json": case_dir / "case.json",
    }


def run_case(
    case: Case,
    network: Path,
    runner: Path,
    out_dir: Path,
    startup_delay_sec: float = 0.0,
    case_timeout_sec: float = 0.0,
    stall_timeout_sec: float = 300.0,
    max_attempts: int = 3,
    reset_vissim_on_timeout: bool = True,
) -> dict[str, object]:
    paths = case_paths(out_dir, case)
    paths["case_dir"].mkdir(parents=True, exist_ok=True)
    paths["case_json"].write_text(json.dumps(asdict(case), ensure_ascii=False, indent=2), encoding="utf-8")
    if startup_delay_sec > 0.0:
        time.sleep(float(startup_delay_sec))
    cmd = [
        "cscript.exe",
        "//nologo",
        str(runner.resolve()),
        str(network.resolve()),
        str(paths["state_csv"].resolve()),
        str(paths["segment_csv"].resolve()),
        str(paths["ramp_csv"].resolve()),
        str(case.sim_period_sec),
        str(case.urban_volume_vph),
        str(case.freeway_volume_vph),
        str(case.ramp_green_d_sec),
        str(case.ramp_green_f_sec),
        str(case.log_interval_sec),
        str(case.rand_seed),
        str(case.vsl_speed_kph),
        str(case.major_green_sec),
        str(case.minor_green_sec),
        str(case.route_bias),
    ]

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

    def kill_vissim() -> None:
        if not reset_vissim_on_timeout:
            return
        for image in ("VISSIM200.exe", "VISSIM200CL.exe"):
            try:
                subprocess.run(
                    ["taskkill.exe", "/IM", image, "/F"],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=30,
                )
            except Exception:
                pass

    def run_attempt(attempt: int) -> dict[str, object]:
        started = time.perf_counter()
        timeout = float(case_timeout_sec) if case_timeout_sec and case_timeout_sec > 0 else None
        stall_timeout = float(stall_timeout_sec) if stall_timeout_sec and stall_timeout_sec > 0 else 0.0
        timed_out = False
        timeout_reason = ""
        first_progress_sec = 0.0
        last_progress_sec = 0.0
        progress_marker_count = 0
        saw_sim_done = False
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

        last_progress_wall = started
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
                    or "STAGE=NET_LOADED" in line
                    or "STAGE=SIM_DONE" in line
                ):
                    made_progress = True
                if "STAGE=SIM_DONE" in line:
                    saw_sim_done = True
            if made_progress:
                progress_marker_count += 1
                last_progress_wall = now
                elapsed_progress = now - started
                last_progress_sec = elapsed_progress
                if first_progress_sec <= 0.0:
                    first_progress_sec = elapsed_progress

            elapsed = now - started
            if stall_timeout > 0.0 and now - last_progress_wall > stall_timeout:
                timed_out = True
                timeout_reason = "stall_no_run_single_step_progress"
                kill_process_tree(proc)
                kill_vissim()
                break
            if timeout is not None and elapsed > timeout:
                timed_out = True
                timeout_reason = "case_timeout"
                kill_process_tree(proc)
                kill_vissim()
                break
            time.sleep(0.5)

        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            kill_process_tree(proc)
            kill_vissim()
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
            if "STAGE=SIM_DONE" in line:
                saw_sim_done = True

        returncode = int(proc.returncode if proc.returncode is not None else 124)
        stdout = "".join(stdout_lines)
        stderr = "".join(stderr_lines)
        if timed_out:
            returncode = 124
            stderr = (stderr or "") + (
                f"\nTIMEOUT reason={timeout_reason} attempt={attempt} "
                f"stall_timeout={stall_timeout} case_timeout={timeout}\n"
            )
        if returncode == 0 and not saw_sim_done:
            returncode = 1
            stderr = (stderr or "") + "\nMISSING_SIM_DONE marker in runner stdout\n"
        elapsed = time.perf_counter() - started
        return {
            "returncode": returncode,
            "elapsed_sec": round(elapsed, 3),
            "timed_out": timed_out,
            "timeout_reason": timeout_reason,
            "stdout": stdout,
            "stderr": stderr,
            "attempt": attempt,
            "first_progress_sec": round(first_progress_sec, 3) if first_progress_sec > 0.0 else "",
            "last_progress_sec": round(last_progress_sec, 3) if last_progress_sec > 0.0 else "",
            "progress_marker_count": progress_marker_count,
        }

    attempts = max(1, int(max_attempts))
    final: dict[str, object] = {}
    attempt_rows: list[dict[str, object]] = []
    for attempt in range(1, attempts + 1):
        final = run_attempt(attempt)
        attempt_rows.append({
            "attempt": final.get("attempt", attempt),
            "returncode": final.get("returncode", ""),
            "elapsed_sec": final.get("elapsed_sec", ""),
            "timed_out": final.get("timed_out", ""),
            "timeout_reason": final.get("timeout_reason", ""),
            "first_progress_sec": final.get("first_progress_sec", ""),
            "last_progress_sec": final.get("last_progress_sec", ""),
            "progress_marker_count": final.get("progress_marker_count", ""),
        })
        if int(final.get("returncode", 1)) == 0:
            break
        if not final.get("timed_out"):
            break

    stdout = str(final.get("stdout", ""))
    stderr = str(final.get("stderr", ""))
    paths["stdout"].write_text(stdout, encoding="utf-8")
    paths["stderr"].write_text(stderr, encoding="utf-8")
    (paths["case_dir"] / "attempts.json").write_text(
        json.dumps(attempt_rows, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return {
        "case_id": case.case_id,
        "returncode": int(final.get("returncode", 1)),
        "elapsed_sec": final.get("elapsed_sec", ""),
        "timed_out": bool(final.get("timed_out", False)),
        "timeout_reason": final.get("timeout_reason", ""),
        "attempt": final.get("attempt", ""),
        "max_attempts": attempts,
        "case_timeout_sec": float(case_timeout_sec) if case_timeout_sec and case_timeout_sec > 0 else "",
        "stall_timeout_sec": float(stall_timeout_sec) if stall_timeout_sec and stall_timeout_sec > 0 else "",
        "first_progress_sec": final.get("first_progress_sec", ""),
        "last_progress_sec": final.get("last_progress_sec", ""),
        "progress_marker_count": final.get("progress_marker_count", ""),
        "state_csv": str(paths["state_csv"]),
        "segment_csv": str(paths["segment_csv"]),
        "ramp_csv": str(paths["ramp_csv"]),
        "signal_csv": str(paths["signal_csv"]),
        "urban_csv": str(paths["urban_csv"]),
        "stdout": str(paths["stdout"]),
        "stderr": str(paths["stderr"]),
    }


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
    manifest_json = out_dir / "batch_manifest.json"
    manifest_json.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    manifest_csv = out_dir / "batch_manifest.csv"
    fields = manifest_fields()
    with manifest_csv.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows({field: row.get(field, "") for field in fields} for row in rows)


def manifest_fields() -> list[str]:
    return [
        "case_id",
        "returncode",
        "elapsed_sec",
        "timed_out",
        "timeout_reason",
        "attempt",
        "max_attempts",
        "case_timeout_sec",
        "stall_timeout_sec",
        "first_progress_sec",
        "last_progress_sec",
        "progress_marker_count",
        "state_csv",
        "segment_csv",
        "ramp_csv",
        "signal_csv",
        "urban_csv",
        "stdout",
        "stderr",
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", choices=["fd-smoke", "fd", "ramp-smoke", "ramp", "ramp-d-bias", "ramp-f-bias", "signal-smoke", "signal", "mfd-smoke", "mfd", "f-ramp-bias-smoke", "all-smoke"], default="all-smoke")
    parser.add_argument("--network", default=str(DEFAULT_NETWORK))
    parser.add_argument("--runner", default=str(DEFAULT_RUNNER))
    parser.add_argument("--out-dir", default="evaluation/runs/calibration_batch_smoke")
    parser.add_argument("--max-workers", type=int, default=2)
    parser.add_argument(
        "--startup-stagger-sec",
        type=float,
        default=20.0,
        help="Delay successive worker starts to reduce Vissim COM startup freezes.",
    )
    parser.add_argument(
        "--case-timeout-sec",
        type=float,
        default=0.0,
        help="Optional wall-clock timeout per case. Timed-out cases are recorded with returncode 124.",
    )
    parser.add_argument(
        "--stall-timeout-sec",
        type=float,
        default=300.0,
        help="Kill and retry a case if no RUN_SINGLE_STEP/SIM_DONE progress appears for this many seconds.",
    )
    parser.add_argument(
        "--max-attempts",
        type=int,
        default=3,
        help="Maximum attempts per case after watchdog timeouts.",
    )
    parser.add_argument(
        "--no-reset-vissim-on-timeout",
        action="store_true",
        help="Do not taskkill leftover VISSIM200 processes when a watchdog timeout fires.",
    )
    args = parser.parse_args()

    network = Path(args.network)
    runner = Path(args.runner)
    out_dir = Path(args.out_dir)
    cases = profile_cases(args.profile)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "profile.json").write_text(
        json.dumps({
            "profile": args.profile,
            "network": str(network),
            "runner": str(runner),
            "max_workers": args.max_workers,
            "case_timeout_sec": args.case_timeout_sec,
            "stall_timeout_sec": args.stall_timeout_sec,
            "max_attempts": args.max_attempts,
            "reset_vissim_on_timeout": not args.no_reset_vissim_on_timeout,
            "case_count": len(cases),
            "cases": [asdict(case) for case in cases],
        }, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    rows: list[dict[str, object]] = []
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
                    out_dir,
                    delay,
                    args.case_timeout_sec,
                    args.stall_timeout_sec,
                    args.max_attempts,
                    not args.no_reset_vissim_on_timeout,
                )
            ] = case
        for fut in futures.as_completed(future_map):
            row = fut.result()
            rows.append(row)
            append_manifest_row(out_dir, row)
            print(json.dumps(row, ensure_ascii=False), flush=True)

    rows.sort(key=lambda r: str(r["case_id"]))
    write_manifest(out_dir, rows)
    failed = [r for r in rows if int(r["returncode"]) != 0]
    if failed:
        print(json.dumps({"status": "failed", "failed_cases": [r["case_id"] for r in failed]}, ensure_ascii=False))
        return 1
    print(json.dumps({"status": "ok", "cases": len(rows), "out_dir": str(out_dir)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
