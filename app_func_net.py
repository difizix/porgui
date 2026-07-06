import streamlit as st
import os
import sys
from stpyvista import stpyvista

from utils_app import get_module_func_args, args_to_cmd_line, func_args_from_inspect, get_xdmf_func_args, run_capturing_output, FormParam
from app_common import render_parseargs
from user_funcs import loadXmf, makeNetworkTubes, mextract, snflow, renderPNMXmf

# Ensure workspace root is in sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
workspace_root = os.path.dirname(current_dir)
if workspace_root not in sys.path:
    sys.path.insert(0, workspace_root)

# Wrap CLI Apps
STANDALONE_FUNCTIONS = {
    # Will be populated dynamically, from ../usr and usr/
}

PYTHON_FUNCTIONS = {
    "loadXmf": loadXmf,
    "makeNetworkTubes": makeNetworkTubes,
    "renderPNMXmf": renderPNMXmf,
    "mextract": mextract,
    "snflow": snflow,
}

CURATED_METHODS = {
    "writeAll": get_xdmf_func_args("writeAll", "Write the network to a file."),
    "readXmf": get_xdmf_func_args("readXmf", "Read the network from a file."),
}

for _sf_name, _sf_tuple in STANDALONE_FUNCTIONS.items():
    try:
        _func, _params = get_module_func_args(*_sf_tuple)
        if _func:
            CURATED_METHODS[_sf_name] = {
                "params": _params,
                "desc": f"Run {_sf_name} standalone CLI script."
            }
    except Exception as _e:
        print(f"Warning: could not load {_sf_name}: {_e}")

# Register fully-annotated Python functions into CURATED_METHODS
for _pf_name, _pf_func in PYTHON_FUNCTIONS.items():
    CURATED_METHODS[_pf_name] = func_args_from_inspect(_pf_func)

