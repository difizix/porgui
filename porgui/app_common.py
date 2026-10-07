import glob
import inspect
import os

import app_presenters as presenters
import streamlit as st
from app_state import SessionStore, Workspace
from uiutils.streamlit.forms import render_param
from uiutils.streamlit.forms import render_parseargs as _render_parseargs
from utils_app import get_output_files

OBJECT_DROPDOWN_TYPE_NAMES = ("VxlImgU16", "VxlImgU8", "VxlImgI32", "VxlImgF32", "VxlImg", "PolyData", "UnstructuredGrid")

NONE_OPTION = "(none)"


def refresh_outputs():
    """Re-scan the plots and logs under runs/, e.g. after a script may have written new ones."""
    st.session_state.png_files, st.session_state.log_files = get_output_files()


class StreamlitStore(SessionStore):
    """SessionStore bound to the live st.session_state.

    st.session_state is itself a MutableMapping, so the base class can wrap it
    directly and writes land in the real session.
    """

    def __init__(self):
        super().__init__(st.session_state)


def get_workspace() -> Workspace:
    """The Workspace for this session, created once and reused across reruns.

    Workspace keeps no state of its own beyond the store, so rebuilding it on a
    rerun is harmless - it re-attaches to the same session_state keys.
    """
    return Workspace(StreamlitStore())


def image_wrappers() -> dict:
    """Map each unpatched C++ image class to the caching subclass on ik.

    app.py rebinds ik.VxlImg* to caching subclasses; results coming back from
    image3kit are plain _core.voxlib instances, so they get re-wrapped through
    this map to stay the caching kind. VoxelImagesBase is deliberately absent:
    it is the common base of all four and would match everything.
    """
    import image3kit as ik

    store = get_workspace().store
    pairs = (
        (store.get("original_VxlImgU16"), ik.VxlImgU16),
        (store.get("original_VxlImgU8"), ik.VxlImgU8),
        (store.get("original_VxlImgI32"), ik.VxlImgI32),
        (store.get("original_VxlImgF32"), ik.VxlImgF32),
    )
    return {base: wrapper for base, wrapper in pairs if base is not None}


def get_presenter(wrappers=None) -> presenters.ExecutionPresenter:
    if wrappers is None:
        wrappers = image_wrappers()
    return presenters.ExecutionPresenter(get_workspace(), wrappers=wrappers)


# Both kept as thin wrappers over the framework-free implementations so the
# existing call sites (and the OBJECT_DROPDOWN_TYPE_NAMES default) keep working.
def is_object_dropdown_type(type_val):
    return presenters.is_object_dropdown_type(type_val, OBJECT_DROPDOWN_TYPE_NAMES)


def resolve_object_args(args_dict, params_meta, workspace_vars):
    return presenters.resolve_object_args(
        args_dict, params_meta, workspace_vars, OBJECT_DROPDOWN_TYPE_NAMES
    )

