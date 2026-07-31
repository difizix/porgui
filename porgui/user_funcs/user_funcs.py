

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
def read_image(
    filename: ImgDropdown,
    new_var_name: str = "img",
    max_nz: int = -1,
) -> object:
    """Load an image (.tif, .mhd, .am, .dat, .png, .npy, .npz) from the runs directory into the workspace."""
    import os
    ext = os.path.splitext(filename)[-1].lower()
    if ext in (".npz", ".npy"):
        return _readNpy(filename, new_var_name, max_nz=max_nz)

    import image3kit as ik
    return ik.read_image(filename, max_nz=max_nz)


def _readNpy(
    filename: ImgDropdown,
    new_var_name: str = "img",
    max_nz: int = -1,
) -> object:
    """Load a .npy or .npz file into a VxlImg of appropriate data type.

    The array dtype auto-selects the VxlImg class.
    2-D arrays are promoted to (nx, ny, 1).
    """
    import image3kit as ik
    import numpy as np
    import tempfile
    import os

    ext = os.path.splitext(filename)[-1].lower()
    if ext == ".npz":
        npz = np.load(filename)
        keys = list(npz.keys())
        if not keys:
            raise ValueError(f"No arrays found in {filename}")
        arr = npz[keys[0]]
        if len(keys) > 1:
            print(f"[_readNpy] npz has multiple keys {keys}; using '{keys[0]}'")
    else:
        arr = np.load(filename)

    if arr.ndim == 2:
        arr = arr[:, :, np.newaxis]
    elif arr.ndim != 3:
        raise ValueError(f"Expected 2-D or 3-D array, got shape {arr.shape}")

    if max_nz > 0 and arr.shape[2] > max_nz:
        arr = arr[:, :, :max_nz]

    dtype_map = {
        np.dtype("uint8"):   ik.VxlImgU8,
        np.dtype("uint16"):  ik.VxlImgU16,
        np.dtype("int32"):   ik.VxlImgI32,
        np.dtype("float32"): ik.VxlImgF32,
        np.dtype("float64"): ik.VxlImgF32,
    }
    cls = dtype_map.get(arr.dtype, ik.VxlImgU16)

    cls_to_dtype = {
        ik.VxlImgU8:   np.uint8,
        ik.VxlImgU16:  np.uint16,
        ik.VxlImgI32:  np.int32,
        ik.VxlImgF32:  np.float32,
    }
    target_dtype = cls_to_dtype.get(cls, np.uint16)
    if arr.dtype != target_dtype:
        arr = arr.astype(target_dtype)

    # Construct the image directly in memory with the array shape,
    # specifying 'shape' explicitly to avoid pybind11 overloading conflicts,
    # then copy the numpy array values into the writeable .data view.
    img = cls(shape=arr.shape)
    img.data[:] = arr
    return img


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
    try:
        import pnmkit as nm
    except ModuleNotFoundError:
        raise ModuleNotFoundError(
            "pnmkit is not installed — it is not bundled with porgui. "
            "Install it manually to use mextract (see the porgui README)."
        ) from None
    import streamlit as st

    if image_var not in st.session_state.workspace_vars:
        raise ValueError(f"Image variable '{image_var}' not found in workspace.")
    img = st.session_state.workspace_vars[image_var]

    config = {
        "OutputName": OutputName,
        "Overwrite": "T" if Overwrite else "F",
        "VoidRange": VoidRange,
    }
    nm.mextract(img, config, verbose=verbose) # removed, we shall lunch skelor standalone exe instead
    return f"Extracted network written to {OutputName}_ms.xmf"


def snflow( # We need to define more Anottated type aliases for the space-seperated str args of this function
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
    try:
        import pnmkit as nm
    except ModuleNotFoundError:
        raise ModuleNotFoundError(
            "pnmkit is not installed — it is not bundled with porgui. "
            "Install it manually to use snflow (see the porgui README)."
        ) from None
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


def render_xdmf_tubes(
    filename: XmfDropdown,
    var_name: str = "radius",
    xRad: float = 0.5,
    trsh: float = -1e32,
    new_var_name: str = "network_tubes",
) -> object:
    """Load an xdmf pore network, linearize edges and generate 3D tube mesh.

    Handles VTK_QUADRATIC_EDGE cells (type 21) in _pn.xmf files by converting
    them to standard LINE cells before applying the vtkTubeFilter.
    Mirrors the pipeline in pnmkit/xdmf_3dl_screenshot.py using PyVista.
    """
    import pyvista as pv
    import numpy as np

    print(f"[render_xdmf_tubes] Reading: {filename}")
    mesh = pv.read(filename, force_ext='.xdmf')
    print(f"  Loaded: {mesh.n_points} points, {mesh.n_cells} cells")
    print(f"  Cell types: {np.unique(mesh.celltypes).tolist()}")

    if str(filename).lower().endswith(("_ms.xmf", "4ds.xmf")):
        print("  Medial/4D surface file detected. Disabling tube filter and returning raw surface mesh.")
        if trsh > -1e30:
            print(f"  Applying threshold {var_name} >= {trsh:.3g} ...")
            mesh = mesh.threshold(value=trsh, scalars=var_name, preference="point")
        return mesh

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
    thresh_val = trsh
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
        radius=1e-6 * xRad,
        scalars=var_name,
        absolute=True,
        radius_factor = xRad,
        n_sides=8,
    )
    print(f"  Tubes: {tubes.n_points} points, {tubes.n_cells} cells")
    if tubes.n_points == 0:
        raise ValueError("Tube filter produced empty mesh. Try increasing xRad or check scalar units.")
    return tubes


