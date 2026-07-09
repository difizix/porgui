import streamlit as st
import os
import numpy as np
import traceback
import image3kit as ik
import PIL
import sys

from utils_app import get_module_func_args, args_to_cmd_line, func_args_from_inspect, get_vxlImg_func_args, run_capturing_output, FormParam
from app_common import render_parseargs
from user_funcs import loadImg, mextract, snflow

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
    "loadImg": loadImg,
    "mextract": mextract,
    "snflow": snflow,
}

CURATED_METHODS = {
    "cropD":        get_vxlImg_func_args("cropD"),
    "medianFilter": get_vxlImg_func_args("medianFilter"),
    "dering":       get_vxlImg_func_args("dering"),
    "segment2":     get_vxlImg_func_args("segment2"),
    "threshold101": get_vxlImg_func_args("threshold101"),
    "write8bit":    get_vxlImg_func_args("write8bit"),
    "distMapExtrude": get_vxlImg_func_args("distMapExtrude"),
    "VxlDifShort":  get_vxlImg_func_args("VxlDifShort"),
    "VxlMinizVar":  get_vxlImg_func_args("VxlMinizVar"),
}

#  TODO Since now U16 has more functions that int and u8, 
#   we got to make sure the functions exposed depend on the image type.
#  Actually we got to split the logic for rendered image (right col)
#  and the arguments of the function that is executed (via a drop-down that defaults to the image being viewed if compatible type).
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

    vxl_types = (
        st.session_state.original_VxlImgU16,
        st.session_state.original_VxlImgU8,
        st.session_state.original_VxlImgI32,
        st.session_state.original_VxlImgF32
    )
    if st.session_state.processed_image is not None and isinstance(st.session_state.processed_image, vxl_types) and "img" not in st.session_state.workspace_vars:
        st.session_state.workspace_vars["img"] = st.session_state.processed_image

    img = None
    col_v_ctrl, col_v_canvas = st.columns([2, 3])

    with col_v_ctrl:

        var_options = [k for k, v in st.session_state.workspace_vars.items() if isinstance(v, vxl_types)]
        if var_options:
            if "active_var" not in st.session_state or st.session_state.active_var not in var_options:
                st.session_state.active_var = var_options[0]

            c1, c2 = st.columns([2, 3])
            with c1:
                st.markdown("<div style='padding-top: 6px;'><b>Viewed Image Variable:</b></div>", unsafe_allow_html=True)
            with c2:
                selected_var = st.selectbox(
                    "Select Viewed Image Variable",
                    var_options,
                    index=var_options.index(st.session_state.active_var),
                    key="active_var_selectbox_widget",
                    label_visibility="collapsed"
                )
            st.session_state.active_var = selected_var
            img = st.session_state.workspace_vars[selected_var]
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
                        if up_img_type == "VxlImgU16":
                            loaded_obj = st.session_state.original_VxlImgU16(temp_path)
                        elif up_img_type == "VxlImgU8":
                            loaded_obj = st.session_state.original_VxlImgU8(temp_path)
                        elif up_img_type == "VxlImgI32":
                            loaded_obj = st.session_state.original_VxlImgI32(temp_path)
                        else:
                            loaded_obj = st.session_state.original_VxlImgF32(temp_path)

                        cache_key = f"{up_img_type}_{os.path.abspath(temp_path)}"
                        st.session_state.image_cache[cache_key] = loaded_obj
                        st.session_state.workspace_vars[new_var_name] = loaded_obj
                        st.session_state.processed_image = loaded_obj
                        st.session_state.active_var = new_var_name
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
        default_func = "loadImg"
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
                default_out_name = f"{ref_var}_filtered" if ref_var else "img_filtered"
                # Prevent overwriting existing workspace variables by making default name unique
                if "workspace_vars" in st.session_state:
                    base_name = default_out_name
                    if base_name in st.session_state.workspace_vars:
                        suffix = 1
                        while f"{base_name}_{suffix}" in st.session_state.workspace_vars:
                            suffix += 1
                        default_out_name = f"{base_name}_{suffix}"
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
            try:
                is_python_func = selected_func in PYTHON_FUNCTIONS
                if is_python_func:
                    func_to_call = PYTHON_FUNCTIONS[selected_func]
                    # Extract the output variable name from the args if present
                    var_name = args.pop("new_var_name", None) or out_var_name or selected_func
                    filename = args.get("filename", "")
                    if "filename" in args and not args["filename"]:
                        st.error("Please select a file to load.")
                        st.stop()
                    result, stdout = run_capturing_output(func_to_call, **args)
                    st.session_state.img_stdout = stdout.strip() # TODO add args_to_cmd_line(selected_func, args, copy_on_write, selected_var, out_var_name, is_standalone)

                    is_vxl = isinstance(result, (
                        st.session_state.original_VxlImgU16,
                        st.session_state.original_VxlImgU8,
                        st.session_state.original_VxlImgI32,
                        st.session_state.original_VxlImgF32,
                    ))
                    if is_vxl:
                        cache_key = f"{type(result).__name__}_{os.path.abspath(filename)}"
                        st.session_state.image_cache[cache_key] = result
                        st.session_state.workspace_vars[var_name] = result
                        st.session_state.processed_image = result
                        st.session_state.active_var = var_name
                        st.session_state.pending_active_var = var_name

                    args_str = ", ".join(f"{k}={repr(v)}" for k, v in args.items())
                    command_line = f"{var_name} = {selected_func}({args_str})"
                    if st.session_state.session_commands:
                        st.session_state.session_commands += f"\n\n{command_line}"
                    else:
                        st.session_state.session_commands = command_line

                    st.session_state.img_success = f"Executed `{selected_func}`, result stored as `{var_name}`."
                    st.rerun()
                elif is_standalone:
                    def run_standalone():
                        _func, _ = get_module_func_args(*STANDALONE_FUNCTIONS[selected_func])
                        return _func(**args)
                    result, stdout = run_capturing_output(run_standalone)
                    st.session_state.img_stdout = stdout.strip() # TODO add args_to_cmd_line(selected_func, args, copy_on_write, selected_var, out_var_name, is_standalone)
                    
                    args_str = ", ".join(f"{k}={repr(v)}" for k, v in args.items())
                    command_line = f"import pyvtk.{selected_func} as {selected_func}\n{selected_func}.main()  # args: {args_str}"
                        
                    if st.session_state.session_commands:
                        st.session_state.session_commands += f"\n\n{command_line}"
                    else:
                        st.session_state.session_commands = command_line
                        
                    st.session_state.img_success = f"Successfully executed standalone command `{selected_func}`!"
                    st.rerun()
                else:
                    # Pop self from args if present, otherwise fallback to viewed image (selected_var)
                    target_var = args.pop("self", None)
                    if target_var:
                        target_img = st.session_state.workspace_vars.get(target_var)
                    else:
                        target_var = selected_var
                        target_img = st.session_state.workspace_vars.get(target_var) if target_var else None

                    if target_img is None:
                        st.error("No target image available to execute method on.")
                        st.stop()

                    # Prepare object to run on
                    if copy_on_write:
                        run_obj = target_img.copy()
                    else:
                        run_obj = target_img

                    # Execute
                    func_to_run = getattr(run_obj, selected_func)
                    result, stdout = run_capturing_output(func_to_run, **args)
                    st.session_state.img_stdout = stdout.strip()

                    # If result is VxlImg, use it, otherwise use run_obj
                    if isinstance(result, (st.session_state.original_VxlImgU16,
                                        st.session_state.original_VxlImgU8,
                                        st.session_state.original_VxlImgI32,
                                        st.session_state.original_VxlImgF32)):
                        raw_img = result
                    else:
                        raw_img = run_obj

                    # Wrap raw_img in its respective patched wrapper class to ensure consistency
                    output_img = raw_img
                    if isinstance(raw_img, st.session_state.original_VxlImgU16) and not isinstance(raw_img, ik.VxlImgU16):
                        output_img = ik.VxlImgU16(raw_img)
                    elif isinstance(raw_img, st.session_state.original_VxlImgU8) and not isinstance(raw_img, ik.VxlImgU8):
                        output_img = ik.VxlImgU8(raw_img)
                    elif isinstance(raw_img, st.session_state.original_VxlImgI32) and not isinstance(raw_img, ik.VxlImgI32):
                        output_img = ik.VxlImgI32(raw_img)
                    elif isinstance(raw_img, st.session_state.original_VxlImgF32) and not isinstance(raw_img, ik.VxlImgF32):
                        output_img = ik.VxlImgF32(raw_img)

                    # Save to workspace vars
                    st.session_state.workspace_vars[out_var_name] = output_img
                    st.session_state.processed_image = output_img
                    st.session_state.active_var = out_var_name
                    st.session_state.pending_active_var = out_var_name

                    # Generate Python command line
                    args_str = ", ".join(f"{k}={repr(v)}" for k, v in args.items())
                    if copy_on_write:
                        command_line = f"{out_var_name} = {target_var}.copy()\n{out_var_name}.{selected_func}({args_str})"
                    else:
                        command_line = f"{out_var_name} = {target_var}\n{out_var_name}.{selected_func}({args_str})"

                    # Append to history
                    if st.session_state.session_commands:
                        st.session_state.session_commands += f"\n\n{command_line}"
                    else:
                        st.session_state.session_commands = command_line

                    st.session_state.img_success = f"Successfully executed `{selected_func}`! Output stored as `{out_var_name}`."
                    st.rerun()
            except Exception as run_err:
                st.session_state.img_error = f"{run_err}\n\n{traceback.format_exc()}"
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
                    caption=f"`{axis.split()[0]}` @ `{slice_idx}` / `{max_slice}` │ color: `{int(min_contrast)}-{int(max_contrast)}` `{data.dtype}` │ span: `{shape}` × `{img.voxelSize}` + `{img.origin}`",
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