def _render_porgui_param(param, widget_key):
    """render_param plus porgui's own types: int3/dbl3, workspace objects, file/case/type dropdowns, dict."""
    p_name = param.name
    default = param.default
    type_val = param.type_val
    help_text = param.help_text
    if param.is_iterable or type_val in (bool, int, float):
        return render_param(param, widget_key)
    if type_val in ("int3", "dbl3"):
        st.write(f"**{p_name}**")
        sub_cols = st.columns(3)
        
        def_vals = [0, 0, 0]
        if default is not None:
            try:
                if isinstance(default, (list, tuple)):
                    def_vals = [float(x) if type_val == "dbl3" else int(x) for x in default]
                elif hasattr(default, "x"):
                    def_vals = [default.x, default.y, default.z]
                else:
                    import re
                    nums = re.findall(r"[-+]?\d*\.?\d+", str(default))
                    if len(nums) == 3:
                        def_vals = [float(x) if type_val == "dbl3" else int(x) for x in nums]
            except Exception:
                pass
        
        if len(def_vals) < 3:
            def_vals = (def_vals + [0, 0, 0])[:3]
        
        val_x = sub_cols[0].number_input("X", value=int(def_vals[0]) if type_val == "int3" else float(def_vals[0]), step=1 if type_val == "int3" else 0.1, key=f"{widget_key}_x")
        val_y = sub_cols[1].number_input("Y", value=int(def_vals[1]) if type_val == "int3" else float(def_vals[1]), step=1 if type_val == "int3" else 0.1, key=f"{widget_key}_y")
        val_z = sub_cols[2].number_input("Z", value=int(def_vals[2]) if type_val == "int3" else float(def_vals[2]), step=1 if type_val == "int3" else 0.1, key=f"{widget_key}_z")
        
        if type_val == "int3":
            return [int(val_x), int(val_y), int(val_z)]
        return [float(val_x), float(val_y), float(val_z)]
    if is_object_dropdown_type(type_val):
        # Figure out the target type name as a string
        target_type_str = ""
        if isinstance(type_val, str):
            for possible in OBJECT_DROPDOWN_TYPE_NAMES:
                if possible in type_val:
                    target_type_str = possible
                    break
        elif inspect.isclass(type_val):
            name = type_val.__name__
            for possible in OBJECT_DROPDOWN_TYPE_NAMES:
                if possible in name:
                    target_type_str = possible
                    break

        # Get acceptable classes
        vxl_types = tuple(
            getattr(st.session_state, name) for name in (
                "original_VxlImgU16", "original_VxlImgU8",
                "original_VxlImgI32", "original_VxlImgF32"
            ) if hasattr(st.session_state, name)
        )

        # Filter workspace variables based on target type
        var_options = []
        for k, v in st.session_state.workspace_vars.items():
            if target_type_str and "VxlImg" in target_type_str:
                if target_type_str == "VxlImg":
                    if isinstance(v, vxl_types):
                        var_options.append(k)
                else:
                    orig_attr = f"original_{target_type_str}"
                    if hasattr(st.session_state, orig_attr):
                        orig_cls = getattr(st.session_state, orig_attr)
                        if isinstance(v, orig_cls):
                            var_options.append(k)
            elif target_type_str:
                v_type_name = type(v).__name__
                if target_type_str in v_type_name:
                    var_options.append(k)
            else:
                var_options.append(k)

        is_optional = p_name != "self" and default is None
        if is_optional:
            var_options = [NONE_OPTION] + var_options

        if not var_options:
            st.warning(f"No compatible variables of type '{target_type_str or 'any'}' found in workspace.")
            return ""
        # Choose default
        default_sel = NONE_OPTION if is_optional else default
        if default_sel not in var_options:
            active_var = st.session_state.get("active_var")
            net_active = st.session_state.get("net_active_var_selectbox")
            if active_var in var_options:
                default_sel = active_var
            elif net_active in var_options:
                default_sel = net_active
            else:
                default_sel = var_options[0]
        default_idx = var_options.index(default_sel)
        val = st.selectbox(p_name, var_options, index=default_idx, key=widget_key, help=help_text)
        return "" if val == NONE_OPTION else val
    if type_val in ("img_dropdown", "file_dropdown"):
        extensions = ["*.tif", "*.tiff", "*.am", "*.png", "*.mhd", "*.dat", "*.raw", "*.raw.gz", "*.npy", "*.npz"]
        found_files = []
        for ext in extensions:
            found_files.extend(glob.glob(ext))
            found_files.extend(glob.glob(f"*/{ext}"))
        found_files = sorted(set(found_files))
        if not found_files:
            st.warning("No compatible files found in runs/ directory.")
            return ""
        default_idx = found_files.index(default) if default in found_files else 0
        val = st.selectbox(p_name, found_files, index=default_idx, key=widget_key, help=help_text)
        return val
    if type_val == "xmf_dropdown":
        found_files = []
        for ext in ["*.xmf", "*.xdmf"]:
            found_files.extend(glob.glob(ext))
            found_files.extend(glob.glob(f"*/{ext}"))
        found_files = sorted(set(found_files))
        if not found_files:
            st.warning("No .xmf files found in runs/ directory.")
            return ""
        default_idx = found_files.index(default) if default in found_files else 0
        val = st.selectbox(p_name, found_files, index=default_idx, key=widget_key, help=help_text)
        return val
    if type_val == "case_dropdown":
        found_dirs = sorted([d for d in os.listdir(".") if os.path.isdir(d) and not d.startswith(".")])
        if not found_dirs:
            st.warning("No case directories found in runs/ directory.")
            return ""
        default_idx = found_dirs.index(default) if default in found_dirs else 0
        val = st.selectbox(p_name, found_dirs, index=default_idx, key=widget_key, help=help_text)
        return val
    if type_val == "type_dropdown":
        type_options = ["VxlImgU16", "VxlImgU8", "VxlImgI32", "VxlImgF32"]
        default_idx = type_options.index(default) if default in type_options else 0
        val = st.selectbox(p_name, type_options, index=default_idx, key=widget_key, help=help_text)
        return val
    if type_val is dict:
        default_str = str(default) if default is not None else "{}"
        val = st.text_input(p_name, value=default_str, key=widget_key, help=help_text)
        try:
            parsed_val = eval(val) if val.strip() else {}
            if isinstance(parsed_val, dict):
                return parsed_val
            st.error(f"{p_name} must be a dictionary.")
            return {}
        except Exception:
            st.error(f"Invalid dictionary format for {p_name}.")
            return {}
    else:
        return render_param(param, widget_key)


def render_parseargs(params, key_prefix="", num_cols=2):
    return _render_parseargs(params, key_prefix, num_cols, render=_render_porgui_param)
