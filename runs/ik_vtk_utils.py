from __future__ import annotations

import sys

import vtkmodules.vtkCommonDataModel
import vtkmodules.vtkFiltersCore
import vtkmodules.vtkRenderingOpenGL2
from vtkmodules.util.numpy_support import numpy_to_vtk
from vtkmodules.vtkCommonColor import vtkNamedColors
from vtkmodules.vtkIOImage import vtkPNGWriter
from vtkmodules.vtkRenderingCore import (
    vtkActor,
    vtkGraphicsFactory,
    vtkPolyDataMapper,
    vtkRenderer,
    vtkRenderWindow,
    vtkWindowToImageFilter,
)

import image3kit as ik


def plot_img3_contour_to_png(img: ik.VxlImgU16, threshold: float, filename: str):
    colors = vtkNamedColors()

    # Setup off-screen rendering.
    _graphics_factory = vtkGraphicsFactory(off_screen_only_mode=True, use_mesa_classes=True)

    imgVtk = numpy_to_vtk(img.data.ravel())

    # Create VTK Image Data
    vtk_img = vtkmodules.vtkCommonDataModel.vtkImageData()
    vtk_img.SetDimensions(img.shape[2], img.shape[1], img.shape[0])  # Z, Y, X to X, Y, Z
    imgVtk.SetName("Scalars")
    vtk_img.GetPointData().SetScalars(imgVtk)
    vtk_img.GetPointData().SetActiveScalars("Scalars")

    # To use a PolyDataMapper, we need to extract a surface (e.g., isosurface)
    contour = vtkmodules.vtkFiltersCore.vtkMarchingCubes()
    contour.SetInputData(vtk_img)
    contour.SetValue(0, threshold)  # Example threshold value

    # Create a mapper and actor.
    mapper = vtkPolyDataMapper()
    contour >> mapper

    actor = vtkActor(mapper=mapper)
    actor.property.color = colors.GetColor3d("White")

    # A renderer and render window.
    renderer = vtkRenderer(background=colors.GetColor3d("SlateGray"))
    render_window = vtkRenderWindow(off_screen_rendering=True)
    render_window.SetSize(1920, 1080)
    render_window.AddRenderer(renderer)

    # Add the actor to the scene.
    renderer.AddActor(actor)

    # Rotate the actor for a better perspective
    actor.RotateX(30)
    actor.RotateY(30)

    render_window.Render()

    window_to_image_filter = vtkWindowToImageFilter(input=render_window)
    window_to_image_filter.update()

    writer = vtkPNGWriter()
    writer.SetFileName(filename)
    window_to_image_filter >> writer
    writer.Write()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage:\npython {sys.argv[0]} <FILENAME.raw...>")  # noqa: T201
        print(f"You need to edit {sys.argv[0]} first!")  # noqa: T201
        sys.exit(1)

    filename = sys.argv[1]

    # Read 3d image
    # Tested against https://web.corral.tacc.utexas.edu/digitalporousmedia/DRP-384/Porous%20carbonate/Porous%20carbonate/Dry.tif
    img = ik.VxlImgU16(filename)
    #  img.cropD((0,0,100), (0,0,800))
    #  img.plotAll("plot_drp384")
    #  img.circleOut(img.nx//2, img.ny//2, 450, 'z', 20000)
    #  plot_img3(img, threshold=16000, filename='screenshot.png')

    plot_img3_contour_to_png(img, threshold=16000, filename="screenshot.png")
