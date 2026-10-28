export const meta = {
  name: 'obs150-probe-and-plan',
  description: 'Author and review the VISSIM COM probe for the 150 s observation path, and write the file-level implementation plan for option (가)',
  phases: [
    { title: 'Probe', detail: 'author probe scripts, review, fix' },
    { title: 'Plan', detail: 'file-level implementation plan + completeness critic' },
  ],
}

const CONTEXT = `
## Background
The SDMPC controller (D:\\VISSIM-merge\\sim3-n31, branch claude/sdmpc-n31-20260924) will move to:
- the 31-cell METANET plant on the FW80/U90 v2 network;
- SimRes 10;
- observations collected once per 150 s decision, with no per-second stepping.
Design doc (read it fully): D:\\VISSIM-merge\\evidence\\OBS150_DESIGN_20260923.md.
31-cell plan: D:\\VISSIM-merge\\evidence\\SDMPC_N31_PLAN_20260923.md.
The per-agent maps behind the design are the "result" lines of
C:\\Users\\TRLAB\\.claude\\projects\\C--Users-TRLAB-Desktop----\\491ef689-f002-4605-9dc5-e6d363495788\\subagents\\workflows\\wf_aac88c91-62c\\journal.jsonl.
The analysis scripts are in C:\\Users\\TRLAB\\AppData\\Local\\Temp\\claude\\C--Users-TRLAB-Desktop----\\491ef689-f002-4605-9dc5-e6d363495788\\scratchpad\\obs150.

## User decisions (2026-09-23 22:40)
- Option (가): keep head observation, rebuilt as a 150 s window v2, and build it EXACTLY ("정확하게 만들어 놓는게 낫지").
- The lane quantities are also exact, not constants:
  - 10643 per-lane destination mix;
  - 10681 per-lane arrival share.
  Both come from per-lane detectors created in memory by COM, like the head detectors.
- Qualified (green-only) crossings, exact:
  - Preferred: VISSIM data-collection raw data (per-vehicle passage times), read ONCE at each decision and intersected with the exact green intervals from the runner's own signal-write log (SimRes 10 => 0.1 s resolution). This needs VISSIM to write/flush the raw file during the run so it can be read at a pause.
  - Fallback: read cumulative detector counts at the signal-transition stops the event runner already makes.
- The user dislikes per-second reads and prefers one collection per 150 s.
- One VISSIM seat is reserved for development. D:\\VISSIM_runs\\20260923_stage1\\launch_reserved.ps1 keeps the stage-1 queue at 3 VISSIMs.
  - A dev run may use the 4th seat, but only if its VISSIM window title matches 'obs150|sdmpc|probe'. So dev network files must be named obs150_*.inpx or sdmpc31_*.inpx.
  - Total VISSIMs must never exceed 4 (a 5th COM creation is refused).
- The lane-change information (lane-group exchange, ramp-origin tags) is not used in the 31-cell path.

## Environment facts
- PTV Vissim 2020 SP14 at C:\\Program Files\\PTV Vision\\PTV Vissim 2020; COM ProgID Vissim.Vissim.
- Launch COM / cscript ONLY from PowerShell; Git Bash mangles Korean paths.
- Python: C:\\Users\\TRLAB\\AppData\\Local\\Programs\\Python\\Python312\\python.exe; set PYTHONUTF8=1.
- The existing fast runner D:\\VISSIM-merge\\sim3\\diagnostics\\fast_nc_run.ps1 / fast_nc_runner.vbs attributes VISSIM PIDs by window title.
- The SDMPC native runner is scripts\\run_real_world_stackelberg_controller.vbs in the worktree. Its RunEventContinuousMode is at ~VBS:721-880.
- v2 network (FW80/U90, base 110, demand v2, simRes 10): D:\\VISSIM_runs\\20260923_stage1\\s31_v2nc\\prepared\\network\\ (baseline_s31_v2nc.inpx and siblings).
- Archive example of in-memory detectors: search the repos for install_eval_detectors.vbs / AddDataCollectionPoint.

## HARD RULES
- NEVER instantiate Vissim COM or start VISSIM in this workflow. 4 licensed runs are live; the probe is launched later by the main session.
- Read-only on D:\\VISSIM-merge\\sim3, D:\\VISSIM-merge\\sim3-n31 and D:\\VISSIM_runs\\20260923_stage1 (live runs and calibration chains).
- Allowed writes, all new folders:
  - D:\\VISSIM-merge\\tools\\obs150_probe\\
  - D:\\VISSIM_runs\\20260923_obs150\\
  - the scratchpad ...\\scratchpad\\obs150_plan\\
- Cite file:line for claims about code.
`

