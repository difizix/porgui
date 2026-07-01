

# ---------------------------------------------------------------------------
# UI marker types — use these as type annotations in Python functions to hint
# which Streamlit widget to render for a parameter.
# ---------------------------------------------------------------------------
from typing import Annotated

FileDropdown = Annotated[str, "file_dropdown"]   # renders a file-picker selectbox
ImgDropdown  = Annotated[str, "img_dropdown"]    # renders an image file selectbox
XmfDropdown  = Annotated[str, "xmf_dropdown"]    # renders a .xmf file selectbox
ImageType    = Annotated[str, "type_dropdown"]   # renders a VxlImg type selectbox
VarDropdown  = Annotated[str, "var_dropdown"]    # renders a workspace variable selectbox


# ---------------------------------------------------------------------------
# Python functions — fully annotated, called directly with **kwargs.
# Add new utility functions here; they will appear in the UI automatically.
# ---------------------------------------------------------------------------
def loadImg(
    filename: ImgDropdown,
    img_type: ImageType = "VxlImgU8",
    new_var_name: str = "img",
) -> object:
    """Load an image (.tif, .mhd, .am, .dat, .png) from the runs directory into the workspace."""
    import image3kit as ik
    cls_map = {
        "VxlImgU16": ik.VxlImgU16,
        "VxlImgU8":  ik.VxlImgU8,
        "VxlImgF32": ik.VxlImgF32,
    }
    cls = cls_map.get(img_type, ik.VxlImgU16)
    return cls(filename)


def mextract(
    image_var: VarDropdown,
    OutputName: str = "network",
    Overwrite: bool = True,
    VoidRange: str = "0 0",
    verbose: bool = False,
) -> str:
    """Extract pore network from a voxel image in the workspace.

    Outputs a network file (e.g., [OutputName]_ms.xmf) in the current directory.
    """
    import pnmkit as nm
    import streamlit as st

    if image_var not in st.session_state.workspace_vars:
        raise ValueError(f"Image variable '{image_var}' not found in workspace.")
    img = st.session_state.workspace_vars[image_var]

    config = {
        "OutputName": OutputName,
        "Overwrite": "T" if Overwrite else "F",
        "VoidRange": VoidRange,
    }
    nm.mextract(img, config, verbose=verbose)
    return f"Extracted network written to {OutputName}_ms.xmf"


def snflow(
    NetworkFile: XmfDropdown,
    OutputName: str = "flow_simulation",
    WaterOil: float = 0.05,
    Water: str = "0.001 1.2 1000.",
    Oil: str = "0.001 1000 1000.",
    UpscaleBox: str = "0.1 0.9",
    Cycle1: str = "0. 1.0E+05 0.05 T T",
    Cycle2: str = "1. -5.0E+04 0.05 T T",
    Cycle3: str = "0. 1.0E+05 0.05 T T",
    AlterContAng: str = "3  30  60   0.25 -1.0  rand  0.",
    InitContAng: str = "1   0   1   0.25 -1.0  rand  0.",
    RandSeed: int = 1001,
    Overwrite: bool = True,
    WriteXmf: str = "1 14 14 14",
) -> str:
    """Run snflow network flow simulation on a network file (.xmf).

    Generates relative permeability and capillary pressure curves/plots.
    """
    import pnmkit as nm
    config = {
        "NetworkFile": NetworkFile,
        "OutputName": OutputName,
        "WaterOil": str(WaterOil),
        "Water": Water,
        "Oil": Oil,
        "UpscaleBox": UpscaleBox,
        "Cycle1": Cycle1,
        "Cycle2": Cycle2,
        "Cycle3": Cycle3,
        "AlterContAng": AlterContAng,
        "InitContAng:": InitContAng,
        "RandSeed:": str(RandSeed),
        "Overwrite": "T" if Overwrite else "F",
        "WriteXmf": WriteXmf,
    }
    nm.snflow(config)
    return f"Simulation completed. Output: {OutputName}_upscal.svg"


