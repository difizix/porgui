# PorGUI: GUI and demos for pore-scale codes

* Example python scripts for pore scale image processing and simulation.

* A streamlit-based dashboard for these pipelines.

The scripts are high-level and primarily CLI-based scripts that write files to disk. The lower-level logic (C++ or python packages) is/shall be usable both interactively from GUI as well as from the CLI scripts, for replaying.

> [!WARNING]
> * **Experimental:** Unstable, main branch will be overwritten.
>     * If you have made no changes, clone again!, or run `git fetch origin && git checkout FETCH_HEAD` followed by `git switch -C main` to update you local repo.
> * **Experimental:** So far [image3kit] and [pnmkit] functionality are barely usable.
> * Unpublished external dependencies.
> * Demos may be moved out of this repo, they are web-UI compatible but commandline-first

See Makefile for instructions on injecting the snm standalone apps to the docker container, while it is running.

## Features

The GUI app consists of multiple tabs:

1. **💻 Workflow Editor** 📝 ⭐⭐: Python script editor with syntax highlighting, live execution, and image caching
2. **🖼️ Image Processing** 🖼️ ⭐⭐⭐ *(Core)*: 2D slice visualization and interactive image3kit function execution
3. **🌐 Network Analysis** 🧊 ⭐⭐⭐ *(Core)*: 3D visualization (pyvista) for VTK/XDMF/network models and pnmkit/xpm analysis
4. **📊 Saved Plots** 🎨 ⭐⭐: SVG/PNG image viewer for generated plots and screenshots
5. **📄 Log Files** 📄 ⭐: Output log file browser and inspector

### 💻 Workflow Editor tab

* Python code editor with syntax highlighting, and image caching
    * So far VxlImg (and Xdmf?) objects are cached, 
    * TODO: do same for VTK/PyViz objects (Xdmf objects not useful for visualization)

### 🖼️ Image Processing (2D visualization and interactive functions)

* Interactive 2D slice visualizer and testing bench for `image3kit` functions.

### 🌐 Network Analysis (3D visualization)

* 3D visualization widget based on pyvista/vtk, both for 3D contour surfaces as well as pnmkit/Xdmf network files.

### Task manager (TODO)

TODO: The long-running workflows shall be launched in background with a lockfile that is used to monitor their pid and status. The task manager shall be used to view and cancel running workflows, also preventing same workflow from running twice in the same directory.
For OpenFOAM, we need to run in containers/remotely, as they are not pip-installable.

### 📄 Log file browser

Copied the `app_logs.py` from [difizix/difgui](https://github.com/difizix/difgui), needs to be adapted to image3kit.

### 📊 Saved Plots (SVG/PNG image viewer)

Copied the `app_plots.py` from [difizix/difgui](https://github.com/difizix/difgui), needs to be adapted to image3kit.

---

## Quick start (pip install, no manual clone, your own runs/*.py scripts)

```bash
# activate a venv, then run:
pip install git+https://github.com/difizix/porgui.git
porgui --serve
```
This opens `http://localhost:8501` in your browser automatically. Use
`porgui --serve --port 8080` / `--host 0.0.0.0` / `--workspace /path/to/project` to
change the port, bind address, or the directory `runs/` (outputs, logs, plots) is
created under (defaults to the current directory). `python -m porgui --serve` works
the same way.

> [!NOTE]
> Add your own scripts to the `runs` folder, see git repository's [./runs](./runs) folder for examples.

Note: `pip install porgui` is intentionally minimal and does not require `vtk`,
`pyvista`/`stpyvista`, or `pnmkit`/`snm`/`xpm`:
* Without `pyvista`/`stpyvista`, the **Network Analysis** tab shows a message telling
  you to install them instead of loading (3D visualization needs pyvista). Run
  `pip install "porgui[dev] @ git+https://github.com/difizix/porgui.git"` to pull in
  `vtk`, `pyvista`, `stpyvista` and the other optional extras.
* With `pyvista` installed but without `pnmkit`, the Network Analysis tab loads
  normally, but functions that need `pnmkit` (`mextract`, `snflow`) show a message
  telling you to install it manually — `pnmkit`/`snm`/`xpm` are never pip extras (see
  below for the dev checkout).

## Docker installation
See Makefile for full instructions. In short, run the following commands to build and run the docker/podman container:

```bash
# cd PATH/TO/porgui
PODMAN=docker # or =podman
${PODMAN} build -t porsmgui -f Dockerfile .
${PODMAN} run -v $PWD:/app:z -p 8501:8501 --rm --name porsmgui porsmgui
```

## GUI local installation (for dev, including pnmkit/snm/xpm):

```bash
## PNMkit dependencies:
sudo apt-get install libboost-all-dev libopenmpi-dev openmpi-bin

## Set up virtual environment and install dependencies:
python -m venv .venv
.venv/bin/python -m pip install -e .
```

For installing XPM `core` branch, run:

```bash
git clone https://github.com/difizix/xpm
.venv/bin/python -m pip install ./xpm
```

Run GUI:
```bash
.venv/bin/python -m streamlit run porgui/app.py
```
then open http://localhost:8501 in your browser


> [!NOTE]
> **XPM Built-in Viewers**:
> XPM includes its own specialized viewers tailored for 3D displacement monitoring and HPC workloads:
> - **Remote Web Viewer** `scripts/serve_xpm_viewer_artifact.py`: A zero-dependency, WebGL-based browser UI for remote HPC/Slurm jobs (e.g. ARCHER2) via SSH tunnel `scripts/slurm/submit_xpm_viewer_artifact_server.sh`, supporting time-scrubbed invasion percolation playback, dynamic $P_c$ / $k_r$ curve synchronization, and dual-continuum (macro + Darcy microporosity) visualization.
> - **Native Desktop GUI** (`xpm -V`): Qt6/VTK-based viewer for local datasets.
> 
> See the [xpm]'s  `docs/XPM_VIEWER_USER_GUIDE.md` and `scripts/slurm/README.md` for full instructions.
>
> In contrast, this repo is primarily targeted for learning and experimentation. Production workflows are typically run via commandline.

## Current Examples, see [./runs](./runs)

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
    - For now you got to edit ik_vtk_utils.py and set the threshold and filename
```bash
python  ik_vtk_utils.py  volume_467x1775x1480.am/NXxNYxNZ.raw
```

✅ You can launch these from editor tab of the streamlit gui as well

### TODO

* Integrate with OpenFOAM/GeoChemFoam ?
* More integration with XPM



### CONTRIBUTING

Please push your changes to a separate branch and open a pull request or let me know somehow. You are welcome to create a github issue for discussing/proposing changes or new features too.


<!-- References -->

[image3kit]: https://github.com/DigiPorFlow/image3kit
[pnmkit]: https://github.com/difizix/pnmkit
[xpm]: https://github.com/difizix/xpm
