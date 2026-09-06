import os
import shutil
import sys
from pathlib import Path

import image3kit as ik
from file_utils import list_files

#list_files()

# Setup paths
img_name = sys.argv[1] if len(sys.argv)>1 else "imgs/microCT_based_design_2D_slice_only.eroded.png"
img_path = Path(__file__).resolve().parent / img_name

assert img_path.exists(), f"Image {img_path} not found"

shutil.rmtree("pak2e", ignore_errors=True)
Path("pak2e").mkdir(exist_ok=True)
os.chdir("pak2e")

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


# Write the voxel image to an MHD file
img.write("netfrom2d.mhd")

# Write the keyword configuration file (combining MHD header and nextract keywords)
keyword_content = f"""ObjectType =  Image
NDims =       3
ElementType = MET_UCHAR
ElementByteOrderMSB = False
ElementNumberOfChannels = 1
CompressedData = True
HeaderSize = 0
DimSize =    	{img.nx}	{img.ny}	{img.nz}
ElementSize = 	{img.spacing[0]}	{img.spacing[1]}	{img.spacing[2]}
Offset =      	0   	0   	0
ElementDataFile = netfrom2d.raw.gz

title            netfrom2d;
overwrite        true;
void_range       0 0;
write_poreMaxBalls true;
write_cylinders  true;
minRPore         1.1;
medialSurfaceSettings 0.05 0.0 0.8 0.95 0.6 1.1 3 0.15 1.9;
"""
with open("pnextract.mhd", "w") as f:
    f.write(keyword_content)

# Run the standalone pnextract executable
import subprocess

print("Running standalone pnextract...")
subprocess.run(["pnextract", "pnextract.mhd"], check=True)




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

list_files()

import glob

# Plot pores and throats raw.gz images using image3kit
sum_img = None
for filepath in glob.glob("netfrom2d_poreMBs*.raw.gz") + glob.glob("netfrom2d_throats_*.raw.gz"):
    print(f"Reading and plotting {filepath} ...")
    raw_img = ik.VxlImgI32(shape=img.shape)
    raw_img.read_bin(filepath)
    raw_img.spacing = img.spacing
    base_name = filepath.removesuffix(".raw.gz")
    raw_img.plot_all(f"{base_name}_", color=False, min_val=0, max_val=1, normal_axis="z", z_profile=False)

    if sum_img is None:
        sum_img = ik.VxlImgI32(raw_img) # raw_img.copy()
    else:
        assert raw_img.shape == sum_img.shape, f"Shape mismatch: {filepath}.shape={raw_img.shape} != sum_img.shape={sum_img.shape}"
        sum_img += raw_img

sum_img.plot_all("netfrom2d_both_", color=False, min_val=0, max_val=1, normal_axis="z", z_profile=False)
print(sum_img)

