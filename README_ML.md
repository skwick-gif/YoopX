## ML System – Current State (2025-10)

This document reflects the actual implemented machine learning + iterative historical training as it exists right now in the repository.

### Supported Model Algorithms (Active)
| Code | Description | Status |
|------|-------------|--------|
| rf   | RandomForestClassifier | Primary & stable |
| xgb  | XGBoost (placeholder wiring – basic training) | Usable (no advanced tuning) |
| lgbm | LightGBM (placeholder wiring – basic training) | Usable (no advanced tuning) |
| transformer | Prototype sequence model | Prototype only (not integrated in dashboard) |

Currently the new Iterative Training UI path always trains RandomForest for each horizon. Extension to xgb/lgbm is planned but not yet implemented inside the iterative loop.

### Key Directories & Files
| Path | Purpose |
|------|---------|
| `ml/feature_engineering.py` | Core tabular feature computation (rolling / basic indicators). |
| `ml/train_model.py` | Single-pass model training entry (historical snapshot training). |
| `ml/iterative_training_system.py` | Iterative historical training engine (multi-horizon loop, accuracy & stopping). |
| `ml/iterative_results/` | JSON artifacts per iteration (`iteration_XX_YYYYMMDD*.json`). |
| `ui/tabs/model_dashboard_tab.py` | Model dashboard (training buttons, iterative controls, results viewer). |
| `main_content.py` | Wires UI signals to background training threads. |
| `ml/registry/` | Snapshot registry (metadata, thresholds, ACTIVE pointer). |

### Iterative Historical Training – Implemented Workflow
The implemented loop (class `IterativeHistoricalTrainer`) executes:
1. Determine latest available trading date across loaded symbols.
2. For iteration i:
   - Compute training cutoff using a lookback window (initial_lookback_days, then expanded +5 business days each subsequent iteration).
   - Train one model per requested horizon (currently RF only) on data up to the cutoff.
   - Generate daily forward predictions across the validation span (cutoff+1 → latest_date) for each symbol & horizon.
   - Collect realized outcomes at target dates (first available trading day ≥ target_date).
   - Assign actual class using dynamic `label_threshold` (return ≥ threshold ⇒ 1 else 0).
   - Compute accuracy per horizon: blended = basic_accuracy*(1-α) + weighted_confidence_accuracy*α (α = blend_alpha).
   - Persist iteration summary & full actual/prediction detail JSON files.
   - Stop if avg_accuracy ≥ target_accuracy OR improvement < min_accuracy_improvement.

Artifacts per iteration:
* `iteration_XX_YYYYMMDD.json` – summary (cutoff, counts, accuracy_by_horizon, avg_accuracy, improvement).
* `iteration_XX_YYYYMMDD_actual_results.json` – detailed per-prediction outcomes.
* `iteration_XX_YYYYMMDD_predictions.json` – raw predictions (if produced).

### Current Metrics Captured
| Metric | Level | Notes |
|--------|-------|-------|
| accuracy_by_horizon | iteration summary | Blended metric (basic + confidence weighting). |
| avg_accuracy | iteration summary | Mean of horizon accuracies. |
| improvement_from_previous | iteration summary | Delta vs previous avg_accuracy. |
| counts (predictions / actual_results) | iteration summary | Volume sanity. |

Not yet implemented: precision/recall, AUC, PR AUC, calibration error, Top-K metrics.

### UI – Model Dashboard
Sections (current layout after refactor):
1. LEFT: Train / Update panel (model toggle buttons RF/XGB/LGBM, horizons input, train range days, auto-rescan, Train / Iterative Train / Iter Results / advanced toggle).
2. RIGHT (same row): Snapshots table (registry entries, horizons column, active highlight).
3. BOTTOM LEFT: Active Model Metrics (model type, validation AUC (if available), samples, thresholds, horizons, drift label).
4. BOTTOM RIGHT: Feature Store & Drift panel (refresh feature snapshots, compute drift estimate).
5. Iterative Results Viewer (collapsible) – shows last iteration actual rows + horizon filter + accuracy summary line.

