
import sys
import numpy as np
import image3kit as ik


def plotAll_save(img: ik.VxlImgU16, filename, save=True):
    img.plotAll(filename+"_", grey=False, min_val=3000, max_val=13500)
    if save:
       img.write(""+filename+".raw") # it adds a .mhd header too

def printInfo(tag: str, img: ik.VxlImgU16):
    print(f"\n{tag:20s}: mean {img.data.mean():10.4f}, std {img.data.std():10.4f}, min {img.data.min():10.4f}, max {img.data.max():10.4f}")
    sys.stdout.flush()

def desharpen(img: ik.VxlImgU16, kernel_radius=1, steps=10, sigma_sh=500, sharpness_sh=0.0, sigma_sm=500, sharpness_sm=0.0):
    printInfo("desharpen before:", img)

    vsh = img.copy()
    vsm = img.copy()
    vsh.bilateralX(kernel_radius=kernel_radius, x_step=steps, sigma_val=sigma_sh, sharpness=sharpness_sh)
    vsm.bilateralX(kernel_radius=kernel_radius+1, x_step=steps, sigma_val=sigma_sm, sharpness=sharpness_sm)
    vsh.data[:] = (vsh.data+10000)-vsm.data
    delAvg = (vsm.data.astype(np.int32)-vsh.data.astype(np.int32)).mean() # to avoid changing image brightness
    # convert to int32, substract the difference and convert back to uint16, to avoid overflow
    img.data[:] = np.maximum(img.data.astype(np.int32) + (vsm.data.astype(np.int32)-vsh.data.astype(np.int32)) - delAvg, 0).astype(np.uint16)

    printInfo("desharpen after:", img)

def medianZ_iterate(img: ik.VxlImgU16, n_iter):
    for _ in range(n_iter):
        img.medianZ()

if __name__ == "__main__":

    if len(sys.argv) < 2:
        print(f"Usage:\npython {sys.argv[0]} <FILENAME.raw...>")
        sys.exit(1)
    filename = sys.argv[1]

# if 1: # filters (median, desharpen and dering)

    img = ik.VxlImgU16(filename)

    img.cropD((0,0,300), (467,1775,580)) # crop during testing phase for speed!

    plotAll_save(img, filename="volu_original", save=False)

    medianZ_iterate(img, 5)
    img.medianFilter()
    plotAll_save(img, filename="volu_median")

    """Remove excessive sharpening artefacts whcih were probabbly added during image reconstruction"""
    desharpen(img)
    plotAll_save(img, filename="volu_desh")

    """Remove ring artefacts"""
    img.dering(x0=374, y0=853, x1=374, y1=853, nr=1000, ntheta=32, nz=148, min_val=8500, max_val=12000, nGrowBox=20, write_dumps=False, scale_dif_val=1.0, bilateral_sharpen=0.05)
    plotAll_save(img, filename="volu_dring")

    if 0:
        """plot dering dump files for inspection"""
        for filename in ["dumpDringBackground",  "dumpDringMeGrow0",    "dumpDringMeGrow1",     "dumpDringSmoothRad", "dumpDringRad",   "dumpFiltDering"]:
            plotAll_save(ik.VxlImgU16(f"{filename}.tif"), filename, save=False)


# if 1: # segmentation
    img = ik.VxlImgU16("volu_dring.mhd")

    """Image segmentation, does not work well TODO document..."""
    img.segment2(thresholds=[0, 6000, 65535], min_sizes=[1, 3], )
    plotAll_save(img, filename="volu_seg", save=False)
    img.write8bit("volu_seg.raw.gz", min=0, max=25500)


# if 1: # convert to 8bit and paint over segmentation artefacts
    img = ik.VxlImgU8("volu_seg.mhd")

    """Paint over segmentation artefacts with a dummy value(=mean*2), the artefact is in the bottom-left"""

    # Convert to binary (0&1) and write as 8bit
    mean = int(img.data.mean())
    img.threshold101(1, mean)  # from 1 to mean (somewhere in the middle of rock and void voxel values) are set to 0
    img.data[:] *= 255


    # img.setOrigin((0,0,0))
    # img.setVoxelSize((1,1,1))
    dx, dy, dz = img.voxelSize()
    nx, ny, nz = img.shape()
    img.paint(ik.cube(p1=(0, dy*(ny-50), 0), size=(50*dx, 50*dy, nz*dz+10000), val=231))

    img.write8bit("volu_seg01.raw.gz")


if 1:
    img = ik.VxlImgU8("volu_seg.mhd")
    im2 = img.copy().astype(np.uint8)
    im2.shrink0()
    im3 = img.copy()
    im3.shrink1()

    im2.XOR(im3)

    img.mapFrom(im2)

