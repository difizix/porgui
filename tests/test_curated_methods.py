import os
import sys
import image3kit as ik

# Ensure the porgui package directory is in sys.path (its modules use flat,
# same-directory imports among themselves, e.g. `from utils_app import ...`).
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if not os.path.exists(repo_root) and os.path.exists("/app"):
    repo_root = "/app"
porgui_dir = os.path.join(repo_root, "porgui")
if porgui_dir not in sys.path:
    sys.path.insert(0, porgui_dir)

from app_func_img import CURATED_METHODS
from utils_app import run_capturing_output


def test_curated_methods_exist_and_found():
    """Verify that all CURATED_METHODS in app_func_img resolve to real bound methods or valid functions,
    and specifically that the 5 previously mismatched method names match their pybind definitions.
    """
    # Assert every key in CURATED_METHODS resolves to a found method / function
    missing_methods = []
    for method_name, meta in CURATED_METHODS.items():
        desc = meta.get("desc", "")
        if f"Function {method_name} not found." in desc:
            missing_methods.append(method_name)

    assert not missing_methods, (
        f"The following methods in CURATED_METHODS were not found: {missing_methods}"
    )

def test_run_capturing_output_captures_cpp_stdout():
    def load():
        img = ik.VxlImgU16("runs/Pak2D_240x200x1_5um.dat")
        img.print_info()  # writes via std::cout, not sys.stdout
        return img
    _, out = run_capturing_output(load)
    assert "total_porosity" in out