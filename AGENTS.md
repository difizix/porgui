# Agent Rules and Context

## General Guidlines

Do not be rock headed: first try to understand the human request and interactions then create a plausible plan that quickly gets the issues resolved rather than getting stuck in an endless loop of tool usage. Once a while revisit your plan and revise if it takes too many iterations of tool usage.

## Deployment

The app may be run locally or as part of [difizix/infra](https://github.com/difizix/infra).

It is cloned somewhere and symlinked to ./infra for reference, see ./infra/compose/docker-compose.yml and ./infra/compose/pingap_config.toml.

If run as part of [difizix/infra](https://github.com/difizix/infra), the Streamlit app is accessible at:

    http://localhost:27900/porgui/

To restart the pod run: `make restartPodman`

After `make restartPodman`, wait for 20+ seconds for the changes to propagate!

For debugging run commands in porsmgui container, e.g.:
```bash
podman exec porsmgui python -c "import image3kit; print(dir(image3kit))"
```
The root directory is mounted in podman, we can run the test script in podman porsmgui container, well unless we change pnmkit which requires `make restartPodman`.

-------

## Git Workflow
- **Do not amend commits**: Do not use `git commit --amend` or mutate previous commit histories, unless explicitely asked to do so.

-------

## App Architecture and Development Notes
- **Working Directory**: The workspace working directory is changed to the `runs/` folder at startup in `porgui/app.py` to prevent code execution outputs from cluttering the root `/app` directory.

- **Image**: The `porgui/app_func_img.py` is primarily used for interacting with individual image3kit functions, try-error, experimenting and understanding its API using a GUI.

- **Net/xdmf**: The `porgui/app_func_net.py` is used interacting with xpm and snm git modules, and visualizing xdmf (.xmf) files using import pyvista as pv and stpyvista 


- **Local repos**: The image3kit, xpm, snm, pnmkit git repositories are cloned locally, for reference, and gitignored. pnmkit is a wrapper around xpm and snm executables, and in future, openfoam simulation and pre-post-processing too.

- **Run dir**: Here we keep what which shall be edited and re-run through ui app. Note these are meant to be usable as both standalone apps as well as runnable through the workflow editor. We shall continue to maintain a list of python utilities in `porgui/toolbox/__init__.py` to be importd and used in runs/*.py files, keeping anything in runs/*.py as high-level as possible. In future we will allow streamlit ui to also auto discover files from runs/toolbox/ as well.  As we mature codes in run/*.py, we can make them reusable and move them to the /toolbox/ and if they are stable and widely usable they can get promoted tobe part of `porgui/toolbox/` or the pnmkit or image3kit repos.

-------

## Coding Standards

- **Find and Fix Root Causes**: 
  When fixing imports, exceptions, or unexpected behavior, address the issue at its true origin (e.g., package `__init__.py`, module exports, or build configuration). Do NOT add quick-fix patches at call sites (e.g., modifying `sys.path` in individual script files or swallowing errors).
- **Minimal & Surgical Diffs**: 
  Modify only the lines necessary to fulfill the request. Preserve existing formatting, comments, and code structure. Do not rename functions, refactor unrelated modules, or add unsolicited wrapper abstractions ("future-proofing").
- **Verify Before Calling APIs**: 
  Always inspect actual source code (in local repos `image3kit`, `xpm`, `snm`, `pnmkit`, or `porgui/toolbox/`) using `grep_search` or `view_file` to confirm signatures, argument names, and types before using them. Never guess or fabricate function signatures.
- **Empirical Runtime Verification**: 
  Never declare a task resolved without running actual verification commands (e.g., via `podman exec porsmgui python ...` or running test scripts). Base completion strictly on empirical execution output.
- **One Step at a Time**: 
  For multi-file or multi-step tasks, make incremental changes and verify each step before proceeding to the next.
- **State Uncertainty Plainly**: 
  If requirements, API behaviors, or design choices are ambiguous, explicitly state the uncertainty and clarify rather than making speculative assumptions.
- **Modern Python Syntax**: 
  Use standard modern Python idioms, such as `pathlib.Path` instead of `os.path` for file path operations, and proper type annotations.