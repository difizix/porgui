"""Framework-independent presenters for the function-execution panels.

This file shall not contain any streamlit related imports.

app_func_img.py and app_func_net.py both offer "pick a function, fill in the
args, run it" and previously carried near-identical copies of the dispatch
below. ExecutionPresenter owns that logic once; the views only render the
returned ExecResult.
"""

import linecache
import os
import shlex
import sys
import traceback
from dataclasses import dataclass, field
from typing import Any, Optional


from app_state import coerce_to_wrapper
from utils_app import run_capturing_output, stream_callable_output


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

    # -- streaming variants ------------------------------------------------
    def run_object_func_stream(self, name, func, args, out_var_name="", store_types=(), filenames=None, result_holder: Optional[dict] = None):
        if result_holder is None:
            result_holder = {}
        args = dict(args)
        var_name = args.pop("new_var_name", None) or out_var_name or name
        filename = args.get("filename", "")
        if "filename" in args and not args["filename"]:
            result_holder["result"] = ExecResult(ok=False, invalid=True, error="Please select a file to load.")
            return

        call_holder = {}
        for chunk in stream_callable_output(lambda: func(**args), call_holder):
            yield chunk

        error = call_holder.get("error")
        if error is not None:
            tb = call_holder.get("tb", "")
            result_holder["result"] = ExecResult(ok=False, error=f"{error}\n\n{tb}")
            return

        result = call_holder.get("result")
        stdout = call_holder.get("output", "").strip()

        res = ExecResult(stdout=stdout, command_line=f"{var_name} = {name}({format_args(args)})")
        if store_types and isinstance(result, store_types):
            self.workspace.store_var(var_name, result)
            res.stored_var = var_name
            if filename and filenames is not None:
                filenames[var_name] = filename
        res.success_msg = f"Executed `{name}`, result stored as `{var_name}`."
        self.workspace.record_command(res.command_line)
        result_holder["result"] = res

    def run_object_method_stream(self, name, target_var, args, result_holder: Optional[dict] = None):
        if result_holder is None:
            result_holder = {}
        run_obj = self.workspace.get(target_var)
        if run_obj is None:
            result_holder["result"] = ExecResult(
                ok=False, invalid=True, error="No target network object available to execute method on."
            )
            return

        call_holder = {}
        for chunk in stream_callable_output(lambda: getattr(run_obj, name)(**args), call_holder):
            yield chunk

        error = call_holder.get("error")
        if error is not None:
            tb = call_holder.get("tb", "")
            result_holder["result"] = ExecResult(ok=False, error=f"{error}\n\n{tb}")
            return

        result = call_holder.get("result")
        stdout = call_holder.get("output", "").strip()

        res = ExecResult(
            stdout=stdout,
            command_line=f"{target_var}.{name}({format_args(args)})",
            success_msg=f"Successfully executed `{name}` in-place on `{target_var}`.",
            nonimage_result=result,
            nonimage_func=name,
        )
        self.workspace.record_command(res.command_line)
        result_holder["result"] = res

    def run_python_func_stream(self, name, func, args, out_var_name="", result_holder: Optional[dict] = None):
        if result_holder is None:
            result_holder = {}
        args = dict(args)
        var_name = args.pop("new_var_name", None) or out_var_name or name
        filename = args.get("filename", "")
        if "filename" in args and not args["filename"]:
            result_holder["result"] = ExecResult(ok=False, invalid=True, error="Please select a file to load.")
            return

        call_holder = {}
        for chunk in stream_callable_output(lambda: func(**args), call_holder):
            yield chunk

        error = call_holder.get("error")
        if error is not None:
            tb = call_holder.get("tb", "")
            result_holder["result"] = ExecResult(ok=False, error=f"{error}\n\n{tb}")
            return

        result = call_holder.get("result")
        stdout = call_holder.get("output", "").strip()

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
        result_holder["result"] = res

    def run_standalone_stream(self, name, func, args, import_prefix="pyvtk.", result_holder: Optional[dict] = None):
        if result_holder is None:
            result_holder = {}
        def call():
            if func is None:
                print(f"{name} not wired in!!!")
                return None
            return func(**args)

        call_holder = {}
        for chunk in stream_callable_output(call, call_holder):
            yield chunk

        error = call_holder.get("error")
        if error is not None:
            tb = call_holder.get("tb", "")
            result_holder["result"] = ExecResult(ok=False, error=f"{error}\n\n{tb}")
            return

        stdout = call_holder.get("output", "").strip()
        command_line = (
            f"import {import_prefix}{name} as {name}\n"
            f"{name}.main()  # args: {format_args(args)}"
        )
        self.workspace.record_command(command_line)
        result_holder["result"] = ExecResult(
            stdout=stdout,
            command_line=command_line,
            success_msg=f"Successfully executed standalone command `{name}`!",
        )

    def run_method_stream(self, name, target_var, args, copy_on_write=True, out_var_name="", result_holder: Optional[dict] = None):
        if result_holder is None:
            result_holder = {}
        target_img = self.workspace.get(target_var)
        if target_img is None:
            result_holder["result"] = ExecResult(ok=False, invalid=True, error="No target image available to execute method on.")
            return

        run_obj = target_img.copy() if copy_on_write else target_img
        out_var_name = out_var_name or target_var

        call_holder = {}
        for chunk in stream_callable_output(lambda: getattr(run_obj, name)(**args), call_holder):
            yield chunk

        error = call_holder.get("error")
        if error is not None:
            tb = call_holder.get("tb", "")
            result_holder["result"] = ExecResult(ok=False, error=f"{error}\n\n{tb}")
            return

        result = call_holder.get("result")
        stdout = call_holder.get("output", "").strip()

        res = ExecResult(stdout=stdout)
        args_str = format_args(args)

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
        result_holder["result"] = res


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
    """Execute a workflow script the way the editor's Run button does."""
    result_holder = {}
    for _ in run_script_stream(script_path, script_code, args_input, workspace, ik, result_holder):
        pass
    res = result_holder.get("result")
    if res is not None:
        return res
    return ScriptRunResult(ok=False, message="No result produced.", console_output="", log_path="", log_text="")


