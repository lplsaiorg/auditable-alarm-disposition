"""Construct current numerical prerequisites from the public raw benchmark files."""
import gc
import joblib
import numpy as np
import pandas as pd
import pyreadr
from sklearn.decomposition import PCA
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from paths import ROOT, RAW_DATA_ROOT, ensure_layout
from reconstruct import features


def prepare_tep():
    """Original 118 features and Training-normal preprocessing, without old v1 fits."""
    ensure_layout()
    outputs = [ROOT / "models/tep_preprocessing.joblib", ROOT / "data/tep_training_features.npz"]
    outputs += [ROOT / "data" / f"tep_{kind}_testing_features.npz" for kind in ["Faulty", "FaultFree"]]
    if all(p.exists() for p in outputs):
        print("Existing TEP mean-feature prerequisites preserved.")
        return
    folder = RAW_DATA_ROOT / "TEP"
    required = [folder / f"TEP_{kind}_{part}.RData" for part in ["Training", "Testing"] for kind in ["FaultFree", "Faulty"]]
    missing = [p.name for p in required if not p.is_file()]
    if missing:
        raise FileNotFoundError("Missing raw TEP files: " + ", ".join(missing))
    normal = next(iter(pyreadr.read_r(str(folder / "TEP_FaultFree_Training.RData")).values()))
    cols = [c for c in normal if c.startswith(("xmeas_", "xmv_"))]
    scaler = StandardScaler().fit(normal[cols])
    pca = PCA(n_components=.95, svd_solver="full").fit(scaler.transform(normal[cols]))
    ni, nx = features(normal, cols, scaler, 20)
    del normal
    gc.collect()
    arrays, ids = [nx], [ni]
    # The exact original order is retained: normal then faulty Training; each
    # Testing cache is separate and v2_numeric concatenates faulty then normal.
    for part in ["Training", "Testing"]:
        for kind in ["Faulty", "FaultFree"]:
            if part == "Training" and kind == "FaultFree":
                continue
            print("Extract mean features:", part, kind, flush=True)
            frame = next(iter(pyreadr.read_r(str(folder / f"TEP_{kind}_{part}.RData")).values()))
            index, x = features(frame, cols, scaler, 20 if part == "Training" else 160)
            del frame
            gc.collect()
            if part == "Training":
                ids.append(index)
                arrays.append(x)
            else:
                np.savez_compressed(ROOT / "data" / f"tep_{kind}_testing_features.npz",
                                    x=x, fault=index.faultNumber.to_numpy(), run=index.simulationRun.to_numpy())
    tx = np.vstack(arrays)
    ti = pd.concat(ids, ignore_index=True)
    np.savez_compressed(ROOT / "data/tep_training_features.npz", x=tx,
                        fault=ti.faultNumber.to_numpy(), run=ti.simulationRun.to_numpy())
    joblib.dump({"scaler": scaler, "pca": pca, "columns": cols}, ROOT / "models/tep_preprocessing.joblib")


def fit_tep_models():
    """Original eight Training-fitted candidates needed by the v3 grouped experiment."""
    from v2_numeric import merged
    ensure_layout()
    training, x = merged("Training")
    y = (training["fault"] > 0).astype(int)
    configs = []
    for width, feature in [(118, "mean"), (378, "dynamic")]:
        for weight in [1, 5, 20]:
            configs.append((f"{feature}_hist_w{weight}", width,
                            HistGradientBoostingClassifier(max_iter=150, max_leaf_nodes=15,
                                                           l2_regularization=1., class_weight={0: weight, 1: 1},
                                                           random_state=20261106)))
        configs.append((f"{feature}_logistic_balanced", width,
                        make_pipeline(StandardScaler(), LogisticRegression(C=1., class_weight="balanced",
                                                                           max_iter=3000, random_state=20261106))))
    for name, width, model in configs:
        destination = ROOT / "experiments/v2/models" / (name + ".joblib")
        if destination.exists():
            print("Existing model preserved:", name)
            continue
        print("Fit TEP:", name, flush=True)
        model.fit(x[:, :width], y)
        joblib.dump(model, destination)
