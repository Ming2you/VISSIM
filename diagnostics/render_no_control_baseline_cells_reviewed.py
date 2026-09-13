"""Render saved cell evidence; move the legend outside data during visual QA."""
from pathlib import Path
import hashlib
import json
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "diagnostics/.plot-deps"))
sys.path.insert(0, str(ROOT))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy
from diagnostics.analyze_no_control_baseline_5400 import cell_plot


def main():
    out = ROOT / "diagnostics/no_control_5400_baseline_diagnosis_v1"
    target = out / "baseline_EW_speed_5400_reviewed.png"
    if target.exists():
        raise ValueError("Preserve the existing reviewed figure")
    draft = out / "plot_layout_revision"
    draft.mkdir()
    source = out / "cells.json"
    # Preserve the reusable plot's figure object for a normal artist layout edit.
    # No data, thresholds, axes or colors are changed.
    with patch.object(plt, "close"):
        cell_plot(json.loads(source.read_text(encoding="utf-8-sig")), draft)
    fig = plt.gcf()
    legend = fig.axes[0].get_legend()
    handles = list(legend.legend_handles)
    labels = [text.get_text() for text in legend.get_texts()]
    legend.remove()
    fig.legend(handles=handles, labels=labels, loc="outside lower center", ncol=2, fontsize=9)
    fig.savefig(target, dpi=170)
    plt.close(fig)
    receipt = {"source_cell_evidence_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
               "renderer_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
               "png_sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
               "matplotlib_version": matplotlib.__version__, "numpy_version": numpy.__version__,
               "scope": "Legend moved outside axes; saved data, axes, masking, threshold and episodes unchanged",
               "global_PYTHONPATH_modified": False, "FZP_model_COM_access": False}
    with (out / "plot_render_receipt.json").open("x", encoding="utf-8") as stream:
        json.dump(receipt, stream, indent=2)
        stream.write("\n")
    print(target)


if __name__ == "__main__":
    main()
