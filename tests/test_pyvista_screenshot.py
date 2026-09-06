"""
Test script: load network_pn.xmf, apply tube filter, save PNG screenshot.
Run inside the podman container:
    podman exec img3gui python test_pyvista_screenshot.py

network_pn.xmf uses VTK_QUADRATIC_EDGE (cell type 21) — 3-node quadratic edges.
We linearize them to standard LINE cells (type 3) so vtkTubeFilter works.
"""
import os

import numpy as np
import pytest
import pyvista as pv

xmf_file = "runs/run_tst_SNM/Pak2DExtruded_240x200x28_5p0um_pn.xmf"
var_name  = "radius"
xRad      = 0.5
out_png   = "runs/fig/test_network_pn.png"


@pytest.mark.skipif(not os.path.exists(xmf_file), reason=f"{xmf_file} does not exist")
def test_pyvista_screenshot():
    print(f"Reading {xmf_file} ...")
    mesh = pv.read(xmf_file, force_ext='.xdmf')
    print(f"  {mesh.n_points} points, {mesh.n_cells} cells, celltypes={np.unique(mesh.celltypes)}")
    print(f"  Arrays: {list(mesh.point_data.keys()) + list(mesh.cell_data.keys())}")

    # threshold: keep only positive radius
    print(f"Thresholding by {var_name} > 0 ...")
    mesh_thr = mesh.threshold(value=1e-9, scalars=var_name, preference="point")
    print(f"  After threshold: {mesh_thr.n_points} points, {mesh_thr.n_cells} cells")

    # linearize VTK_QUADRATIC_EDGE (type 21) → standard LINE (type 3)
    # Each quadratic edge cell has 3 nodes: [n0, n1, mid] — we keep only [n0, n1]
    print("Linearizing quadratic edges → standard LINE cells ...")
    raw_cells = mesh_thr.cells  # flat array: [3, n0, n1, mid, 3, n0, n1, mid, ...]
    n_cells   = mesh_thr.n_cells
    lines = np.empty(n_cells * 3, dtype=np.int_)
    for i in range(n_cells):
        base = i * 4
        lines[i*3]   = 2
        lines[i*3+1] = raw_cells[base + 1]
        lines[i*3+2] = raw_cells[base + 2]

    poly = pv.PolyData()
    poly.points = mesh_thr.points
    poly.lines  = lines
    # copy point data
    for name in mesh_thr.point_data:
        poly.point_data[name] = mesh_thr.point_data[name]

    print(f"  PolyData: {poly.n_points} points, {poly.n_cells} lines")

    # tube filter
    print(f"Applying tube filter (radius=5e-5, radius_factor={xRad}, scalars={var_name}) ...")
    tubes = poly.tube(radius=5e-5, scalars=var_name, absolute=True, radius_factor=xRad, n_sides=10)
    print(f"  Tubes: {tubes.n_points} points, {tubes.n_cells} cells")

    # render and save
    print(f"Rendering to {out_png} ...")
    plotter = pv.Plotter(off_screen=True, window_size=[1024, 1024])
    plotter.background_color = pv.Color("#0f172a")
    plotter.add_mesh(tubes, scalars=var_name, cmap="viridis", show_scalar_bar=True)
    plotter.add_axes()
    plotter.view_isometric()
    plotter.screenshot(out_png)
    print(f"Done → {out_png}")


if __name__ == "__main__":
    test_pyvista_screenshot()
