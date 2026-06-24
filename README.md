## GUI app

* A GUI for image3kit and pnmkit in order to make them easier to use

The image3kit has been a cmd-based app that writes files into disk. It works by running a non-interactive script (e.g. runs/workflow.py). The idea is to create a GUI for it, in a way it can be used interactively for building up the workflow script, if needed save it as a python script, edit and replay it whenever needed.

The idea is to create a minimal one based on the dering_segment.py workflow. The img variable needs to be cached (persistant between different GUI actions).

The GUI app consists of multiple tabs:

1. workflow (python) script editor tab
2. 2D visualization and interactive function executions tab
3. 3D visualization tab (TODO for later)
4. task manager tab (TODO for later)
5. log file browser tab (TODO for later)
6. svg/png image viewer tab (TODO for later)


### workflow (python) script editor tab
Widgets:
* Python code editor with syntax highlighting, and image caching utilities
    * TODO write a global a function for reusing cached image variables, ideally we need a function named get_load_image() that returns the loaded image object and caches it in the session state if not already cached. A thin right-hand side column shall show all the cached variables, including image size.

    * The img variable shall be defaulted to the first cached variable that is of VoxelImage type (currently named img), but a drop down shall allow the user to select any cached variable of VoxelImage type.


### 2D visualization and interactive function executions tab:

I want a generic function arg visualizer, for the Interactive visualizer tab, for so that it can be used to visualize the arguments of any class member function, and a button to run it. In this app it shall be used to visualize the arguments of a selection of functions of image3kit and pnmkit, selected by the user (from a drop-down menu). The arguments shall be displayed below the dropdown, and the user can change the arguments, and then click a button to run the function. The commands run shall be saved in a sesstion string and be viewable in the python editor widget.

This shall also include a name for the output of the function (if it is an image, it shall be added to the cached variables).

We may need to improve the type hints of the image3kit and pnmkit to allow the general function arg visualizer to work properly.


### 3D visualization tab (TODO for later)

* The third step is to create a 3D visualization widget based on vtk, both for 3D countour surfaces as well as the pnmkit/Xdmf stack files.

### Task manager tab (TODO for later)

forget this for now!
The workflows shall run in background with a lockfile that is used to monitor their pid and status. The task manager shall be used to view and cancel running workflows, also preventing same workflow from running twice. in the same directory.

### Log file browser tab (TODO for later)

I have copied the `app_logs.py` from [image3kit/agui](https://github.com/image3kit/agui), needs to be adapted to image3kit.

### SVG/PNG image viewer tab (TODO for later)

I have copied the `app_plots.py` from [image3kit/agui](https://github.com/image3kit/agui), needs to be adapted to image3kit.

---

## Command-line usage

* Setup venv:
```
python -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

### Current Examples

* [dering_segment.py](./dering_segment.py)
    * Illustrates how to create new filters using NumPy: `desharpen` function
    * Illustrates use of dering filter (rather flimsy -- difficult to get its parameters right)
    * `segment2` function (do not use this in production, does not work well, unless you are willing to improve it!)
    * Plotting / screenshots

* run dering_segment.py:
```
.venv/bin/python  dering_segment.py  volume_467x1775x1480.raw
```

* [ik_vtk_utils.py](./ik_vtk_utils.py)
    - Using VTK for offscreen 3D visualisation
    - For now you got to edit ik_vtk_utils.py and and set the threshold and filename
```
python  ik_vtk_utils.py  <IMAGE_NAME>.am/_NXxNYxNZ.raw/.tif/.mhd
```

### TODO

* Integrate with OpenFoam/GeoChemFoam

### CONTRIBUTING

Please let me know beforehand and I will make this repo more professional.

The `image3kit` pip package lacks proper documentation, but you can clone the [image3kit] repository and use LLMs for help!



> [!CAUTION]
> The original author will submit draft commits to the `main` branch directly, and overwrites the git history!, unless someone else starts pushing git commits.


<!-- References -->

[image3kit]: https://github.com/digiporflow/image3kit
