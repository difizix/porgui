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
        transform: translateY(-2px);
    }
    
    .card-title {
        font-size: 1.25rem;
        font-weight: 600;
        margin-bottom: 12px;
        color: #58a6ff;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    
    /* Terminal logs styling */
    .terminal-container {
        background-color: #0d1117;
        border-radius: 8px;
        padding: 16px;
        border: 1px solid #30363d;
        max-height: 400px;
        overflow-y: auto;
    }
    
    /* Smooth button styling */
    .stButton>button {
        background-color: #21262d;
        color: #c9d1d9;
        border: 1px solid #30363d;
        border-radius: 8px;
        padding: 8px 16px;
        font-weight: 600;
        transition: all 0.2s ease;
    }
    
    .stButton>button:hover {
        background-color: #238636;
        border-color: #2ea043;
        color: white;
        box-shadow: 0 0 8px rgba(46, 160, 67, 0.4);
    }
    
    .save-btn>div>button {
        background-color: #21262d;
        border-color: #30363d;
    }
    
    .save-btn>div>button:hover {
        background-color: #1f6feb;
        border-color: #388bfd;
        color: white;
        box-shadow: 0 0 8px rgba(56, 139, 253, 0.4);
    }
    
    /* Title gradient */
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

# Headings
st.markdown('<div class="title-gradient">🔬 image3kit Workflow Studio</div>', unsafe_allow_html=True)
st.markdown("<p style='color: #8b949e; margin-top:-10px; margin-bottom:25px;'>An interactive workbench that preserves CLI scripts as the core workflow</p>", unsafe_allow_html=True)

# Import image3kit inside a safe block
try:
    import image3kit as ik
except ImportError:
    st.error("image3kit is not installed in this environment. Please run `pip install ./image3kit` to compile and install it.")
    st.stop()

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

# Patch factory creator
def get_patched_class(original_cls, class_name):
    class PatchedClass(original_cls):
        def __init__(self, filepath, *args, **kwargs):
            # Resolve absolute path to identify the file uniquely
            abs_path = os.path.abspath(filepath)
            cache_key = f"{class_name}_{abs_path}"

            # If cached in st.session_state, copy its underlying data in memory
            if cache_key in st.session_state.image_cache:
                cached_obj = st.session_state.image_cache[cache_key]
                # Initialize using the cached object configuration
                super().__init__(cached_obj.shape, 0)
                self.voxelSize = cached_obj.voxelSize
                self.origin = cached_obj.origin
                # Fast copy data buffer
                self.data[:] = cached_obj.data
            else:
                # Load from file using C++ implementation
                super().__init__(filepath, *args, **kwargs)
                # Store the loaded image object in the cache (persists in RAM)
                st.session_state.image_cache[cache_key] = self.copy()
    return PatchedClass

# Apply monkeypatching globally to image3kit modules
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

# Scan directory for workspace scripts
script_files = sorted(glob.glob("*.py"))
# Filter out this GUI file
script_files = [f for f in script_files if f != "gui.py" and f != "app.py"]

# ----------------------------------------------------
# SIDEBAR CONTROLS
# ----------------------------------------------------
st.sidebar.markdown('<div class="card-title">⚙️ Workflow Setup</div>', unsafe_allow_html=True)

# Select Python script
selected_script = st.sidebar.selectbox("Select Core CLI Script", script_files if script_files else ["No scripts found"])

# Input CLI arguments (arguments to mock sys.argv)
args_input = st.sidebar.text_input(
    "CLI Input Arguments",
    value="Water_saturated.tif" if os.path.exists("Water_saturated.tif") else ""
)

# Cache management status card
st.sidebar.markdown("---")
st.sidebar.markdown('<div class="card-title">🧠 In-Memory Cache</div>', unsafe_allow_html=True)
if st.session_state.image_cache:
    for k in st.session_state.image_cache.keys():
        name = os.path.basename(k.split("_")[-1])
        st.sidebar.code(f"• {name} (Loaded)", language="text")
    if st.sidebar.button("Clear Memory Cache"):
        st.session_state.image_cache.clear()
        st.sidebar.success("Cache cleared!")
        st.rerun()
else:
    st.sidebar.info("Cache is empty. Images will be loaded on first script execution.")

# ----------------------------------------------------
# MAIN STUDIO INTERFACE
# ----------------------------------------------------
if not script_files:
    st.warning("No python scripts found in the current directory. Create a CLI script like `dering_segment.py` to get started.")
    st.stop()

# Read the script code
if selected_script:
    with open(selected_script, "r") as f:
        script_code = f.read()
else:
    script_code = ""

# Split main window into tabs
tab_workflow, tab_viewer = st.tabs(["💻 Workflow Studio", "🖼️ Interactive Visualizer"])

# TAB 1: WORKFLOW STUDIO
with tab_workflow:
    col_code, col_run_panel = st.columns([3, 2])

    run_triggered = False

    with col_code:
        st.markdown('<div class="card-title">📝 Code Editor</div>', unsafe_allow_html=True)

        # Display rich code editor or fallback text area
        try:
            from streamlit_code_editor import code_editor
            custom_buttons = [
                {
                    "name": "Save Script",
                    "feather": "Save",
                    "hasText": True,
                    "event": "save",
                    "style": {"color": "#bc8cff", "borderColor": "#30363d"}
                },
                {
                    "name": "Run Workspace",
                    "feather": "Play",
                    "hasText": True,
                    "event": "run",
                    "style": {"color": "#58a6ff", "borderColor": "#30363d", "fontWeight": "bold"}
                }
            ]
            response = code_editor(
                script_code,
                lang="python",
                theme="monokai",
                buttons=custom_buttons,
                height=[25, 40]
            )
            edited_code = response.get("text", script_code)
            action_save = response.get("type") == "save"
            run_triggered = response.get("type") == "run"
        except ImportError:
            # Fallback layout if streamlit-code-editor is missing
            edited_code = st.text_area("Script Code", value=script_code, height=500)
            c_btn1, c_btn2 = st.columns(2)
            with c_btn1:
                action_save = st.button("💾 Save Script Changes")
            with c_btn2:
                run_triggered = st.button("🚀 Run Workflow")

        # Handle Save Event
        if action_save:
            with open(selected_script, "w") as f:
                f.write(edited_code)
            st.success(f"Changes saved successfully to `{selected_script}`! The script remains runnable directly via command line.")
            st.rerun()

    # Run execution block outside/before rendering outputs
    if run_triggered:
        stdout_buf = io.StringIO()
        stderr_buf = io.StringIO()

        # Setup CLI environment (mock sys.argv and absolute path workspace)
        original_argv = sys.argv
        sys.argv = [selected_script] + shlex.split(args_input)

        # Execute code inside custom namespace
        exec_namespace = {
            "__name__": "__main__",
            "__file__": os.path.abspath(selected_script),
            "image3kit": ik,
            "ik": ik
        }

        with st.spinner("Executing workflow..."):
            try:
                with redirect_stdout(stdout_buf), redirect_stderr(stderr_buf):
                    exec(edited_code, exec_namespace)

                st.session_state.console_output = stdout_buf.getvalue()
                st.toast("Workflow executed successfully!", icon="✅")

                # Parse image statistics from stdout
                lines = st.session_state.console_output.split("\n")
                stats = []
                for line in lines:
                    if "mean" in line and "std" in line:
                        stats.append(line.strip())
                st.session_state.parsed_stats = stats

                # Search namespace for any output VxlImg object to pass to the visualizer
                found_img = None
                for val in exec_namespace.values():
                    if isinstance(val, (st.session_state.original_VxlImgU16,
                                        st.session_state.original_VxlImgU8,
                                        st.session_state.original_VxlImgF32)):
                        found_img = val
                if found_img is not None:
                    st.session_state.processed_image = found_img

            except Exception as e:
                st.session_state.console_output = stdout_buf.getvalue() + "\n" + stderr_buf.getvalue() + "\n" + traceback.format_exc()
                st.error("Workflow failed with execution error.")
            finally:
                sys.argv = original_argv
                st.rerun()

    # Render Console logs below the editor in col_code
    with col_code:
        st.markdown('<div class="card-title" style="margin-top: 20px;">🖥️ Standard Output (stdout)</div>', unsafe_allow_html=True)
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.text_area("Console Logs", value=st.session_state.console_output, height=250, key="log_area", disabled=True, label_visibility="collapsed")
        st.markdown('</div>', unsafe_allow_html=True)

    with col_run_panel:
        st.markdown('<div class="card-title">📊 Execution Results & Stats</div>', unsafe_allow_html=True)

        # Render Collapsible parsed printInfo statistics
        with st.expander("📈 Collapsible printInfo Stats", expanded=True):
            if st.session_state.parsed_stats:
                for stat in st.session_state.parsed_stats:
                    st.markdown(f"• `{stat}`")
            else:
                st.info("No printInfo() output parsed yet. Run a workflow that outputs statistics.")

# TAB 2: INTERACTIVE VISUALIZER
with tab_viewer:
    st.markdown('<div class="card-title">🖼️ Live 3D Slice Viewer (In-Memory)</div>', unsafe_allow_html=True)

    img = st.session_state.processed_image

    if img is not None:
        try:
            data = img.data
            shape = data.shape

            # Interactive visualizer controls
            col_v_ctrl, col_v_canvas = st.columns([1, 2])

            with col_v_ctrl:
                st.markdown("<p style='font-size:0.95rem; color:#8b949e;'>Adjust visual representation of the cached 3D array:</p>", unsafe_allow_html=True)

                # Image metadata table
                st.markdown(f"""
                | Property | Value |
                | :--- | :--- |
                | **Data Type** | `{data.dtype}` |
                | **Voxel Shape** | `{shape}` (Z, Y, X) |
                | **Voxel Size** | `{img.voxelSize}` |
                | **Origin** | `{img.origin}` |
                """)

                # Axis selection
                axis = st.selectbox("Slice View Axis", ["Z (Slice index)", "Y (Coronal index)", "X (Sagittal index)"])
                axis_idx = 0 if "Z" in axis else (1 if "Y" in axis else 2)

                # Slice index slider
                max_slice = shape[axis_idx] - 1
                slice_idx = st.slider("Select Slice Index", 0, int(max_slice), int(max_slice // 2))

                # Grayscale windowing (contrast) adjustment
                data_min = float(data.min())
                data_max = float(data.max())

                # Default ranges matching dering_segment.py defaults
                val_range = st.slider(
                    "Contrast Range Window",
                    data_min, data_max,
                    (max(data_min, 3000.0), min(data_max, 13500.0))
                )
                min_contrast, max_contrast = val_range

                st.info("Visual representation is computed directly in RAM without any disk write operation.")

            with col_v_canvas:
                # Slicing the numpy array based on chosen axis
                if axis_idx == 0:
                    slice_2d = data[slice_idx, :, :]
                elif axis_idx == 1:
                    slice_2d = data[:, slice_idx, :]
                else:
                    slice_2d = data[:, :, slice_idx]

                # Fast scaling and windowing
                norm_slice = np.clip((slice_2d - min_contrast) / (max_contrast - min_contrast) * 255.0, 0, 255).astype(np.uint8)
                pil_image = Image.fromarray(norm_slice)

                # Render using Streamlit's container width
                st.image(
                    pil_image,
                    caption=f"Axis: {axis.split()[0]} | Slice: {slice_idx} / {max_slice} | Window: [{int(min_contrast)}, {int(max_contrast)}]",
                    use_container_width=True
                )
        except Exception as slice_err:
            st.error(f"Error rendering image slice from memory: {slice_err}")
            st.code(traceback.format_exc())
    else:
        st.info("No active image found in memory workspace. Run a workflow that defines an image variable (e.g., `img`).")

    # Render static plot outputs if generated in fig/
    st.markdown("---")
    st.markdown('<div class="card-title">📈 Saved Disk Visualizations (fig/ directory)</div>', unsafe_allow_html=True)
    if os.path.exists("fig"):
        fig_files = sorted(glob.glob("fig/*.png") + glob.glob("fig/*.svg"))
        if fig_files:
            # Let user select which saved plot to display
            selected_fig = st.selectbox("Select saved chart / slice file to view", fig_files)
            if selected_fig:
                st.image(selected_fig, caption=os.path.basename(selected_fig), use_container_width=True)
        else:
            st.info("No generated files found in `fig/` directory.")
    else:
        st.info("No `fig/` directory exists yet. Run a script containing `plotAll()` or `plotSlice()` to create one.")
