# porgui: URL contract, then JSON API

_Status: phase 1 partly done (2026-10-11)._

**Goal**: a porgui view can be reproduced from its URL, so docs, humans, agents and screenshot/smoke tests share one entry point. Later, the same operations are exposed as JSON for scripts and agents.

**Rules**
* GET is idempotent: a URL may select, load (cached) and view, never run or save. Run/Save stay buttons (or `POST` in phase 2).
* Keys are short, unique across pages (Streamlit widget keys are app-global), and match the widget `key=`.
* Paths are relative to `<workspace>/runs/` (the app's cwd).
* Bind with `bind="query-params"`. Plain `st.query_params.get` only for load-once params (`img`, `net`).

## Inventory

| Page | Bound now | Planned |
|---|---|---|
| `docs` | `doc`, `docq` | – |
| `editor` | `script` | `args` (CLI text box) |
| `image` | `img` (load), `axis`, `slice`, `imgfn` | `var`, `vmin`/`vmax`, function args `i_<arg>`, `out` |
| `network` | `net` (load), `netfn`, `scalar` | `var`, function args `n_<arg>` |
| `plots` / `logs` | `plot`, `plotq` / `log`, `logq`, `log_keep`, `log_remove` | – |
| `make` | `mk`, `mkq` | variables `mk_var_<VAR>` |

Example: `image?img=pakextr/extruded_240x200x28_5p0um.mhd&axis=Z&slice=14`

Load-once `img`/`net` and their pitfalls: [docs/url_params.md](../url_params.md).

## Phase 1: finish the URL contract
1. Function args: pass `bind=` through porgui's `render_parseargs` (`porgui/app_common.py`) to uiutils `forms.render_parseargs` (already supported), and add `bind=` to the custom widgets in `_render_porgui_param` (int3/float3, var/file/dir pickers). Key prefixes `i_` (image), `n_` (network), replacing `func_arg`/`net_func_arg`.
2. `var` selectors: bind the viewed-variable selectbox. A URL `var` that is not in the session falls back to the first variable.
3. `editor?args=`, `make` variables.
4. Smoke test: one playwright test per row above, opening the URL and checking the widget value (`tests/test_ui_smoke.py` pattern). `tests/make_screenshots.py` already drives `image?img=` and `network?net=`.

Open: a URL `slice` beyond the loaded image's range is untested; clamp it.

## Phase 2: JSON API (same server)
Streamlit ≥1.57 ships `streamlit.starlette.App(script, routes=[...])`, which adds Starlette routes on the same port. pingap's `/porgui` path and OAuth then cover the API too.

| Route | Returns |
|---|---|
| `GET /api/files?glob=` | files under `runs/` |
| `GET /api/functions?kind=image\|network` | names, params, docs (`CURATED_METHODS`) |
| `POST /api/run {fn, input, args}` | `{stdout, code, result, url}`, where `url` is the phase-1 link to view the result |

* Service layer: `app_presenters.py` / `app_state.py` (no Streamlit imports), with a server-side `Workspace` instead of `st.session_state`.
* Launch: `porgui/__main__.py` and the compose `command` switch from `streamlit run` to `uvicorn porgui.asgi:app`. Check the `--server.baseUrlPath=/porgui` equivalent.
* Open: is state per-session (needs a session id) or per-workspace? Do long runs block (subprocess, like the editor)? Large images move as file paths, never in JSON.

## Deployments to keep working
* Host: `porgui --serve [--workspace DIR]`, or `python -m streamlit run porgui/app.py` from the repo.
* infra/compose service `porsmgui`: code is baked into the image, only `runs/` is mounted, base path `/porgui`.
