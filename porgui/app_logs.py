import time

import streamlit as st
from utils_app import filter_by_search_query, get_output_files, top_dir


def refresh_outputs():
    pngs, logs = get_output_files()
    st.session_state.png_files = pngs
    st.session_state.log_files = logs

def render_logs():
    col_logs_ctrl, col_logs_view = st.columns([2, 3])

    with col_logs_ctrl:
        st.write("### 📄 Output Log Files")

        # Track search changes to reset selectbox
        if "prev_log_name_filter" not in st.session_state:
            st.session_state["prev_log_name_filter"] = ""
        current_log_search = st.session_state.get("log_name_filter", "")
        if st.session_state["prev_log_name_filter"] != current_log_search:
            st.session_state["prev_log_name_filter"] = current_log_search
            if "log_select_box" in st.session_state:
                del st.session_state["log_select_box"]

        ref_col, search_col = st.columns([1, 1.5])
        with ref_col:
            if st.button("🔄 Refresh", key="refresh_logs_btn"):
                refresh_outputs()
                st.rerun()
        with search_col:
            log_search = st.text_input(
                "Filter logs:",
                value="",
                placeholder="Search/filter logs...",
                label_visibility="collapsed",
                key="log_name_filter",
            )

        if st.session_state.log_files:
            _filtered_logs = st.session_state.log_files

            # Further filter by log_search
            _filtered_logs, _has_err = filter_by_search_query(st.session_state.log_files, log_search)
            if _has_err:
                st.caption("⚠️ *Invalid regex pattern*")

            if log_search.strip():
                st.caption(f"🔍 Filtering by query: `{log_search}` ({len(_filtered_logs)} of {len(st.session_state.log_files)} logs)")

            selected_log_file = st.selectbox(
                "Select Log file to display:",
                options=_filtered_logs,
                format_func=str,
                key="log_select_box",
            )

            st.write("---")
            st.write("### 🔍 Filter Log Display")
            keep_txt = st.text_input("Keep lines containing (split by space):", value=st.session_state.applied_keep, key=f"temp_keep_input_{st.session_state.filter_version}", help="Split by whitespace. If empty, keeps all lines.")
            remove_txt = st.text_input("Remove lines containing (split by space):", value=st.session_state.applied_remove, key=f"temp_remove_input_{st.session_state.filter_version}", help="Split by whitespace.")
            col_filt_1, col_filt_2 = st.columns([1, 1])
            with col_filt_1:
                if st.button("🚫 Filter Out", width="stretch"):
                    st.session_state.applied_keep = keep_txt
                    st.session_state.applied_remove = remove_txt
                    st.session_state.filter_applied = True
                    st.rerun()
            with col_filt_2:
                if st.button("🧹 Clear Filter", width="stretch"):
                    st.session_state.applied_keep = ""
                    st.session_state.applied_remove = ""
                    st.session_state.filter_applied = False
                    st.session_state.filter_version += 1
                    st.rerun()
        else:
            selected_log_file = None
            st.info("No log files found in the workspace.")

    with col_logs_view:

        if selected_log_file:
            full_path = top_dir / selected_log_file
            st.write(f"#### `{selected_log_file}`")
            try:
                stats = full_path.stat()
                mod_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(stats.st_mtime))

                with full_path.open() as f:
                    log_content = f.read()

                if st.session_state.filter_applied:
                    keep_terms = st.session_state.applied_keep.split()
                    remove_terms = st.session_state.applied_remove.split()

                    original_lines = log_content.splitlines()
                    filtered_lines = []
                    for line in original_lines:
                        keep = True
                        if keep_terms:
                            keep = all(term.lower() in line.lower() for term in keep_terms)
                        if keep and remove_terms and any(term.lower() in line.lower() for term in remove_terms):
                            keep = False
                        if keep:
                            filtered_lines.append(line)

                    log_content = "\n".join(filtered_lines)
                    st.caption(f"📅 Last Modified: {mod_time} | 📦 Size: {stats.st_size / 1024:.2f} KB | 🔍 Showing {len(filtered_lines)} of {len(original_lines)} lines")
                else:
                    st.caption(f"📅 Last Modified: {mod_time} | 📦 Size: {stats.st_size / 1024:.2f} KB")

                st.text_area("File Contents", value=log_content, height=600)
            except Exception as e:
                st.error(f"Failed to read file {selected_log_file}: {e}")
