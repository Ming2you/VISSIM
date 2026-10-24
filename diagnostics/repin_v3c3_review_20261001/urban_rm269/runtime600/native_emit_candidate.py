"""Diagnostic hook: replace only the fused closure's emitter; preserve arithmetic."""
from evaluation.controllers import sdmpc_tangent_reverse as ad
from evaluation.controllers.sdmpc_tangent_summary import install_fused_operations
import native_emit


def install():
    install_fused_operations()
    native_emit.configure(ad, ad.Dual)
    cells = dict(zip(ad.Dual.__add__.__code__.co_freevars, ad.Dual.__add__.__closure__))
    cell = cells['emit']
    original = cell.cell_contents
    cell.cell_contents = native_emit.emit
    return cell, original