def render_xdmf_3dl(
    filename: XmfDropdown,
    pore_scalar: str = "radius",
    throat_scalar: str = "radius",
    xRadPore: float = 1.0,
    xRadThroat: float = 1.0,
    new_var_name: str = "network_mesh",
) -> object:
    """Render pore network with pores as sphere glyphs and throats as tubes.
    
    Pores are rendered as spheres of radius proportional to pore_scalar if xRadPore > 0.
    Throats are rendered as tubes of radius proportional to throat_scalar if xRadThroat > 0.
    """
    import pyvista as pv
    import numpy as np

    print(f"[render_xdmf_3dl] Reading: {filename}")
    mesh = pv.read(filename, force_ext='.xdmf')
    print(f"  Loaded: {mesh.n_points} points, {mesh.n_cells} cells")

    if str(filename).lower().endswith(("_ms.xmf", "4ds.xmf")):
        print("  Medial/4D surface file detected. Disabling sphere/tube generation and returning raw surface mesh.")
        return mesh

    # Auto-detect scalars
    avail_all = list(mesh.point_data.keys()) + list(mesh.cell_data.keys())
    if pore_scalar not in avail_all:
        if "radius" in avail_all:
            pore_scalar = "radius"
        elif "radus" in avail_all:
            pore_scalar = "radus"
            
    if throat_scalar not in avail_all:
        if "radius" in avail_all:
            throat_scalar = "radius"
        elif "radus" in avail_all:
            throat_scalar = "radus"

    parts = []

    # 1. Generate Pore Spheres
    if xRadPore > 0:
        print(f"  Generating pore spheres using scalar '{pore_scalar}' with xRadPore={xRadPore} ...")
        pore_mesh = mesh
        if pore_scalar in pore_mesh.cell_data and pore_scalar not in pore_mesh.point_data:
            pore_mesh = pore_mesh.cell_data_to_point_data()
            
        if pore_scalar not in pore_mesh.point_data:
            raise ValueError(f"Pore scalar '{pore_scalar}' not found in point or cell data.")
            
        # Pores are vertices, extract points as PolyData
        pores = pv.PolyData(pore_mesh.points)
        pores.point_data[pore_scalar] = pore_mesh.point_data[pore_scalar].copy()
        
        # Glyph sphere geometry (radius 1.0) scaled by scalar * factor
        sphere_geom = pv.Sphere(radius=1.0, phi_resolution=10, theta_resolution=10)
        spheres = pores.glyph(geom=sphere_geom, scale=pore_scalar, factor=xRadPore, orient=False)
        print(f"  Generated pore spheres: {spheres.n_points} points, {spheres.n_cells} cells")
        parts.append(spheres)

    # 2. Generate Throat Tubes
    if xRadThroat > 0:
        print(f"  Generating throat tubes using scalar '{throat_scalar}' with xRadThroat={xRadThroat} ...")
        
        # Linearize or extract edges
        VTK_QUADRATIC_EDGE = 21
        cell_types = np.unique(mesh.celltypes).tolist()
        if VTK_QUADRATIC_EDGE in cell_types:
            n_cells = mesh.n_cells
            raw     = mesh.cells
            lines   = np.empty(n_cells * 3, dtype=np.intp)
            for i in range(n_cells):
                b = i * 4
                lines[i*3], lines[i*3+1], lines[i*3+2] = 2, raw[b+1], raw[b+2]
            poly = pv.PolyData()
            poly.points = mesh.points.copy()
            poly.lines  = lines
            for name in mesh.point_data.keys():
                poly.point_data[name] = mesh.point_data[name].copy()
            for name in mesh.cell_data.keys():
                poly.cell_data[name] = mesh.cell_data[name].copy()
        else:
            poly = mesh.extract_all_edges()
            
        # Ensure throat scalar is point-centered for tube filter
        if throat_scalar in poly.cell_data and throat_scalar not in poly.point_data:
            poly = poly.cell_data_to_point_data()
            
        if throat_scalar not in poly.point_data:
            raise ValueError(f"Throat scalar '{throat_scalar}' not found in point or cell data.")

        tubes = poly.tube(
            radius=1e-6,
            scalars=throat_scalar,
            absolute=True,
            radius_factor=xRadThroat,
            n_sides=10,
        )
        print(f"  Generated throat tubes: {tubes.n_points} points, {tubes.n_cells} cells")
        parts.append(tubes)

    if not parts:
        raise ValueError("At least one of xRadPore or xRadThroat must be positive.")

    # Combine all parts
    combined = parts[0]
    for part in parts[1:]:
        combined = combined + part

    return combined