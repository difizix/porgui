# Agent Rules and Context

## App URI

### Local runs
If run locally, the default Streamlit URI:port is:

    http://localhost:8501/img3gui

### Pod runs

The app may be run locally or as part of [image3kit/pods](https://github.com/image3kit/pods).

If run as part of [image3kit/pods](https://github.com/image3kit/pods), the Streamlit app is accessible at:

    http://localhost:47900/img3gui/

To restart the pod run of the app:
```bashrc
podman rm -f img3gui ; podman-compose -f ../pods/compose/docker-compose.yml up -d --build img3gui
```

give pingap some time to propagate the changes!

For debugging run commands in img3gui container:
```bash
podman exec img3gui python -c "import image3kit; print(dir(image3kit))"
```

## Git Workflow
- **Do not amend commits**: Always create new commits for any incremental changes. Do not use `git commit --amend` or mutate previous commit histories, unless explicitely asked to do so.

## App Architecture and Development Notes
- **Working Directory**: The workspace working directory is changed to the `runs/` folder at startup in `app.py` to prevent code execution outputs from cluttering the root `/app` directory. Keep this in mind when specifying paths.
- **File Format Support**: The app handles `.dat`, `.png`, `.am`, `.tif`/`.tiff`, and `.mhd`/`.raw` formats.
