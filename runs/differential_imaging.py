"""
When openning porgui web interface, you can open existing or create new scripts via the drop-down in Workflow editor tab.
example scripts for loading an image and displaying its info is given below, see the other scripts for more practical use cases 
"""
import image3kit as ik

img = ik.VxlImgU16("Pak2D_240x200x1_5um.dat")
img.print_info()