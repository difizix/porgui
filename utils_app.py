import argparse
import contextlib
import inspect
import io
import queue
import re
import shlex
import subprocess
import sys
import threading
import traceback
from pathlib import Path
from typing import Optional

from image3kit._core import ostream_redirect

# This file shall not contain any streamlit related imports, those utilities go into app_common.py

top_dir = Path(__file__).parent.resolve()

if str(top_dir) not in sys.path:
    sys.path.insert(0, str(top_dir))

class FormParam:
    def __init__(self, name, default, has_default, type_val, help_text="", is_iterable=False):
        self.name = name
        self.default = default
        self.has_default = has_default
        self.type_val = type_val
        self.help_text = help_text
        self.is_iterable = is_iterable

# Used in difiz, why not here?
def parser2uiparams(parser, fixedargs=None, selected_log_file=None, top_dir=None) -> list:
    if fixedargs is None:
        fixedargs = {}
    actions = [a for a in parser._actions if a.dest != "help"]
    ui_params = []
    for action in actions:
        p_name = action.dest
        if p_name == "logfiles":
            default = [str(top_dir / selected_log_file)] if (selected_log_file and top_dir) else []
            is_iterable = True
            type_val = list
        elif p_name in fixedargs:
            continue
        else:
            default = action.default
            is_iterable = action.nargs in ("+", "*")
            type_val = list if is_iterable else (action.type or (type(default) if default is not None else str))

        ui_params.append(FormParam(
            name=p_name,
            default=default,
            has_default=True,
            type_val=type_val,
            help_text=action.help or "",
            is_iterable=is_iterable
        ))
    return ui_params


def get_module_func_args(module_name: str, argparse_func_name, main_func_name):
    try:
        module = __import__(module_name)
        parser_factory = getattr(module, argparse_func_name)
        main_func = getattr(module, main_func_name)
    except Exception as e:
        print(f"Error loading {module_name}: {e}")
        return None, []

    parser = parser_factory()
    params_meta = []

    for action in parser._actions:
        if action.dest == "help" or isinstance(action, argparse._HelpAction):
            continue

        p_name = action.dest
        p_type = action.type if action.type is not None else str

        if isinstance(action, (argparse._StoreTrueAction, argparse._StoreFalseAction)):
            p_type = bool

        p_default = action.default
        if p_default is argparse.SUPPRESS:
            p_default = None

        p_desc = action.help or ""

        # Map to specific UI dropdown types dynamically based on argument name and description
        p_name_lower = p_name.lower()
        p_desc_lower = p_desc.lower()
        if "xmf" in p_name_lower or "xmf" in p_desc_lower:
            p_type = "xmf_dropdown"
        elif any(k in p_name_lower for k in ("image", "img", "filename")) or "image" in p_desc_lower:
            p_type = "img_dropdown"
        elif "case" in p_name_lower or "case" in p_desc_lower:
            p_type = "case_dropdown"

        params_meta.append({
            "name": p_name,
            "type": p_type,
            "default": p_default,
            "desc": p_desc,
            "action": action
        })

    def wrapped_func(**kwargs):
        cmd_args = []
        for p in params_meta:
            action = p["action"]
            val = kwargs.get(p["name"], p["default"])

            if val is None and action.option_strings:
                continue

            if action.option_strings:
                opt_name = action.option_strings[0]
                if isinstance(action, argparse._StoreTrueAction):
                    if val:
                        cmd_args.append(opt_name)
                elif isinstance(action, argparse._StoreFalseAction):
                    if not val:
                        cmd_args.append(opt_name)
                else:
                    cmd_args.append(opt_name)
                    cmd_args.append(str(val))
            else:
                if val is not None:
                    cmd_args.append(str(val))

        orig_argv = sys.argv
        sys.argv = [main_func.__module__] + cmd_args
        try:
            return main_func()
        finally:
            sys.argv = orig_argv

    cleaned_params = []
    for p in params_meta:
        cleaned_params.append({
            "name": p["name"],
            "type": p["type"],
            "default": p["default"] if p["default"] is not None else "",
            "desc": p["desc"]
        })

    return wrapped_func, cleaned_params



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
    Use FileDropdown / ImageType from user_funcs.py as annotation types to
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
        args_str = ", ".join(f"{k}={repr(v)}" for k, v in args.items())
        cmd_line = f"import {selected_func} as {selected_func}\n{selected_func}.main()  # args: {args_str}"
    elif "self" in args:
        # Object method call (e.g. img.crop(...))
        target_var = args["self"] or selected_var
        other_args = {k: v for k, v in args.items() if k != "self"}
        args_str = ", ".join(f"{k}={repr(v)}" for k, v in other_args.items())
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
        args_str = ", ".join(f"{k}={repr(v)}" for k, v in other_args.items())
        if var_name:
            cmd_line = f"{var_name} = {selected_func}({args_str})"
        else:
            cmd_line = f"{selected_func}({args_str})"
    return cmd_line

