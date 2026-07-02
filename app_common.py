import inspect
import streamlit as st


def render_parseargs(params, key_prefix=""):
    args_dict = {}
    for param in params:
        p_name = param.name
        default = param.default
        has_default = param.has_default
        is_iterable = param.is_iterable
        type_val = param.type_val
        widget_key = f"{key_prefix}_{p_name}"

        col_label, col_widget = st.columns([1, 4])

        if is_iterable:
            with col_label:
                st.markdown(f"<div style='display: flex; align-items: flex-start; padding-top: 10px;'><strong>{p_name}</strong></div>", unsafe_allow_html=True)
            with col_widget:
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
                    label_visibility="collapsed"
                )
                args_dict[p_name] = [line.strip() for line in val.split("\n") if line.strip()]
        elif type_val is bool:
            with col_label:
                st.markdown(f"<div style='display: flex; align-items: center; min-height: 40px;'><strong>{p_name}</strong></div>", unsafe_allow_html=True)
            with col_widget:
                val = st.checkbox(p_name, value=bool(default), key=widget_key, label_visibility="collapsed")
                args_dict[p_name] = val
        elif type_val in (int, float):
            with col_label:
                st.markdown(f"<div style='display: flex; align-items: center; min-height: 40px;'><strong>{p_name}</strong></div>", unsafe_allow_html=True)
            with col_widget:
                if type_val is int:
                    val = st.number_input(p_name, value=int(default) if (default is not None and default is not inspect.Parameter.empty) else 0, step=1, key=widget_key, label_visibility="collapsed")
                else:
                    val = st.number_input(p_name, value=float(default) if (default is not None and default is not inspect.Parameter.empty) else 0.0, step=0.1, key=widget_key, label_visibility="collapsed")
                args_dict[p_name] = val
        else:
            with col_label:
                st.markdown(f"<div style='display: flex; align-items: center; min-height: 40px;'><strong>{p_name}</strong></div>", unsafe_allow_html=True)
            with col_widget:
                default_str = ""
                if has_default and default is not None and default is not inspect.Parameter.empty:
                    default_str = str(default)
                val = st.text_input(p_name, value=default_str, key=widget_key, label_visibility="collapsed")
                args_dict[p_name] = val

    return args_dict
