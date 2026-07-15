# Demand sweep — stable-congested band search + PFO re-evaluation (2026-06-30)

no-control 1800s, fw2600 fixed, sym, seed13, warmup 300s. Saturation = does total vehicles plateau
(stable) or keep growing (oversaturated). Includes u1000/u1800 references (fw differs slightly there).

## No-control saturation trajectory (total vehicles, % stopped)

| urban demand | t=300 | t=900 | t=1800 | growth(1500->1800) | regime |
| --- | --- | --- | --- | ---: | --- |
| u1000 | 576 (22%) | 570 (11%) | 617 (25%) | +36 | **STABLE (undersaturated)** |
| u1200 | 678 (23%) | 811 (24%) | 990 (43%) | +88 | growing (oversaturated) |
| u1400 | 744 (26%) | 1071 (36%) | 1340 (49%) | +109 | growing |
| u1600 | 866 (26%) | 1319 (48%) | 1601 (53%) | +100 | growing |
| u1800 | 1014 (29%) | 1530 (49%) | 1686 (51%) | +186 | growing |

## PFO vs no-control across the sweep

| urban demand | TTT vs nc | stopped vs nc | speed vs nc | nc mean speed |
| --- | ---: | ---: | ---: | ---: |
| u1200 | -1.6% | -1.4% | +1.5% | 38.1 |
| u1400 | -1.6% | -5.4% | +2.7% | 30.2 |
| u1600 | -0.9% | -3.1% | +1.9% | 25.2 |
| u1800 | -3.6% | -10.4% | +9.0% | 23.9 |

## Findings

1. **There is NO stable-congested band.** The network transitions sharply from stable/undersaturated at
   u1000 (total ~590, 11-25% stopped, oscillating) to oversaturated/loading at u1200 already (total
   678->990, 43% stopped, still growing). The capacity threshold is ~u1000-1100. Every demand at/above
   u1200 keeps loading for the full 1800s (never reaches steady state) and sits at 43-53% stopped.

2. **PFO's benefit is modest at EVERY demand level** (TTT -0.9% to -3.6%, stopped -1.4% to -10.4%) and
   does not have a sweet spot. If anything it grows slightly with load (largest at u1800) but stays
   small; the u1800 -3.6%/-10.4% is a single seed (3-seed mean was -1.7%/-8.2%). So the controller's
   FAIR BEST in this network is a few % TTT / up to ~10% stopped, regardless of demand.

3. Therefore the small controller benefit is NOT because we tested the wrong demand. There is no demand
   regime in this network where adaptive split control dramatically helps: below ~u1100 there is nothing
   to control, above it the network is oversaturated and loading toward gridlock where split control can
   only slow (not reverse) accumulation under persistent over-demand.

## What this leaves

The controller ceiling (~few % TTT / ~10% stopped) is real and demand-insensitive. Two non-exclusive
explanations remain:
- (a) the network genuinely has little controllable headroom (sharp capacity threshold, no stable-
  congested operating band), and/or
- (b) the model-plant mismatch caps even split control.

The decisive discriminator is a model-free measured-queue controller (max-pressure) at the same demands:
if it matches PFO, the ceiling is the network (a); if it clearly beats PFO, the model is the limit (b).
