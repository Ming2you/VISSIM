export const meta = {
  name: 'vissim-step-cost',
  description: 'Find why the SDMPC native run needs 12-15 min per 150 sim-s and what would speed it up',
  phases: [
    { title: 'Investigate', detail: 'frame writer, consumer, actuation writes, live measurement' },
    { title: 'Verify', detail: 'one adversarial checker per investigator' },
    { title: 'Synthesize', detail: 'attribution + ranked speedups' },
  ],
}

const SCRATCH = 'C:\\Users\\TRLAB\\AppData\\Local\\Temp\\claude\\C--Users-TRLAB-Desktop----\\491ef689-f002-4605-9dc5-e6d363495788\\scratchpad\\stepcost'

const CONTEXT = `
## Situation (all facts below were checked by the lead)
A native VISSIM closed-loop run of an SDMPC traffic controller is LIVE right now:
run folder D:\\VISSIM_runs\\20260923_sdmpc\\sdmpc_lp_9000b (9000 sim-s, started 13:32 today, expected ~20 h).
The user asks (Korean): "Why does simulating 150 s take 12-15 min? Is COM overwritten every second?
Wouldn't writing COM only when a signal changes -- or once per 150 s, since the signal plan is held for
150 s -- be much faster?"

### HARD RULES -- the live run must not be disturbed
- Read-only. Do NOT kill, stop, suspend or launch VISSIM, cscript, powershell or python processes of the run.
  Do NOT start any VISSIM instance. Do NOT attach to the running VISSIM via COM (no GetObject).
- Do NOT modify any file under D:\\VISSIM-merge\\sim3, C:\\Users\\TRLAB\\Documents\\ChatGPT\\VISSIM, or D:\\VISSIM_runs.
  The run re-reads Python sources from D:\\VISSIM-merge\\sim3 at every decision.
- Write scratch files (benchmarks, scripts) only under ${SCRATCH} (create it).
- frame_*.json files are ~1 MB each: never print a whole one; summarize them with Python.
- Shell: Git Bash via the Bash tool (paths like /d/VISSIM-merge/...), or PowerShell for process queries.
  Python: \`python\` (3.12). cscript is available for VBScript micro-benchmarks (no VISSIM needed).

### Code
- Runner: D:\\VISSIM-merge\\sim3\\scripts\\run_real_world_stackelberg_controller.vbs (6482 lines).
  RunStepwiseMode (~line 672) does, every simulated second: Vissim.Simulation.RunSingleStep,
  ValidateRuntimeSignalPersistence, CollectHeadObservation, RunControllerDecision (only every 150 s),
  ApplyRuntimeSignals, ApplyRuntimeRampMeters, ApplyIncidentLaneClosure, SealHeadSignalStates,
  LogStateCsv (every 30 s). Stepwise mode is forced because head observation is enabled
  (obsEnabled -> "RUN_MODE=STEPWISE_PHYSICAL_HEAD_OBSERVATION"); other modes exist
  (RunContinuousStaticMode, RunEventContinuousMode using RunContinuousTo + SimBreakAt, ~lines 721-880).
- PerfAdd/PerfCount instrumentation (enabled only with env RW_PERF=1, OFF in this run) with names such as
  scan.vehicles, head.capture, head.history, head.seal, head.signal_capture, signals.runtime,
  signals.readback, rampmeters.runtime, log.state_csv, sim.step. Report lines look like
  "PERF name=<n> sec=<s> n=<count>".
- VBS config used by the run: C:\\Users\\TRLAB\\Documents\\ChatGPT\\VISSIM\\.worktrees\\sdmpc-lane-plant-20260921\\diagnostics\\lane_plant_20260921\\scenario\\lane_native.vbs
  (byte copy: D:\\VISSIM-merge\\sim3\\diagnostics\\lane_plant_20260921\\scenario\\lane_native.vbs).
- Env of the run: RW_LANE_PLANT_OBSERVATION=1, RW_VEHICLE_OBSERVATION_INTERVAL_SEC=1, RW_SIGNAL_OBSERVATION=1,
  RW_QUEUE_COUNTER=1, RW_QUEUE_WINDOW=1, RW_MAINLINE_SG_ONLY=1, RW_DECISION_FAIL_FAST=1, RW_OFFSET_WRITER=experiment,
  RW_RAMP_AMBER_SEC=0. Provenance: <run>\\run_provenance_sdmpc_lp_9000b.json. Log: <run>\\runlog_sdmpc_lp_9000b.txt.
- Python consumer: D:\\VISSIM-merge\\sim3\\evaluation\\controllers\\ (vissim_stackelberg_adapter.py main ->
  runtime_setup.configure_runtime -> lane_plant_runtime.observe_live, head observation code). When head
  observation was sampled every 5 s instead of 1 s the lane plant failed with KeyError: 2 at sim_sec=150,
  i.e. it indexes per-second frames.

### Measurements already made
- Previous identical run (sdmpc_lp_9000, died at 1050 s) after ~91 min wall: CPU seconds
  cscript 3466, VISSIM200 285, python ~830 (decisions). VISSIM itself (including serving COM calls) is small.
- Wall time per 150 sim-s during the no-control warmup grew with traffic: 0-150 ~2 min, 150-300 ~5,
  300-450 ~8, 450-600 ~10, 600-750 ~11.5, 750-900 ~12.6, 900-1050 ~15.
- Fast no-control runs (diagnostics/fast_nc_run.ps1, continuous mode) do ~153 sim-s per wall minute.
- <run>\\decisions_sdmpc_lp_9000b held 751 files frame_000000..000750.json at t~750 (~850 KB each at t~740,
  423 MB total); right after the 750 s decision they were all gone. Also there: observer_checkpoint.json,
  signal_readback.csv, vsl_readback.csv, state_*.json (~0.35-0.73 MB), action_*.json.
  The native fzp (vissim_eval\\baseline_001.fzp) was only 15.8 MB at t~750.
- Timeline today: sim 750->900 runs ~14:09-14:22, then the 900 s SDMPC decision (~8.5 min, python busy,
  no new frames), then sim 900->1050 (~15 min).
`

