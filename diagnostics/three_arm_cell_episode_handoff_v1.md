# Three-arm freeway cell episodes: prepared, full analysis pending

`plot_three_arm_cell_episodes.py` prepares the two static E/W heatmaps and episode CSV for the completed baseline / LCD2000 / upstream1135 no-control 5400-second runs. No new-run data or figures have been processed yet.

The only executed check read the old NC segment CSV header plus 126 rows (1, 30 and 60 seconds, 42 cells each), and the state CSV header plus three rows. All cell addresses and stock sums passed. `three_arm_cell_episode_schema_v1/schema_validation.json` preserves the exact prefix hashes and explicitly does not claim full-file validation, plotting, FZP access or model execution. The producer SHA at this check was `0241f088a8a9398604f28e7557e79f5c2ba25705bbd63b07d34cc36e0cb2a553`.

## Run after all three completed receipts are available

From the review worktree, substitute the three actual completed run directories supplied by the parent. The output must be a new directory beneath `diagnostics`.

```powershell
& 'C:\Users\alsrj\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -B -X utf8 diagnostics/plot_three_arm_cell_episodes.py `
  --baseline 'evaluation/runs/<completed-baseline-5400>' `
  --lcd 'evaluation/runs/<completed-lcd10635_2000-5400>' `
  --upstream 'evaluation/runs/<completed-upstream1135-5400>' `
  --out diagnostics/no_control_5400_three_arm_cell_episodes_v1
```

Outputs are `FW_E_three_arm_speed.png`, `FW_W_three_arm_speed.png`, `episodes.csv`, `cell_summary.csv`, `cell_samples.csv` and `manifest.json`. Each direction has three vertically aligned panels, one common 0–120 km/h sequential scale, gray masked cells and black episode spans. The completion status remains `complete_rendered_pending_visual_review` until the images are actually inspected.

## Measurement contract

- Reuses the existing pure `diagnostics.audit_observed_nc_trajectory.episodes`; the older `scripts/analyze_control_run.py` helper has a 900-second cutoff and is not used for this full no-control analysis.
- An eligible sample has `count >= 5` and `mean_speed_kph < 30`. An episode needs four or more consecutive 30-second observations: elapsed duration is `last_slow_sec - start_sec >= 90`, without adding a fictitious final 30 seconds. This is sampled persistence, not a claim that every intervening second was congested.
- Startup second 1 is checked for cell/state stock consistency but excluded from the regular plot/episode grid. The required grid is 30, 60, …, 5400, with no interpolation or silent gap repair. Missing, duplicate or incomplete timestamps fail.
- Every `count < 5` sample is gray, including empty cells whose serialized speed is zero. Ending an episode because count falls below 5 is reported separately from a subsequent eligible sample reaching 30 km/h. End-of-run episodes are right-censored.
- Both E and W index 0 is upstream and index 20 downstream in the direction of travel. Plot index increases upward. Recorded VBS chain links, chain offsets and 22 cell boundaries provide the spatial interpretation; the CSV `physical_link` column is only a representative model-link alias. Exact geometry must match among arms.
- Each timestamp must contain exactly E/W × 21 unique cells; the sum of 42 counts must equal the simultaneous state CSV freeway count. Nonfinite/negative quantities and stopped counts exceeding stock fail. Seed 13, no-control, period 5400, `SIM_DONE`, unchanged input CSV/provenance bytes and absence of reported runner error/fallback are required.

This producer reads only the small bottleneck/state CSVs and provenance/config/log files. It does not scan FZP, import a traffic model, call COM, use SciPy, or alter runtime inputs. The parent run receipts remain the authority for matched demand, native signals, command reapplication and experimental network differences; a successful plot is not an independent certification of those controls. This is observational analysis, not a timing benchmark.
