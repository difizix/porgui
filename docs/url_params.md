# URL parameters: load-once `img`, `net`

`image?img=<path>` and `network?net=<path.xmf>` open a page with a file loaded and shown. Paths are relative to `runs/`. Example: `image?img=pakextr/extruded_240x200x28_5p0um.mhd&axis=Z&slice=14`.

They are read by `_load_url_image` (`porgui/app_func_img.py`) and `_load_url_network` (`porgui/app_func_net.py`), before the page's widgets:
* Once per path per session (`session_state._url_img` / `_url_net`), otherwise every rerun would force the URL file back into view.
* The variable is named after the file (stem up to the first dot) and loaded only if that name is free. The view switches to it through `pending_active_var` (image) or the selectbox key (network).
* GET-safe: they only load and view, never write.

## Pitfalls
* **Stale URL**: `?img=` stays after you pick another variable. It is not a two-way binding like `axis`; fix by binding the variable picker as `var`.
* **No retry**: the marker is set before loading, so a failed load shows its error once and is not retried in that session.
* **Name clash**: `x.mhd` and `x.raw.gz` map to the same variable `x`; the second shows the first.
* **Header-less files**: e.g. `extruded_pores_*.raw.gz` loads with a guessed type (all black). Link to `.mhd`/`.am`/`.tif`.
* **Default values drop out**: `axis=Z` (the default) is removed from the URL, so a copied link omits it. Harmless while defaults don't change.

Roadmap (bind all inputs, then a JSON API): [plans/rest_api.md](plans/rest_api.md).
