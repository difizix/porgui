import os
import sys

# Ensure repository root is in sys.path
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

import image3kit as ik

from utils_app import func_args_from_inspect, func_args_from_pybind_doc


def test_otsu_threshold_max_val_default_parses_correctly():
    """otsu_threshold's return-type annotation contains a nested paren
    (typing.Annotated[list[float], "FixedSize(5)"]), which used to confuse
    the signature parser's greedy regex and corrupt max_val's default.
    """
    parsed = func_args_from_pybind_doc(ik.VxlImgU8.otsu_threshold.__doc__)
    by_name = {p["name"]: p for p in parsed["params"]}
    assert by_name["min_val"]["default"] == 0
    assert by_name["max_val"]["default"] == 255


def test_func_args_from_inspect_handles_overloaded_pybind11_builtin():
    """threshold01_otsu is bound once per dtype (U8, U16) onto the same voxlib
    module, so pybind11 merges them into one "Overloaded function." object whose
    generic first-line docstring has no parseable __text_signature__. inspect.signature()
    raises ValueError on it (this used to crash app_func_img.py's import at startup);
    func_args_from_inspect() must fall back to the first overload instead of raising.
    """
    parsed = func_args_from_inspect(ik.threshold01_otsu)
    by_name = {p["name"]: p for p in parsed["params"]}
    assert set(by_name) == {"image", "minvi", "maxvi", "skipFrac"}
    assert by_name["minvi"]["default"] == 0
    assert by_name["maxvi"]["default"] == 255

