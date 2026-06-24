import sys
import image3kit as ik

fname = "Dry.tif" if len(sys.argv) <=1 else sys.argv[1]
img = ik.VxlImgU16(fname)

print(img.shape)
print(1121111)