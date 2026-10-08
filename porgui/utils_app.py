from __future__ import annotations

import contextlib
import inspect
import io
import os
import queue
import re
import sys
import threading
import traceback
from pathlib import Path

from image3kit._core import ostream_redirect
from uiutils.argparse_form import form2argv, parser2uiparams
from uiutils.file_discovery import find_outputs

# This file shall not contain any streamlit related imports, those utilities go into app_common.py

# This package's own directory (for sys.path, so the flat `import app_common`
# style used throughout the app keeps working regardless of cwd).
pkg_dir = Path(__file__).parent.resolve()

if str(pkg_dir) not in sys.path:
    sys.path.insert(0, str(pkg_dir))

# Workspace root: where runs/ (outputs, logs, plots) lives. Defaults to the
# current working directory (so `porgui --serve` uses wherever the user
# launched it from), overridable via PORGUI_WORKSPACE. Kept in sync with the
# same default in app.py.
top_dir = Path(os.environ.get("PORGUI_WORKSPACE", os.getcwd())).resolve()

def _dropdown_type(name: str, desc: str, type_val):
    """porgui's file/case dropdown for an argparse option, guessed from its name and help text."""
    name, desc = name.lower(), desc.lower()
    if "xmf" in name or "xmf" in desc:
        return "xmf_dropdown"
    if any(k in name for k in ("image", "img", "filename")) or "image" in desc:
        return "img_dropdown"
    if "case" in name or "case" in desc:
        return "case_dropdown"
    return type_val


def get_module_func_args(module_name: str, argparse_func_name, main_func_name):
    """(main wrapped to take form values as kwargs, form params) of a module with an argparse CLI."""
    try:
        module = __import__(module_name)
        parser = getattr(module, argparse_func_name)()
        main_func = getattr(module, main_func_name)
    except Exception as e:
        print(f"Error loading {module_name}: {e}")
        return None, []

    params = [{"name": p.name, "type": _dropdown_type(p.name, p.help_text, p.type_val),
               "default": "" if p.default is None else p.default, "desc": p.help_text}
              for p in parser2uiparams(parser)]

    def wrapped_func(**kwargs):
        orig_argv = sys.argv
        sys.argv = [main_func.__module__, *form2argv(parser, kwargs)]
        try:
            return main_func()
        finally:
            sys.argv = orig_argv

    return wrapped_func, params



def _first_overload_doc(doc: str) -> str:
    """Reduce a pybind11 "Overloaded function." docstring to its first overload.

    pybind11 free functions bound more than once under the same name (e.g. once
    per dtype) get merged into one object whose docstring's first line is a
    generic "name(*args, **kwargs)" placeholder followed by numbered overload
    signatures - that placeholder has no parseable __text_signature__, so
    inspect.signature() raises ValueError on it. Pull out overload "1." (its
    signature line plus description) so it parses like a normal single-signature
    doc via func_args_from_pybind_doc().
    """
    match = re.search(r"^\d+\.\s*(.+)$", doc, re.MULTILINE)
    if not match:
        return doc
    rest = doc[match.end():]
    next_match = re.search(r"\n\d+\.\s", rest)
    body = rest[:next_match.start()] if next_match else rest
    return match.group(1) + "\n" + body.strip()


def func_args_from_inspect(func) -> dict:
    """Extract params from a fully-annotated Python function using inspect.

    The function must have full type annotations on all parameters.
    Use FileDropdown / ImageType from porgui.toolbox as annotation types to
    get special Streamlit widgets instead of a plain text input.

    Falls back to parsing the docstring's first overload for pybind11 builtins
    bound more than once, which inspect.signature() cannot introspect.

    Returns {"params": [...], "desc": "..."} compatible with CURATED_METHODS.
    """
    try:
        sig = inspect.signature(func)
    except (ValueError, TypeError):
        return func_args_from_pybind_doc(_first_overload_doc(func.__doc__ or ""))
    doc = inspect.getdoc(func) or ""
    params = []
    for name, param in sig.parameters.items():
        annotation = param.annotation
        default = param.default if param.default is not inspect.Parameter.empty else None

        # Resolve Annotated[X, "hint"] → use the hint string as the UI type key,
        # so the renderer can pick the right widget (file_dropdown, type_dropdown, …)
        origin = getattr(annotation, "__metadata__", None)
        if origin:                              # it's an Annotated type
            ui_type = origin[0]                 # e.g. "file_dropdown"
        elif annotation is inspect.Parameter.empty:
            ui_type = str
        else:
            ui_type = annotation                # plain Python type: int, float, bool, str, …

        params.append({
            "name": name,
            "type": ui_type,
            "default": default if default is not None else "",
            "desc": name,   # callers can override via extra_help or docstring parsing
        })

    return {"params": params, "desc": doc}


