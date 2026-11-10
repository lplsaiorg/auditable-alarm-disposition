# Reproducing the current manuscript

This release accompanies **Auditable Alarm Disposition through Executable Evidence Role Separation and Asymmetric Risk Calibration**. It uses the numerical study and review analyses recorded on 6 November 2026. The older August demonstration package is not the implementation of these results.

There are three distinct levels of reproduction:

1. **Verify archived results.** The saved-result checker uses only the Python standard library. It checks file hashes, counts, nominal binomial bounds, group separation, historical-query invariance, Table S4 mappings, the length control and query overlap. It does not refit models, regenerate language-model responses, or recompute every bootstrap interval or AUROC.
2. **Rerun the numerical experiments.** The commands below construct features from the raw public benchmarks, fit the current numerical candidates, and repeat calibration and the same-protocol HAI comparisons.
3. **Recompute analyses of saved reader outputs.** The paired-effect stage uses the archived response-level labels. The prompts and history interventions are provided without a network client. A new language-model call is not a deterministic reproduction of the recorded response.

The experiments are retrospective. The final TEP calibration targets and sample size were selected after inspecting comparisons on the same outer groups. Repeated folds overlap, and HAI windows are correlated. Reproduction does not turn these results into independent validation or a distribution-free deployment guarantee.

## Environment

Python 3.10 or later is required. Install numerical dependencies with:

```sh
python -m pip install -r requirements.txt
```

The version ranges are compatibility bounds, not a tested matrix. The original observed environment was Python 3.12.13 with NumPy 2.5.4, pandas 3.1.1, SciPy 1.18.1, scikit-learn 1.9.1, joblib 1.6.0, and pyreadr 0.5.9; this is also recorded in `code/original_environment.json`. Floating-point behavior, model fits, and serialized-model hashes may differ across versions and platforms. The raw-data training stages were not rerun during repository packaging.

The code reads no credential files and makes no network requests. API orchestration, account configuration, raw network logs, and the earlier report-building scripts are excluded.

## Archived-result verification

From the repository root:

```sh
python scripts/verify_saved_results.py
```

The original verification manifest covers 25 files. Expected checks include 15 final TEP evaluations passing the nominal criteria, mean coverage `0.8770666666666667`, HAI episode hits of 14/15/13/17/17 for PCA/IsolationForest/fusion/logistic regression/ExtraTrees, and 40 queries with an invariant numerical route. The extended checks include all eight Table S4 rows, 15 length-control passes with coverage `0.8268`, and 30/38 query-event overlaps with evaluation/calibration sets. Additional repository artifacts are described separately and do not retroactively change that historical manifest.

## Raw benchmark inputs and output isolation

