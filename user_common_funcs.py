

# ---------------------------------------------------------------------------
# UI marker types — use these as type annotations in Python functions to hint
# which Streamlit widget to render for a parameter.
# ---------------------------------------------------------------------------
from typing import Annotated

FileDropdown = Annotated[str, "file_dropdown"]   # renders a file-picker selectbox
ImageType    = Annotated[str, "type_dropdown"]   # renders a VxlImg type selectbox


# ---------------------------------------------------------------------------
# Python functions — fully annotated, called directly with **kwargs.
# Add new utility functions here; they will appear in the UI automatically.
# ---------------------------------------------------------------------------
def loadImg(
    filename: FileDropdown,
    img_type: ImageType = "VxlImgU16",
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
