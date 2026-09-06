import os
import shutil
import sys
from pathlib import Path

import image3kit as ik
from file_utils import list_files

import pnmkit as nm

#list_files()

# Setup paths
img_name = sys.argv[1] if len(sys.argv)>1 else "imgs/microCT_based_design_2D_slice_only.eroded.png"
img_path = Path(__file__).resolve().parent / img_name

assert img_path.exists(), f"Image {img_path} not found"

shutil.rmtree("pak2d", ignore_errors=True)
Path("pak2d").mkdir(exist_ok=True)
os.chdir("pak2d")

img = ik.VxlImgU8(img_path)

img.threshold101(1, 255) # asigns 0 to void
img.print_info()
print(img)
# for _ in range(2):
#     img.grow_label(0)
img.spacing = (3.28e-6, 3.28e-6, 3.28e-6)

img.plot_all("netfrom2d_original_", color=False, min_val=0, max_val=1, normal_axis="z", z_profile=False)

# Do not extrude, here we want to test network extraction from a 2D image
# img.distMapExtrude(offset=0.5, scale=2.0)
# imgextrude_name = f"Pak2DExtruded_{img.nx}x{img.ny}x{img.nz}_5p0um"
# img.write(f"{imgextrude_name}.raw")


nm.mextract(img, {
    "OutputName": "netfrom2d",
    "Overwrite": "true", 
    "VoidRange": "0 0",
    "WriteSpheres": "true", 
    "WriteCylinders": "true",
    "RNoise": "1.1", # minRPore in pneXtract
    "DistMapSettings": "0.05  0.0  1", # AGENTS: sync with image3kit's DistMap
    #MedSurfSettings: midRFrac  RMedSurfNoise  lenNf  vmvRadRelNf  RCorsf  RCors
    "MedSurfSettings": "0.8       0.95.         0.6.      1.1       0.15    1.9",
})

# nm.snflow({
#     'NetworkFile': 'netfrom2d_ms.xmf',
#     'OutputName': 'flow_simulation',
#     'WaterOil': '0.05',
#     'Water': '0.001 1.2 1000.',
#     'Oil': '0.001 1000 1000.',
#     'UpscaleBox': '0.1 0.9',
#     'Cycle1': '0. 1.0E+05 0.05 T T',
#     'Cycle2': '1. -5.0E+04 0.05 T T',
#     'Cycle3': '0. 1.0E+05 0.05 T T',
#     'AlterContAng': '3  30  60   0.25 -1.0  rand  0.',
#     'InitContAng:': '1   0   1   0.25 -1.0  rand  0.',
#     'RandSeed:': '1001',
#     'Overwrite': 'T',
#     'WriteXmf': '1 15 15 15'
# })

list_files() # for user info/debugging.

import glob

# Plot pores and throats raw.gz images using image3kit
sum_img = None
for filepath in glob.glob("netfrom2d_pores_*.raw.gz") + glob.glob("netfrom2d_throats_*.raw.gz"):
    print(f"Reading and plotting {filepath} ...")
    raw_img = ik.VxlImgI32(filepath)
    base_name = filepath.removesuffix(".raw.gz")
    raw_img.plot_all(f"{base_name}_", color=False, min_val=0, max_val=1, normal_axis="z", z_profile=False)

    if sum_img is None:
        sum_img = ik.VxlImgI32(raw_img) # raw_img.copy()
    else:
        assert raw_img.shape == sum_img.shape, f"Shape mismatch: {filepath}.shape={raw_img.shape} != sum_img.shape={sum_img.shape}"
        sum_img += raw_img

sum_img.plot_all("netfrom2d_both_", color=False, min_val=0, max_val=1, normal_axis="z", z_profile=False)
print(sum_img)
