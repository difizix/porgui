import image3kit as ik

from pathlib import Path
assert Path('imgs/01_Dry_1316_1316_1087_16bit_6pt5um.raw').exists(), \
    "Please upload images from https:dx.doi.org/10.17612/6rtt-5w16 to imgs folder first"

MAX_NZ = 50
dry = ik.VxlImgU16('imgs/01_Dry_1316_1316_1087_16bit_6pt5um.raw', max_nz=MAX_NZ)
wet = ik.VxlImgU16('imgs/02_KI_1316_1316_1087_16bit_6pt5um.raw', max_nz=MAX_NZ)
dry.print_info()
wet.print_info()

rock_mask = ik.threshold01_otsu(wet)
rock_mask.median_filter()
rock_mask.median_filter()
rock_mask.shrink0()


threshold = int(wet.otsu_threshold()[2])

mineral = wet.copy()
mineral.blend_min_variance(image2=dry, bgn=threshold, end=65535, shift=-2.0, span=5.0, mask=rock_mask)
mineral.print_info()
