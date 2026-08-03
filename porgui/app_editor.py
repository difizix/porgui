import os
import glob
from app_common import get_workspace
from app_presenters import run_script, run_script_stream
from utils_app import get_output_files, render_stream_preformatted

# ----------------------------------------------------
# TAB 1: WORKFLOW STUDIO
# ----------------------------------------------------
def _new_file_dialog(st):
    """Show a blocking dialog to create a new workflow script."""
    @st.dialog("Create New Workflow Script")
    def _dialog():
        name = st.text_input("File name", placeholder="my_workflow.py")
        if st.button("✅ Create", use_container_width=True):
            if name:
                fname = name if name.endswith(".py") else name + ".py"
                with open(fname, "w") as f:
                    f.write("import image3kit as ik\n\n# Your code here\n")
                st.session_state.last_executed_script = fname
                st.rerun()
            else:
                st.error("Please enter a valid file name.")
    _dialog()


def workflow_studio(st, ik):

    # Scan directory for workspace scripts
    script_files = sorted(glob.glob("*.py"))
    if script_files:
        options = script_files + ["➕ New File..."]
    else:
        options = ["(No script found)", "➕ New File..."]

    # Consolidation bar at the top
    col_select, col_args, col_actions = st.columns([1.5, 2, 2])

    with col_select:
        selected_script = st.selectbox(
            "Select Workflow Script",
            options,
            index=0 if "last_executed_script" not in st.session_state or st.session_state.last_executed_script not in options else options.index(st.session_state.last_executed_script),
            label_visibility="collapsed"
        )
        if selected_script == "➕ New File...":
            _new_file_dialog(st)
            selected_script = None
        elif selected_script == "(No script found)":
            selected_script = None

    with col_args:
        args_input = st.text_input(
            "Script CLI Arguments",
            value="",
            placeholder="e.g. --x0 374 --y0 853",
            label_visibility="collapsed"
        )

    with col_actions:
        btn_col1, btn_col2, btn_col3, btn_col4 = st.columns([1, 1, 1.2, 1.2])
        with btn_col1:
            run_pressed = st.button("▶️ Run", key="run_script_btn", width="stretch")
        with btn_col2:
            save_pressed = st.button("💾 Save", key="save_script_btn", width="stretch")
        with btn_col3:
            show_cache = st.button("🗂️ Cache", key="cache_status_btn", width="stretch")
        with btn_col4:
            clear_cache = st.button("🧹 Clear", key="clear_cache_btn", width="stretch")

    if save_pressed:
        if selected_script:
            st.toast(f"Saved {selected_script} successfully!", icon="💾")
        else:
            st.warning("No script selected to save.")

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

    if selected_script and os.path.exists(selected_script):
        with open(selected_script, "r") as f:
            script_code = f.read()
    else:
        script_code = ""

    if selected_script:
        try:
            from code_editor import code_editor
            response = code_editor(
                script_code,
                lang="python",
                theme="monokai",
                options={"wrap": True, "autoScrollEditorIntoView": True},
                response_mode=["debounce", "blur"],
                key=f"code_editor_{selected_script.replace('.', '_').replace('/', '__')}"
            )

            # If the response contains new text (from blur or submit event), save it
            new_text = response.get("text")
            if new_text and new_text != script_code:
                with open(selected_script, "w") as f:
                    f.write(new_text)
                script_code = new_text

            if response.get("type") == "submit":
                pass # Explicit submit (Ctrl+S) handled above since text is updated

        except ImportError:
            edited_code = st.text_area("Script Code Editor", value=script_code, height=450, key="fallback_editor")
            if edited_code != script_code:
                with open(selected_script, "w") as f:
                    f.write(edited_code)
                script_code = edited_code
    else:
        st.info("💡 No workflow script selected. Select a script from the dropdown above or click **➕ New File...** to create one.")

    # Execution logic
    if run_pressed and selected_script:
        st.session_state.last_executed_script = selected_script

        os.makedirs("fig", exist_ok=True)

        workspace = get_workspace()
        result_holder = {}
        stream_gen = run_script_stream(selected_script, script_code, args_input, workspace, ik, result_holder)

        @st.dialog("⚙️ Streaming Workflow Script Output", width="large")
        def _run_dialog():
            render_stream_preformatted(st, stream_gen)
            result = result_holder.get("result")

            if result:
                st.session_state.console_output = result.console_output
                (st.success if result.ok else st.error)(result.message)

                with open(result.log_path, "w") as lf:
                    lf.write(result.log_text)

                if result.absorbed_vars and workspace.active_var:
                    st.session_state.active_var_selectbox_widget = workspace.active_var

                pngs, logs = get_output_files()
                st.session_state.png_files = pngs
                st.session_state.log_files = logs
            st.rerun()
        _run_dialog()

    # Render Console logs and Command History side-by-side below the editor
    col_hist, col_log = st.columns([1, 1])

    with col_hist:
        st.markdown('<div class="card-title" style="margin-top: 20px;">📜 Interactive Commands History</div>', unsafe_allow_html=True)
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.text_area("Executed Commands", value=st.session_state.session_commands, height=250, disabled=True, label_visibility="collapsed")

        # Add button to insert history into editor
        col_clear_hist, col_append_hist = st.columns([1, 1])
        with col_clear_hist:
            if st.button("🧹 Clear History", width="stretch"):
                st.session_state.session_commands = ""
                st.rerun()
        with col_append_hist:
            if st.button("➕ Append to Current Script", width="stretch") and selected_script:
                try:
                    with open(selected_script, "a") as sf:
                        sf.write("\n\n# --- Interactively Generated Commands ---\n" + st.session_state.session_commands)
                    st.success("Appended commands to script!")
                    st.rerun()
                except Exception as append_err:
                    st.error(f"Failed to append to script: {append_err}")
        st.markdown('</div>', unsafe_allow_html=True)

    with col_log:
        st.markdown('<div class="card-title" style="margin-top: 20px;">🖥️ Standard Output (stdout)</div>', unsafe_allow_html=True)
        st.markdown('<div class="card">', unsafe_allow_html=True)
        log_path = (os.path.splitext(os.path.basename(selected_script))[0] + ".log") if selected_script else None
        if log_path and os.path.exists(log_path):
            with open(log_path, "r") as lf:
                log_display = lf.read()
        else:
            log_display = st.session_state.console_output

        if log_display and len(log_display) > 50000:
            log_display = log_display[-50000:] + "\n...[truncated for UI performance]"

        st.text_area("Console Logs", value=log_display, height=250, disabled=True, label_visibility="collapsed")
        st.markdown('</div>', unsafe_allow_html=True)