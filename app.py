import streamlit as st
import os
import sys

# Ensure the original root directory is in sys.path before chdir
root_dir = os.path.dirname(os.path.abspath(__file__))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

# Change directory to runs/ to prevent writing any files to the root /app folder
os.makedirs(os.path.join(root_dir, "runs"), exist_ok=True)
os.chdir(os.path.join(root_dir, "runs"))

from utils_app import get_output_files

# Set page configuration with a premium wide layout
st.set_page_config(
    layout="wide",
    page_title="PorGUI",
    page_icon="💠"
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
        background-color: var(--secondary-background-color, #1f242c);
        border-radius: 12px;
        padding: 20px;
        border: 1px solid var(--border-color, rgba(128, 128, 128, 0.2));
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
        margin-bottom: 20px;
        transition: all 0.3s ease;
    }
    
    .card-title {
        font-size: 1.25rem;
        font-weight: 600;
        margin-bottom: 15px;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    
    /* Styling Streamlit buttons to look premium */
    div.stButton > button {
        border: 1px solid var(--border-color, rgba(128, 128, 128, 0.2));
        border-radius: 6px;
        padding: 6px 16px;
        font-weight: 600;
        transition: all 0.2s ease;
    }
    
    div.stButton > button:hover {
        border-color: var(--primary-color, #8b949e);
    }

    /* Custom Title Style */
    .title-gradient {
        font-weight: 700;
        font-size: 2.5rem;
        margin-bottom: 5px;
    }

    /* Style and limit height of interactive image slices & plots */
    div.stImage img {
        max-height: 75vh !important;
        object-fit: contain !important;
        width: auto !important;
        height: auto !important;
        border-radius: 4px;
        box-shadow: 0 4px 10px rgba(0, 0, 0, 0.3);
    }
</style>
""", unsafe_allow_html=True)

# Import image3kit inside a safe block
try:
    import image3kit as ik
except ImportError:
    st.error("image3kit is not installed in this environment. Please run `pip install ./image3kit` to compile and install it.")
    st.stop()


def update_workspace_vars(namespace):
    if "workspace_vars" not in st.session_state:
        st.session_state.workspace_vars = {}
    
    # Extract any VxlImg variables from the namespace
    core_mod = getattr(ik, "_core", None)
    voxlib_mod = getattr(core_mod, "voxlib", None) if core_mod else None
    vxl_base = getattr(voxlib_mod, "voxelImageTBase", tuple()) if voxlib_mod else tuple()
    
    for k, v in namespace.items():
        if isinstance(v, (st.session_state.original_VxlImgU16,
                          st.session_state.original_VxlImgU8,
                          st.session_state.original_VxlImgI32,
                          st.session_state.original_VxlImgF32,
                          vxl_base)):
            st.session_state.workspace_vars[k] = v
            # Default active image to the last detected 'img' variable, or first detected image
            if k == "img" or st.session_state.processed_image is None:
                st.session_state.processed_image = v
                st.session_state.active_var = k
                st.session_state.active_var_selectbox_widget = k

# ----------------------------------------------------
# TRANSPARENT MEMORY CACHING (Monkeypatching loader classes)
# ----------------------------------------------------
if "image_cache" not in st.session_state:
    st.session_state.image_cache = {}

# Save references to original C++ classes directly from _core.voxlib
core_mod = getattr(ik, "_core", None)
voxlib_mod = getattr(core_mod, "voxlib", None) if core_mod else None
if voxlib_mod and ("original_VxlImgU16" not in st.session_state or getattr(st.session_state.original_VxlImgU16, "__name__", "") == "PatchedClass"):
    st.session_state.original_VxlImgU16 = voxlib_mod.VxlImgU16
    st.session_state.original_VxlImgU8 = voxlib_mod.VxlImgU8
    st.session_state.original_VxlImgI32 = voxlib_mod.VxlImgI32
    st.session_state.original_VxlImgF32 = voxlib_mod.VxlImgF32



def get_patched_class(original_cls, class_name):
    class PatchedClass(original_cls):
        def __init__(self, *args, **kwargs):
            if len(args) == 1 and isinstance(args[0], str):
                var_name = args[0]
                # 1. Check if it is an in-memory variable in workspace_vars and not a file on disk
                if "workspace_vars" in st.session_state and var_name in st.session_state.workspace_vars and not os.path.exists(var_name):
                    cached_obj = st.session_state.workspace_vars[var_name]
                    if isinstance(cached_obj, original_cls):
                        super().__init__(cached_obj)
                        return
                
                # 2. Check if cached in file-based image_cache
                abs_path = os.path.abspath(args[0])
                cache_key = f"{class_name}_{abs_path}"
                
                if cache_key in st.session_state.image_cache:
                    cached_obj = st.session_state.image_cache[cache_key]
                    super().__init__(cached_obj)
                    return
                else:
                    super().__init__(*args, **kwargs)
                    st.session_state.image_cache[cache_key] = self.copy()
            else:
                super().__init__(*args, **kwargs)
                
        def copy(self):
            orig_copy = super().copy()
            return PatchedClass(orig_copy)
                
    return PatchedClass

ik.VxlImgU16 = get_patched_class(st.session_state.original_VxlImgU16, "VxlImgU16")
ik.VxlImgU8 = get_patched_class(st.session_state.original_VxlImgU8, "VxlImgU8")
ik.VxlImgI32 = get_patched_class(st.session_state.original_VxlImgI32, "VxlImgI32")
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
if "workspace_vars" not in st.session_state:
    st.session_state.workspace_vars = {}
if "session_commands" not in st.session_state:
    st.session_state.session_commands = ""

# Populate files lists for app_plots / app_logs
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


# Main Tab Layout
tabs = st.tabs(["💻 Workflow Editor", "🖼️ Image Processing", "🌐 Network Analysis", "📊 Saved Plots", "📄 Log Files"])

# ----------------------------------------------------
# TAB 2: INTERACTIVE VISUALIZER
# ----------------------------------------------------
with tabs[2]:
    import app_func_net
    app_func_net.render_pnm_tab()

# ----------------------------------------------------
# TAB 1: WORKFLOW EDITOR
# ----------------------------------------------------
with tabs[0]:
    import app_editor
    app_editor.workflow_studio(st, ik, update_workspace_vars)

# ----------------------------------------------------
# TAB 2: INTERACTIVE VISUALIZER
# ----------------------------------------------------
with tabs[1]:
    import app_func_img
    app_func_img.render_imgpro_tab()

# ----------------------------------------------------
# TAB 3: SAVED PLOTS
# ----------------------------------------------------
with tabs[3]:
    import app_plots
    app_plots.render_plots()

# ----------------------------------------------------
# TAB 4: LOG FILES
# ----------------------------------------------------
with tabs[4]:
    import app_logs
    app_logs.render_logs()