def args_to_cmd_line(selected_func, args, copy_on_write, selected_var, out_var_name, is_standalone):
    if is_standalone:
        args_str = ", ".join(f"{k}={v!r}" for k, v in args.items())
        cmd_line = f"import {selected_func} as {selected_func}\n{selected_func}.main()  # args: {args_str}"
    elif "self" in args:
        # Object method call (e.g. img.crop(...))
        target_var = args["self"] or selected_var
        other_args = {k: v for k, v in args.items() if k != "self"}
        args_str = ", ".join(f"{k}={v!r}" for k, v in other_args.items())
        if copy_on_write:
            cmd_line = f"{out_var_name} = {target_var}.copy()\n{out_var_name}.{selected_func}({args_str})"
        else:
            cmd_line = f"{out_var_name} = {target_var}\n{out_var_name}.{selected_func}({args_str})"
    else:
        # Standalone Python function (e.g. read_image, mextract, snflow)
        var_name = args.get("new_var_name")
        other_args = {k: v for k, v in args.items() if k != "new_var_name"}
        if other_args.get("max_nz") == -1:
            other_args.pop("max_nz", None)
        args_str = ", ".join(f"{k}={v!r}" for k, v in other_args.items())
        if var_name:
            cmd_line = f"{var_name} = {selected_func}({args_str})"
        else:
            cmd_line = f"{selected_func}({args_str})"
    return cmd_line

def get_output_files():
    """Plots and logs under runs/, as (pngs, logs) relative to top_dir, newest first."""
    return find_outputs(top_dir, prune=lambda d: d.parts[0] != "runs", keep=lambda p: p.parts[0] == "runs")


def func_args_from_pybind_doc(doc: str) -> dict:
    """Parse a pybind11 method docstring into a CURATED_METHODS-compatible dict.

    Returns {"params": [...], "desc": "..."} where desc comes from lines after
    the signature, and params are parsed from the signature's type annotations.
    """
    if not doc:
        return {"params": [], "desc": ""}
    lines = doc.strip().split("\n")
    desc = "\n".join(lines[1:]).strip().replace("\n", " ")
    first_line = lines[0]
    open_idx = first_line.find("(")
    if open_idx == -1:
        return {"params": [], "desc": desc}
    depth = 0
    close_idx = None
    for i in range(open_idx, len(first_line)):
        ch = first_line[i]
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
            if depth == 0:
                close_idx = i
                break
    if close_idx is None:
        return {"params": [], "desc": desc}
    arg_list_str = first_line[open_idx + 1:close_idx]
    parts = []
    current = []
    bracket_depth = 0
    paren_depth = 0
    for char in arg_list_str:
        if char == ',' and bracket_depth == 0 and paren_depth == 0:
            parts.append("".join(current).strip())
            current = []
        else:
            if char in ('[', '{'): bracket_depth += 1
            elif char in (']', '}'): bracket_depth -= 1
            elif char == '(': paren_depth += 1
            elif char == ')': paren_depth -= 1
            current.append(char)
    if current:
        parts.append("".join(current).strip())
    params = []
    for part in parts:
        if not part:
            continue
        if '=' in part:
            declaration, default_str = part.split('=', 1)
            default_str = default_str.strip()
        else:
            declaration = part
            default_str = None
            
        if ':' in declaration:
            name, type_str = declaration.split(':', 1)
            name = name.strip()
            type_str = type_str.strip()
        else:
            name = declaration.strip()
            type_str = ""
            
        py_type = str
        if "bool" in type_str:
            py_type = bool
        elif "int3" in type_str:
            py_type = "int3"
        elif "dbl3" in type_str:
            py_type = "dbl3"
        elif "float" in type_str or "SupportsFloat" in type_str:
            py_type = float
        elif "int" in type_str or "SupportsInt" in type_str or "SupportsIndex" in type_str:
            py_type = int
        elif "Sequence" in type_str or "list" in type_str or "tuple" in type_str:
            py_type = list
        elif "dict" in type_str:
            py_type = dict
        elif "VxlImgU16" in type_str:
            py_type = "VxlImgU16"
        elif "VxlImgU8" in type_str:
            py_type = "VxlImgU8"
        elif "VxlImgI32" in type_str:
            py_type = "VxlImgI32"
        elif "VxlImgF32" in type_str:
            py_type = "VxlImgF32"
        elif "VxlImg" in type_str:
            py_type = "VxlImg"

            
        default_val = None
        if default_str:
            try:
                if default_str == "True":
                    default_val = True
                elif default_str == "False":
                    default_val = False
                elif default_str == "None":
                    default_val = None
                else:
                    default_val = eval(default_str)
            except Exception:
                default_val = default_str

        params.append({"name": name, "type": py_type, "default": default_val, "desc": f"Type: {type_str}"})
    return {"params": params, "desc": desc}


