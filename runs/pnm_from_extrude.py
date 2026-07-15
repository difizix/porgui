import os
import sys
from pathlib import Path
from file_utils import list_files

import image3kit as ik
import pnmkit as nm

# Setup paths
img_name = sys.argv[1] if len(sys.argv)>1 else "TPak2D_240x200x1_5um.dat"
img_path = Path(__file__).resolve().parent / img_name

assert img_path.exists(), f"Image {img_path} not found"

Path("tpakextr").mkdir(exist_ok=True)
os.chdir("tpakextr")

img = ik.VxlImgU8(img_path)
for _ in range(2):
    img.grow_label(0)
img.spacing = (5.0e-6, 5.0e-6, 5.0e-6)
img.extrude_dist_map(offset=0.5, scale=2.0)
img.write(f"extruded_{img.nx}x{img.ny}x{img.nz}_5p0um.raw.gz")


nm.mextract(img, {
    "OutputName": "extruded",
    "Overwrite": "T",
    "VoidRange": "0 0",
    "WriteSpheres": "True",
    "WriteCylinders": "True",
})

nm.snflow({
    'NetworkFile': 'extruded_ms.xmf',
    'OutputName': 'flow_simulation',
    'WaterOil': '0.05',
    'Water': '0.001 1.2 1000.',
    'Oil': '0.001 1000 1000.',
    'UpscaleBox': '0.1 0.9',
    'Cycle1': '0. 1.0E+05 0.05 T T',
    'Cycle2': '1. -5.0E+04 0.05 T T',
    'Cycle3': '0. 1.0E+05 0.05 T T',
    'AlterContAng': '3  30  60   0.25 -1.0  rand  0.',
    'InitContAng:': '1   0   1   0.25 -1.0  rand  0.',
    'RandSeed:': '1001',
    'Overwrite': 'T',
    'WriteXmf': '1 14 14 14'
})


list_files()

import glob
# Plot pores and throats raw.gz images using image3kit
for filepath in glob.glob("extruded_pores_*.raw.gz") + glob.glob("extruded_throats_*.raw.gz"):
    print(f"Reading and plotting {filepath} ...")
    raw_img = ik.VxlImgI32(filepath)
    base_name = filepath[:-7] if filepath.endswith(".raw.gz") else filepath
    raw_img.plot_all(f"{base_name}_", color=False, min_val=0, max_val=1, normal_axis="z", z_profile=False)