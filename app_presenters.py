"""Framework-independent presenters for the function-execution panels.

This file shall not contain any streamlit related imports.

app_func_img.py and app_func_net.py both offer "pick a function, fill in the
args, run it" and previously carried near-identical copies of the dispatch
below. ExecutionPresenter owns that logic once; the views only render the
returned ExecResult.
"""

import os
import shlex
import sys
import traceback
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import dataclass, field
from io import StringIO
from typing import Any, Optional

from image3kit._core import ostream_redirect

from app_state import coerce_to_wrapper
from utils_app import run_capturing_output


def is_object_dropdown_type(type_val, type_names):
    """True if a parameter should be filled from a workspace variable."""
    if type_val == "var_dropdown":
        return True
    if isinstance(type_val, str):
        return any(x in type_val for x in type_names)
    if isinstance(type_val, type):
        return any(x in type_val.__name__ for x in type_names)
    return False


def resolve_object_args(args_dict, params_meta, workspace_vars, type_names):
    """Swap workspace variable *names* for the objects they refer to.

    Object-typed params arrive from the form as variable names. "(none)" comes
    through falsy, in which case the kwarg is dropped so the bound function's
    own default applies.
    """
    for p in params_meta:
        p_name = p["name"]
        if p_name == "self" or p_name not in args_dict:
            continue
        if is_object_dropdown_type(p["type"], type_names):
            val = args_dict[p_name]
            if val:
                args_dict[p_name] = workspace_vars.get(val)
            else:
                del args_dict[p_name]
    return args_dict


def format_args(args: dict) -> str:
    return ", ".join(f"{k}={v!r}" for k, v in args.items())


@dataclass
class ExecResult:
    """What the view needs to render one run. No streamlit types."""

    ok: bool = True
    stdout: str = ""
    success_msg: str = ""
    error: str = ""
    command_line: str = ""
    stored_var: Optional[str] = None
    is_image: bool = False
    nonimage_result: Any = None
    nonimage_func: Optional[str] = None
    #: set when the run was rejected before executing (missing required input)
    invalid: bool = False
    extras: dict = field(default_factory=dict)


