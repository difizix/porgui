

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

