# Agent Rules and Context

### Pod runs

The app may be run locally or as part of [image3kit/pods](https://github.com/image3kit/pods).

If run as part of [image3kit/pods](https://github.com/image3kit/pods), the Streamlit app is accessible at:

    http://localhost:47900/img3gui/

To restart the pod run:
make restartPodman

give pingap some time to propagate the changes!

For debugging run commands in img3gui container:
```bash
podman exec img3gui python -c "import image3kit; print(dir(image3kit))"
```
The root directory is mounted in podman, we can run the test script in podman img3gui container, well unless we change pnmkit which requires `make restartPodman`.

## Git Workflow
- **Do not amend commits**: Always create new commits for any incremental changes. Do not use `git commit --amend` or mutate previous commit histories, unless explicitely asked to do so.

## App Architecture and Development Notes
- **Working Directory**: The workspace working directory is changed to the `runs/` folder at startup in `app.py` to prevent code execution outputs from cluttering the root `/app` directory.

- **Image**: The app_func_img.py handles `.dat`, `.png`, `.am`, `.tif`/`.tiff`, and `.mhd`/`.raw` formats.

- **xdmf**: The app_func_net.py is used visualizing xdmf (.xmf) files using import pyvista as pv and stpyvista 
