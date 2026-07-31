"""Round-trip test: VxlImgU16 → .npy → VxlImgU16 via user_funcs.loadImg.

Usage:
    python test_npz_roundtrip.py
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "porgui"))

import numpy as np
import tempfile
import image3kit as ik
from user_funcs import read_image

DAT_FILE = "runs/Pak2D_240x200x1_5um.dat"


def test_roundtrip():
    # --- Step 1: load original as U16 ---
    orig = ik.VxlImgU16(DAT_FILE)
    arr_orig = orig.data           # (nx, ny, nz), dtype=uint16
    print(f"Loaded:   nx={orig.nx}  ny={orig.ny}  nz={orig.nz}")
    print(f"img.data: shape={arr_orig.shape}  dtype={arr_orig.dtype}  sum={arr_orig.sum()}")

    with tempfile.TemporaryDirectory() as d:
        npy_path = os.path.join(d, "img.npy")

        # --- Step 2: save img.data as .npy ---
        np.save(npy_path, arr_orig)

        # --- Step 3: reload via read_image (redirects to _readNpy) ---
        rec = read_image(npy_path)
        arr_rec = rec.data
        print(f"read_image: nx={rec.nx}  ny={rec.ny}  nz={rec.nz}  dtype={arr_rec.dtype}  sum={arr_rec.sum()}")

        # --- Step 4: assertions ---
        assert arr_rec.dtype == arr_orig.dtype, \
            f"dtype mismatch: {arr_rec.dtype} != {arr_orig.dtype}"
        assert arr_rec.shape == arr_orig.shape, \
            f"shape mismatch: {arr_rec.shape} != {arr_orig.shape}"
        assert np.array_equal(arr_rec, arr_orig), "Values do not match!"

    print("\n✅ All assertions passed.")
    print(f"   dtype  : {arr_orig.dtype}")
    print(f"   shape  : {arr_orig.shape}")
    print(f"   values : match ✓")


if __name__ == "__main__":
    test_roundtrip()
