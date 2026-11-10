# Frozen result verification package

These are the original saved-result artifacts dated 2026-11-06, version 2. The 25 files listed in `manifest_20261106_v02.json` are preserved byte for byte, including the historical package README and verifier. The historical README's statement that no public URL had been assigned describes the package at preparation time; the current public location is this repository.

From the repository root:

```bash
python scripts/verify_saved_results.py
```

Python 3.10 or newer is sufficient. No packages, API credentials, network access, raw benchmark downloads, or model weights are required. Use ordinary Python execution: the original verifier uses assertions, so `-O` and `-OO` disable its checks. The wrapper rejects these modes.

The verifier checks file hashes, TEP directional counts and nominal bounds, calibration/evaluation group separation, HAI counts and episode hits, paired-effect point estimates, the invariance of saved numerical routes across historical conditions, all eight Table S4 rows, the length control, and query overlap. It does not retrain models, recompute every diagnostic AUROC, rerun bootstrap intervals, regenerate language-model responses, or certify semantic explanation quality.

The saved records include evaluation labels for scoring. Those labels are not inputs to the numerical disposition or language reader in the experiment. See [reproduction instructions](../docs/REPRODUCTION.md) for the separate raw-data workflow.

`pollution_cohort.json` is an additional original study input used to reconstruct query selection. Its separate `public_additions_manifest.json` is checked by the repository wrapper without altering the original 25-file manifest.
