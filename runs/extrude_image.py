import os
import shutil
from pathlib import Path
from file_utils import list_files

import image3kit as ik
import pnmkit as nm

# Setup paths
img_name = "TPak2D_240x200x1_5um.dat"
img_path = Path(__file__).resolve().parent / img_name

assert img_path.exists(), f"Image {img_path} not found"

tmp_path = Path("extrude")
tmp_path.mkdir(exist_ok=True)
os.chdir(tmp_path)

img = ik.VxlImgU8(img_path)
for _ in range(2):
    img.growLabel(0)
img.voxelSize = (1e-6, 1e-6, 1e-6)
img.distMapExtrude(offset=0.5, scale=2.0)
img_name = f"TPak2DExtruded_{img.nx}x{img.ny}x{img.nz}_5p0um"
img.write(f"{img_name}.raw")


nm.mextract(img,  {"OutputName": img_name, "Overwrite": "T", "VoidRange": "0 0"})
        
list_files()