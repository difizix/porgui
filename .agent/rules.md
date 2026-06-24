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