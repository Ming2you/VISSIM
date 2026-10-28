"""Read-only checks for the K9-2-7 freeze FRZ_K92 (amendment 34 section 4.2, conditions 1-12).

Form follows SP/j1/fix/freeze/check_freeze_k8r.py (K8b). Differences: the new freeze folder and
the preflight folder are not known before the run, so this tool finds them from the captured
output (FREEZE_TOOL FRZ= line, PLAN LAUNCH_PLAN_OK line) and from the frozen/ top-level delta
against frozen_top_before.txt. Every key carries its amendment 34 section 4.2 condition number
("c1".."c12") or "x" for K8b-form extra checks. ALL_OK needs every key true.

Reads only: git (GIT_OPTIONAL_LOCKS=0), files. Writes only check_freeze_k92.json next to itself.
Prints paths, counts and sha only; last line is ALL_OK or NOT_OK.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

GWT8 = Path(r"D:\VISSIM-merge\sim3-n31-k8")
FROZEN = Path(r"D:\VISSIM-merge\frozen")
FRZ_OLD = FROZEN / "sdmpc31_b9734abe_202610141821"
RUNS_ROOT = Path(r"D:\VISSIM_runs\20261023_sdmpc31_k92")
NAME = "sdmpc31_v3c3_k92pre_s31"
SPF = Path(__file__).resolve().parent
OUT = SPF / "k92_freeze_preflight.out"
BEFORE = SPF / "frozen_top_before.txt"
HEAD = "c20aff1d7bf0c432cb4f20e2922bd406d857aa5d"
BASE = "b9734abe1c83f95c9cec5fca5e42b7b18cd45991"
BRANCH = "claude/k92-b1-20261016"
TUNING_REL = "diagnostics/sdmpc_n31_20260924/config_n31_v2.json"
TUNING_SHA = "c8e3ee2c99b66c255b2279f0aa18eaafc18d4c7689e59e260109fac3b7d71866"
TUNING_BLOB = "b6ccd50d96321e293f6ad9cf020e53ce1a8fbf5c"
TUNING_SIZE = 278607
GB7_REL = "diagnostics/sdmpc_n31_20260924/k8_gates/gb7_allowed.py"
GB7_SHA = "61c70c222cf3bed2a0a299b539aa3fccad288c059b72be678cceda2c3dc6f319"
GB7_BLOB = "1ca72d81f6e63736fa835cd408c9c9d6b7563ffa"
NET_SHA = "3de889f0257d998bed50611f798ea388bcf69396dbc40e5726b1e88ebdd31c2e"
DET_SHA = "108debbb4b021796b195927ba2140dafab571e1d976734190f5d8f5bd255cfbc"
OLD_FREEZE_SHA = "6143d3eb0d455e5fde46b190b4d4d8c2a7068a96c7fc9178126b922af937c7b6"
POLICY = "hold_previous_on_exception"
EXP_M, EXP_A, EXP_D = 12, 21, 0

GENV = dict(os.environ, GIT_OPTIONAL_LOCKS="0")


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def git(*args: str) -> str:
    return subprocess.run(["git", "-C", str(GWT8), *args], check=True, capture_output=True,
                          text=True, env=GENV).stdout


def blob_of(p: Path) -> str:
    return subprocess.run(["git", "hash-object", "--no-filters", str(p)], check=True,
                          capture_output=True, text=True, cwd=str(GWT8), env=GENV).stdout.strip()


def entry_sha(v):
    if isinstance(v, str):
        return v
    if isinstance(v, dict):
        return v.get("sha256")
    raise TypeError(type(v))


def same_path(a, b) -> bool:
    return str(a).rstrip("\\/").lower() == str(b).rstrip("\\/").lower()


res: dict = {}
ok_all = True


def check(key, cond, detail=None):
    global ok_all
    res[key] = {"ok": bool(cond), "detail": detail}
    if not cond:
        ok_all = False


# ---- captured output and discovery -------------------------------------------------------
out_lines = OUT.read_text(encoding="utf-8", errors="replace").splitlines()
res["out_sha256"] = sha(OUT)
res["out_line_count"] = len(out_lines)


def grab(pat):
    return [m for m in (re.search(pat, ln) for ln in out_lines) if m]


frz_m = grab(r"FREEZE_TOOL FRZ=(.+?)\s*$")
check("c8_frz_line_eq1", len(frz_m) == 1, len(frz_m))
FRZ_NEW = Path(frz_m[0].group(1)) if frz_m else None
plan_m = grab(r"PLAN LAUNCH_PLAN_OK plan=(.+?)\\launch_plan\.json\s*$")
check("x_plan_ok_line_eq1", len(plan_m) == 1, len(plan_m))
PRE = Path(plan_m[0].group(1)) if plan_m else None
rd_m = grab(r"\bRUN_DIR (.+?)\s*$")
check("x_run_dir_eq_plan_dir", len(rd_m) == 1 and PRE is not None and same_path(rd_m[0].group(1), PRE),
      [m.group(1) for m in rd_m])
if FRZ_NEW is None or PRE is None:
    res["ALL_OK"] = False
    (SPF / "check_freeze_k92.json").write_text(json.dumps(res, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("NOT_OK (freeze or preflight folder not found in output)")
    sys.exit(1)
res["frz_new"] = str(FRZ_NEW)
res["preflight_dir"] = str(PRE)
check("c8_frz_name", same_path(FRZ_NEW.parent, FROZEN)
      and re.fullmatch(rf"sdmpc31_{HEAD[:8]}_\d{{12}}", FRZ_NEW.name) is not None, FRZ_NEW.name)
check("x_pre_under_runs_root", same_path(PRE.parent, RUNS_ROOT / "_preflight")
      and re.fullmatch(rf"{re.escape(NAME)}_\d{{8}}_\d{{6}}", PRE.name) is not None, PRE.name)

# ---- FREEZE.json --------------------------------------------------------------------------
new_freeze_sha = sha(FRZ_NEW / "FREEZE.json")
old_freeze_sha = sha(FRZ_OLD / "FREEZE.json")
res["new_freeze_sha256"] = new_freeze_sha
fn = json.loads((FRZ_NEW / "FREEZE.json").read_text(encoding="utf-8"))
fo = json.loads((FRZ_OLD / "FREEZE.json").read_text(encoding="utf-8"))
check("c11_old_freeze_unchanged", old_freeze_sha == OLD_FREEZE_SHA, old_freeze_sha)
check("c8_new_git_head", fn["git"]["head"] == HEAD, fn["git"]["head"])
check("c8_new_branch", fn["git"]["branch"] == BRANCH, fn["git"]["branch"])
check("c8_new_status_entries_0", fn["git"]["status_entries"] == 0, fn["git"]["status_entries"])
remote_ref = git("rev-parse", f"refs/remotes/origin/{BRANCH}").strip()
check("c8_head_eq_pushed_ref", remote_ref == HEAD, remote_ref)

# ---- condition 10: file-table diff vs git diff ---------------------------------------------
nf = {k: entry_sha(v) for k, v in fn["files"].items()}
of = {k: entry_sha(v) for k, v in fo["files"].items()}
changed = sorted(k for k in nf.keys() & of.keys() if nf[k] != of[k])
added = sorted(nf.keys() - of.keys())
removed = sorted(of.keys() - nf.keys())
gd = {"M": set(), "A": set(), "D": set(), "other": set()}
for line in git("diff", "--name-status", "--no-renames", BASE, HEAD).splitlines():
    st, path = line.split("\t", 1)
    gd.get(st, gd["other"]).add(path)
check("c10_diff_M_eq_changed", set(changed) == gd["M"], {"changed": changed, "git_M": sorted(gd["M"])})
check("c10_diff_A_eq_added", set(added) == gd["A"], {"added": added, "git_A": sorted(gd["A"])})
check("c10_diff_D_eq_removed", set(removed) == gd["D"], {"removed": removed, "git_D": sorted(gd["D"])})
check("c10_diff_other_empty", not gd["other"], sorted(gd["other"]))
check("c10_counts_M12_A21_D0", (len(changed), len(added), len(removed)) == (EXP_M, EXP_A, EXP_D),
      {"M": len(changed), "A": len(added), "D": len(removed)})
check("c10_total_33", len(changed) + len(added) + len(removed) == 33, len(changed) + len(added) + len(removed))
check("x_file_count", fn["file_count"] == len(nf) == len(of) + len(added) - len(removed),
      {"new": fn["file_count"], "old": fo["file_count"]})
blob_rows = []
blob_ok = True
for p in sorted(gd["M"] | gd["A"]):
    lt = git("ls-tree", HEAD, "--", p).split()
    fpath = FRZ_NEW / Path(p)
    ho = blob_of(fpath)
    s = sha(fpath)
    row_ok = (len(lt) >= 3 and lt[2] == ho) and (s == nf[p])
    blob_ok &= row_ok
    blob_rows.append({"path": p, "ls_tree": lt[2] if len(lt) >= 3 else None, "frz_blob": ho,
                      "frz_sha256": s, "table_sha256": nf[p], "ok": row_ok})
check("c10_frz_bytes_eq_commit_33", blob_ok and len(blob_rows) == 33, blob_rows)

# ---- condition 9: tuning and gb7 -----------------------------------------------------------
t_frz = FRZ_NEW / Path(TUNING_REL)
t_sha = sha(t_frz)
check("c9_tuning_frz_sha", t_sha == TUNING_SHA, t_sha)
check("c9_tuning_frz_blob", blob_of(t_frz) == TUNING_BLOB, blob_of(t_frz))
check("c9_tuning_table_sha", nf.get(TUNING_REL) == TUNING_SHA, nf.get(TUNING_REL))
check("c9_tuning_gwt8_sha", sha(GWT8 / Path(TUNING_REL)) == TUNING_SHA, sha(GWT8 / Path(TUNING_REL)))
check("c9_tuning_head_blob", git("ls-tree", HEAD, "--", TUNING_REL).split()[2] == TUNING_BLOB, None)
check("x_tuning_size", t_frz.stat().st_size == TUNING_SIZE, t_frz.stat().st_size)
g_frz = FRZ_NEW / Path(GB7_REL)
g_blob = blob_of(g_frz)
check("c9_gb7_frz_blob_eq_head", g_blob == GB7_BLOB == git("ls-tree", HEAD, "--", GB7_REL).split()[2], g_blob)
check("c9_gb7_frz_sha", sha(g_frz) == GB7_SHA == nf.get(GB7_REL), sha(g_frz))

# ---- conditions 3 and 5: plan and provenance -----------------------------------------------
plan_p = PRE / "launch_plan.json"
plan = json.loads(plan_p.read_text(encoding="utf-8"))
prov_p = PRE / "preflight" / f"run_provenance_{NAME}.json"
prov = json.loads(prov_p.read_text(encoding="utf-8"))
res["plan_sha256"] = sha(plan_p)
res["prov_sha256"] = sha(prov_p)
pf = plan.get("freeze") or {}
pt = plan.get("tuning") or {}
pee = plan.get("expected_env") or {}
res["plan_freeze"] = {k: pf.get(k) for k in ("sha256", "head", "tree_sha256")}
res["plan_tuning_sha256"] = pt.get("sha256")
res["plan_detectors"] = {k: (plan.get("detectors") or {}).get(k) for k in ("sha256", "rows")}
check("c3_plan_tuning_sha", pt.get("sha256") == TUNING_SHA, pt.get("sha256"))
check("c3_plan_warnings_empty", plan.get("warnings") == [], plan.get("warnings"))
check("c3_plan_expected_env_policy", pee.get("RW_DECISION_ERROR_POLICY") == POLICY, pee.get("RW_DECISION_ERROR_POLICY"))
check("x_plan_freeze_sha_head", pf.get("sha256") == new_freeze_sha and pf.get("head") == HEAD, None)
check("x_plan_root", same_path(plan.get("root"), FRZ_NEW), plan.get("root"))
check("x_plan_detectors", (plan.get("detectors") or {}).get("sha256") == DET_SHA
      and (plan.get("detectors") or {}).get("rows") == 294, res["plan_detectors"])
check("x_plan_name_ctrl_seed_period", plan.get("name") == NAME and plan.get("controller") == "no-control"
      and plan.get("seed") == 31 and plan.get("sim_period") == 9000,
      {k: plan.get(k) for k in ("name", "controller", "seed", "sim_period")})
pfiles = prov.get("files") or {}
penv = prov.get("env") or {}
res["prov_run_id"] = prov.get("run_id")
res["prov_workspace_git_commit"] = prov.get("workspace_git_commit")
check("c5_prov_env_policy", penv.get("RW_DECISION_ERROR_POLICY") == POLICY, penv.get("RW_DECISION_ERROR_POLICY"))
check("c5_prov_files_tuning", (pfiles.get("tuning") or {}).get("sha256") == TUNING_SHA, (pfiles.get("tuning") or {}).get("sha256"))
check("c5_prov_files_network", (pfiles.get("network") or {}).get("sha256") == NET_SHA, (pfiles.get("network") or {}).get("sha256"))
check("x_prov_workspace_root", same_path(prov.get("workspace_root"), FRZ_NEW), prov.get("workspace_root"))
for k in ("controller", "seed", "sim_period_sec"):
    res[f"prov_{k}"] = prov.get(k)

# ---- log lines (conditions 1-7, 12) --------------------------------------------------------
def count(pat):
    return sum(1 for ln in out_lines if re.search(pat, ln))


H = re.escape(HEAD)
F = re.escape(new_freeze_sha)
pats = {
    "c1_FREEZE_OK": rf"FREEZE_TOOL FREEZE_OK .*sha256={F} .*head={H} status_entries=0\s*$",
    "c1_FREEZE_DONE": r"FREEZE_TOOL FREEZE_DONE ",
    "c2_FREEZE_VERIFIED": rf"FREEZE FREEZE_VERIFIED .*sha256={F} .*head={H}\s*$",
    "c3_LAUNCH_PLAN_DETAIL": r"PLAN LAUNCH_PLAN_DETAIL .*network_sha=3de889f0 detectors=294 controller=no-control sim_period=9000 seed=31 ",
    "c4_NETWORK_COPY_OK": rf"NETCOPY NETWORK_COPY_OK .*sha256={NET_SHA} sig=42 ",
    "c4_NETWORK_OK": rf"NETWORK NETWORK_OK .*sha256={NET_SHA} sig=42\s*$",
    "c5_PROVENANCE_OK": rf"PREFLIGHT PROVENANCE_OK .*freeze={F}\s*$",
    "c6_WD_POLICY": r"WD RW_DECISION_ERROR_POLICY=hold_previous_on_exception \(runtime\.decision_error_policy\)\s*$",
    "c6_WD_POLICY_any": r"RW_DECISION_ERROR_POLICY",
    "c7_PREFLIGHT_ONLY_done": r"PREFLIGHT_ONLY done; no VISSIM started\s*$",
    "c7_EXIT0": rf"EXIT {re.escape(NAME)} code=0\s*$",
    "c7_EXIT_any": r"\bEXIT ",
    "x_ROBOCOPY_exit1": r"FREEZE_TOOL ROBOCOPY exit=1 ",
    "x_OBS150_rows294": r"OBS150 cadence=decision150 .*rows=294 ",
    "x_no_global_kill": r"OBS150 kill_policy=pid_only no_global_kill=True max_attempts=1\s*$",
    "x_WATCHDOG_ARGS_NoGlobalKill_PreflightOnly": r"WATCHDOG_ARGS .* -NoGlobalKill( |.* )-PreflightOnly\s*$",
    "x_LAUNCH_preflight_only": r"LAUNCH name=sdmpc31_v3c3_k92pre_s31 .*preflight_only=True ",
}
cnt = {k: count(p) for k, p in pats.items()}
res["log_counts"] = cnt
for k in pats:
    check(f"{k}_eq1", cnt[k] == 1, cnt[k])
plan_detail = grab(r"PLAN LAUNCH_PLAN_DETAIL sha256=([0-9a-f]{64}) ")
check("x_plan_detail_sha_eq_file", len(plan_detail) == 1 and plan_detail[0].group(1) == res["plan_sha256"],
      [m.group(1) for m in plan_detail])
bad_words = [ln for ln in out_lines if re.search(r"(?i)\b(error|exception|fail|refuse|warning)\b", ln)
             and "RW_DECISION_FAIL_FAST" not in ln and "RW_DECISION_ERROR_POLICY" not in ln]
check("c12_log_no_error_words", not bad_words, bad_words)

# run-folder launch log equals captured output
ll_p = PRE / f"launch_{NAME}.log"
ll = ll_p.read_text(encoding="utf-8", errors="replace").splitlines()
res["launch_log_sha256"] = sha(ll_p)
check("x_launch_log_eq_out", ll == out_lines, {"launch_log_lines": len(ll), "out_lines": len(out_lines)})

# sig count in preflight network
sigs = [p for p in (PRE / "network").iterdir() if p.suffix.lower() == ".sig"]
check("c4_sig_files_42", len(sigs) == 42, len(sigs))

# ---- condition 11: caches in FRZ_NEW, frozen/ top-level delta -------------------------------
cache_hits = []
for root, dirs, files in os.walk(FRZ_NEW):
    for d in dirs:
        if d in ("__pycache__", "__tangentcache__", ".pytest_cache"):
            cache_hits.append(os.path.join(root, d))
    for f in files:
        if f.endswith(".pyc"):
            cache_hits.append(os.path.join(root, f))
check("c11_frz_new_no_cache", not cache_hits, cache_hits[:20])
before = {ln.split("\t")[0] for ln in BEFORE.read_text(encoding="utf-8-sig").splitlines() if ln.strip()}
after = {p.name for p in FROZEN.iterdir()}
check("c11_frozen_top_delta", (after - before) == {FRZ_NEW.name, f"robocopy_{FRZ_NEW.name}.log"} and not (before - after),
      {"added": sorted(after - before), "removed": sorted(before - after), "before": len(before), "after": len(after)})
check("x_no_gitstate_tmp", not [n for n in after if n.startswith(".gitstate_")], None)

# run name not occupied: RunsRoot holds only _preflight\<this preflight>
rr = sorted(p.name for p in RUNS_ROOT.iterdir())
pr = sorted(p.name for p in (RUNS_ROOT / "_preflight").iterdir())
check("x_runs_root_only_preflight", rr == ["_preflight"] and pr == [PRE.name], {"runs_root": rr, "_preflight": pr})

res["new_tree_sha256"] = fn.get("tree_sha256")
res["new_file_count"] = fn.get("file_count")
res["new_total_bytes"] = fn.get("total_bytes")
res["new_created_at"] = fn.get("created_at")
res["new_plan_subtree_files"] = fn.get("plan_subtree_files")
res["old_plan_subtree_files"] = fo.get("plan_subtree_files")
res["new_freeze_json_bytes"] = (FRZ_NEW / "FREEZE.json").stat().st_size
res["ALL_OK"] = ok_all
dst = SPF / "check_freeze_k92.json"
dst.write_text(json.dumps(res, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
n_checks = sum(1 for v in res.values() if isinstance(v, dict) and "ok" in v)
n_ok = sum(1 for v in res.values() if isinstance(v, dict) and v.get("ok") is True)
print(f"CHECKS {n_ok}/{n_checks} json={dst} frz={FRZ_NEW} freeze_sha256={new_freeze_sha}")
for k, v in res.items():
    if isinstance(v, dict) and "ok" in v and not v["ok"]:
        print("FAIL", k, json.dumps(v["detail"], ensure_ascii=False)[:2000])
print("ALL_OK" if ok_all else "NOT_OK")
sys.exit(0 if ok_all else 1)
