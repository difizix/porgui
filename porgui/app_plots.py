import time

import streamlit as st
from utils_app import filter_by_search_query, get_output_files, top_dir


def refresh_outputs():
    pngs, logs = get_output_files()
    st.session_state.png_files = pngs
    st.session_state.log_files = logs


def set_selected_plot(plot_val):
    st.session_state["plot_select_box"] = plot_val


def render_plots():
    col_plots_ctrl, col_plots_view = st.columns([3, 4])

    with col_plots_ctrl:
        st.write("### 🖼️ Generated Plots")

        # Track search changes to reset selectbox
        if "prev_plot_name_filter" not in st.session_state:
            st.session_state["prev_plot_name_filter"] = ""
        current_plot_search = st.session_state.get("plot_name_filter", "")
        if st.session_state["prev_plot_name_filter"] != current_plot_search:
            st.session_state["prev_plot_name_filter"] = current_plot_search
            if "plot_select_box" in st.session_state:
                del st.session_state["plot_select_box"]

        ref_col, search_col = st.columns([1, 1.5])
        with ref_col:
            if st.button("🔄 Refresh", key="refresh_plots_btn"):
                refresh_outputs()
                st.rerun()
        with search_col:
            plot_search = st.text_input(
                "Filter plots:",
                value="",
                placeholder="Search/filter plots...",
                label_visibility="collapsed",
                key="plot_name_filter",
            )

        if st.session_state.png_files:
            _filtered_pngs = st.session_state.png_files

            # Further filter by plot_search
            _filtered_pngs, _has_err = filter_by_search_query(st.session_state.png_files, plot_search)
            if _has_err:
                st.caption("⚠️ *Invalid regex pattern*")

            if plot_search.strip():
                st.caption(f"🔍 Filtering by query: `{plot_search}` ({len(_filtered_pngs)} of {len(st.session_state.png_files)} plots)")

            selected_plot = st.selectbox(
                "Select Plot to display:",
                options=_filtered_pngs,
                format_func=str,
                key="plot_select_box",
            )

            if _filtered_pngs:
                try:
                    current_idx = _filtered_pngs.index(selected_plot)
                except ValueError:
                    current_idx = -1

                next_idx = (current_idx + 1) % len(_filtered_pngs) if current_idx != -1 else 0
                prev_idx = (current_idx - 1) % len(_filtered_pngs) if current_idx != -1 else 0

                next_plot = _filtered_pngs[next_idx]
                prev_plot = _filtered_pngs[prev_idx]

                col_prev, col_next = st.columns(2)
                with col_prev:
                    st.button(
                        "⬅️ Previous Plot",
                        key="prev_plot_btn",
                        width="stretch",
                        on_click=set_selected_plot,
                        args=(prev_plot,),
                    )
                with col_next:
                    st.button(
                        "➡️ Next Plot",
                        key="next_plot_btn",
                        width="stretch",
                        on_click=set_selected_plot,
                        args=(next_plot,),
                    )
        else:
            selected_plot = None
            st.info("No plot images found in the workspace.")

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
