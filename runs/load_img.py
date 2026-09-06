import sys

import image3kit as ik

fname = "Pak2D_240x200x1_5um.dat" if len(sys.argv) <=1 else sys.argv[1]
img = ik.VxlImgU16(fname)

print(img.shape)
