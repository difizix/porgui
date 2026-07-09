import inspect
import streamlit as st
import os
import glob

def render_parseargs(params, key_prefix="", num_cols=2):
    args_dict = {}
    if not params:
        return args_dict

    cols = st.columns(num_cols)
    for idx, param in enumerate(params):
        col = cols[idx % num_cols]
        p_name = param.name
        default = param.default
        has_default = param.has_default
        is_iterable = param.is_iterable
        type_val = param.type_val
        help_text = getattr(param, "help_text", "")
        widget_key = f"{key_prefix}_{p_name}"

        with col:
            if is_iterable:
                default_str = ""
                if has_default and default:
                    if isinstance(default, (list, tuple)):
                        default_str = "\n".join(str(d) for d in default)
                    else:
                        default_str = str(default)
                val = st.text_area(
                    p_name,
                    value=default_str,
                    key=widget_key,
                    help=help_text
                )
                args_dict[p_name] = [line.strip() for line in val.split("\n") if line.strip()]
            elif type_val is bool:
                val = st.checkbox(p_name, value=bool(default), key=widget_key, help=help_text)
                args_dict[p_name] = val
            elif type_val in (int, float):
                if type_val is int:
                    try:
                        val_default = int(default)
                    except (ValueError, TypeError):
                        val_default = 0
                    val = st.number_input(p_name, value=val_default, step=1, key=widget_key, help=help_text)
                else:
                    try:
                        val_default = float(default)
                    except (ValueError, TypeError):
                        val_default = 0.0
                    val = st.number_input(p_name, value=val_default, step=0.1, key=widget_key, help=help_text)
                args_dict[p_name] = val
            elif type_val == "var_dropdown":
                var_options = list(st.session_state.workspace_vars.keys())
                if not var_options:
                    st.warning("No variables found in workspace.")
                    args_dict[p_name] = ""
                else:
                    default_idx = var_options.index(default) if default in var_options else 0
                    val = st.selectbox(p_name, var_options, index=default_idx, key=widget_key, help=help_text)
                    args_dict[p_name] = val
            elif type_val in ("img_dropdown", "file_dropdown"):
                extensions = ["*.tif", "*.tiff", "*.am", "*.png", "*.mhd", "*.dat", "*.raw", "*.raw.gz", "*.npy", "*.npz"]
                found_files = []
                for ext in extensions:
                    found_files.extend(glob.glob(ext))
                    found_files.extend(glob.glob(f"*/{ext}"))
                found_files = sorted(list(set(found_files)))
                if not found_files:
                    st.warning("No compatible files found in runs/ directory.")
                    args_dict[p_name] = ""
                else:
                    default_idx = found_files.index(default) if default in found_files else 0
                    val = st.selectbox(p_name, found_files, index=default_idx, key=widget_key, help=help_text)
                    args_dict[p_name] = val
            elif type_val == "xmf_dropdown":
                found_files = []
                for ext in ["*.xmf", "*.xdmf"]:
                    found_files.extend(glob.glob(ext))
                    found_files.extend(glob.glob(f"*/{ext}"))
                found_files = sorted(list(set(found_files)))
                if not found_files:
                    st.warning("No .xmf files found in runs/ directory.")
                    args_dict[p_name] = ""
                else:
                    default_idx = found_files.index(default) if default in found_files else 0
                    val = st.selectbox(p_name, found_files, index=default_idx, key=widget_key, help=help_text)
                    args_dict[p_name] = val
            elif type_val == "case_dropdown":
                found_dirs = sorted([d for d in os.listdir(".") if os.path.isdir(d) and not d.startswith(".")])
                if not found_dirs:
                    st.warning("No case directories found in runs/ directory.")
                    args_dict[p_name] = ""
                else:
                    default_idx = found_dirs.index(default) if default in found_dirs else 0
                    val = st.selectbox(p_name, found_dirs, index=default_idx, key=widget_key, help=help_text)
                    args_dict[p_name] = val
            elif type_val == "type_dropdown":
                type_options = ["VxlImgU16", "VxlImgU8", "VxlImgI32", "VxlImgF32"]
                default_idx = type_options.index(default) if default in type_options else 0
                val = st.selectbox(p_name, type_options, index=default_idx, key=widget_key, help=help_text)
                args_dict[p_name] = val
            elif type_val is dict:
                default_str = str(default) if default is not None else "{}"
                val = st.text_input(p_name, value=default_str, key=widget_key, help=help_text)
                try:
                    parsed_val = eval(val) if val.strip() else {}
                    if isinstance(parsed_val, dict):
                        args_dict[p_name] = parsed_val
                    else:
                        st.error(f"{p_name} must be a dictionary.")
                        args_dict[p_name] = {}
                except Exception:
                    st.error(f"Invalid dictionary format for {p_name}.")
                    args_dict[p_name] = {}
            else:
                default_str = ""
                if has_default and default is not None and default is not inspect.Parameter.empty:
                    default_str = str(default)
                val = st.text_input(p_name, value=default_str, key=widget_key, help=help_text)
                args_dict[p_name] = val

    return args_dict
