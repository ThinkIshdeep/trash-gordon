# Experiments and reproduction

Run `python scripts/evaluate_all.py` from this repository. The report is written to `reports/evaluation-results.json`. This executes real calculations; model quality is separate from test success.

## Recorded baseline

```json
{
  "navigation_tasks": 20,
  "successes": 20,
  "collisions": 0,
  "bag_motion_interlock": true,
  "note": "Twenty seeded goal checks in the authored room; physical sensors, SLAM, sealing and inflation are not validated."
}
```

## Interpretation

Known-map A* navigation and simulated lid/bag/docking logic. No SLAM, physical mechanism validation or telepathic speaker localization.

The raw reports describe whether measurements are synthetic benchmarks, controlled regression fixtures or invariants. Do not interpret regression-fixture accuracy as a held-out real-world score. Preserve seeds and splits when comparing changes.
