# Agent Rules and Context

## App URI
The main developer runs the app as part of [image3kit/pods](https://github.com/image3kit/pods) and the Streamlit app is accessible at:

    http://localhost:47900/img3gui/

If run locally, the default Streamlit URI:port is:

    http://localhost:8501/img3gui


To restart the app:
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
- **Streamlit Slider Safeguards**: Always guard sliders from value boundary constraints. Check for conditions where `min_value == max_value` (e.g., single-slice dimension size `max_slice <= 0` or constant value contrast ranges `data_min >= data_max`) and fall back to safe read-only elements or custom layouts.
- **Image Aspect Ratio & Sizing**: Avoid converting large slice images to base64 strings to prevent performance overhead. Instead, use native `st.image` widgets and style them via the global CSS stylesheet (specifically target `div[data-testid="stImage"] img` with custom `max-height` limits and `object-fit: contain`).