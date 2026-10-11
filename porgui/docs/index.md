# PorGUI

Browser workbench for pore-scale images and networks: try [image3kit](https://github.com/DigiPorFlow/image3kit) functions on a slice, extract and view pore networks ([pnmkit](https://github.com/difizix/pnmkit)), and run the `runs/*.py` workflow scripts that produce them.

The main selections (script, file, function, slice) are kept in the URL, so a link reproduces a view.

## Pages

* **Workflow Editor**: edit and run `runs/*.py`, output streamed live. [Open](editor?script=pnm_from_extrude.py)
* **Image Processing**: slice viewer and form for any image3kit function. [Open](image?img=pakextr/extruded_240x200x28_5p0um.mhd&axis=Z)
* **Network Analysis**: 3D view of `.xmf` networks, pnmkit functions. [Open](network?net=pakextr/extruded_ms.xmf)
* **Saved Plots**, **Log Files**: outputs found under `runs/`. [Plots](plots?) [Logs](logs?)
* **Make**: Makefile targets with editable `?=` variables. [Open](make?)

## Example: 2D image → 3D network → flow

1. Run `pnm_from_extrude.py`: extrudes a 2D image to 3D, extracts the network, runs two-phase flow (`runs/pakextr/`). [Editor](editor?script=pnm_from_extrude.py)
2. View the extruded image. [Image](image?img=pakextr/extruded_240x200x28_5p0um.mhd&axis=Z&slice=14)
3. View the network. [Network](network?net=pakextr/extruded_ms.xmf)

Image and network links load files on first open; links that point at missing outputs show an error until step 1 has been run.