const PROBE_SPEC = `
## Probe to build
Scripts: D:\\VISSIM-merge\\tools\\obs150_probe\\probe.vbs, run_probe.ps1 (the launcher I will run from PowerShell), check_probe.py (reads the results and prints a verdict per check).

Network: copy the whole v2 network folder to D:\\VISSIM_runs\\20260923_obs150\\probe\\network\\ with the .inpx renamed obs150_probe.inpx.
Find every file the .inpx references (signal controller supply files .sig and others, absolute or relative) and make the copy self-contained. Verify it statically.

Run: SimRes 10, from 0 to 1200 s, SimBreakAt at every multiple of 150, plus the extra stops the checks need. Log every COM call with its Err.Number. One failed check must not stop the others (explicit Err checks, never a blanket error-suppression that hides failures). Write results JSON with one block per check.

Checks:
(a) Enable data collection by COM before the first step. Find the Evaluation attribute names (candidates like DataCollCollectData, DataCollFromTime, DataCollToTime, DataCollInterval, and the raw-data flag). Report which names work.
(b) Create DataCollectionPoints in memory by COM and attach them to new DataCollectionMeasurements:
    - at 3-5 real signal-head positions (same link/lane/pos as the signalHead), including one SC1001-SC1005 head;
    - on each lane of connector 10681;
    - on each lane of 10643;
    - at a pos-40 station on link 26.
    Confirm the .inpx on disk is unchanged (sha before/after; never save the network).
(c) SimBreakAt precision at SimRes 10: is SimSec exactly t at each break?
(d) Vehs(Current,k,All) with k=t/150 versus (Current,Last,All) at each break for those measurements. Does the interval ending at t close at the pause?
(e) Link evaluation Volume(Current,k,All) on 2-3 connectors (e.g. 10681 and one off connector), plus its segment/attribute form.
(f) Ground truth for one window (e.g. 750-900): step RunSingleStep at SimRes 10 (0.1 s) through that window. Track vehicle fronts crossing the detector positions from (b). Compare with the detector counts of (d).
(g) Signal timing: on one COM-controlled signal group, write SigState at an integer break t. Single-step and read SigState at t+0.1, t+0.2 and t+1 to show when the write takes effect.
(h) Raw data: enable data-collection raw output. At several pauses, check that the file exists, grows, and holds records up to the current SimSec (flushed while paused). Parse per-vehicle passage times. Compare them with (f) for the ground-truth window.
(i) Wall time per 150 s of simulation between breaks, and per break.
Also report the Vissim version string.

Get API names from:
- repo usage (grep all VBS under D:\\VISSIM-merge\\sim3 and sim3-n31, including _archive);
- the Vissim type library, read OFFLINE without creating the COM object: e.g. pythoncom.LoadTypeLib on the installed .exe/.dll/.tlb, or .NET TypeLib reading. Report which method worked.
Mark every name that was not confirmed.

Deliver the exact PowerShell launch command, the expected wall time, and what each outcome means for the design (preferred vs fallback).
`

phase('Probe')
const author = await agent(CONTEXT + PROBE_SPEC + '\n## Your job: build the probe (do NOT run it). Return a report: files written, API-name evidence table (name | source | confirmed?), network copy verification, launch command, expected runtime, known uncertainties.', { label: 'probe:author', phase: 'Probe' })

