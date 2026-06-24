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
        /*display: none;*/
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
# st.markdown('<div class="title-gradient">🔬 image3kit Workflow Studio</div>', unsafe_allow_html=True)
# st.markdown("<p style='color: #8b949e; margin-top:-10px; margin-bottom:25px;'>An interactive workbench that preserves CLI scripts as the core workflow</p>", unsafe_allow_html=True)

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
# MAIN STUDIO INTERFACE
# ----------------------------------------------------
if not script_files:
    st.warning("No python scripts found in the current directory. Create a CLI script like `dering_segment.py` to get started.")
    st.stop()

# Split main window into tabs
tab_workflow, tab_viewer = st.tabs(["💻 Workflow Studio", "🖼️ Interactive Visualizer"])

# TAB 1: WORKFLOW STUDIO
with tab_workflow:
    run_triggered = False

    st.markdown('<div class="card-title">📝 Code Editor</div>', unsafe_allow_html=True)

    # 4-column row for controls and buttons (moved from sidebar / bottom)
    col1, col2, col3, col4 = st.columns([3, 3, 2, 2])

    with col1:
        selected_script = st.selectbox(
            "Select Script",
            script_files if script_files else ["No scripts found"]
        )

    with col2:
        args_input = st.text_input(
            "CLI Input Arguments",
            value="Dry.tif" if os.path.exists("Dry.tif") else ""
        )

    with col3:
        st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
        action_save = st.button("💾 Save Script Changes", use_container_width=True)

    with col4:
        st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
        run_triggered = st.button("🚀 Run Workspace", use_container_width=True)

    # In-Memory Cache Status (moved from sidebar)
    with st.expander("🧠 In-Memory Cache Status", expanded=False):
        if st.session_state.image_cache:
            for k in st.session_state.image_cache.keys():
                name = os.path.basename(k.split("_")[-1])
                st.code(f"• {name} (Loaded)", language="text")
            if st.button("Clear Memory Cache"):
                st.session_state.image_cache.clear()
                st.success("Cache cleared!")
                st.rerun()
        else:
            st.info("Cache is empty. Images will be loaded on first script execution.")

    # Read the script code
    if selected_script and selected_script != "No scripts found":
        with open(selected_script, "r") as f:
            script_code = f.read()
    else:
        script_code = ""

    # Display rich code editor or fallback text area
    try:
        from code_editor import code_editor
        response = code_editor(
            script_code,
            lang="python",
            theme="monokai",
            height=[25, 40],
            response_mode=["debounce", "blur"],
            key=f"editor_{selected_script}"
        )
        edited_code = response.get("text") or script_code  # fallback to disk content if editor hasn't sent text yet
    except ImportError:
        # Fallback layout if streamlit-code-editor is missing
        edited_code = st.text_area("Script Code", value=script_code, height=500)

    # Debug logs in stdout
    print(f"[DEBUG] selected_script={selected_script}, run_triggered={run_triggered}, action_save={action_save}", flush=True)
    if 'response' in locals() and isinstance(response, dict):
        print(f"[DEBUG] response dict keys: {list(response.keys())}, type={response.get('type')}, text_len={len(response.get('text', ''))}", flush=True)

    # Handle Save Event
    if action_save:
        with open(selected_script, "w") as f:
            f.write(edited_code)
        st.success(f"Changes saved successfully to `{selected_script}`! The script remains runnable directly via command line.")
        st.rerun()

    # Run execution block outside/before rendering outputs
    if run_triggered:
        print("[DEBUG] Run Workspace triggered! Executing script...", flush=True)
        stdout_buf = io.StringIO()
        stderr_buf = io.StringIO()

        # Log file: same directory as script, same name with .log extension
        log_path = os.path.splitext(os.path.abspath(selected_script))[0] + ".log"
        print(f"[DEBUG] Logging run to: {log_path}", flush=True)

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

                captured_out = stdout_buf.getvalue()
                captured_err = stderr_buf.getvalue()
                captured_combined = captured_out
                if captured_err:
                    captured_combined += "\n--- stderr ---\n" + captured_err
                st.session_state.console_output = captured_combined
                st.toast("Workflow executed successfully!", icon="✅")

                # Write to log file (stdout + stderr)
                with open(log_path, "w") as lf:
                    lf.write(f"# Script: {selected_script}\n")
                    lf.write(f"# Args: {args_input}\n")
                    lf.write("# Status: OK\n\n")
                    lf.write(captured_combined)

                # Parse image statistics from stdout
                lines = st.session_state.console_output.split("\n")
                stats = []
                for line in lines:
                    if "mean" in line and "std" in line:
                        stats.append(line.strip())
                st.session_state.parsed_stats = stats

                # Search namespace for any output VxlImg object to pass to the visualizer
                found_img = None
                if "img" in exec_namespace and isinstance(exec_namespace["img"], (
                    st.session_state.original_VxlImgU16,
                    st.session_state.original_VxlImgU8,
                    st.session_state.original_VxlImgF32
                )):
                    found_img = exec_namespace["img"]
                else:
                    for val in exec_namespace.values():
                        if isinstance(val, (st.session_state.original_VxlImgU16,
                                            st.session_state.original_VxlImgU8,
                                            st.session_state.original_VxlImgF32)):
                            found_img = val
                if found_img is not None:
                    st.session_state.processed_image = found_img

            except Exception as e:
                err_text = stdout_buf.getvalue() + "\n" + stderr_buf.getvalue() + "\n" + traceback.format_exc()
                st.session_state.console_output = err_text
                st.error("Workflow failed with execution error.")

                # Write error to log file
                with open(log_path, "w") as lf:
                    lf.write(f"# Script: {selected_script}\n")
                    lf.write(f"# Args: {args_input}\n")
                    lf.write("# Status: ERROR\n\n")
                    lf.write(err_text)

                # Search namespace even on error to preserve loaded images in viewer
                found_img = None
                if "img" in exec_namespace and isinstance(exec_namespace["img"], (
                    st.session_state.original_VxlImgU16,
                    st.session_state.original_VxlImgU8,
                    st.session_state.original_VxlImgF32
                )):
                    found_img = exec_namespace["img"]
                else:
                    for val in exec_namespace.values():
                        if isinstance(val, (st.session_state.original_VxlImgU16,
                                            st.session_state.original_VxlImgU8,
                                            st.session_state.original_VxlImgF32)):
                            found_img = val
                if found_img is not None:
                    st.session_state.processed_image = found_img
            finally:
                sys.argv = original_argv
                st.rerun()


    # Render Console logs below the editor
    st.markdown('<div class="card-title" style="margin-top: 20px;">🖥️ Standard Output (stdout)</div>', unsafe_allow_html=True)
    st.markdown('<div class="card">', unsafe_allow_html=True)

    # Read log file if it exists (most up-to-date source after st.rerun)
    log_path = os.path.splitext(os.path.abspath(selected_script))[0] + ".log"
    if os.path.exists(log_path):
        with open(log_path, "r") as lf:
            log_display = lf.read()
    else:
        log_display = st.session_state.console_output

    st.text_area("Console Logs", value=log_display, height=250, disabled=True, label_visibility="collapsed")
    st.markdown('</div>', unsafe_allow_html=True)


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
                    width="content"
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
                st.image(selected_fig, caption=os.path.basename(selected_fig), width="content")
        else:
            st.info("No generated files found in `fig/` directory.")
    else:
        st.info("No `fig/` directory exists yet. Run a script containing `plotAll()` or `plotSlice()` to create one.")
