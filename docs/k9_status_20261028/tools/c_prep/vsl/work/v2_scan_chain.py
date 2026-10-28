# V2a (VSL_OFFLINE, data-after declaration): run the existing pinned FW_E scanner
# rmcause/phys/fwe_scan.py (sha 0619e9fc...) over 64cf-s29 FZPs, ONE AT A TIME, read only.
# Output: VS/out/scan/<tag>.json. Skips a tag whose output already exists.
import subprocess, sys, os, time, hashlib
SP = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8'
SCAN = SP + '/rmcause/phys/fwe_scan.py'
PIN = '0619e9fcbe14fd1b2e53d1cf884a8d740c0542f5686df33ef26f450a2b08bae7'
OUT = SP + '/c_port/vsl/out/scan'
PY = sys.executable
JOBS = [
    ('cx_joint_s29', 'D:/VISSIM_handoff/20261024/raw/joint/sdmpc/vissim_eval/sdmpc31_sdmpc8100_s29_001.fzp'),
    ('cx_window_s29', 'D:/VISSIM_handoff/20261024/raw/window/sdmpc/vissim_eval/sdmpc31_sdmpc8100_s29_001.fzp'),
    ('cx_off_s29', 'D:/VISSIM_handoff/20261024/raw/off/sdmpc/vissim_eval/sdmpc31_sdmpc8100_s29_001.fzp'),
    ('a1_s29', 'D:/VISSIM_runs/20261025_codex_a1_s29/sdmpc/vissim_eval/sdmpc31_sdmpc8100_s29_001.fzp'),
    ('cx_fwonly_s29', 'D:/VISSIM_handoff/20261024/raw/freeway_only/sdmpc/vissim_eval/sdmpc31_sdmpc8100_s29_001.fzp'),
]
if hashlib.sha256(open(SCAN, 'rb').read()).hexdigest() != PIN:
    raise SystemExit('fwe_scan.py sha differs from pin')
os.makedirs(OUT, exist_ok=True)
for tag, fzp in JOBS:
    if os.path.exists(f'{OUT}/{tag}.json'):
        print('skip', tag, flush=True)
        continue
    t0 = time.time()
    r = subprocess.run([PY, '-B', SCAN, tag, fzp, OUT], capture_output=True, text=True,
                       creationflags=0x00004000)  # BELOW_NORMAL_PRIORITY_CLASS
    print(tag, 'exit', r.returncode, round(time.time() - t0, 1), r.stdout.strip()[-200:], r.stderr.strip()[-400:], flush=True)
print('CHAIN_DONE', flush=True)