class ExecutionPresenter:
    """Runs a user-selected function and folds the outcome into the Workspace.

    `wrappers` maps unpatched C++ image classes to the caching subclasses
    app.py installs on the image3kit module, so results get re-wrapped
    consistently no matter which layer produced them.
    """

    def __init__(self, workspace, wrappers=None, image_types=None):
        self.workspace = workspace
        self.wrappers = wrappers or {}
        self._image_types = image_types

    @property
    def image_types(self) -> tuple:
        if self._image_types is not None:
            return self._image_types
        return self.workspace.image_types

    # -- helpers -----------------------------------------------------------
    def _looks_like_image(self, result) -> bool:
        types = self.image_types
        if types and isinstance(result, types):
            return True
        # Results can arrive as patched subclasses whose base is not in `types`
        # (app.py rebinds ik.VxlImg* at import); fall back to the class name.
        return result is not None and "VxlImg" in type(result).__name__

    def _wrap(self, raw):
        return coerce_to_wrapper(raw, self.wrappers)

    @staticmethod
    def _capture(func, **kwargs):
        """Run func, capturing stdout (C++ included). Returns (result, stdout, error)."""
        try:
            result, stdout = run_capturing_output(func, **kwargs)
        except Exception as err:
            return None, "", f"{err}\n\n{traceback.format_exc()}"
        return result, stdout.strip(), None

    # -- object (network) variants ----------------------------------------
    # Networks are pyvista meshes, not images: they are never copy-on-write and
    # never re-wrapped, so they get their own entry points rather than bending
    # the image ones out of shape.
    def run_object_func(self, name, func, args, out_var_name="", store_types=(), filenames=None):
        """Run a plain function whose result is a non-image object (a mesh)."""
        args = dict(args)
        var_name = args.pop("new_var_name", None) or out_var_name or name
        filename = args.get("filename", "")
        if "filename" in args and not args["filename"]:
            return ExecResult(ok=False, invalid=True, error="Please select a file to load.")

        result, stdout, error = self._capture(func, **args)
        if error:
            return ExecResult(ok=False, error=error)

        res = ExecResult(stdout=stdout, command_line=f"{var_name} = {name}({format_args(args)})")
        if store_types and isinstance(result, store_types):
            self.workspace.store_var(var_name, result)
            res.stored_var = var_name
            if filename and filenames is not None:
                filenames[var_name] = filename
        res.success_msg = f"Executed `{name}`, result stored as `{var_name}`."
        self.workspace.record_command(res.command_line)
        return res

    def run_object_method(self, name, target_var, args):
        """Run an in-place method on a workspace object (mesh)."""
        run_obj = self.workspace.get(target_var)
        if run_obj is None:
            return ExecResult(ok=False, invalid=True,
                              error="No target network object available to execute method on.")

        result, stdout, error = self._capture(getattr(run_obj, name), **args)
        if error:
            return ExecResult(ok=False, error=error)

        res = ExecResult(
            stdout=stdout,
            command_line=f"{target_var}.{name}({format_args(args)})",
            success_msg=f"Successfully executed `{name}` in-place on `{target_var}`.",
            nonimage_result=result,
            nonimage_func=name,
        )
        self.workspace.record_command(res.command_line)
        return res

    # -- the three dispatch branches --------------------------------------
    def run_python_func(self, name, func, args, out_var_name=""):
        """Run a plain Python/pybind function, e.g. read_image, threshold01_otsu."""
        args = dict(args)
        var_name = args.pop("new_var_name", None) or out_var_name or name
        filename = args.get("filename", "")
        if "filename" in args and not args["filename"]:
            return ExecResult(ok=False, invalid=True, error="Please select a file to load.")

        result, stdout, error = self._capture(func, **args)
        if error:
            return ExecResult(ok=False, error=error)

        res = ExecResult(stdout=stdout, command_line=f"{var_name} = {name}({format_args(args)})")

        if self._looks_like_image(result):
            output_img = self._wrap(result)
            if filename:
                cache_key = f"{type(output_img).__name__}_{os.path.abspath(filename)}"
                self.workspace.image_cache[cache_key] = output_img
            self.workspace.store_image(var_name, output_img)
            res.is_image = True
            res.stored_var = var_name
            res.success_msg = f"Executed `{name}`, result stored as `{var_name}`."
        else:
            res.nonimage_result = result
            res.nonimage_func = name
            if result is None:
                res.success_msg = f"Executed `{name}` (no return value; nothing stored)."
            else:
                res.success_msg = (
                    f"Executed `{name}` — returned a non-image result (see right panel); nothing stored."
                )

        self.workspace.record_command(res.command_line)
        return res

    def run_standalone(self, name, func, args, import_prefix="pyvtk."):
        """Run a standalone CLI-style entry point (mextract, snflow, ...)."""
        def call():
            if func is None:
                print(f"{name} not wired in!!!")
                return None
            return func(**args)

        _, stdout, error = self._capture(call)
        if error:
            return ExecResult(ok=False, error=error)

        command_line = (
            f"import {import_prefix}{name} as {name}\n"
            f"{name}.main()  # args: {format_args(args)}"
        )
        self.workspace.record_command(command_line)
        return ExecResult(
            stdout=stdout,
            command_line=command_line,
            success_msg=f"Successfully executed standalone command `{name}`!",
        )

    def run_method(self, name, target_var, args, copy_on_write=True, out_var_name=""):
        """Run a method on a workspace image, e.g. img.median_filter()."""
        target_img = self.workspace.get(target_var)
        if target_img is None:
            return ExecResult(ok=False, invalid=True, error="No target image available to execute method on.")

        run_obj = target_img.copy() if copy_on_write else target_img
        out_var_name = out_var_name or target_var

        result, stdout, error = self._capture(getattr(run_obj, name), **args)
        if error:
            return ExecResult(ok=False, error=error)

        res = ExecResult(stdout=stdout)
        args_str = format_args(args)

        # A new image is the result; None means an in-place mutator, so the
        # object we ran on is the result; anything else is genuine data
        # (stats, thresholds) that must not masquerade as an image.
        if self._looks_like_image(result):
            raw_img = result
        elif result is None:
            raw_img = run_obj
        else:
            raw_img = None

        if raw_img is not None:
            output_img = self._wrap(raw_img)
            self.workspace.store_image(out_var_name, output_img)
            res.is_image = True
            res.stored_var = out_var_name
            if copy_on_write:
                res.command_line = f"{out_var_name} = {target_var}.copy()\n{out_var_name}.{name}({args_str})"
            else:
                res.command_line = f"{out_var_name} = {target_var}\n{out_var_name}.{name}({args_str})"
            res.success_msg = f"Successfully executed `{name}`! Output stored as `{out_var_name}`."
        else:
            res.nonimage_result = result
            res.nonimage_func = name
            if copy_on_write:
                res.command_line = f"_tmp = {target_var}.copy()\nresult = _tmp.{name}({args_str})"
            else:
                res.command_line = f"result = {target_var}.{name}({args_str})"
            res.success_msg = (
                f"Executed `{name}` — returned a non-image result (see right panel); "
                "no new image variable was created."
            )

        self.workspace.record_command(res.command_line)
        return res