### Parameter Flow (Iterative Training)
| UI Field | Internal Key | Usage |
|----------|--------------|-------|
| Validation Days | initial_lookback_days | Defines training cutoff (lookback window). |
| Target Acc | target_accuracy | Early stopping threshold. |
| Improve Δ | min_accuracy_improvement | Minimum avg accuracy improvement to continue. |
| Max Iter | max_iterations | Hard iteration limit. |
| Label Thr (ret) | label_threshold | Return threshold for positive class. |
| Blend α | blend_alpha | Weight for confidence-weighted accuracy. |
| Iter Horizons | horizons | Comma-separated horizon list. |

### Known Limitations / Gaps (As of Now)
| Area | Limitation |
|------|------------|
| Iterative windowing | Expands validation window instead of strict walk-forward shift. |
| Algorithms | Iterative loop trains RF only. |
| Metrics | No AUC / precision / recall / F1 / PR AUC yet in iteration artifacts. |
| Threshold dynamics | label_threshold static per run (not volatility-adjusted). |
| Data leakage checks | No explicit guards besides time cutoff logic. |
| Calibration | No probability calibration applied inside iterative loop. |
| Ensemble | No stacking / blending between algorithms yet. |
| Class imbalance | No re-weighting or sampling logic. |
| Regime awareness | No market regime features or segmentation. |

### Quick Usage (Iterative)
1. Open Model tab.
2. (Optional) Enter horizons (e.g. `1,5,10`).
3. Set target accuracy / improvement / max iterations.
4. Adjust label_threshold + blend_alpha if needed.
5. Click “Iterative Train”.
6. After completion, click “Iter Results” to inspect the last iteration details.

### Quick Usage (Single Snapshot Training)
1. Choose model via RF/XGB/LGBM toggle.
2. Set horizons and train range days.
3. Click “Train”.
4. A snapshot directory with metadata & thresholds (if implemented) is registered and can be activated.

### Output Locations
| Path | Content |
|------|---------|
| `ml/iterative_results/` | Iteration JSON summaries & detailed results. |
| `ml/registry/index.json` | List of model snapshots (single-train path). |
| `ml/registry/ACTIVE.txt` | Points to currently active snapshot directory. |
| `logs/` | General logs (not all wiring shown here). |

### Safety / Operational Notes
* Validate that data indices are timezone-consistent (UTC normalization already added in iterative system).
* If iteration 2+ shows zero predictions, verify symbols contain enough rows before cutoff.
* Large horizon lists multiply runtime linearly – start narrow.

### Minimal Programmatic Example
```python
from ml.iterative_training_system import IterativeHistoricalTrainer, IterativeTrainingConfig

trainer = IterativeHistoricalTrainer(data_map)
cfg = IterativeTrainingConfig(
    initial_lookback_days=60,
    horizons=[5],
    max_iterations=3,
    target_accuracy=0.75,
    min_accuracy_improvement=0.01,
    label_threshold=0.02,
    blend_alpha=0.4
)
results = trainer.run_iterative_training(cfg)
print(results[-1].accuracy_by_horizon if results else 'no results')
```

### Immediate Next Opportunities (Planned – not yet implemented)
1. Walk-forward (sliding) validation instead of expanding window.
2. Add AUC / precision@K / recall / F1 to iteration summaries.
3. Introduce XGB + LGBM inside iterative loop.
4. Probability calibration (Isotonic / Platt) per iteration.
5. Dynamic label threshold based on recent volatility (e.g. ATR percentile).
6. Ensemble (stacked / weighted) across algorithm families and horizons.
7. Guardrails: block promotion if drift or performance degradation.
8. Feature regime tagging & stratified accuracy reporting.
9. Top-K trade simulation metrics + PnL surrogate.

---
Document maintained as of latest refactor of iterative training UI and engine.
