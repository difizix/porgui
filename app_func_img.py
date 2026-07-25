import streamlit as st
import os
import numpy as np
import traceback
import image3kit as ik
import PIL
import sys

from utils_app import get_module_func_args, args_to_cmd_line, func_args_from_inspect, get_vxlImg_func_args, run_capturing_output, FormParam
from app_common import render_parseargs, resolve_object_args, get_presenter, get_workspace
from user_funcs import read_image, mextract, snflow

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
    "read_image": read_image,
    "threshold01_otsu": ik.threshold01_otsu,
    "mextract": mextract,
    "snflow": snflow,
}
# TODO add image3kit.labelImage to lists above 

CURATED_METHODS = {
    "crop":         get_vxlImg_func_args("crop"),
    "median_filter": get_vxlImg_func_args("median_filter"),
    "dering":       get_vxlImg_func_args("dering"),
    "segment2":     get_vxlImg_func_args("segment2"),
    "threshold101": get_vxlImg_func_args("threshold101"),
    "write_8bit":    get_vxlImg_func_args("write_8bit"),
    "extrude_dist_map": get_vxlImg_func_args("extrude_dist_map"),
    "scaled_diff":  get_vxlImg_func_args("scaled_diff"),
    "blend_min_variance": get_vxlImg_func_args("blend_min_variance"),
    "segment": get_vxlImg_func_args("segment"),
    "to_foam":  get_vxlImg_func_args("to_foam"),  
    "to_foam_par": get_vxlImg_func_args("to_foam_par"), 
    "to_foam_par_incremental": get_vxlImg_func_args("to_foam_par_incremental"), 
    "to_surf_mesh": get_vxlImg_func_args("to_surf_mesh"), 
    "print_info": get_vxlImg_func_args("print_info"), 
    "write": get_vxlImg_func_args("write"), 
    "write_no_header": get_vxlImg_func_args("write_no_header"), 
    "read_ascii": get_vxlImg_func_args("read_ascii"), 
    "grow_box": get_vxlImg_func_args("grow_box"), 
    "shrink_box": get_vxlImg_func_args("shrink_box"), 
    "fill_holes": get_vxlImg_func_args("fill_holes"), 
    "write_a_connected_void_voxel": get_vxlImg_func_args("write_a_connected_void_voxel"), 
    "and_": get_vxlImg_func_args("and_"), 
    "not_": get_vxlImg_func_args("not_"), 
    "or_": get_vxlImg_func_args("or_"),  
    "xor_": get_vxlImg_func_args("xor_"), 
    "resample_mode": get_vxlImg_func_args("resample_mode"), 
    "resample_max": get_vxlImg_func_args("resample_max"), 
    "resample_mean": get_vxlImg_func_args("resample_mean"), 
    "reslice_z": get_vxlImg_func_args("reslice_z"), 
    "paint": get_vxlImg_func_args("paint"), 
    "paint_add": get_vxlImg_func_args("paint_add"), 
    "paint_before": get_vxlImg_func_args("paint_before"), 
    "paint_after": get_vxlImg_func_args("paint_after"), 
    "paint_add_before": get_vxlImg_func_args("paint_add_before"), 
    "paint_add_after": get_vxlImg_func_args("paint_add_after"), 
    "write_contour": get_vxlImg_func_args("write_contour"), 
    "plot_slice": get_vxlImg_func_args("plot_slice"), 
    "rescale_values": get_vxlImg_func_args("rescale_values"),  
    "redirect": get_vxlImg_func_args("redirect"),  
    "direction": get_vxlImg_func_args("direction"),  
    "grow0": get_vxlImg_func_args("grow0"),  
    "shrink0": get_vxlImg_func_args("shrink0"),  
    "resample": get_vxlImg_func_args("resample"), 
    "range_to": get_vxlImg_func_args("range_to"), 
    "replace_range": get_vxlImg_func_args("replace_range"), 
    "read_from_header": get_vxlImg_func_args("read_from_header"), 
    "read_bin": get_vxlImg_func_args("read_bin"),
    "median_x": get_vxlImg_func_args("median_x"), 
    "median_y": get_vxlImg_func_args("median_y"), 
    "median_z": get_vxlImg_func_args("median_z"), 
    "median06": get_vxlImg_func_args("median06"), 
    "median032": get_vxlImg_func_args("median032"), 
    "median06_grow": get_vxlImg_func_args("median06_grow"), 
    "delense032": get_vxlImg_func_args("delense032"), 
    "circle_out": get_vxlImg_func_args("circle_out"), 
    "grow_label": get_vxlImg_func_args("grow_label"), 
    "keep_largest": get_vxlImg_func_args("keep_largest"), 
    "map_from": get_vxlImg_func_args("map_from"), 
    "add_surf_noise": get_vxlImg_func_args("add_surf_noise"),  
    "average_with": get_vxlImg_func_args("average_with"), 
    "average_with_skip_extremes": get_vxlImg_func_args("average_with_skip_extremes"), 
    "plot_all": get_vxlImg_func_args("plot_all"), 
    "mode6": get_vxlImg_func_args("mode6"), 
    "mode26": get_vxlImg_func_args("mode26"), 
    "growing_threshold": get_vxlImg_func_args("growing_threshold"), 
    "grow_outside_value": get_vxlImg_func_args("grow_outside_value"), 
    "smooth_bilateral": get_vxlImg_func_args("smooth_bilateral"), 
    "plot_histogram": get_vxlImg_func_args("plot_histogram"), 
    "plot_z_profile": get_vxlImg_func_args("plot_z_profile"), 
    "flip_endian": get_vxlImg_func_args("flip_endian"), 
    "replace_range_by_image": get_vxlImg_func_args("replace_range_by_image"), 
    "replace_by_image_range": get_vxlImg_func_args("replace_by_image_range"), 
    "read_from_float": get_vxlImg_func_args("read_from_float"), 
    "bilateral_wide": get_vxlImg_func_args("bilateral_wide"), 
    "bilateral_gauss": get_vxlImg_func_args("bilateral_gauss"), 
    "mean_wide": get_vxlImg_func_args("mean_wide"), 
    "otsu_threshold": get_vxlImg_func_args("otsu_threshold"), 
    "adjust_brightness_with": get_vxlImg_func_args("adjust_brightness_with"), 
    "adjust_slice_brightness": get_vxlImg_func_args("adjust_slice_brightness"), 
    "cut_outside": get_vxlImg_func_args("cut_outside"), 
    "variance": get_vxlImg_func_args("variance"),
}

