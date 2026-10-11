# AGENTS.md

Guide for coding agents and developers working on porgui. User-facing docs: [README.md](README.md) and the in-app Home page ([porgui/docs/index.md](porgui/docs/index.md)).

## Layout

| Path | Role |
|---|---|
| `porgui/app.py` | Entry script: chdir to `<workspace>/runs`, image caching, `PAGES` (url_path → page) |
| `porgui/app_editor.py` | Workflow Editor page (`editor`) |
| `porgui/app_func_img.py` | Image Processing page (`image`) |
| `porgui/app_func_net.py` | Network Analysis page (`network`) |
| `porgui/app_presenters.py`, `app_state.py` | Logic and session state, no widgets; unit-tested |
| `porgui/app_common.py`, `utils_app.py` | Shared widget/form helpers |
| `porgui/toolbox/` | Functions for `runs/*.py` and the function forms |
| `porgui/docs/` | User docs, shown on the Home page (packaged) |
| `docs/` | Developer docs (`url_params.md`, `security.md`, `plans/`) and README screenshots (`img/`) |
| `runs/` | Example workflow scripts; all outputs are written here |
| `tests/` | pytest; `test_ui_smoke.py` and `make_screenshots.py` drive a live app with playwright |

Docs, Plots, Logs and Make pages come from [uiutils](https://github.com/difizix/uiutils). Fix shared behaviour there, not here.

## Run

* Host: `porgui --serve [--workspace DIR]`, or `python -m streamlit run porgui/app.py` from the repo root.
* infra/compose (service `porsmgui`, served at `/porgui/`): code is baked into the image and only `runs/` is mounted, so rebuild after code changes. snm/xpm are installed by `porgui/deps.mk`: from the Make page (which falls back to `deps.mk` when the workspace has no Makefile) or `make injectSnm` / `injectXpm` from the host. Installs into the container are lost when it is recreated.
* `make runPodman`: standalone container with the repo bind-mounted at `/app`.

## Conventions

* URL state: bind selections with `bind="query-params"`; keys are short and unique across pages. Loading from a URL must be idempotent. Load-once params and their pitfalls: [docs/url_params.md](docs/url_params.md).
* Docs are brief, link to pages with in-app routes (`[Open](image?img=...)`), and never restate code. Script usage belongs in the `runs/*.py` docstring.
* Keep `runs/*.py` high-level and runnable both from the CLI and from the editor. Move stable helpers to `porgui/toolbox/`, then to pnmkit/image3kit.

## Rules

* Minimal, surgical diffs; fix root causes (no call-site `sys.path` hacks or swallowed errors).
* Check signatures in the source (image3kit, pnmkit, toolbox) before calling an API.
* Verify by running: `pytest`, the app itself, or `podman exec porsmgui python ...`.
* No commit amends or history rewrites unless asked.
