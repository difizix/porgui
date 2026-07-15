
# TODO this shall be used as an example file used to dynamically inject functions to interactive function executer tabs

import os
import sys
from pathlib import Path

# Ensure the parent app directories are in sys.path
run_dir = Path(__file__).resolve().parent
app_dir = run_dir.parent
workspace_root = app_dir.parent

if str(workspace_root) not in sys.path:
    sys.path.insert(0, str(workspace_root))

import image3kit as ik
import pnmkit as nm
from img3gui.utils_app import STANDALONE_FUNCTIONS

def main():
    os.chdir(run_dir)
    img_name = sys.argv[-1] if len(sys.argv)>1 else "TPak2D_240x200x1_5um.dat"
    print(f"Loading image {img_name}...")
    
    img = ik.VxlImgU8(img_name)
    for _ in range(2):
        img.grow_label(0)
    img.spacing = (1e-6, 1e-6, 1e-6)
    img.extrude_dist_map(offset=0.5, scale=2.0)
    
    extruded_name = f"TPak2DExtruded_{img.nx}x{img.ny}x{img.nz}_5p0um"
    print(f"Writing extruded image to {extruded_name}.raw...")
    img.write(f"{extruded_name}.raw")
    
    print("Extracting network using pnmkit.mextract...")
    extract_params = {"OutputName": extruded_name, "Overwrite": "T", "VoidRange": "0 0"}
    nm.mextract(img, extract_params)
    
    xmf_file = f"{extruded_name}_ms.xmf"
    assert Path(xmf_file).exists(), f"Expected XMF file {xmf_file} not found"
    print(f"Network extracted successfully. Output: {xmf_file}")

    print("Running vtkXdmfAnimate wrapper function...")
    animate_func = STANDALONE_FUNCTIONS["vtkXdmfAnimate"]
    # Run with small resolution and frame steps to verify off-screen VTK rendering fast
    animate_func(xmf_file=xmf_file, var_name="radius", zoom=1.1, resX=400, resY=400)
    print("Animation completed successfully!")

if __name__ == "__main__":
    main()
