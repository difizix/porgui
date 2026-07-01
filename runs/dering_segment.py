import image3kit as ik
try:
    img = ik.VxlImgU16("runs/TPak2D_240x200x1_5um.dat")
    print("Success loading runs/TPak2D_240x200x1_5um.dat")
except Exception as e:
    print("Failed runs/TPak2D_240x200x1_5um.dat:", e)

try:
    img2 = ik.VxlImgU16("TPak2D_240x200x1_5um.dat")
    print("Success loading TPak2D_240x200x1_5um.dat")
except Exception as e:
    print("Failed TPak2D_240x200x1_5um.dat:", e)