const FINDINGS = {
  type: 'object',
  properties: {
    summary: { type: 'string', description: '3-6 sentences: the answer from this angle' },
    findings: { type: 'array', items: { type: 'object', properties: {
      claim: { type: 'string' },
      evidence: { type: 'string', description: 'file:line citations, commands run, numbers measured' },
      confidence: { type: 'string', enum: ['high', 'medium', 'low'] } },
      required: ['claim', 'evidence', 'confidence'] } },
    speedups: { type: 'array', items: { type: 'object', properties: {
      change: { type: 'string' },
      expected_saving: { type: 'string', description: 'per 150 sim-s at ~5000 vehicles, with how it was estimated' },
      output_identical: { type: 'string', description: 'identical VISSIM trajectory AND identical files the controller reads? yes / no / unknown, with why' },
      effort_and_risk: { type: 'string' },
      files: { type: 'string' } },
      required: ['change', 'expected_saving', 'output_identical', 'effort_and_risk'] } },
  },
  required: ['summary', 'findings', 'speedups'],
}

const VERDICTS = {
  type: 'object',
  properties: {
    verdicts: { type: 'array', items: { type: 'object', properties: {
      claim: { type: 'string' },
      verdict: { type: 'string', enum: ['confirmed', 'refuted', 'uncertain'] },
      note: { type: 'string', description: 'what you re-checked and what you found' } },
      required: ['claim', 'verdict', 'note'] } },
    speedup_notes: { type: 'string', description: 'which proposed speedups are wrong, overstated, or not output-identical, and why' },
  },
  required: ['verdicts', 'speedup_notes'],
}

