import time

import streamlit as st
from uiutils.streamlit.widgets import filtered_select
from utils_app import get_output_files, top_dir


def refresh_outputs():
    pngs, logs = get_output_files()
    st.session_state.png_files = pngs
    st.session_state.log_files = logs


def render_plots():
    col_plots_ctrl, col_plots_view = st.columns([3, 4])

    with col_plots_ctrl:
        st.write("### 🖼️ Generated Plots")

        selected_plot = filtered_select("plot", "Select Plot to display:", st.session_state.png_files, refresh_outputs)

    with col_plots_view:
        if selected_plot:
            full_path = top_dir / selected_plot
            st.image(str(full_path), width="stretch")

            st.write(f"#### `{selected_plot}`")
            # Calculate metadata details
            try:
                stats = full_path.stat()
                mod_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(stats.st_mtime))
                st.caption(f"📅 Last Modified: {mod_time} | 📦 Size: {stats.st_size / 1024:.2f} KB")
            except Exception:
                pass
