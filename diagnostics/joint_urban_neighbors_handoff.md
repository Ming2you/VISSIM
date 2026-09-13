# Urban full-green and offset neighborhood — unapplied proposal

The two functions in `joint_urban_neighbors_candidate.py` prepare **one finite, ordered neighborhood of one urban owner**. The patch adds only `evaluation/controllers/joint_urban_neighbors.py`; it depends on the separate unapplied `joint_owner_addresses.py` proposal. No runtime dispatch, production flag, model evaluation, price production, traffic allocator or solver is added.

**Validation:** 10 small tests PASS in 3.032 s (subprocess wall 3.262 s); source changes `[]`. Exact result and stdout/stderr are in `joint_urban_neighbors_validation_v1/`. The harness uses the actual selected 17-SC plan, control mapping, v4 exchange-step declaration and parameter values. It imports pure signal helpers and AST-extracts the unchanged actual `ControlAction`, budget projection, phase exchange/wrapper and SG writer functions. It does **not** build/import the model controller or adapter, replay a state, execute an endpoint, or access COM/VISSIM. This is not full canonical builder/worker/CSV integration validation. The generated patch also passes `git apply --check` and remains unapplied.

## Implemented interface

```python
bundle = generate_urban_requests(
    follower, owner, incumbent, ownership=catalog)
out = realize_urban_requests(
    bundle, incumbent, follower.cfg, ownership=catalog,
    selected_plan=plan, actuation=tuning['actuation'], metadata=metadata,
    signal_group_rows=adapter.signal_group_action_rows)
```

Generation calls the **installed** pure `_phase_exchange_candidates` and reads `cfg.mpc.phase_price_exchange_steps_sec`, `follower.offset_fractions`, and the effective offset price/reference/trust. Realization calls `project_vector`, `validate_vector`, `written_offset_sec`, `validate_writer`, and the actual pure `signal_group_action_rows` callback. Passing that callback avoids another adapter import/implementation in this helper. Caller installation must supply the canonical function, not a substitute serializer.

Output is a plain dictionary: `candidates` (tuple of copied complete actions), `complete`, `domain_label`, `incomplete_reason`, `command_keys`, `aliases`, `rejected` and counts. Flow's loop can form `Neighborhood(out['candidates'], out['complete'], out['domain_label'], out['incomplete_reason'])`. No extra bridge class is required. `complete=True` means the declared neighborhood was fully generated and realized; it does **not** mean every candidate satisfies shared receiving/head budgets or N_P/N_UF constraints.

## Exact domain and ordering

1. Incumbent first.
2. Green-only candidates, in configured step order and the installed generator's ordered source/target phase order.
3. Offset-only candidates, in the follower's existing fraction order after its active reference/trust filter.
4. Explicit full product, green outer / offset inner, including aliases. Deduplication happens **after** realization; all requested origins and signed lifts are retained.

The current v4 declaration supplies exchange step `[6.0]`. The existing offset domain is eight fractions of the existing global cycle; active price trust is read from the already prepared follower (normally cycle/8). The helper adds no step, δ, candidate cap, or tuning. The incumbent offset is retained as an explicit point for incumbent/green-only requests, even if a relinearized price anchor makes it fall outside the filtered lattice. Thus the declared offset set is **incumbent union the existing admitted lattice**. This is visible in request kinds and aliases, not an unexplained trust fallback.

The active v4 phase mode is post-refinement, whose vector exchange path uses its phase box and total budget without the scalar p1 ±6/trust filter. This proposal preserves that vector domain. It does not silently impose the earlier scalar-stage trust on all phases. The dormant `phase_price_in_gne` anchored-vector mode is explicitly rejected until its domain is deliberately integrated; leader offset directives and disabled ramp offsets are also outside scope. Current `refine_rounds=12` belongs to the old descent algorithm, not the neighborhood domain: the new helper performs **no** internal descent or round cap. The joint-owner loop may recall it after a changed incumbent.

This is an **algorithm change** from scalar green/offset search followed by phase refinement. It is not a claim that the old postprocessing order, candidate visits, final action, or costs stay equal. A complete returned neighborhood is one-hop exchange × offset; it is not exhaustive search over the whole connected green lattice or a continuous GNE certificate.

## Physical realization and invariants

- All four phase coordinates are explicit. Current plan-active headless phases remain strategies (including SC1 p4); all five dead phases stay zero. Pair exchange and canonical millisecond projection preserve the signal's total green/cycle budget. FW free/recovery zones and all meters are untouched.
- Only the owner's four green values and offset are assigned on a `deepcopy` of the incumbent. Foreign lever values, leader targets, allocations, infeasibility fields and nested diagnostics are preserved. Outputs do not alias each other or the input. This helper does not run a meter or VSL finalizer; the incumbent must already contain their valid realized values and schedule metadata.
- Incumbent green/offset must already be physically realizable; it is never silently migrated. Nonfinite/bool values, unknown owner, stale owner/domain bundle, unsupported writer, suppressed urban rows, missing/different plan, partial SG windows or differing global/per-signal cycle fail closed. The selected current writer must be explicitly `experiment` in cfg/actuation and have its existing environment authority.
- Offset modulo and 3-decimal rounding come from the canonical writer. A grid point retains its original `fraction * cycle`, plus the existing Wu circular chart's signed lift relative to the incumbent. The exact half-cycle rule is explicitly the existing formula's **−C/2**. Written points are lifted near that declared request, and checked to differ by no more than the writer's half millisecond. The written trust filter is checked again. This is not a new finite-difference stencil or an arbitrary shortest-arc change to a supplied FD direction.
- The dedupe key contains the owner's full signal vector, written offset and **all actual writer-derived SG physical columns** (metadata excluded). SG identity/coverage, zero-based window indices, offset and cycle must agree with the verified owner/plan. It is command identity, not equality of GREEN exposure over one sampled horizon. Examples in the fixture: 52 requested aliases collapse to 39 physical programs with the existing ±cycle/8 trust; with all eight offsets, 117 aliases collapse to 104. These are fixture/domain counts, not a hard-coded cap or traffic result.

## Next integration gates

Use one pinned decision/price/operational context throughout generation, realization and scoring. Rebuild requests after an owned control/domain change. The game must independently fingerprint the complete physical command **per owner**, including meter schedule diagnostics and plan/mapping context; its old lever-value-only key cannot certify that invariant. The urban `command_keys` here can supply the SC partition, but they do not produce FW/meter tokens.

The candidate-dependent combined allocation must re-evaluate physical head/receiving and declared quantity feasibility. Do not reserve another owner's previous accepted traffic as a new hard constraint. Local payoff remains the agreed frozen-price local expression, not JΩ. At the final incumbent, regenerate all owner neighborhoods and re-evaluate final unilateral gaps. Final full CSV projection and any later phase/offset/meter change must preserve or invalidate that certificate explicitly. Those boundaries are outside this proposal and are not claimed as tested.

Exact source/proposal pins are in `joint_urban_neighbors_validation.json`. Re-run only the small harness with:

```powershell
& 'C:\Users\alsrj\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -B -X utf8 -m unittest diagnostics.test_joint_urban_neighbors -v
```

No existing run result, active configuration, runtime source, manifest or Git index was changed.