Download the benchmark files manually from [Additional Tennessee Eastman Process Simulation Data, Harvard Dataverse, version 1](https://doi.org/10.7910/DVN/6C3JR1) and the [official HAI 21.03 release directory](https://github.com/icsdataset/hai/tree/master/hai-21.03), respecting their distribution terms. No automatic download is performed. Place them in this structure, or pass another directory to `--raw-data`:

```text
raw-data/
  TEP/
    TEP_FaultFree_Training.RData
    TEP_Faulty_Training.RData
    TEP_FaultFree_Testing.RData
    TEP_Faulty_Testing.RData
  HAI21.03/
    train1.csv.gz
    test1.csv.gz
    test2.csv.gz
    test3.csv.gz
    test4.csv.gz
    test5.csv.gz
```

The TEP files must contain the original `faultNumber`, `simulationRun`, `sample`, `xmeas_*`, and `xmv_*` columns. HAI input is release 21.03: gzip-compressed, comma-separated CSV with `time`, `attack`, and its original sensor/control columns. The archived `train1` and `test4` headers were checked during packaging: 84 columns, including the expected time/attack fields; filtering time and all `attack*` columns leaves 79 sensor/control variables. Preserve the source column order. The primary HAI chain uses `train1` before 13 July 2020, plus `test1/test2` for supervised fitting; `test3` calibrates policies and `test4/test5` evaluate them. No `train2/train3` files enter this primary chain.

Generated features, models and results default to `workspace/`. Use `--workspace runs/my-rerun` consistently on every command to select another output tree. The equivalent environment variables are `PAPER2_WORKSPACE` (or `PAPER2_WORKDIR`) and `PAPER2_RAW_DATA`. Published `saved_results/` are never used as an output directory. Use an empty workspace for a genuinely new rerun: several original experiment entrypoints intentionally preserve completed outputs, and fitted model caches are reused when present.

Raw TEP files are large, and RData loading is not streamed. Feature extraction and the candidate-family fits require substantial memory and processing time. This package does not claim a measured runtime or a small-memory training configuration.

## TEP: features, training, grouped evaluation and calibration

Run in this order:

```sh
python code/reproduce.py prepare-tep --raw-data raw-data
python code/reproduce.py fit-tep --raw-data raw-data
python code/reproduce.py grouped-tep --raw-data raw-data
python code/reproduce.py candidates-tep --raw-data raw-data
python code/reproduce.py calibrate-tep
python code/reproduce.py tep-summary
```

| Stage | Implementation and outputs |
| --- | --- |
| `prepare-tep` | Fits the original Training-normal scaler and PCA reference, and constructs the original 118 mean-based features through `reconstruct.features`. Writes `data/tep_*features.npz` and `models/tep_preprocessing.joblib` in the workspace. It does not rerun the obsolete v1 selection experiment. |
| `fit-tep` | `prepare_numerical.fit_tep_models` uses `v2_numeric.merged` to construct the 378-feature representation and fits the original eight mean/dynamic HGB and balanced-logistic candidates with their original settings and seed. |
| `grouped-tep` | `v3_numeric.risk` retains the original random-number sequence for the three seeded five-fold partitions and within-fold sampling. It writes `experiments/v3/results/risk_splits.json` and `risk_predictions.csv`. |
| `candidates-tep` | `v4_tep.main` fits the extra and matched-480 candidates and specialist, writes `experiments/v4/data/tep_scores.npz`, and evaluates the seven-model family and specialist variants. |
| `calibrate-tep` | `v4_calibration.main` repeats the fixed-model target/volume comparisons and writes `calibration_followup.json`, `calibration_bindings.json`, and `calibration_predictions.csv`. The manuscript's final procedure is `guarded_margin_cal400`. |
| `tep-summary` | `review_revision_20261106_v01.tep` writes the per-fault counts and run-cluster bootstrap intervals under `experiments/v5_review/results/`. |

The primary trained classifier is `dynamic_hist_w20`. Standard Training events use samples 21–500 and standard Testing events use samples 161–960. The seven-model family used by Table S4 is distinct from `old_family_nominal_same_calibration`, which contains only three HGB models. Do not substitute that three-model control for the table's candidate-family row.

The final calibration uses 400 normal and 1600 fault events outside each evaluation fold, targets `.02/.025`, and an ordered threshold grid with `.005` spacing. The outer nominal evaluation criteria remain `.05/.10`. No generated explanation enters this numerical decision rule.

## HAI: strict chronology and matched comparators

This chain is independent of the TEP chain:

```sh
python code/reproduce.py fit-hai --raw-data raw-data
python code/reproduce.py compare-hai --raw-data raw-data
```

`v4_hai_strict.main` constructs complete, non-overlapping 120-row windows with the original 790 features, fits the three strict-past feature-view candidates, selects the view using `test3`, and retains every candidate's evaluation record. `review_revision_20261106_v01.hai` fits the normal-only PCA/IsolationForest/fusion and supervised logistic comparators on the same feature cache. It recalibrates each model on `test3` and keeps the original ExtraTrees model as primary.

Outputs include `experiments/v4/results/hai_strict_results.json` and `experiments/v5_review/results/hai_comparison_20261106_v01.json`. The archived primary result is 17/17 episode hits, 2 fault-to-benign errors, 4 normal-to-fault errors, and 16 abstentions among 1100 held-out windows (`1084/1100 = 98.545%` automatic coverage). Episode labels are reconstructed directly from the raw HAI `attack` column; the portable implementation does not require a legacy detector-score cache just to obtain this ground truth.

The earlier official-file HAI experiments that used `train2/train3`, and their historical component ablations, are not the current strict-past model. Those earlier training/reporting pipelines are outside these raw-data commands; the archived-result checker also does not claim to recompute all of those supplementary diagnostics.

## Saved-reader analyses and the fixed-model length control

```sh
python code/reproduce.py paired-effects
python code/reproduce.py length-control --raw-data raw-data
```

`paired-effects` requires the published `fair_per_response.csv`. It copies that input into the workspace without changing it and recomputes the direct paired effects and 10,000-draw run-cluster intervals. It needs no raw sensor data or API access. Use `--saved-results path/to/archive` if the archive is stored elsewhere.

`length-control` requires the completed TEP stages, the archived `fair_per_response.csv` and `pollution_cohort.json`, and the raw TEP files. It runs `round3_checks_20261106_v01.main`: the existing 378-feature HGB model is retained, only the Testing segment ends at sample 640 instead of 960, and thresholds are recalibrated with the same final bindings and targets. It also reconstructs the 40 selected query identities and their overlaps with the calibration/evaluation groups. The first 118 matched-length features deliberately use the original grouped-raw-mean implementation; replacing it with algebraically equivalent averages of standardized rows can alter tree decisions at floating-point split boundaries.

## Evidence contract and history interventions

`code/evidence_contract.py` provides the executable current-reference and numerical-quotation gate. Its passing result establishes the implemented syntactic checks, not semantic truth. See the accompanying example and tests for its exact contract.

`code/reader_protocol.py` contains the original ordinary/separated prompts and a pure function for clean, flipped-outcome, fabricated-benign, stale-regime, and no-history conditions. It preserves historical reference namespaces and the compound nature of the fabricated-history intervention. It neither selects a new experimental cohort nor invokes a model. The release therefore supports inspection and replay of the contract and saved experimental labels without promising identical future MiniMax responses.

## Source preservation and validation scope

The current scientific functions were retained from `v2_numeric`, `v3_numeric`, `v4_tep`, `v4_calibration`, `v4_hai_strict`, `review_revision_20261106_v01`, and `round3_checks_20261106_v01`. `v4_hai` retains the calibration/metric helpers used by the strict-past and same-protocol studies. `reconstruct` retains the original mean-feature function. The new preparation wrapper fits the same prerequisites directly, instead of requiring unrelated earlier experiments to finish first.

Portability changes replace local absolute paths, isolate generated outputs, create required directories, remove import-time execution of the length-control experiment, and obtain HAI episode truth from raw labels. The code's public rerun-protocol digest identifies the new execution; it is not presented as the original run's stored hash.

During packaging, the historical standard-library verifier passed, as did CLI parsing and imports of the 13 numerical/protocol modules. In an isolated workspace, the original frozen score/split caches were used to rerun all six TEP calibration comparison strategies over 15 folds. The resulting calibration predictions were byte-identical to the archive, and the calibration summaries/bindings were exactly equal after JSON parsing. The paired-effect analysis and TEP per-fault/run-cluster analysis were also rerun: their complete JSON outputs, including bootstrap intervals, exactly matched the archive. Original prompt strings and feature-field names were checked for equality. These tests used the observed original numerical environment above. No full raw-data benchmark retraining or live language-model experiment was performed as part of packaging.
