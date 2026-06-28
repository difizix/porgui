import streamlit as st
import os
import numpy as np
import traceback
import PIL

CURATED_METHODS = {
    "cropD": {
        "params": [
            {"name": "begin", "type": tuple, "default": (0, 0, 300), "desc": "Begin indices (x, y, z)"},
            {"name": "end", "type": tuple, "default": (467, 1775, 580), "desc": "End indices (x, y, z)"},
            {"name": "emptyLayers", "type": int, "default": 0, "desc": "Number of empty layers"},
            {"name": "emptyLayersValue", "type": int, "default": 1, "desc": "Value for empty layers"},
            {"name": "verbose", "type": bool, "default": False, "desc": "Verbose output"}
        ],
        "desc": "Crop the image (inplace) from begin index tuple to end index tuple."
    },
    "medianFilter": {
        "params": [],
        "desc": "Apply a 1+6-neighbour median filter in-place."
    },
    "dering": {
        "params": [
            {"name": "x0", "type": int, "default": 374, "desc": "Center X of ring at z=0"},
            {"name": "y0", "type": int, "default": 853, "desc": "Center Y of ring at z=0"},
            {"name": "x1", "type": int, "default": 374, "desc": "Center X of ring at end of image"},
            {"name": "y1", "type": int, "default": 853, "desc": "Center Y of ring at end of image"},
            {"name": "nr", "type": int, "default": 1000, "desc": "Width of ring artefacts (voxels)"},
            {"name": "ntheta", "type": int, "default": 32, "desc": "Number of angles"},
            {"name": "nz", "type": int, "default": 148, "desc": "Number of layers"},
            {"name": "min_val", "type": int, "default": 8500, "desc": "Min voxel-value range for ring detection"},
            {"name": "max_val", "type": int, "default": 12000, "desc": "Max voxel-value range for ring detection"},
            {"name": "nGrowBox", "type": int, "default": 20, "desc": "Grow box size near image boundary"},
            {"name": "write_dumps", "type": bool, "default": False, "desc": "Write dump files for debugging"}
        ],
        "desc": "Remove ring artefacts from the image."
    },
    "segment2": {
        "params": [
            {"name": "thresholds", "type": list, "default": [0, 6000, 65535], "desc": "Threshold values list"},
            {"name": "min_sizes", "type": list, "default": [1, 3], "desc": "Minimum component sizes list"},
            {"name": "noise_val", "type": float, "default": 2.0, "desc": "Noise value"},
            {"name": "local_factor", "type": float, "default": 0.05, "desc": "Local factor"},
            {"name": "flatnes", "type": float, "default": 0.1, "desc": "Flatness factor"},
            {"name": "effective_resolution", "type": float, "default": 2.0, "desc": "Effective resolution"},
            {"name": "gradient_factor", "type": float, "default": 0.0, "desc": "Gradient factor"},
            {"name": "kernel_radius", "type": int, "default": 2, "desc": "Kernel radius"},
            {"name": "n_iterations", "type": int, "default": 13, "desc": "Number of iterations"},
            {"name": "write_dumps", "type": int, "default": 0, "desc": "Write dump files (0/1)"}
        ],
        "desc": "Apply multi-threshold segmentation."
    },
    "threshold101": {
        "params": [
            {"name": "min", "type": int, "default": 1, "desc": "Minimum threshold value"},
            {"name": "max", "type": int, "default": 6000, "desc": "Maximum threshold value"}
        ],
        "desc": "Threshold values in range [min, max] to 0, and others to 1."
    },
    "write8bit": {
        "params": [
            {"name": "filename", "type": str, "default": "volume_out.raw.gz", "desc": "Output filename (.raw/.raw.gz)"},
            {"name": "min", "type": float, "default": 0.0, "desc": "Min scale value (maps to 0)"},
            {"name": "max", "type": float, "default": 25500.0, "desc": "Max scale value (maps to 255)"}
        ],
        "desc": "Write the image as an 8-bit raw.gz file, scaled between min and max."
    },
    "loadImg": {
        "params": [
            {"name": "filename", "type": "file_dropdown", "default": "", "desc": "Select image file to load from current directory"},
            {"name": "img_type", "type": "type_dropdown", "default": "VxlImgU16", "desc": "Select image precision/type"},
            {"name": "new_var_name", "type": str, "default": "img", "desc": "Variable name to store in workspace"}
        ],
        "desc": "Load an image (.tif, .mhd, .am, .dat, .png) from the runs directory into the workspace."
    }
}