# --------------------------------------------------------------------------
# Workflow script execution (the Workflow Editor tab)
# --------------------------------------------------------------------------
@dataclass
class ScriptRunResult:
    """What the editor view needs to render one script run."""

    ok: bool
    message: str
    console_output: str
    log_path: str
    log_text: str
    absorbed_vars: list = field(default_factory=list)
    #: raw SystemExit.code (may be an int, a string, or None) - None if the
    #: run raised a different exception, or completed without exiting at all.
    exit_code: Any = None


def parse_cli_args(args_input: str) -> list:
    """Split a CLI-arg string, resolving args that are existing filesystem
    paths to absolute (relative to the current working directory)."""
    parsed = shlex.split(args_input)
    return [os.path.abspath(a) if os.path.exists(a) else a for a in parsed]


def build_exec_namespace(script_path, workspace, ik) -> dict:
    """The globals a workflow script runs against: identity, image3kit, and
    every variable currently in the workspace.
    """
    namespace = {
        "__name__": "__main__",
        "__file__": os.path.abspath(script_path),
        "image3kit": ik,
    }
    namespace.update(workspace.vars)
    return namespace


def run_script(script_path, script_code, args_input, workspace, ik) -> ScriptRunResult:
    """Execute a workflow script the way the editor's Run button does.

    Sets up CLI-style sys.argv and puts the script's own directory on
    sys.path, execs with combined Python+C++ stdout/stderr capture, and
    always folds the resulting namespace into the workspace - on success,
    on a SystemExit, and on an uncaught exception alike - so a script that
    dies partway through does not discard whatever it had already built (the
    rock_mask case: threshold01_otsu succeeds, a later call fails, and the
    mask must still show up in the workspace).

    Never raises: mirrors ExecutionPresenter's contract of handing the view a
    result object instead of letting exceptions escape into it.

    TODO (see TODO.md): a future version may run scripts out-of-process
    (subprocess.Popen) to stream output live via st.write_stream instead of
    returning it all at once. That is a bigger change than swapping the
    stdout-capture mechanism: workspace variables are passed into the script
    today as live Python objects via exec_namespace, which only works
    in-process. Going subprocess means designing how those objects cross the
    process boundary (serialize to the image_cache, a shared file, ...)
    before output streaming itself is worth doing.
    """
    exec_namespace = build_exec_namespace(script_path, workspace, ik)
    parsed_args = parse_cli_args(args_input)
    cmd_desc = f"{script_path} {args_input}"
    log_path = os.path.abspath(os.path.splitext(os.path.basename(script_path))[0] + ".log")

    script_dir = os.path.dirname(os.path.abspath(script_path))
    original_argv = sys.argv
    original_path = list(sys.path)
    sys.argv = [script_path] + parsed_args
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)

    stdout_buf, stderr_buf = StringIO(), StringIO()
    exit_code = None
    excepted = False
    tb_text = ""
    try:
        with redirect_stdout(stdout_buf), redirect_stderr(stderr_buf):
            with ostream_redirect(stdout=True, stderr=True):
                exec(script_code, exec_namespace)
    except SystemExit as se:
        exit_code = se.code
    except BaseException:
        excepted = True
        tb_text = traceback.format_exc()
    finally:
        sys.argv = original_argv
        sys.path[:] = original_path
        absorbed = workspace.absorb_namespace(exec_namespace)

    captured = stdout_buf.getvalue() + "\n" + stderr_buf.getvalue()
    ok = not excepted and exit_code in (None, 0)

    if ok:
        message = "Workflow completed successfully!"
        console_output = captured
        log_text = f"✅ cmd: '{cmd_desc}':\n{captured}"
    elif not excepted:
        message = f"Workflow exited with code {exit_code}."
        console_output = captured
        log_text = f"⛔ cmd: '{cmd_desc}':\n# Status: ERROR (SystemExit: {exit_code})\n\n{captured}"
    else:
        message = "Workflow failed with execution error."
        console_output = captured + "\n" + tb_text
        log_text = f"⛔ cmd: '{cmd_desc}':\n# Status: ERROR\n\n{console_output}"

    return ScriptRunResult(
        ok=ok,
        message=message,
        console_output=console_output,
        log_path=log_path,
        log_text=log_text,
        absorbed_vars=absorbed,
        exit_code=exit_code,
    )