def get_vxlImg_func_args(func_name: str, extra_help=None):
    """Parse args for a VxlImg method from its pybind11 docstring.
    Returns a dict {"params": [...], "desc": "..."} compatible with CURATED_METHODS.
    Falls back to empty params if parsing fails.
    """
    import image3kit as ik
    func = None
    classes_with_func = []
    for cls_name in ["VxlImgU16", "VxlImgU8", "VxlImgI32", "VxlImgF32"]:
        cls = getattr(ik, cls_name, None)
        if cls:
            f = getattr(cls, func_name, None)
            if f:
                classes_with_func.append(cls_name)
                if not func:
                    func = f
    if not func:
        return {"params": [], "desc": f"Function {func_name} not found.\n\n{extra_help}"}

    ret_dict = func_args_from_pybind_doc(func.__doc__ or "")
    if len(classes_with_func) > 1:
        for p in ret_dict["params"]:
            if p["name"] == "self" or (isinstance(p["type"], str) and any(c in p["type"] for c in classes_with_func)):
                p["type"] = "VxlImg"

    if extra_help:
        ret_dict["desc"] += f"\n\n{extra_help}"
    return ret_dict

def get_xdmf_func_args(func_name: str, extra_help=None):
    """Stub to return empty params and description."""
    return {"params": [], "desc": extra_help or ""}


OUTPUT_CAPTURE_LOCK = threading.Lock() # process-wide (all users)


def run_capturing_output(func, *args, **kwargs):
    """Runs a function and captures its combined stdout and stderr.

    Returns:
        tuple: (result, output_str)
    """
    with OUTPUT_CAPTURE_LOCK: # allow one user script run at a time
        stdout_buf = io.StringIO()
        with contextlib.redirect_stdout(stdout_buf), contextlib.redirect_stderr(stdout_buf):
            with ostream_redirect(stdout=True, stderr=True):
                result = func(*args, **kwargs)
    return result, stdout_buf.getvalue()


def render_stream_preformatted(st, stream_gen):
    """Render a live-updating, preformatted (whitespace-preserving) view of a text stream.

    Uses st.code() instead of st.write_stream()/Markdown so indentation, blank
    lines, and exact line breaks from subprocess/print output aren't mangled.
    Returns the full accumulated text once the generator is exhausted.
    """
    placeholder = st.empty()
    chunks = []
    for chunk in stream_gen:
        chunks.append(chunk)
        placeholder.code("".join(chunks), language="text")
    return "".join(chunks)


class _QueueWriter(io.StringIO):
    def __init__(self, q: queue.Queue):
        super().__init__()
        self.q = q

    def write(self, s: str) -> int:
        if s:
            self.q.put(s)
        return len(s) if s else 0

    def flush(self) -> None:
        pass


def stream_callable_output(func, result_holder: dict | None = None, *args, **kwargs):
    """Generator yielding stdout/stderr chunks live while executing func(*args, **kwargs).

    Captures final (result, full_output, error) into result_holder if provided.
    Serializes output redirection using OUTPUT_CAPTURE_LOCK to prevent cross-thread leakage.
    """
    if result_holder is None:
        result_holder = {}

    q = queue.Queue()
    writer = _QueueWriter(q)
    state = {"result": None, "error": None, "tb": ""}

    def worker():
        try:
            with OUTPUT_CAPTURE_LOCK:
                with contextlib.redirect_stdout(writer), contextlib.redirect_stderr(writer):
                    with ostream_redirect(stdout=True, stderr=True):
                        state["result"] = func(*args, **kwargs)
        except BaseException as err:
            state["error"] = err
            state["tb"] = f"{err}\n\n{traceback.format_exc()}"
        finally:
            q.put(None)

    t = threading.Thread(target=worker, daemon=True)
    try:
        from streamlit.runtime.scriptrunner import (
            add_script_run_ctx,
            get_script_run_ctx,
        )
        ctx = get_script_run_ctx()
        if ctx is not None:
            add_script_run_ctx(t, ctx)
    except Exception:
        pass

    t.start()

    accumulated = []
    while True:
        chunk = q.get()
        if chunk is None:
            break
        accumulated.append(chunk)
        yield chunk

    t.join()
    full_output = "".join(accumulated)
    result_holder["result"] = state["result"]
    result_holder["output"] = full_output
    result_holder["error"] = state["error"]
    result_holder["tb"] = state["tb"]

