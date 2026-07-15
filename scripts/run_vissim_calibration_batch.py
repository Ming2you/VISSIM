from __future__ import annotations

import argparse
import concurrent.futures as futures
import csv
import json
import subprocess
import sys
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
        str(network),
        str(paths["state_csv"]),
        str(paths["segment_csv"]),
        str(paths["ramp_csv"]),
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
    started = time.perf_counter()
    timeout = float(case_timeout_sec) if case_timeout_sec and case_timeout_sec > 0 else None
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
        returncode = proc.returncode
        stdout = proc.stdout
        stderr = proc.stderr
        timed_out = False
    except subprocess.TimeoutExpired as exc:
        returncode = 124
        stdout = exc.stdout if isinstance(exc.stdout, str) else (exc.stdout or b"").decode("utf-8", errors="replace")
        stderr = exc.stderr if isinstance(exc.stderr, str) else (exc.stderr or b"").decode("utf-8", errors="replace")
        stderr = (stderr or "") + f"\nTIMEOUT after {timeout} sec\n"
        timed_out = True
    elapsed = time.perf_counter() - started
    paths["stdout"].write_text(stdout or "", encoding="utf-8")
    paths["stderr"].write_text(stderr or "", encoding="utf-8")
    return {
        "case_id": case.case_id,
        "returncode": returncode,
        "elapsed_sec": round(elapsed, 3),
        "timed_out": timed_out,
        "case_timeout_sec": timeout or "",
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
    fields = ["case_id", "returncode", "elapsed_sec", "timed_out", "case_timeout_sec", "state_csv", "segment_csv", "ramp_csv", "signal_csv", "urban_csv", "stdout", "stderr"]
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
    fields = ["case_id", "returncode", "elapsed_sec", "timed_out", "case_timeout_sec", "state_csv", "segment_csv", "ramp_csv", "signal_csv", "urban_csv", "stdout", "stderr"]
    with manifest_csv.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


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
            future_map[pool.submit(run_case, case, network, runner, out_dir, delay, args.case_timeout_sec)] = case
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
