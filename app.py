import streamlit as st
import sys
import os
import io
import shlex
import traceback
import glob
from contextlib import redirect_stdout, redirect_stderr
from PIL import Image
import numpy as np

# Set page configuration with a premium wide layout
st.set_page_config(
    layout="wide",
    page_title="image3kit Workflow Studio",
    page_icon="🔬"
)

# Custom CSS for rich aesthetics (sleek dark theme, clean typography, cards, and animations)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&family=JetBrains+Mono:wght@400;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif;
    }
    
    code, pre, [class*="stCode"] {
        font-family: 'JetBrains Mono', monospace !important;
    }
    
    .stApp {
        background: linear-gradient(135deg, #0e1117 0%, #161b22 100%);
        color: #c9d1d9;
    }
    .stMainBlockContainer {
        padding: 0 1rem 10rem 1rem;
    }
    .stAppHeader {
        z-index: -1 !important;
    }

    /* Transparent Header */
    header[data-testid="stHeader"] {
        background: transparent !important;
    }

    /* Premium card design */
    .card {
        background-color: #1f242c;
        border-radius: 12px;
        padding: 20px;
        border: 1px solid #30363d;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25);
        margin-bottom: 20px;
        transition: all 0.3s ease;
    }
    
    .card:hover {
        border-color: #58a6ff;
        box-shadow: 0 4px 25px rgba(88, 166, 255, 0.15);
    }
    
    .card-title {
        font-size: 1.25rem;
        font-weight: 600;
        margin-bottom: 15px;
        color: #58a6ff;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    
    /* Styling Streamlit buttons to look premium */
    div.stButton > button {
        background: linear-gradient(180deg, #21262d 0%, #161b22 100%);
        color: #c9d1d9;
        border: 1px solid #30363d;
        border-radius: 6px;
        padding: 6px 16px;
        font-weight: 600;
        transition: all 0.2s ease;
    }
    
    div.stButton > button:hover {
        color: #ffffff;
        border-color: #8b949e;
        background: #30363d;
    }
    
    div.stButton > button:active {
        background: #21262d;
    }

    /* Custom Title Style */
    .title-gradient {
        background: linear-gradient(90deg, #58a6ff 0%, #bc8cff 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 700;
        font-size: 2.5rem;
        margin-bottom: 5px;
    }
</style>
""", unsafe_allow_html=True)

# Import image3kit inside a safe block
try:
    import image3kit as ik
except ImportError:
    st.error("image3kit is not installed in this environment. Please run `pip install ./image3kit` to compile and install it.")
    st.stop()

# Helper function to extract images
def update_workspace_vars(namespace):
    if "workspace_vars" not in st.session_state:
        st.session_state.workspace_vars = {}
    found_img = None
    if "img" in namespace and isinstance(namespace["img"], (
        st.session_state.original_VxlImgU16,
        st.session_state.original_VxlImgU8,
        st.session_state.original_VxlImgF32
    )):
        found_img = namespace["img"]
    else:
        for val in namespace.values():
            if isinstance(val, (st.session_state.original_VxlImgU16,
                                st.session_state.original_VxlImgU8,
                                st.session_state.original_VxlImgF32)):
                found_img = val
                break
    if found_img is not None:
        st.session_state.processed_image = found_img
        st.session_state.workspace_vars["img"] = found_img

# ----------------------------------------------------
# TRANSPARENT MEMORY CACHING (Monkeypatching loader classes)
# ----------------------------------------------------
if "image_cache" not in st.session_state:
    st.session_state.image_cache = {}

# Save references to original classes
if "original_VxlImgU16" not in st.session_state:
    st.session_state.original_VxlImgU16 = ik.VxlImgU16
    st.session_state.original_VxlImgU8 = ik.VxlImgU8
    st.session_state.original_VxlImgF32 = ik.VxlImgF32

def get_patched_class(original_cls, class_name):
    class PatchedClass(original_cls):
        def __init__(self, *args, **kwargs):
            if len(args) == 1 and isinstance(args[0], str):
                abs_path = os.path.abspath(args[0])
                cache_key = f"{class_name}_{abs_path}"
                
                # Check if cached in memory
                if cache_key in st.session_state.image_cache:
                    cached_obj = st.session_state.image_cache[cache_key]
                    super().__init__(cached_obj)
                    self.voxelSize = cached_obj.voxelSize
                    self.origin = cached_obj.origin
                    return
                else:
                    super().__init__(*args, **kwargs)
                    st.session_state.image_cache[cache_key] = self.copy()
            else:
                super().__init__(*args, **kwargs)
                
    return PatchedClass

ik.VxlImgU16 = get_patched_class(st.session_state.original_VxlImgU16, "VxlImgU16")
ik.VxlImgU8 = get_patched_class(st.session_state.original_VxlImgU8, "VxlImgU8")
ik.VxlImgF32 = get_patched_class(st.session_state.original_VxlImgF32, "VxlImgF32")


# ----------------------------------------------------
# APPLICATION STATE & ENVIRONMENT SETUP
# ----------------------------------------------------
if "console_output" not in st.session_state:
    st.session_state.console_output = ""
if "last_executed_script" not in st.session_state:
    st.session_state.last_executed_script = None
if "processed_image" not in st.session_state:
    st.session_state.processed_image = None
if "parsed_stats" not in st.session_state:
    st.session_state.parsed_stats = []
if "workspace_vars" not in st.session_state:
    st.session_state.workspace_vars = {}
if "session_commands" not in st.session_state:
    st.session_state.session_commands = ""

# Populate files lists for app_plots / app_logs
from app_utils import get_output_files
if "png_files" not in st.session_state or "log_files" not in st.session_state:
    pngs, logs = get_output_files()
    st.session_state.png_files = pngs
    st.session_state.log_files = logs

if "applied_keep" not in st.session_state:
    st.session_state.applied_keep = ""
if "applied_remove" not in st.session_state:
    st.session_state.applied_remove = ""
if "filter_applied" not in st.session_state:
    st.session_state.filter_applied = False
if "filter_version" not in st.session_state:
    st.session_state.filter_version = 0

# Scan directory for workspace scripts
script_files = sorted(glob.glob("*.py"))
script_files = [f for f in script_files if f != "gui.py" and f != "app.py" and f != "app_plots.py" and f != "app_logs.py" and f != "app_utils.py"]

# Headings
st.markdown('<div class="title-gradient">🔬 image3kit Workflow Studio</div>', unsafe_allow_html=True)
st.markdown("<p style='color: #8b949e; margin-top:-10px; margin-bottom:25px;'>An interactive workbench that preserves CLI scripts as the core workflow</p>", unsafe_allow_html=True)

# Main Tab Layout
tabs = st.tabs(["💻 Workflow Studio", "🖼️ Interactive Visualizer", "📊 Saved Plots", "📄 Log Files"])

# ----------------------------------------------------
# TAB 1: WORKFLOW STUDIO
# ----------------------------------------------------
with tabs[0]:
    if not script_files:
        st.warning("⚠️ No Python workflow scripts (*.py) found in the root workspace directory.")
    else:
        # Consolidation bar at the top
        col_select, col_args, col_actions = st.columns([1.5, 2, 1.5])
        
        with col_select:
            selected_script = st.selectbox(
                "Select Workflow Script", 
                script_files, 
                index=0 if "last_executed_script" not in st.session_state or st.session_state.last_executed_script not in script_files else script_files.index(st.session_state.last_executed_script),
                label_visibility="collapsed"
            )
            
        with col_args:
            args_input = st.text_input(
                "Script CLI Arguments",
                value="",
                placeholder="e.g. --x0 374 --y0 853",
                label_visibility="collapsed"
            )
            
        with col_actions:
            btn_col1, btn_col2, btn_col3 = st.columns([1, 1, 1.2])
            with btn_col1:
                run_pressed = st.button("▶️ Run", key="run_script_btn", use_container_width=True)
            with btn_col2:
                show_cache = st.button("💾 Cache", key="cache_status_btn", use_container_width=True)
            with btn_col3:
                clear_cache = st.button("🧹 Clear", key="clear_cache_btn", use_container_width=True)
        
        if clear_cache:
            if st.session_state.image_cache:
                for k in list(st.session_state.image_cache.keys()):
                    del st.session_state.image_cache[k]
                st.session_state.workspace_vars.clear()
                st.session_state.processed_image = None
                st.success("Successfully cleaned in-memory caches.")
                st.rerun()
            else:
                st.info("No active elements in memory.")

        if show_cache:
            st.markdown('<div class="card-title">💾 In-Memory Cache Status</div>', unsafe_allow_html=True)
            st.markdown('<div class="card">', unsafe_allow_html=True)
            if st.session_state.image_cache or st.session_state.workspace_vars:
                if st.session_state.image_cache:
                    st.write("**Loader Image cache (monkeypatched paths):**")
                    for k in st.session_state.image_cache.keys():
                        st.code(k)
                if st.session_state.workspace_vars:
                    st.write("**Interactive Workspace Variables:**")
                    for k, v in st.session_state.workspace_vars.items():
                        st.code(f"{k} : {type(v).__name__}")
            else:
                st.info("No objects currently cached in RAM.")
            st.markdown('</div>', unsafe_allow_html=True)

        if selected_script:
            with open(selected_script, "r") as f:
                script_code = f.read()
        else:
            script_code = ""

        try:
            from code_editor import code_editor
            response = code_editor(
                script_code,
                lang="python",
                theme="monokai",
                options={"wrap": True, "autoScrollEditorIntoView": True},
                key="code_editor_component"
            )
            if response.get("type") == "submit" or (response.get("text") and response["text"] != script_code):
                with open(selected_script, "w") as f:
                    f.write(response["text"])
                script_code = response["text"]
        except ImportError:
            edited_code = st.text_area("Script Code Editor", value=script_code, height=450, key="fallback_editor")
            if edited_code != script_code:
                with open(selected_script, "w") as f:
                    f.write(edited_code)
                script_code = edited_code

        # Execution logic
        if run_pressed and selected_script:
            st.session_state.last_executed_script = selected_script
            
            original_cwd = os.getcwd()
            os.makedirs("runs", exist_ok=True)
            
            original_argv = sys.argv
            try:
                parsed_args = shlex.split(args_input)
                # Resolve relative input file paths to absolute paths before chdir
                for idx, arg in enumerate(parsed_args):
                    if os.path.exists(arg):
                        parsed_args[idx] = os.path.abspath(arg)
                sys.argv = [selected_script] + parsed_args
            except Exception as arg_err:
                st.error(f"Failed to parse arguments: {arg_err}")
                st.stop()
                
            exec_namespace = {
                "__name__": "__main__",
                "__file__": os.path.abspath(os.path.join(original_cwd, selected_script)),
                "image3kit": ik,
            }
            for k, v in st.session_state.workspace_vars.items():
                exec_namespace[k] = v
            
            stdout_buf = io.StringIO()
            stderr_buf = io.StringIO()
            log_path = os.path.join(original_cwd, "runs", os.path.splitext(selected_script)[0] + ".log")
            
            os.chdir("runs")
            try:
                with redirect_stdout(stdout_buf), redirect_stderr(stderr_buf):
                    exec(script_code, exec_namespace)
                
                captured_combined = stdout_buf.getvalue() + "\n" + stderr_buf.getvalue()
                st.session_state.console_output = captured_combined
                st.success("Workflow completed successfully!")
                
                with open(log_path, "w") as lf:
                    lf.write(f"# Script: {selected_script}\n")
                    lf.write(f"# Args: {args_input}\n")
                    lf.write("# Status: OK\n\n")
                    lf.write(captured_combined)

                lines = st.session_state.console_output.split("\n")
                stats = []
                for line in lines:
                    if "mean" in line and "std" in line:
                        stats.append(line.strip())
                st.session_state.parsed_stats = stats

                update_workspace_vars(exec_namespace)

            except Exception as e:
                err_text = stdout_buf.getvalue() + "\n" + stderr_buf.getvalue() + "\n" + traceback.format_exc()
                st.session_state.console_output = err_text
                st.error("Workflow failed with execution error.")

                with open(log_path, "w") as lf:
                    lf.write(f"# Script: {selected_script}\n")
                    lf.write(f"# Args: {args_input}\n")
                    lf.write("# Status: ERROR\n\n")
                    lf.write(err_text)

                update_workspace_vars(exec_namespace)
            finally:
                os.chdir(original_cwd)
                sys.argv = original_argv
                pngs, logs = get_output_files()
                st.session_state.png_files = pngs
                st.session_state.log_files = logs
                st.rerun()

        # Render output display
        st.markdown('<div class="card-title" style="margin-top: 20px;">🖥️ Standard Output (stdout)</div>', unsafe_allow_html=True)
        st.markdown('<div class="card">', unsafe_allow_html=True)
        log_path = os.path.join("runs", os.path.splitext(selected_script)[0] + ".log")
        if os.path.exists(log_path):
            with open(log_path, "r") as lf:
                log_display = lf.read()
        else:
            log_display = st.session_state.console_output
        st.text_area("Console Logs", value=log_display, height=250, disabled=True, label_visibility="collapsed")
        st.markdown('</div>', unsafe_allow_html=True)


# ----------------------------------------------------
# TAB 2: INTERACTIVE VISUALIZER
# ----------------------------------------------------
with tabs[1]:
    st.markdown('<div class="card-title">🖼️ Live 3D Slice Viewer (In-Memory)</div>', unsafe_allow_html=True)
    img = st.session_state.processed_image

    if img is not None:
        try:
            data = img.data
            shape = data.shape

            col_v_ctrl, col_v_canvas = st.columns([1, 2])
            with col_v_ctrl:
                st.markdown(f"""
                | Property | Value |
                | :--- | :--- |
                | **Data Type** | `{data.dtype}` |
                | **Voxel Shape** | `{shape}` (Z, Y, X) |
                | **Voxel Size** | `{img.voxelSize}` |
                | **Origin** | `{img.origin}` |
                """)
                axis = st.selectbox("Slice View Axis", ["Z (Slice index)", "Y (Coronal index)", "X (Sagittal index)"])
                axis_idx = 0 if "Z" in axis else (1 if "Y" in axis else 2)
                max_slice = shape[axis_idx] - 1
                slice_idx = st.slider("Select Slice Index", 0, int(max_slice), int(max_slice // 2))
                data_min = float(data.min())
                data_max = float(data.max())
                val_range = st.slider(
                    "Contrast Range Window",
                    data_min, data_max,
                    (max(data_min, 3000.0), min(data_max, 13500.0))
                )
                min_contrast, max_contrast = val_range

            with col_v_canvas:
                if axis_idx == 0:
                    slice_2d = data[slice_idx, :, :]
                elif axis_idx == 1:
                    slice_2d = data[:, slice_idx, :]
                else:
                    slice_2d = data[:, :, slice_idx]
                if max_contrast > min_contrast:
                    norm_slice = np.clip((slice_2d - min_contrast) / (max_contrast - min_contrast) * 255.0, 0, 255).astype(np.uint8)
                else:
                    norm_slice = np.zeros_like(slice_2d, dtype=np.uint8)
                pil_image = Image.fromarray(norm_slice)
                st.image(
                    pil_image,
                    caption=f"Axis: {axis.split()[0]} | Slice: {slice_idx} / {max_slice} | Window: [{int(min_contrast)}, {int(max_contrast)}]",
                    use_container_width=True
                )
        except Exception as slice_err:
            st.error(f"Error rendering image slice from memory: {slice_err}")
    else:
        st.info("No active image found in memory workspace. Run a workflow that defines an image variable (e.g. `img`).")


# ----------------------------------------------------
# TAB 3: SAVED PLOTS
# ----------------------------------------------------
with tabs[2]:
    import app_plots
    app_plots.render_plots()

# ----------------------------------------------------
# TAB 4: LOG FILES
# ----------------------------------------------------
with tabs[3]:
    import app_logs
    app_logs.render_logs()