const DIMENSIONS = [
  { key: 'frame-writer', prompt: `
## Your angle: the per-second frame writer (VBScript side)
Find exactly what CollectHeadObservation and the lane-plant frame writer (WriteLanePlantObservation, and whatever
writes decisions_*/frame_NNNNNN.json) do each second:
1. Which COM reads: per-vehicle AttValue loops over Vissim.Net.Vehicles, or batched
   GetMultipleAttributes / GetMultiAttValues? Which attributes? Which object sets (all vehicles, links, lanes,
   signal groups, detectors)? Count COM calls per second as a function of vehicle count N. Include lane_native.vbs.
2. How the JSON text is built: repeated \`s = s & ...\` concatenation is O(total_length^2) in VBScript,
   array + Join is linear. Also per-second Dictionary rebuilds, sorting, string formatting helpers (Num(), etc.).
3. The file write (FileSystemObject, ADODB.Stream, sizes).
4. VBScript micro-benchmark with cscript in ${SCRATCH} (no VISSIM): time building strings of ~200 KB, 500 KB,
   850 KB and 1.5 MB with the same pattern the code uses versus an array + Join, using realistic piece sizes
   (copy the actual formatting per vehicle). Also time the number of per-vehicle COM-free VBS operations the code
   does. Report whether serialization alone accounts for seconds per simulated second and for the growth with N.
5. Propose a rewrite that writes byte-identical frame files, and estimate the saving.
Cite file:line for every claim.` },
  { key: 'consumer', prompt: `
## Your angle: what the controller actually consumes from the per-second frames
1. Trace the Python side that reads decisions_*/frame_NNNNNN.json (and observer_checkpoint.json): which module,
   which fields, which vehicles/links/lanes, which seconds (every second since the last checkpoint?), and who
   deletes frames and when (frames 0..750 existed at t~750 and were all gone right after the 750 s decision).
2. Why one-second frames are required (the KeyError: 2 at sim_sec=150 with 5 s sampling). Is it the lane plant's
   per-second state reconstruction (vehicle positions per lane cell, head/queue observation, cohort tracking)?
3. Is the frame content a superset of what is consumed? List consumed fields vs written fields, and which
   vehicles are consumed (only lane-plant links / the 21-cell corridor, or the whole network?). Estimate how much
   smaller a frame limited to what is consumed would be, and whether the controller's observation would then be
   provably identical.
4. Could the same per-second observation be reconstructed from VISSIM's own vehicle record (the .fzp that the
   run writes anyway) or other native outputs instead of COM polling? Check what the fzp contains and its
   resolution/flush behaviour (look at the run's vissim_eval folder and the .inpx/.layx evaluation configuration
   in D:\\VISSIM-merge\\sim3 or the lane-plant worktree), and what would break (timing, flush, provenance proofs).
Cite file:line for every claim.` },
  { key: 'actuation', prompt: `
## Your angle: test the user's hypothesis about per-second COM writes
For every per-second subroutine OTHER than the head observation collection -- ValidateRuntimeSignalPersistence,
ApplyRuntimeSignals, ApplyRuntimeRampMeters, ApplyIncidentLaneClosure, SealHeadSignalStates, LogStateCsv,
bottleneck link/segment logging, signal_readback.csv / vsl_readback.csv writers, VSL writes -- determine:
1. Does it WRITE to COM every second, or only when a value changes? Does it READ COM every second (e.g. SigState
   readback for all signal groups)? Count COM calls per second.
2. How are signals driven in this run: SignalGroup SigState set via COM each second (ContrByCOM), or a signal
   program/.sig plan? What does ValidateRuntimeSignalPersistence check and why does it exist -- does VISSIM keep a
   COM-set SigState across steps? What does SealHeadSignalStates do?
3. Would writing signals/meters/VSL only when they change, or once per 150 s plan, give an identical VISSIM
   trajectory? Is there an existing mode that does this (RunEventContinuousMode with SimBreakAt at the next change,
   RunContinuousStaticMode) and exactly why this run cannot use it (the head-observation requirement)? What would a
   hybrid need (continuous between observation points is impossible if observation is every second)?
4. Estimate the per-second cost of these subs relative to the head observation (from code structure: number of
   COM calls and VBS work), so the user's hypothesis gets a quantitative yes/no.
Cite file:line for every claim.` },
  { key: 'measurement', prompt: `
## Your angle: live, read-only measurement of the running sdmpc_lp_9000b
1. Per-process CPU: with PowerShell Get-Process (cscript, VISSIM*, python), sample CPU seconds every ~10 s for at
   least 3 minutes WHILE THE SIMULATION ADVANCES (frames are appearing and python CPU is flat; not during a
   decision). Report CPU-sec per wall-sec for each, and the idle remainder. If you land inside a decision,
   wait until new frame files appear again (use a polling loop with short sleeps inside one command, max ~9 min
   per command).
2. From frame_NNNNNN.json modification times in <run>\\decisions_sdmpc_lp_9000b (frames exist between decisions),
   compute wall seconds per simulated second over time, and relate it to frame size and to vehicle count
   (count vehicles in 2-3 frames with python json -- inspect the structure first with a tiny summary). Fit
   wall_per_step vs size: linear or superlinear? Also use runlog RUN_SINGLE_STEP lines if they carry timing.
   The state_sdmpc_lp_9000b.csv (every 30 s) may carry vehicle counts.
3. Search for PERF report lines ("PERF name=") from earlier runs anywhere under D:\\VISSIM_runs, D:\\VISSIM-merge,
   C:\\Users\\TRLAB\\Documents\\ChatGPT\\VISSIM (runlogs, *.txt, *.log; use grep -rl with --include and keep it
   bounded). If found, summarize the top time sinks per simulated second and which run/config they came from.
4. Find the wall time of lane-plant no-control runs such as lane_native_nc2850_s13_v3 (search for the folder and
   its runlog/provenance timestamps) and of fast_nc runs, to compare stepwise+frames vs continuous.
Report concrete numbers with the commands used.` },
]