def run_script_stream(script_path, script_code, args_input, workspace, ik, result_holder: Optional[dict] = None):
    """Execute a workflow script while streaming output live via yield generator.

    Stores ScriptRunResult in result_holder['result'].
    """
    if result_holder is None:
        result_holder = {}

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

    exit_code = None
    excepted = False
    tb_text = ""

    filename = os.path.abspath(script_path) if script_path else "<string>"
    lines = [line + "\n" for line in script_code.splitlines()]
    linecache.cache[filename] = (len(script_code), None, lines, filename)

    def _exec_target():
        nonlocal exit_code, excepted, tb_text
        try:
            code_obj = compile(script_code, filename, "exec")
            exec(code_obj, exec_namespace)
        except SystemExit as se:
            exit_code = se.code
        except BaseException as e:
            excepted = True
            _, _, tb = sys.exc_info()
            if isinstance(e, SyntaxError):
                tb_text = "".join(traceback.format_exception(e.with_traceback(None)))
            elif tb and tb.tb_next:
                tb_text = "".join(traceback.format_exception(e.with_traceback(tb.tb_next)))
            else:
                tb_text = traceback.format_exc()
        finally:
            sys.argv = original_argv
            sys.path[:] = original_path

    call_holder = {}
    for chunk in stream_callable_output(_exec_target, call_holder):
        yield chunk

    absorbed = workspace.absorb_namespace(exec_namespace)
    captured = call_holder.get("output", "")
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

    res = ScriptRunResult(
        ok=ok,
        message=message,
        console_output=console_output,
        log_path=log_path,
        log_text=log_text,
        absorbed_vars=absorbed,
        exit_code=exit_code,
    )
    result_holder["result"] = res