# ----------------------------------------------------
# TAB 2: INTERACTIVE VISUALIZER
# ----------------------------------------------------
def render_visualizer_tab():
    # Dropdown to choose which image variable from workspace to visualize
    if st.session_state.processed_image is not None and "img" not in st.session_state.workspace_vars:
        st.session_state.workspace_vars["img"] = st.session_state.processed_image

    img = None
    col_v_ctrl, col_v_canvas = st.columns([2, 3])

    with col_v_ctrl:

        var_options = list(st.session_state.workspace_vars.keys())
        if var_options:
            selected_var = st.selectbox("Select Active Image Variable", var_options, index=0, key="active_var_selectbox")
            img = st.session_state.workspace_vars[selected_var]
        else:
            selected_var = None

        # Render Slice Viewer if we have an image
        st.markdown('<div class="card-title">🖼️ Live 3D Slice Viewer (In-Memory)</div>', unsafe_allow_html=True)

        with st.expander("📤 Upload & Load Image to Cache"):
            uploaded_file = st.file_uploader("Upload Image (TIFF, MHD/RAW, PNG, AM, DAT)", type=["tif", "tiff", "mhd", "raw", "dat", "png", "am"], key="uploader_widget")
            if uploaded_file is not None:
                ext = os.path.splitext(uploaded_file.name)[1].lower()
                default_idx = 1 if ext in [".png", ".am", ".dat"] else 0
                col_up_name, col_up_type = st.columns([1, 1])
                with col_up_name:
                    new_var_name = st.text_input("Variable Name", value="img_uploaded", key="up_var_name")
                with col_up_type:
                    up_img_type = st.selectbox("Type", ["VxlImgU16", "VxlImgU8", "VxlImgF32"], index=default_idx, key="up_img_type")

                is_raw = uploaded_file.name.endswith(".raw")
                raw_shape = None
                if is_raw:
                    shape_str = st.text_input("RAW Shape (Z, Y, X), e.g. (148, 1775, 467)", value="", key="raw_shape_str")
                    if shape_str:
                        try:
                            raw_shape = eval(shape_str)
                        except Exception:
                            st.error("Invalid shape format.")

                if st.button("Load Image", key="btn_load_uploaded"):
                    temp_path = uploaded_file.name
                    with open(temp_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    try:
                        # Let's check the type and load using the appropriate VxlImg class
                        if up_img_type == "VxlImgU16":
                            loaded_obj = st.session_state.original_VxlImgU16(temp_path)
                        elif up_img_type == "VxlImgU8":
                            loaded_obj = st.session_state.original_VxlImgU8(temp_path)
                        else:
                            loaded_obj = st.session_state.original_VxlImgF32(temp_path)

                        cache_key = f"{up_img_type}_{os.path.abspath(temp_path)}"
                        st.session_state.image_cache[cache_key] = loaded_obj
                        st.session_state.workspace_vars[new_var_name] = loaded_obj
                        st.session_state.processed_image = loaded_obj
                        st.success(f"Loaded {uploaded_file.name} as `{new_var_name}`!")
                        st.rerun()
                    except Exception as load_err:
                        st.error(f"Error loading image: {load_err}")


        if img is not None:
            data = img.data
            shape = data.shape
            axis = st.selectbox("Slice Normal Axis", ["Z (Axial)", "Y (Coronal)", "X (Sagittal)"], key="view_axis_sel")
            axis_idx = 2 if "Z" in axis else (1 if "Y" in axis else 0)
            max_slice = shape[axis_idx] - 1
            if max_slice <= 0:
                st.caption("Slice Index: 0 (Dimension size is 1)")
                slice_idx = 0
            else:
                slice_idx = st.slider("Select Slice Index", 0, int(max_slice), int(max_slice // 2), key="slice_slider")
            
            data_min = float(data.min())
            data_max = float(data.max())
            if data_min >= data_max:
                st.caption(f"Contrast Range Window: {data_min} (Constant image value)")
                min_contrast, max_contrast = data_min, data_max
            else:
                default_start = data_min
                default_end = data_max
                
                val_range = st.slider(
                    "Contrast Range Window",
                    data_min, data_max,
                    (default_start, default_end),
                    key="contrast_slider"
                )
                min_contrast, max_contrast = val_range
        else:
            st.info("No active image found in memory workspace. Run a workflow or upload an image to begin.")


        # 🛠️ Interactive Function Executor Section
        st.markdown("---")
        st.markdown('<div class="card-title">🛠️ Interactive Function Executor</div>', unsafe_allow_html=True)

        # Get list of functions
        if img is not None:
            func_options = sorted(list(CURATED_METHODS.keys()))
        else:
            func_options = ["loadImg"]

        selected_func = st.selectbox("Select Function to Execute", func_options, key="exec_func_sel")

        # Display description
        st.markdown(f"**Description**: *{CURATED_METHODS[selected_func]['desc']}*")

        # Retrieve function params
        params_meta = CURATED_METHODS[selected_func]["params"]

        args = {}
        if params_meta:
            st.write("##### Function Arguments:")
            # Render widgets in a grid (3 columns)
            cols = st.columns(3)
            for idx, p in enumerate(params_meta):
                col = cols[idx % 3]
                p_name = p["name"]
                p_type = p["type"]
                p_default = p["default"]
                p_desc = p["desc"]

                with col:
                    if p_type is bool:
                        args[p_name] = st.checkbox(f"{p_name}", value=p_default, help=p_desc, key=f"func_arg_{p_name}")
                    elif p_type is int:
                        args[p_name] = st.number_input(f"{p_name} (int)", value=int(p_default), step=1, help=p_desc, key=f"func_arg_{p_name}")
                    elif p_type is float:
                        args[p_name] = st.number_input(f"{p_name} (float)", value=float(p_default), step=0.1, help=p_desc, key=f"func_arg_{p_name}")
                    elif p_type in (list, tuple):
                        val_str = st.text_input(f"{p_name} ({p_type.__name__})", value=str(p_default), help=p_desc, key=f"func_arg_{p_name}")
                        try:
                            args[p_name] = eval(val_str)
                        except Exception:
                            st.error(f"Invalid format for {p_name}")
                            args[p_name] = p_default
                    elif p_type == "file_dropdown":
                        import glob
                        extensions = ["*.tif", "*.tiff", "*.am", "*.png", "*.mhd", "*.dat"]
                        found_files = []
                        for ext in extensions:
                            found_files.extend(glob.glob(ext))
                            found_files.extend(glob.glob(ext.upper()))
                        found_files = sorted(list(set(found_files)))
                        if not found_files:
                            st.warning("No compatible files found in runs/ directory.")
                            args[p_name] = ""
                        else:
                            args[p_name] = st.selectbox(f"{p_name}", found_files, key=f"func_arg_{p_name}", help=p_desc)
                    elif p_type == "type_dropdown":
                        args[p_name] = st.selectbox(f"{p_name}", ["VxlImgU16", "VxlImgU8", "VxlImgF32"], key=f"func_arg_{p_name}", help=p_desc)
                    else:
                        args[p_name] = st.text_input(f"{p_name}", value=str(p_default), help=p_desc, key=f"func_arg_{p_name}")
        else:
            st.info("This function does not take any arguments.")

        if selected_func != "loadImg":
            st.write("---")
            st.write("##### Execution Options:")
            col_opt1, col_opt2 = st.columns([1, 1])
            with col_opt1:
                out_var_name = st.text_input("Output Variable Name", value=f"{selected_var}_filtered" if selected_var else "img_filtered")
            with col_opt2:
                copy_on_write = st.checkbox("Copy first (protect original image)", value=True, help="If unchecked, the operation is run in-place modifying the selected variable.")

        if st.button("▶️ Run Function", key="btn_run_interactive_func", width="stretch"):
            try:
                if selected_func == "loadImg":
                    filename = args["filename"]
                    img_type = args["img_type"]
                    var_name = args["new_var_name"]
                    if not filename:
                        st.error("Please select a file to load.")
                        st.stop()

                    if img_type == "VxlImgU16":
                        loaded_obj = st.session_state.original_VxlImgU16(filename)
                    elif img_type == "VxlImgU8":
                        loaded_obj = st.session_state.original_VxlImgU8(filename)
                    else:
                        loaded_obj = st.session_state.original_VxlImgF32(filename)

                    cache_key = f"{img_type}_{os.path.abspath(filename)}"
                    st.session_state.image_cache[cache_key] = loaded_obj
                    st.session_state.workspace_vars[var_name] = loaded_obj
                    st.session_state.processed_image = loaded_obj

                    command_line = f"{var_name} = ik.{img_type}('{filename}')"
                    if st.session_state.session_commands:
                        st.session_state.session_commands += f"\n\n{command_line}"
                    else:
                        st.session_state.session_commands = command_line

                    st.success(f"Loaded {filename} as `{var_name}`!")
                    st.rerun()
                else:
                    # Prepare object to run on
                    if copy_on_write:
                        run_obj = img.copy()
                    else:
                        run_obj = img

                    # Execute
                    func_to_run = getattr(run_obj, selected_func)
                    result = func_to_run(**args)

                    # If result is VxlImg, use it, otherwise use run_obj
                    if isinstance(result, (st.session_state.original_VxlImgU16,
                                        st.session_state.original_VxlImgU8,
                                        st.session_state.original_VxlImgF32)):
                        output_img = result
                    else:
                        output_img = run_obj

                    # Save to workspace vars
                    st.session_state.workspace_vars[out_var_name] = output_img
                    st.session_state.processed_image = output_img

                    # Generate Python command line
                    args_str = ", ".join(f"{k}={repr(v)}" for k, v in args.items())
                    if copy_on_write:
                        command_line = f"{out_var_name} = {selected_var}.copy()\n{out_var_name}.{selected_func}({args_str})"
                    else:
                        command_line = f"{out_var_name} = {selected_var}\n{out_var_name}.{selected_func}({args_str})"

                    # Append to history
                    if st.session_state.session_commands:
                        st.session_state.session_commands += f"\n\n{command_line}"
                    else:
                        st.session_state.session_commands = command_line

                    st.success(f"Successfully executed `{selected_func}`! Output stored as `{out_var_name}`.")
                    st.rerun()
            except Exception as run_err:
                st.error(f"Execution failed: {run_err}")
                st.code(traceback.format_exc())

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
                    caption=f"`{axis.split()[0]}` @ `{slice_idx}` / `{max_slice}` │ color: `{int(min_contrast)}-{int(max_contrast)}` `{data.dtype}` │ span: `{shape}` × `{img.voxelSize}` + `{img.origin}`",
                    width="stretch"
                )
            except Exception as slice_err:
                st.error(f"Error rendering image slice from memory: {slice_err}")

