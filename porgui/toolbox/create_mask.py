
# TODO: 
# these shall be made reusable functions for creating rock and tubig masks
# from either a dry image or ideally from a wet image, or even better from both

import image3kit as ik
from image3kit import VxlImgU16


def create_tubing_mask(wetimg: VxlImgU16, dryimg: VxlImgU16):

    min_avg_thr_avg_max = wetimg.otsu_threshold(0, 65535)
    minerals = wetimg.blend_min_variance(dryimg, bgn=min_avg_thr_avg_max[2])
    ik.threshold01_otsu(minerals)
# 	 echo "core and tube masks"
#    run { /// tube mask  -- Tested

#     VxlRead  ../Imgs/brineZ2.am -> corMsk {
#       operat b 1;  circleOut z 455 440 440 0;  threshold101 0 26000;
#       mode26 2; write8bit Imgs/corMsk.mhd; info; plotAll corMsk }


#       VxlRead  ../Imgs/brineZ2.am -> dry plotAll dry
#       VxlCopy  dry -> tub { modeFilter ;
#            threshold101  16000 20000 ; info
#            operat |  corMsk ; operat ! ;  info
#            mode26 2;             modeFilter;  info }
#      for IMG { in   dry brine   fw0  fw15  fw30  fw50  fw70  fw85 fw100
#           // cut out where reg == dry as defaultV was -1 during reg
#           VxlRead ../Imgs/IMGZ2.am -> img { modeFilter ; threshold101  2000 25000; modeFilter ; operat !}
#           VxlOpr tub *= img
#           VxlPro tub info
#           erase  img  }
#       VxlPro tub { growLabel 1 2;  growLabel 0 4;  mode26 2;
#                    write8bit Imgs/tubeMask.mhd;  info; plotAll tube }
#       erase  tub  dry
#     }

def get_image_centre_rad(img: VxlImgU16): # TODO implement this in C++
    img.cut_outside() # TODO this shall be replaced with a function thats crop the image
    nx, ny, _ = img.shape
    x_centre, y_centre = nx // 2, ny // 2
    radius = (nx + ny) // 4
    return x_centre, y_centre, radius

def create_solid_mask(dry_img: VxlImgU16, wet_img: VxlImgU16):
    # echo "Rock mask"
    # run { /// rock mask

    #   VxlRead  ../Imgs/brineZ2.am -> bri   circleOut  z 460 440 400 //; plotAll briCutOut 25000 55000
    x_centre, y_centre, radius = get_image_centre_rad(wet_img)
    dry_img.circle_out(x_centre, y_centre, radius )
    wet_img.circle_out(x_centre, y_centre, radius )
    #   VxlRead  ../Imgs/dryZ2.am   -> dry  circleOut  z 460 440 400  //; plotAll dryCutOut 0000  20000

    #   VxlOpr dry *= 1.7174   ///  should have done before registration: operat *= f = 32400-17200 / 13200-6500;   operat += 117 - 83*f
    #   VxlOpr bri -= dry 10000 ; VxlPro bri plotAll difBriDry
    #   VxlPro dry threshold101  65535 65535
    #   VxlOpr bri *= dry
    #   VxlPro bri { svgHistogram  difBrinDryDistCutOut.svg 128 0 255
    #         write  Imgs/difBrinDryCutOut.mhd ;
    #         threshold101  1 22000 ;  operat ! ; growLabel 1 2;  growLabel 0 4;  mode26 2; plotAll rockMask
    #         write8bit  Imgs/rockMask.mhd ; info}
    #   erase  bri  dry

    # }

# def adjust_slice_brightness(): # will be implemented by user
    # echo "Adjust Slice Brightness"
    # {
    #   VxlRead  ../Imgs/brineZ2.am -> bri ;                      expose bri
    #   VxlRead  Imgs/tubeMask.mhd  -> tubMsk { growLabel 0 2 } ;  expose tubMsk
    #   VxlRead  Imgs/corMsk.mhd    -> corMsk ;   // core mask
    #   VxlRead  Imgs/rockMask.mhd  -> rokMsk { growLabel 0 2 };  expose rokMsk

    #   for IMG { in   dry  fw0  fw15  fw30  fw50  fw70  fw85  fw100
    #     VxlPro  ../Imgs/IMGZ2.am  {
    #       adjustSliceBrightness  bri tubMsk rokMsk 3 5
    #       write  IMG_toBrin.mhd ;   plotAll IMG_toBrin;
    #       operat  -= bri 40000
    #       write  IMGdifBrin.mhd
    #       operat  *= corMsk;   plotAll IMGdifBrin;  resliceZ  5;  svgZProfile  IMGdifBrinProfilezZ5.svg 1 65535  }
    #   }

    #   VxlRead  ../Imgs/dryZ2.am -> dry ;  expose dry
    #   VxlPro  bri {  adjustSliceBrightness  dry tubMsk rokMsk 3 5
    #             write  IMG_toDry.mhd; plotAll bri_toDry; }

    #   erase  bri dry tubMsk corMsk rokMsk
    # }