# ----------------------------------------------------
# TAB 3: NETWORK ANALYSIS
# ----------------------------------------------------
def render_pnm_tab():
    if "net_generated_code" not in st.session_state:
        st.session_state.net_generated_code = None

    if "net_filenames" not in st.session_state:
        st.session_state.net_filenames = {}

    if "net_stdout" not in st.session_state:
        st.session_state.net_stdout = ""
    if "net_success" not in st.session_state:
        st.session_state.net_success = ""
    if "net_error" not in st.session_state:
        st.session_state.net_error = ""

    net_obj = None
    col_v_ctrl, col_v_canvas = st.columns([2, 3])

    with col_v_ctrl:
        # Filter workspace_vars to find potential networks
        import pnmkit as nm
        import pyvista as pv
        net_types = (nm.Xdmf, nm.Xdml, pv.PolyData, pv.UnstructuredGrid)
        var_options = [k for k, v in st.session_state.workspace_vars.items() if isinstance(v, net_types)]
        if var_options:
            c1, c2 = st.columns([2, 3])
            with c1:
                st.markdown("<div style='padding-top: 6px;'><b>Active Network Variable:</b></div>", unsafe_allow_html=True)
            with c2:
                selected_var = st.selectbox("Select Active Network Variable", var_options, index=0, key="net_active_var_selectbox", label_visibility="collapsed")
            net_obj = st.session_state.workspace_vars[selected_var]
        else:
            selected_var = None

        with st.expander("📤 Upload & Load Network (.xmf)"):
            uploaded_file = st.file_uploader("Upload Network (.xmf)", type=["xmf"], key="net_uploader_widget")
            if uploaded_file is not None:
                new_var_name = st.text_input("Variable Name", value="net_uploaded", key="net_up_var_name")
                if st.button("Load Network", key="net_btn_load_uploaded"):
                    temp_path = uploaded_file.name
                    with open(temp_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    try:
                        import pnmkit as nm
                        loaded_obj = nm.Xdml(temp_path)
                        st.session_state.workspace_vars[new_var_name] = loaded_obj
                        st.session_state.net_filenames[new_var_name] = temp_path
                        st.success(f"Loaded {uploaded_file.name} as `{new_var_name}`!")
                        st.rerun()
                    except Exception as load_err:
                        st.error(f"Error loading network: {load_err}")

        st.markdown('<div class="card-title">🛠️ Interactive Function Executor</div>', unsafe_allow_html=True)

        # Get list of functions
        standalone_options = list(STANDALONE_FUNCTIONS.keys())
        available_standalones = [f for f in standalone_options if f in CURATED_METHODS]
        if net_obj is not None:
            func_options = sorted(list(CURATED_METHODS.keys()))
        else:
            func_options = sorted(list(PYTHON_FUNCTIONS.keys()) + available_standalones)

        default_func = "renderPNMXmf"
        default_idx = func_options.index(default_func) if default_func in func_options else 0

        c1_fn, c2_fn = st.columns([2, 3])
        with c1_fn:
            st.markdown("<div style='padding-top: 6px;'><b>Function to Execute:</b></div>", unsafe_allow_html=True)
        with c2_fn:
            selected_func = st.selectbox("Function to Execute:", func_options, index=default_idx, key="net_exec_func_sel", label_visibility="collapsed")

        # Display description
        st.markdown(f"**Description**: *{CURATED_METHODS[selected_func]['desc']}*")

        # Retrieve function params
        params_meta = CURATED_METHODS[selected_func]["params"]

        args = {}
        if params_meta:
            st.write("##### Function Arguments:")
            form_params = []
            for p in params_meta:
                form_params.append(FormParam(
                    name=p["name"],
                    default=p["default"],
                    has_default=True,
                    type_val=p["type"],
                    help_text=p["desc"],
                    is_iterable=p["type"] in (list, tuple)
                ))
            args = render_parseargs(form_params, key_prefix="net_func_arg")
        else:
            st.info("This function does not take any arguments.")

        is_standalone = selected_func in STANDALONE_FUNCTIONS
        out_var_name = ""
        copy_on_write = True
        if selected_func not in PYTHON_FUNCTIONS and not is_standalone:
            st.write("---")
            st.write("##### Execution Options:")
            col_opt1, col_opt2 = st.columns([1, 1])
            with col_opt1:
                out_var_name = st.text_input("Output Variable Name", value=f"{selected_var}_modified" if selected_var else "net_modified", key="net_out_var_name")
            with col_opt2:
                copy_on_write = st.checkbox("Copy first (protect original)", value=True, help="If unchecked, operation is in-place.", key="net_copy_on_write")

        # Reset generated code if function changed
        if "net_last_selected_func" not in st.session_state:
            st.session_state.net_last_selected_func = selected_func
        elif st.session_state.net_last_selected_func != selected_func:
            st.session_state.net_last_selected_func = selected_func
            st.session_state.net_generated_code = None

        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            btn_gen = st.button("📋 Generate Code", key="net_btn_gen_interactive_func", use_container_width=True)
        with col_btn2:
            btn_run = st.button("▶️ Run Function", key="net_btn_run_interactive_func", use_container_width=True)

        if btn_gen:
            try:
                st.session_state.net_generated_code = args_to_cmd_line(selected_func, args, copy_on_write, selected_var, out_var_name, is_standalone)
            except Exception as gen_err:
                st.error(f"Failed to generate code: {gen_err}")

        if btn_run:
            st.session_state.net_stdout = ""
            st.session_state.net_success = ""
            st.session_state.net_error = ""
            try:
                is_python_func = selected_func in PYTHON_FUNCTIONS
                if is_python_func:
                    func_to_call = PYTHON_FUNCTIONS[selected_func]
                    var_name = args.pop("new_var_name", None) or out_var_name or selected_func
                    filename = args.get("filename", "")
                    if "filename" in args and not args["filename"]:
                        st.error("Please select a file to load.")
                        st.stop()

                    result, stdout = run_capturing_output(func_to_call, **args)
                    st.session_state.net_stdout = stdout.strip() # TODO add args_to_cmd_line(selected_func, args, copy_on_write, selected_var, out_var_name, is_standalone)

                    import pnmkit as nm
                    import pyvista as pv
                    if isinstance(result, (nm.Xdmf, nm.Xdml, pv.PolyData, pv.UnstructuredGrid)):
                        st.session_state.workspace_vars[var_name] = result
                        if filename:
                            st.session_state.net_filenames[var_name] = filename

                    args_str = ", ".join(f"{k}={repr(v)}" for k, v in args.items())
                    command_line = f"{var_name} = {selected_func}({args_str})"
                    if st.session_state.session_commands:
                        st.session_state.session_commands += f"\n\n{command_line}"
                    else:
                        st.session_state.session_commands = command_line

                    st.session_state.net_success = f"Executed `{selected_func}`, result stored as `{var_name}`."
                    st.rerun()
                elif is_standalone:
                    def run_standalone():
                        _func, _ = get_module_func_args(*STANDALONE_FUNCTIONS[selected_func])
                        return _func(**args)
                    result, stdout = run_capturing_output(run_standalone)
                    st.session_state.net_stdout = stdout.strip() # TODO add args_to_cmd_line(selected_func, args, copy_on_write, selected_var, out_var_name, is_standalone)

                    args_str = ", ".join(f"{k}={repr(v)}" for k, v in args.items())
                    command_line = f"import pyvtk.{selected_func} as {selected_func}\n{selected_func}.main()  # args: {args_str}"
                    if st.session_state.session_commands:
                        st.session_state.session_commands += f"\n\n{command_line}"
                    else:
                        st.session_state.session_commands = command_line
                    st.session_state.net_success = f"Successfully executed standalone command `{selected_func}`!"
                    st.rerun()
                else:
                    if copy_on_write:
                        st.error("Copy-on-write is not implemented for custom Xdmf objects. Please run in-place.")
                        st.stop()
                    run_obj = net_obj
                    func_to_run = getattr(run_obj, selected_func)

                    result, stdout = run_capturing_output(func_to_run, **args)
                    st.session_state.net_stdout = stdout.strip() # TODO add args_to_cmd_line(selected_func, args, copy_on_write, selected_var, out_var_name, is_standalone)

                    args_str = ", ".join(f"{k}={repr(v)}" for k, v in args.items())
                    command_line = f"{selected_var}.{selected_func}({args_str})"
                    if st.session_state.session_commands:
                        st.session_state.session_commands += f"\n\n{command_line}"
                    else:
                        st.session_state.session_commands = command_line

                    st.session_state.net_success = f"Successfully executed `{selected_func}` in-place on `{selected_var}`."
                    st.rerun()
            except Exception as run_err:
                import traceback
                st.session_state.net_error = f"{run_err}\n\n{traceback.format_exc()}"
                st.rerun()

        if st.session_state.net_generated_code:
            st.markdown("---")
            st.markdown("##### 📋 Generated Python Code:")
            st.code(st.session_state.net_generated_code, language="python")

        if st.session_state.net_stdout:
            st.markdown("---")
            st.markdown("##### 💬 Execution Output:")
            st.code(st.session_state.net_stdout, language="text")

        if st.session_state.net_success:
            st.success(st.session_state.net_success)

        if st.session_state.net_error:
            st.error("Execution failed:")
            st.code(st.session_state.net_error, language="text")

        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown("---")

    with col_v_canvas:
        mesh = None
        xmf_path = None
        if selected_var:
            val = st.session_state.workspace_vars[selected_var]
            if isinstance(val, (pv.PolyData, pv.UnstructuredGrid)):
                # Already a PyVista mesh (e.g. result of makeNetworkTubes)
                mesh = val
                xmf_path = st.session_state.net_filenames.get(selected_var, "Mesh Object")
            else:
                # Xdml/Xdmf object — not directly renderable; guide user
                st.info(
                    f"**`{selected_var}`** is a network object (pnmkit). "
                    "Run **makeNetworkTubes** on it to generate a 3D tube mesh for visualization."
                )

        if mesh is not None and mesh.n_points > 0:
            display_name = os.path.basename(xmf_path) if xmf_path and xmf_path != "Mesh Object" else selected_var or "Mesh"
            st.markdown(f"#### 🌐 3D Network Visualization (`{display_name}`)")
            try:
                # Extract scalar fields
                available_scalars = list(mesh.point_data.keys()) + list(mesh.cell_data.keys())
                selected_scalar = None
                if available_scalars:
                    default_idx = 0
                    if 'radius' in available_scalars:
                        default_idx = available_scalars.index('radius')
                    elif 'radus' in available_scalars:
                        default_idx = available_scalars.index('radus')

                    selected_scalar = st.selectbox(
                        "Color by Attribute:",
                        available_scalars,
                        index=default_idx,
                        key="net_color_scalar_selectbox"
                    )


                # --------------------------
                # to be implemented as a general function pyvistaplot
                # Initialize Plotter
                plotter = pv.Plotter(window_size=[500, 500])
                plotter.background_color = "#0f172a"

                # Detect if the mesh is just 1D lines (needs line rendering)
                is_line_mesh = False
                import numpy as np
                if isinstance(mesh, pv.UnstructuredGrid):
                    cts = np.unique(mesh.celltypes)
                    # 3=LINE, 4=POLY_LINE, 21=QUADRATIC_EDGE
                    if len(cts) > 0 and all(ct in [3, 4, 21] for ct in cts):
                        is_line_mesh = True
                elif isinstance(mesh, pv.PolyData):
                    if mesh.n_lines > 0 and mesh.n_faces == 0:
                        is_line_mesh = True

                plot_args = {
                    "scalars": selected_scalar,
                    "cmap": "viridis",
                    "show_scalar_bar": True,
                }
                if is_line_mesh:
                    plot_args["render_lines_as_tubes"] = True
                    plot_args["line_width"] = 2.5
                else:
                    plot_args["smooth_shading"] = True

                plotter.add_mesh(mesh, **plot_args)

                plotter.add_axes()
                plotter.reset_camera()
                plotter.view_isometric()

                # end of func pyvistaplot (to be implemented as a general function)

                stpyvista(plotter, key=f"net_pv_plot_{selected_var or 'default'}")

                # Diagnostics expander
                diag_rows = [
                    ("Points", f"{mesh.n_points:,}"),
                    ("Cells",  f"{mesh.n_cells:,}"),
                    ("X bounds", f"{mesh.bounds[0]:.2f} – {mesh.bounds[1]:.2f}"),
                    ("Y bounds", f"{mesh.bounds[2]:.2f} – {mesh.bounds[3]:.2f}"),
                    ("Z bounds", f"{mesh.bounds[4]:.2f} – {mesh.bounds[5]:.2f}"),
                ]
                if selected_scalar:
                    arr = mesh.point_data.get(selected_scalar)
                    if arr is None:
                        arr = mesh.cell_data.get(selected_scalar)
                    if arr is not None:
                        diag_rows += [
                            (f"{selected_scalar} min", f"{arr.min():.4g}"),
                            (f"{selected_scalar} max", f"{arr.max():.4g}"),
                        ]
                with st.expander("🔍 Mesh Diagnostics", expanded=True):
                    for label, val in diag_rows:
                        c1, c2 = st.columns([2, 3])
                        c1.markdown(f"**{label}**")
                        c2.markdown(val)
            except Exception as render_err:
                import traceback
                st.error(f"Error rendering 3D network: {render_err}")
                st.code(traceback.format_exc())
        elif mesh is not None and mesh.n_points == 0:
            st.warning("Generated mesh has zero points — the tube filter may need different parameters (e.g. adjust `xRad` or check the scalar array name).")
        elif not selected_var:
            st.info("No network variable selected. Load a network file with **loadXmf**, then run **makeNetworkTubes** to visualize it.")
