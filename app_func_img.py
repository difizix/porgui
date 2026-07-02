import streamlit as st
import os
import numpy as np
import traceback
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
    "vtkXdmfScreenshot": ("pyvtk.vtkXdmfScreenshot", "make_parser", "main"),
    "vtkXdmfAnimate": ("pyvtk.vtkXdmfAnimate", "make_parser", "main"),
    "vtkFoamEnd2Png": ("pyvtk.vtkFoamEnd2Png", "make_parser", "main"),
    "vtkFoamAnimate": ("pyvtk.vtkFoamAnimate", "make_parser", "main"),
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
# TAB 2: INTERACTIVE VISUALIZER
# ----------------------------------------------------
def render_imgpro_tab():
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
            c1, c2 = st.columns([2, 3])
            with c1:
                st.markdown("<div style='padding-top: 6px;'><b>Active Image Variable:</b></div>", unsafe_allow_html=True)
            with c2:
                selected_var = st.selectbox("Select Active Image Variable", var_options, index=0, key="active_var_selectbox", label_visibility="collapsed")
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
        else:
            st.info("No image loaded yet. Run a workflow or upload an image to begin.")


        # 🛠️ Interactive Function Executor Section
        st.markdown('<div class="card-title">🛠️ Interactive Function Executor</div>', unsafe_allow_html=True)

        # Get list of functions
        standalone_options = list(STANDALONE_FUNCTIONS.keys())
        available_standalones = [f for f in standalone_options if f in CURATED_METHODS]
        if img is not None:
            func_options = sorted(list(CURATED_METHODS.keys()))
        else:
            func_options = sorted(list(PYTHON_FUNCTIONS.keys()) + available_standalones)

        c1_fn, c2_fn = st.columns([2, 3])
        with c1_fn:
            st.markdown("<div style='padding-top: 6px;'><b>Function to Execute:</b></div>", unsafe_allow_html=True)
        with c2_fn:
            selected_func = st.selectbox("Function to Execute:", func_options, key="exec_func_sel", label_visibility="collapsed")

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
                out_var_name = st.text_input("Output Variable Name", value=f"{selected_var}_filtered" if selected_var else "img_filtered")
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
                st.session_state.generated_code = args_to_cmd_line(selected_func, args, copy_on_write, selected_var, out_var_name, is_standalone)
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
                    # Prepare object to run on
                    if copy_on_write:
                        run_obj = img.copy()
                    else:
                        run_obj = img

                    # Execute
                    func_to_run = getattr(run_obj, selected_func)
                    result, stdout = run_capturing_output(func_to_run, **args)
                    st.session_state.img_stdout = stdout.strip() # TODO addargs_to_cmd_line(selected_func, args, copy_on_write, selected_var, out_var_name, is_standalone)

                    # If result is VxlImg, use it, otherwise use run_obj
                    if isinstance(result, (st.session_state.original_VxlImgU16,
                                        st.session_state.original_VxlImgU8,
                                        st.session_state.original_VxlImgI32,
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