const review = await agent(CONTEXT + PROBE_SPEC + `
## Your job: independent reviewer (do NOT run VISSIM). Read the probe files under D:\\VISSIM-merge\\tools\\obs150_probe and the network copy.
Check:
- API names against the type library or repo evidence.
- Each check establishes the fact it claims.
- Isolation: nothing written to live folders, the title matches 'obs150', the .inpx is never saved.
- Seat safety: the launcher refuses to start if 4 VISSIMs are running.
- Error handling: no hidden failures.
- The network copy is self-contained.
- The ground-truth logic of (f) and (h) is correct (sub-step crossing detection, lane matching).
Return a numbered list of REQUIRED fixes (with file:line) and optional improvements, or "no required fixes".

Author report:
${author}`, { label: 'probe:review', phase: 'Probe' })

const fixed = await agent(CONTEXT + PROBE_SPEC + `
## Your job: apply every REQUIRED fix from the review to the probe files (do NOT run VISSIM). Re-verify statically. Then return the final report:
- files and their purpose;
- the API evidence table;
- the launch command;
- the expected runtime;
- per check, what each outcome means;
- fixes applied / declined with reasons.

Author report:
${author}

Review:
${review}`, { label: 'probe:fix', phase: 'Probe' })

phase('Plan')
const plan = await agent(CONTEXT + `
## Your job: the file-level implementation plan for option (가), exact, integrated with the SDMPC-31 connection on the v2 network (read-only; write the plan to ...\\scratchpad\\obs150_plan\\PLAN.md and return it).
Cover, with file:line anchors in D:\\VISSIM-merge\\sim3-n31:
1. Runner (VBS):
   - SimRes from the network; SDMPC in event mode;
   - first step; VehRecResolution; frameAdvance at SimRes 10;
   - the decision-time read bundle (snapshot, link-eval volumes, detector counts, raw-data read);
   - COM detector creation (235 heads with eligibility per physical_groups, 10643/10681 per lane, sources, off-split stations);
   - the runner's green/ownership integration from its own writes and the .sig integration for native SGs;
   - source cumulative admitted + schedule integral;
   - removal of the per-second locks (VBS:464, 474-479, 675-680, 6058-6069) and the watchdog ps1 checks.
2. Python:
   - the new 150 s lane observer (off-split identity with T and T-150 snapshots; exact lane shares);
   - head window v2 (exact green-only crossings from raw passages x green intervals) and the consumer schema v2 in signal_head_observation.py;
   - provenance version; freeway_exit_count by conservation;
   - asserts against silent emptying (RW_STATE_LOG=decision).
3. SDMPC-31 wiring from SDMPC_N31_PLAN:
   - n31 manifest; scenario pack re-pinned to the v2 network (which pinned files, how each is regenerated);
   - head contract regenerated for v2 (head_service_resources.py:44-51);
   - source boundary A1; VSL wired (plant VSL derivative fix deferred by the user).
4. Tools: replay (make_replay_state etc.), watch_sdmpc.
5. Validation:
   - a SimRes-10 run with a one-off per-second recorder, to compare every new 150 s quantity with its per-second truth;
   - the offline replay equivalence;
   - a paired no-control run on the same runner.
6. The 9000 s launch recipe on v2.
For each step: inputs, outputs, verification, which probe check it depends on and the fallback. Keep the 21-cell path selectable by one config key (supersede-don't-flag: the new path is canonical). Give an honest effort estimate and the critical path.`, { label: 'plan:write', phase: 'Plan' })

const critic = await agent(CONTEXT + `
## Your job: completeness critic for this implementation plan. Compare it against OBS150_DESIGN_20260923.md (every table row and risk) and SDMPC_N31_PLAN_20260923.md (every blocker and review item).
List what is missing, wrong, unverifiable or mis-ordered, with file:line where possible. Be specific; say "complete" only if it is.

Plan:
${plan}`, { label: 'plan:critic', phase: 'Plan' })

return { probe: fixed, probe_review: review, plan, critic }
