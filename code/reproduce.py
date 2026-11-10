"""Explicit stages for current numerical reruns and saved-reader analyses."""
import argparse
import hashlib
import os
from pathlib import Path
import shutil

STAGES = ["prepare-tep", "fit-tep", "grouped-tep", "candidates-tep", "calibrate-tep",
          "fit-hai", "compare-hai", "paired-effects", "tep-summary", "length-control"]


def copy_saved_input(saved_root, filename, destination):
    matches = sorted(saved_root.rglob(filename))
    if not matches:
        raise FileNotFoundError(f"Missing saved reader input {filename}; supply --saved-results with the published saved-results directory.")
    digests = {hashlib.sha256(p.read_bytes()).hexdigest() for p in matches}
    if len(digests) != 1:
        raise ValueError(f"Multiple different saved inputs named {filename}; choose a specific --saved-results directory.")
    if destination.exists():
        if hashlib.sha256(destination.read_bytes()).hexdigest() not in digests:
            raise FileExistsError(f"Existing workspace input {filename} differs; use a separate workspace.")
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(matches[0], destination)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=STAGES)
    parser.add_argument("--workspace", type=Path, help="Generated outputs (default: repository/workspace or PAPER2_WORKSPACE).")
    parser.add_argument("--raw-data", type=Path, help="Directory containing TEP/ and HAI21.03/ (or PAPER2_RAW_DATA).")
    parser.add_argument("--saved-results", type=Path, default=Path(__file__).resolve().parents[1] / "saved_results")
    args = parser.parse_args()
    if args.workspace is not None:
        os.environ["PAPER2_WORKSPACE"] = str(args.workspace.resolve())
    if args.raw_data is not None:
        os.environ["PAPER2_RAW_DATA"] = str(args.raw_data.resolve())
    from paths import ROOT, ensure_layout
    ensure_layout()
    if args.stage in ["paired-effects", "length-control"]:
        copy_saved_input(args.saved_results, "fair_per_response.csv", ROOT / "experiments/v3/results/fair_per_response.csv")
    if args.stage == "length-control":
        copy_saved_input(args.saved_results, "pollution_cohort.json", ROOT / "experiments/v2/results/pollution_cohort.json")

    if args.stage == "prepare-tep":
        from prepare_numerical import prepare_tep
        prepare_tep()
    elif args.stage == "fit-tep":
        from prepare_numerical import fit_tep_models
        fit_tep_models()
    elif args.stage == "grouped-tep":
        from v3_numeric import risk
        risk()
    elif args.stage == "candidates-tep":
        from v4_tep import main as run
        run()
    elif args.stage == "calibrate-tep":
        from v4_calibration import main as run
        run()
    elif args.stage == "fit-hai":
        from v4_hai_strict import main as run
        run()
    elif args.stage == "compare-hai":
        from review_revision_20261106_v01 import protocol, hai
        protocol()
        hai()
    elif args.stage == "paired-effects":
        from review_revision_20261106_v01 import protocol, paired
        protocol()
        paired()
    elif args.stage == "tep-summary":
        from review_revision_20261106_v01 import protocol, tep
        protocol()
        tep()
    elif args.stage == "length-control":
        from round3_checks_20261106_v01 import main as run
        run()


if __name__ == "__main__":
    main()
