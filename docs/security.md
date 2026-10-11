# Security

porgui is a single-user (or trusted-team) workbench. **Do not expose it, or its container, to the public internet.** Anyone who can open the page can run arbitrary code as the server's user, which is root in the container, and there is no isolation between users.

Run it on `localhost` (the `porgui --serve` default), over an SSH tunnel, or behind an authenticating proxy that admits only trusted people (infra/compose: pingap OAuth on `/porgui`).

## Code execution by design
* **Workflow Editor**: saves and runs Python scripts. They run inside the Streamlit server process (`exec` in `app_presenters.py`), so a script can read every session's state, environment variables and mounted files.
* **Make page**: runs any target of the workspace Makefile or `porgui/deps.mk`. Variable values are passed to `make` unchecked and can carry shell code. `installSnm`/`installXpm` clone and build code from `SNM_GIT`/`XPM_GIT`, which any user can change.
* **Function forms**: dict-typed arguments are parsed with `eval()` (`app_common.py`), and so are defaults read from docstrings (`utils_app.py`).

## No user isolation
* All sessions share one process, one working directory (`runs/`), one image cache and one set of installed tools. Users can read, overwrite or delete each other's outputs, and a run started by one user (e.g. `make`) affects everyone.
* The app has no login or roles of its own; access control is entirely the proxy's job.

## Files and paths
* Paths in URL parameters (`?img=`, `?net=`, `?doc=`) and file pickers are not confined to `runs/`. A crafted link can open any file the server can read.
* Uploads are written to `runs/` under the client-supplied file name, overwriting any existing file of that name.
* The container runs as root. Its bind mounts are `runs/` in compose, and the whole repo in `make runPodman`, so they are writable from the GUI.

## Network exposure
* `make runPodman` publishes `-p 8501:8501` on all interfaces, not just localhost. Use `-p 127.0.0.1:8501:8501` on shared or public networks.
* `porgui --serve --host 0.0.0.0` makes the app reachable from the network with no authentication.

## Supply chain
* Dependencies are installed unpinned from git branches (`image3kit@wip/main`, `pnmkit@wip/main`, `uiutils` default branch) and from PyPI.
* The docs page loads mermaid from a CDN at view time, with `securityLevel: 'loose'`, and markdown is rendered with raw HTML allowed. Treat docs and markdown reports from untrusted sources as untrusted HTML.

## Secrets
* Values typed on the Make page (e.g. a token inside `SNM_GIT`) appear in the shown command, the console log and the process list.
* Keep `.env`, SSH keys and tokens out of the mounted directories. Anything mounted is readable by code run from the GUI.

## Resources
* Large images, builds and simulations have no quotas or timeouts. One user can exhaust the CPU, memory or disk of the host.