phase('Investigate')
const results = await pipeline(
  DIMENSIONS,
  d => agent(CONTEXT + d.prompt, { label: 'investigate:' + d.key, phase: 'Investigate', schema: FINDINGS }),
  (r, d) => r ? agent(CONTEXT + `
## Your job: adversarial verification
Another investigator (angle: ${d.key}) reported the findings below. Try to REFUTE each claim: re-read the cited code
yourself, re-run cheap measurements or benchmarks where possible (same hard rules; scratch only under ${SCRATCH}\\verify_${d.key}).
Mark a claim 'confirmed' only if you checked it yourself; 'uncertain' if you could not. For each proposed speedup,
check that the saving is not overstated and that "output identical" really holds (VISSIM trajectory and every file
the controller reads).

Findings to check:
${JSON.stringify(r, null, 1)}`, { label: 'verify:' + d.key, phase: 'Verify', schema: VERDICTS }).then(v => ({ key: d.key, report: r, check: v })) : null,
)

const done = results.filter(Boolean)
log(`${done.length}/${DIMENSIONS.length} angles investigated and verified`)

phase('Synthesize')
const synthesis = await agent(CONTEXT + `
## Your job: synthesize the answer
Below are four investigations, each with an adversarial check. Use only claims marked confirmed (or state clearly
when you rely on an uncertain one). Write, in Korean, for a traffic-control researcher who knows VISSIM COM well:
1. Attribution: where the 12-15 min per 150 sim-s goes, with numbers (CPU split, per-second cost vs vehicle count,
   the biggest sinks and whether growth is linear or superlinear).
2. The user's hypothesis (per-second COM overwrites of signals) and proposal (write only on change / once per 150 s):
   right or wrong, how much it would save, and whether it is output-identical.
3. Ranked speedup options: expected saving per 150 sim-s, whether the VISSIM trajectory and the controller's inputs
   stay identical, effort, risk, and how to verify (e.g. byte-compare frames from a short run).
4. Whether it is worth stopping and restarting the live 20 h run after implementing the best option, given it is
   at ~t=900 now; give the arithmetic.
Keep it tight: tables where useful, cite file:line for the key code facts.

Material:
${JSON.stringify(done, null, 1)}`, { label: 'synthesize', phase: 'Synthesize' })

return { synthesis, results: done }