# ---------------------------------------------------------------------------
# Python functions — fully annotated, called directly with **kwargs.
# Add new utility functions here; they will appear in the UI automatically.
# ---------------------------------------------------------------------------
def loadXmf(
    filename: XmfDropdown,
    new_var_name: str = "network",
) -> object:
    """Load an network (.xmf) from the runs directory into the workspace."""
    import pnmkit as nm
    return nm.Xdml(filename)


def makeNetworkTubes(
    filename: XmfDropdown,
    var_name: str = "radius",
    xRad: float = 0.5,
    trsh: float = -1e32,
    new_var_name: str = "network_tubes",
) -> object:
    """Load an xdmf pore network, linearize edges and generate 3D tube mesh.

    Handles VTK_QUADRATIC_EDGE cells (type 21) in _pn.xmf files by converting
    them to standard LINE cells before applying the vtkTubeFilter.
    Mirrors the pipeline in pyvtk/vtkXdmfScreenshot.py using PyVista.
    """
    import pyvista as pv
    import numpy as np

    print(f"[makeNetworkTubes] Reading: {filename}")
    mesh = pv.read(filename, force_ext='.xdmf')
    print(f"  Loaded: {mesh.n_points} points, {mesh.n_cells} cells")
    print(f"  Cell types: {np.unique(mesh.celltypes).tolist()}")

    # Auto-detect radius scalar
    avail = list(mesh.point_data.keys()) + list(mesh.cell_data.keys())
    print(f"  Available arrays: {avail}")
    if var_name not in avail:
        if "radius" in avail:
            var_name = "radius"
        elif "radus" in avail:
            var_name = "radus"
        else:
            raise ValueError(
                f"Scalar '{var_name}' not found. Available: {avail}"
            )
    print(f"  Using scalar: '{var_name}'")
    r = mesh.point_data.get(var_name)
    if r is None:
        r = mesh.cell_data.get(var_name)
    if r is not None:
        print(f"  {var_name} range: {r.min():.4g} – {r.max():.4g}")

    # Threshold to remove zero/negative radii
    thresh_val = trsh if trsh > -1e30 else 1e-9
    print(f"  Thresholding {var_name} >= {thresh_val:.3g} ...")
    mesh = mesh.threshold(value=thresh_val, scalars=var_name, preference="point")
    print(f"  After threshold: {mesh.n_points} points, {mesh.n_cells} cells")
    if mesh.n_cells == 0:
        raise ValueError("All cells removed by threshold — check scalar values or lower trsh.")

    # Linearize VTK_QUADRATIC_EDGE (type 21) → standard LINE (type 3)
    # Each quadratic edge: [3, n0, n1, mid] — keep only n0, n1 endpoints
    VTK_QUADRATIC_EDGE = 21
    cell_types = np.unique(mesh.celltypes).tolist()
    if VTK_QUADRATIC_EDGE in cell_types:
        print(f"  Linearizing VTK_QUADRATIC_EDGE (type 21) cells ...")
        n_cells = mesh.n_cells
        raw     = mesh.cells  # flat: [3, n0, n1, mid, ...]
        lines   = np.empty(n_cells * 3, dtype=np.intp)
        for i in range(n_cells):
            b = i * 4
            lines[i*3], lines[i*3+1], lines[i*3+2] = 2, raw[b+1], raw[b+2]
        poly = pv.PolyData()
        poly.points = mesh.points.copy()
        poly.lines  = lines
        for name in mesh.point_data.keys():
            poly.point_data[name] = mesh.point_data[name].copy()
        print(f"  PolyData lines: {poly.n_points} points, {poly.n_cells} lines")
    else:
        print(f"  Extracting edges from cell types {cell_types} ...")
        poly = mesh.extract_all_edges()
        print(f"  Edges: {poly.n_points} points, {poly.n_cells} lines")

    print(f"  Applying tube filter (radius=5e-5, xRad={xRad}, scalars={var_name}) ...")
    tubes = poly.tube(
        radius=5e-5,
        scalars=var_name,
        absolute=True,
        radius_factor=xRad,
        n_sides=10,
    )
    print(f"  Tubes: {tubes.n_points} points, {tubes.n_cells} cells")
    if tubes.n_points == 0:
        raise ValueError("Tube filter produced empty mesh. Try increasing xRad or check scalar units.")
    return tubes