def get_output_files(dir=top_dir/"runs"):
    png_files = []
    log_files = []
    exclude_dirs = {".git", ".venv", "__pycache__", ".deps", ".ruff_cache", ".agents", ".antigravity", "tmp-"}

    try:
        for path in dir.rglob("*"):
            if path.is_dir():
                continue
            if any(parent.name in exclude_dirs for parent in path.parents):
                continue
            if path.suffix == ".png":
                png_files.append(path.relative_to(top_dir))
            elif path.suffix == ".log" or path.name in {"log", "log-"} or path.name.startswith("log_"):
                log_files.append(path.relative_to(top_dir))
    except Exception:
        pass

    def sort_key(p):
        try:
            return (-(top_dir / p).stat().st_mtime, str(p))
        except Exception:
            return (0, str(p))

    png_files.sort(key=sort_key)
    log_files.sort(key=sort_key)
    return [str(p) for p in png_files], [str(p) for p in log_files]

def dict2args(args_dict, iterables=None, sig=None, nokey=None, fixedargs=None) -> list:
    if isinstance(iterables, str):
        nokey = iterables
        fixedargs = sig
        iterables = None
        sig = None

    if nokey is not None or fixedargs is not None:
        if fixedargs is None:
            fixedargs = {}
        argv = []
        for k, v in args_dict.items():
            if k == nokey:
                argv.extend(v or [])
            elif v is not None and v != "":
                argv.extend([f"--{k}", str(v)])
        for k, v in fixedargs.items():
            option_flag = f"--{k}"
            if option_flag not in argv:
                argv.extend([option_flag, str(v) if v is not None else ""])
        return argv

    if iterables is None:
        iterables = []
    cmd_parts = []
    for p_name, val in args_dict.items():
        flag_name = p_name.replace("_", "-")
        if p_name in iterables:
            if val:
                for item in val:
                    cmd_parts.append(f"--{flag_name} {shlex.quote(str(item))}")
        elif isinstance(val, bool):
            if val:
                cmd_parts.append(f"--{flag_name}")
            elif sig and p_name in sig.parameters and sig.parameters[p_name].default is True:
                cmd_parts.append(f"--no-{flag_name}")
        else:
            if val == "" or val is None or str(val).strip().lower() == "none":
                continue
            cmd_parts.append(f"--{flag_name} {shlex.quote(str(val))}")
    return cmd_parts

def filter_by_search_query(file_list, query_str):
    if not query_str or not query_str.strip():
        return list(file_list), False

    filtered = list(file_list)
    terms = query_str.split()
    has_error = False

    for term in terms:
        try:
            pattern = re.compile(term.strip(), re.IGNORECASE)
            filtered = [f for f in filtered if pattern.search(str(f))]
        except re.error:
            has_error = True
            filtered = []
            break

    return filtered, has_error


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


def stream_process_output(cmd, cwd=None, env=None):
    """Generator yielding each line of stdout/stderr from a process in real time.

    Streamlit usage:
        st.write_stream(stream_process_output(cmd))
    """
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        cwd=cwd,
        env=env,
    )

    if process.stdout:
        for line in iter(process.stdout.readline, ''):
            yield line
        process.stdout.close()
    process.wait()


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


def stream_callable_output(func, result_holder: Optional[dict] = None, *args, **kwargs):
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
        from streamlit.runtime.scriptrunner import add_script_run_ctx, get_script_run_ctx
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

