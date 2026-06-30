from contextlib import redirect_stderr
from contextlib import redirect_stdout
import os
import sys
import shlex
import io
import traceback
import glob
from app_utils import get_output_files

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


def workflow_studio(st, ik, update_workspace_vars):

    # Scan directory for workspace scripts
    script_files = sorted(glob.glob("*.py"))
    options = script_files + ["➕ New File..."]

    if not script_files:
        st.warning("⚠️ No Python workflow scripts (*.py) found in the runs directory.")
        _new_file_dialog(st)
        st.stop()
        return

    # Consolidation bar at the top
    col_select, col_args, col_actions = st.columns([1.5, 2, 1.5])
    
    with col_select:
        selected_script = st.selectbox(
            "Select Workflow Script", 
            options, 
            index=0 if "last_executed_script" not in st.session_state or st.session_state.last_executed_script not in options else options.index(st.session_state.last_executed_script),
            label_visibility="collapsed"
        )
        if selected_script == "➕ New File...":
            _new_file_dialog(st)
            st.stop()
        
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
        st.toast(f"Saved {selected_script} successfully!", icon="💾")
    
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

    # Execution logic
    if run_pressed and selected_script:
        st.session_state.last_executed_script = selected_script
        
        os.makedirs("fig", exist_ok=True)
        
        original_argv = sys.argv
        try:
            parsed_args = shlex.split(args_input)
            # Resolve relative input file paths to absolute paths
            for idx, arg in enumerate(parsed_args):
                if os.path.exists(arg):
                    parsed_args[idx] = os.path.abspath(arg)
            sys.argv = [selected_script] + parsed_args
        except Exception as arg_err:
            st.error(f"Failed to parse arguments: {arg_err}")
            st.stop()
            
        exec_namespace = {
            "__name__": "__main__",
            "__file__": os.path.abspath(selected_script),
            "image3kit": ik,
        }
        for k, v in st.session_state.workspace_vars.items():
            exec_namespace[k] = v
        
        stdout_buf = io.StringIO()
        stderr_buf = io.StringIO()
        log_path = os.path.abspath(os.path.splitext(os.path.basename(selected_script))[0] + ".log")
        
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

        except BaseException:
            err_text = stdout_buf.getvalue() + "\n" + stderr_buf.getvalue() + "\n" + traceback.format_exc()
            st.session_state.console_output = err_text
            st.error("Workflow failed with execution error (or sys.exit was called).")

            with open(log_path, "w") as lf:
                lf.write(f"# Script: {selected_script}\n")
                lf.write(f"# Args: {args_input}\n")
                lf.write("# Status: ERROR\n\n")
                lf.write(err_text)

            update_workspace_vars(exec_namespace)
        finally:
            sys.argv = original_argv
            pngs, logs = get_output_files()
            st.session_state.png_files = pngs
            st.session_state.log_files = logs
            st.rerun()

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
        log_path = os.path.splitext(os.path.basename(selected_script))[0] + ".log"
        if os.path.exists(log_path):
            with open(log_path, "r") as lf:
                log_display = lf.read()
        else:
            log_display = st.session_state.console_output
        
        if log_display and len(log_display) > 50000:
            log_display = log_display[-50000:] + "\n...[truncated for UI performance]"
            
        st.text_area("Console Logs", value=log_display, height=250, disabled=True, label_visibility="collapsed")
        st.markdown('</div>', unsafe_allow_html=True)