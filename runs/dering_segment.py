import image3kit as ik
try:
    img = ik.VxlImgU16("runs/Pak2D_240x200x1_5um.dat")
    print("Success loading runs/Pak2D_240x200x1_5um.dat")
except Exception as e:
    print("Failed runs/Pak2D_240x200x1_5um.dat:", e)

try:
    img2 = ik.VxlImgU16("Pak2D_240x200x1_5um.dat")
    print("Success loading Pak2D_240x200x1_5um.dat")
except Exception as e:
    print("Failed Pak2D_240x200x1_5um.dat:", e)
