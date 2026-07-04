## GUI and demos for pore-scale modelling codes

* Example python scripts for pore scale image processing and simulation.

* A streamlit-based dashboard for these pipelines.

The dashboard is work in progress: so far image3kit and pnmkit functioanlity are barely usable.

The scripts are high-level and primarily cli-based that writes files into disk. The lower-level logic (C++ or python packages) is/shall be usable both interactively from GUI as well as from the cli scripts, for replaying.

## Features

The GUI app consists of multiple tabs:

1. workflow (python) script editor tab
2. 2D visualization and interactive function executions tab
3. 3D visualization tab based on pyvista for vtk/xdmf and OpenFOAM (TODO) output files
4. log file browser tab
5. svg/png image viewer tab
6. TODO: workflow / task management


### workflow (python) script editor tab

* Python code editor with syntax highlighting, and image caching
    * So far VxlImg (and Xdmf?) objects are cached, 
    * TODO: do same for VTK/PyViz objects (Xdmf objects not usefull for visualization)


### 2D visualization and interactive function executions

### 3D visualization

* The third step is to create a 3D visualization widget based on vtk, both for 3D countour surfaces as well as the pnmkit/Xdmf stack files.

### Task manager (TODO)

TODO: The long-running workflows shall be launched in background with a lockfile that is used to monitor their pid and status. The task manager shall be used to view and cancel running workflows, also preventing same workflow from running twice. in the same directory.
For OpenFOAM, we need to run in containers/remotely, as they are not pip-installable.

### Log file browser

Copied the `app_logs.py` from [image3kit/difizui](https://github.com/image3kit/agui), needs to be adapted to image3kit.

### SVG/PNG image viewer

Copied the `app_plots.py` from [image3kit/difizui](https://github.com/image3kit/agui), needs to be adapted to image3kit.

---

## GUI local installation:

```bash
## PNMkit dependencies:
sudo apt-get install libboost-all-dev libopenmpi-dev openmpi-bin

## Set up virtual environment and install dependencies:
python -m venv .venv
# ⚠️ Uncomment pnmkit and pyvtk in requirements.txt
.venv/bin/python -m pip install -r requirements.txt
```

Run GUI:
```bash
.venv/bin/python -m streamlit run app.py
```
then open http://localhost:8501 in your browser

### Current Examples, see [./runs](./runs)

* [dering_segment.py](./runs/dering_segment.py)
    * Illustrates how to create new filters using NumPy: `desharpen` function
    * Illustrates use of dering filter (rather flimsy -- difficult to get its parameters right)
    * `segment2` function (do not use this in production, does not work well, unless you are willing to improve it!)
    * Plotting / screenshots

* run dering_segment.py from command line:
```bash
source .venv/bin/activate
cd runs
python  dering_segment.py  volume_467x1775x1480.raw
```

* [ik_vtk_utils.py](./runs/ik_vtk_utils.py)
    - Using VTK for offscreen 3D visualisation
    - For now you got to edit ik_vtk_utils.py and and set the threshold and filename
```bash
python  ik_vtk_utils.py  volume_467x1775x1480.am/NXxNYxNZ.raw
```

✅ You can lunch these from editor tab of the streamlit gui as well

### TODO

* Integrate with OpenFoam/GeoChemFoam ?
* More integration with XPM



### CONTRIBUTING

Please push your changes to a seperate branch and open a pull request or let me know somehow. You are also welcome to create a github issue for discussing/proposing changes or new features.

Before getting your hands dirty with code, check the other branches, in particular `wip/main`, which contains changes whose commit history is overwritten (via force push and rebase).

The repo is mostly vibe-coded and is in pre-release (pre-alpha) state, so expect bugs, and missing features.

<!-- References -->

[image3kit]: https://github.com/digiporflow/image3kit
