"""Portable paths for numerical reruns; generated files never overwrite saved_results."""
from pathlib import Path
import json
import os

REPOSITORY = Path(__file__).resolve().parents[1]
ROOT = Path(os.environ.get("PAPER2_WORKSPACE", os.environ.get("PAPER2_WORKDIR", REPOSITORY / "workspace"))).expanduser().resolve()
RAW_DATA_ROOT = Path(os.environ.get("PAPER2_RAW_DATA", ROOT / "data")).expanduser().resolve()


def ensure_layout():
    archive = (REPOSITORY / "saved_results").resolve()
    if ROOT == archive or archive in ROOT.parents:
        raise ValueError("The workspace must be outside the published saved_results archive.")
    for relative in ["data", "models", "results"]:
        (ROOT / relative).mkdir(parents=True, exist_ok=True)
    for version in ["v2", "v3", "v4", "v5_review", "v6_review"]:
        for relative in ["data", "models", "results", "figures"]:
            (ROOT / "experiments" / version / relative).mkdir(parents=True, exist_ok=True)
    # v4_tep records a protocol digest in its completion marker. This identifies
    # the portable rerun, rather than impersonating the original local run hash.
    protocol = ROOT / "experiments/v4/protocol.json"
    if not protocol.exists():
        protocol.write_text(json.dumps({
            "scope": "Portable rerun of the manuscript's retrospective numerical comparisons; not new independent validation.",
            "model_seed": 20261112,
            "source": "code/v4_tep.py and code/v4_calibration.py",
            "note": "The source release preserves numerical definitions. Rerun model and protocol hashes can differ from archived study artifacts."
        }, indent=2), encoding="utf-8")