# Since U16 has more functions that int and u8, 
# we got to make sure the functions exposed depend on the image type.
# The right  Viewer column shall show the output of the executed function if it is a VXlImgU... type,
# If the execution log shows that a png or svg files are generated, those shall be rendered below the slice , in the right-side column


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
# TAB 2: INTERACTIVE VISUALIZER
# ----------------------------------------------------
def render_imgpro_tab():
    if "pending_active_var" in st.session_state:
        pending = st.session_state.pop("pending_active_var")
        st.session_state.active_var = pending
        st.session_state.active_var_selectbox_widget = pending




    if "generated_code" not in st.session_state:
        st.session_state.generated_code = None
    if "img_stdout" not in st.session_state:
        st.session_state.img_stdout = ""
    if "img_success" not in st.session_state:
        st.session_state.img_success = ""
    if "img_error" not in st.session_state:
        st.session_state.img_error = ""
    if "img_nonimage_result" not in st.session_state:
        st.session_state.img_nonimage_result = None
    if "img_nonimage_result_func" not in st.session_state:
        st.session_state.img_nonimage_result_func = None

    workspace = get_workspace()
    vxl_types = workspace.image_types

    if workspace.processed_image is not None and isinstance(workspace.processed_image, vxl_types) and "img" not in workspace.vars:
        workspace.store_var("img", workspace.processed_image)

    img = None
    col_v_ctrl, col_v_canvas = st.columns([2, 3])

    with col_v_ctrl:

        var_options = workspace.image_vars()
        if var_options:
            if workspace.active_var not in var_options:
                workspace.set_active(var_options[0])

            c1, c2 = st.columns([2, 3])
            with c1:
                st.markdown("<div style='padding-top: 6px;'><b>Viewed Image Variable:</b></div>", unsafe_allow_html=True)
            with c2:
                selected_var = st.selectbox(
                    "Select Viewed Image Variable",
                    var_options,
                    index=var_options.index(workspace.active_var),
                    key="active_var_selectbox_widget",
                    label_visibility="collapsed"
                )
            workspace.set_active(selected_var)
            img = workspace.get(selected_var)
        else:
            selected_var = None


        with st.expander("📤 Upload & Load Image to Cache"):
            uploaded_file = st.file_uploader("Upload Image (TIFF, MHD/RAW, PNG, AM, DAT, RAW.GZ)", type=["tif", "tiff", "mhd", "raw", "raw.gz", "gz", "dat", "png", "am"], key="uploader_widget")
            if uploaded_file is not None:
                ext = os.path.splitext(uploaded_file.name)[1].lower()
                default_idx = 1 if ext in [".png", ".am", ".dat"] else 0
                col_up_name, col_up_type = st.columns([1, 1])
                with col_up_name:
                    new_var_name = st.text_input("Variable Name", value="img_uploaded", key="up_var_name")
                with col_up_type:
                    up_img_type = st.selectbox("Type", ["VxlImgU16", "VxlImgU8", "VxlImgI32", "VxlImgF32"], index=default_idx, key="up_img_type")

                if st.button("Load Image", key="btn_load_uploaded"):
                    temp_path = uploaded_file.name
                    with open(temp_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    try:
                        loader = workspace.store[f"original_{up_img_type}"]
                        loaded_obj = loader(temp_path)

                        cache_key = f"{up_img_type}_{os.path.abspath(temp_path)}"
                        workspace.image_cache[cache_key] = loaded_obj
                        workspace.store_image(new_var_name, loaded_obj)
                        st.session_state.pending_active_var = new_var_name
                        st.success(f"Loaded {uploaded_file.name} as `{new_var_name}`!")
                        st.rerun()
                    except Exception as load_err:
                        st.error(f"Error loading image: {load_err}")


        if img is not None:
            data = img.data
            shape = data.shape
            c1_ax, c2_ax = st.columns([2, 2])
            with c1_ax:
                st.markdown("<div style='padding-top: 6px;'><b>View Normal Axis:</b></div>", unsafe_allow_html=True)
            with c2_ax:
                axis = st.selectbox("View Normal Axis", ["Z (Axial)", "Y (Coronal)", "X (Sagittal)"], key="view_axis_sel", label_visibility="collapsed")
            axis_idx = 2 if "Z" in axis else (1 if "Y" in axis else 0)
            max_slice = shape[axis_idx] - 1
            if max_slice <= 0:
                st.caption("Slice Index: 0 (Dimension size is 1)")
                slice_idx = 0
            else:
                c1_sl, c2_sl = st.columns([1, 3])
                with c1_sl:
                    st.markdown("<div style='padding-top: 6px;'><b>Select Slice Index:</b></div>", unsafe_allow_html=True)
                with c2_sl:
                    slice_idx = st.slider("Slice Index", 0, int(max_slice), int(max_slice // 2), key="slice_slider", label_visibility="collapsed")
            
            data_min = float(data.min())
            data_max = float(data.max())
            if data_min >= data_max:
                st.caption(f"Contrast Range: {data_min} (Constant image value)")
                min_contrast, max_contrast = data_min, data_max
            else:
                default_start = data_min
                default_end = data_max
                
                c1_co, c2_co = st.columns([1, 3])
                with c1_co:
                    st.markdown("<div style='padding-top: 6px;'><b>Contrast Range:</b></div>", unsafe_allow_html=True)
                with c2_co:
                    val_range = st.slider(
                        "Contrast Range",
                        data_min, data_max,
                        (default_start, default_end),
                        key="contrast_slider",
                        label_visibility="collapsed"
                    )
                min_contrast, max_contrast = val_range


        # 🛠️ Interactive Function Executor Section
        st.markdown('<div class="card-title">🛠️ Interactive Function Executor</div>', unsafe_allow_html=True)

        # Get list of functions
        func_options = sorted(list(CURATED_METHODS.keys()))
        default_func = "read_image"
        default_idx = func_options.index(default_func) if default_func in func_options else 0

        c1_fn, c2_fn = st.columns([2, 3])
        with c1_fn:
            st.markdown("<div style='padding-top: 6px;'><b>Function to Execute:</b></div>", unsafe_allow_html=True)
        with c2_fn:
            selected_func = st.selectbox("Function to Execute:", func_options, index=default_idx, key="exec_func_sel", label_visibility="collapsed")

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
            args = render_parseargs(form_params, key_prefix="func_arg")
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
                ref_var = args.get("self") or args.get("image_var") or selected_var
                base_name = f"{ref_var}_filtered" if ref_var else "img_filtered"
                # Suffix the default so it never silently overwrites an existing variable
                default_out_name = workspace.unique_name(base_name)
                out_var_name = st.text_input("Output Variable Name", value=default_out_name)
            with col_opt2:
                copy_on_write = st.checkbox("Copy first (protect original image)", value=True, help="If unchecked, the operation is run in-place modifying the selected variable.")

        # Update last selected function tracker and reset generated code if function changed
        if "last_selected_func" not in st.session_state:
            st.session_state.last_selected_func = selected_func
        elif st.session_state.last_selected_func != selected_func:
            st.session_state.last_selected_func = selected_func
            st.session_state.generated_code = None

        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            btn_gen = st.button("📋 Generate Code", key="btn_gen_interactive_func", use_container_width=True)
        with col_btn2:
            btn_run = st.button("▶️ Run Function", key="btn_run_interactive_func", use_container_width=True)

        if btn_gen:
            try:
                st.session_state.generated_code = args_to_cmd_line(
                    selected_func, args, copy_on_write,
                    args.get("self") or selected_var, out_var_name, is_standalone
                )
            except Exception as gen_err:
                st.error(f"Failed to generate code: {gen_err}")

        if btn_run:
            st.session_state.img_stdout = ""
            st.session_state.img_success = ""
            st.session_state.img_error = ""
            st.session_state.img_nonimage_result = None
            st.session_state.img_nonimage_result_func = None

            presenter = get_presenter()

            if selected_func in PYTHON_FUNCTIONS:
                res = presenter.run_python_func(
                    selected_func, PYTHON_FUNCTIONS[selected_func], args, out_var_name
                )
            elif is_standalone:
                standalone_func, _ = get_module_func_args(*STANDALONE_FUNCTIONS[selected_func])
                res = presenter.run_standalone(selected_func, standalone_func, args)
            else:
                # "self" comes from the form; fall back to the viewed image
                target_var = args.pop("self", None) or selected_var
                # Object-typed args (e.g. alpha_image) arrive as variable names
                args = resolve_object_args(args, params_meta, presenter.workspace.vars)
                res = presenter.run_method(
                    selected_func, target_var, args, copy_on_write, out_var_name
                )

            if res.invalid:
                st.error(res.error)
                st.stop()

            if res.ok:
                st.session_state.img_stdout = res.stdout
                st.session_state.img_success = res.success_msg
                st.session_state.img_nonimage_result = res.nonimage_result
                st.session_state.img_nonimage_result_func = res.nonimage_func
                if res.stored_var:
                    st.session_state.pending_active_var = res.stored_var
            else:
                st.session_state.img_error = res.error
            st.rerun()


        # Display generated code block if available
        if st.session_state.generated_code:
            st.markdown("---")
            st.markdown("##### 📋 Generated Python Code:")
            st.code(st.session_state.generated_code, language="python")

        if st.session_state.img_stdout:
            st.markdown("---")
            st.markdown("##### 💬 Execution Output:")
            st.code(st.session_state.img_stdout, language="text")

        if st.session_state.img_success:
            st.success(st.session_state.img_success)

        if st.session_state.img_error:
            st.error("Execution failed:")
            st.code(st.session_state.img_error, language="text")

        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown("---")

    with col_v_canvas:
        if img is not None:
            try:
                data = img.data
                shape = data.shape
                if axis_idx == 0:
                    slice_2d = data[slice_idx, :, :]
                elif axis_idx == 1:
                    slice_2d = data[:, slice_idx, :]
                else:
                    slice_2d = data[:, :, slice_idx]
                # Scale values
                if max_contrast > min_contrast:
                    norm_slice = np.clip((slice_2d - min_contrast) / (max_contrast - min_contrast) * 255.0, 0, 255).astype(np.uint8)
                else:
                    norm_slice = np.zeros_like(slice_2d, dtype=np.uint8)
                pil_image = PIL.Image.fromarray(norm_slice)
                st.image(
                    pil_image,
                    caption=f"`{axis.split()[0]}` @ `{slice_idx}` / `{max_slice}` │ color: `{int(min_contrast)}-{int(max_contrast)}` `{data.dtype}` │ span: `{shape}` × `{img.spacing}` + `{img.origin}`",
                    width="stretch"
                )
            except Exception as slice_err:
                st.error(f"Error rendering image slice from memory: {slice_err}")

            if st.session_state.get("img_stdout"):
                import re
                from pathlib import Path
                matches = re.findall(r"[\w/\.-]+\.(?:png|svg)", st.session_state.img_stdout)
                seen = set()
                existing_plots = []
                for match in matches:
                    clean_path = match.strip("'\" \t\r\n")
                    if clean_path in seen:
                        continue
                    seen.add(clean_path)
                    p = Path(clean_path)
                    if not p.is_absolute():
                        p = Path(workspace_root) / p
                    if p.exists():
                        existing_plots.append(p)

                if existing_plots:
                    st.markdown("---")
                    st.markdown("##### 📊 Generated Plots/Output Files:")
                    for plot_path in existing_plots:
                        st.write(f"**`{plot_path.name}`**")
                        if plot_path.suffix.lower() == ".svg":
                            try:
                                with open(plot_path, "r", encoding="utf-8") as svg_f:
                                    svg_content = svg_f.read()
                                st.components.v1.html(svg_content, height=400, scrolling=True)
                            except Exception as svg_err:
                                st.error(f"Error reading SVG {plot_path.name}: {svg_err}")
                        else:
                            st.image(str(plot_path), use_container_width=True)
        else:
            st.info("**No image loaded yet. Run a workflow or upload an image to begin.**")

        # Non-image results from curated methods that returned a real value
        # (e.g. otsu_threshold's [min, avg_0, threshold, avg_1, max] stats list).
        if st.session_state.get("img_nonimage_result") is not None:
            st.markdown("---")
            func_label = st.session_state.get("img_nonimage_result_func") or "function"
            st.markdown(f"##### 🔢 Function Result (`{func_label}`):")
            _res = st.session_state.img_nonimage_result
            if isinstance(_res, (list, tuple, dict)):
                try:
                    st.json(_res)
                except Exception:
                    st.write(_res)
            else:
                st.write(_res)