import argparse
import inspect
import re
import shlex
import sys
import io
import contextlib
from pathlib import Path

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



def func_args_from_inspect(func) -> dict:
    """Extract params from a fully-annotated Python function using inspect.

    The function must have full type annotations on all parameters.
    Use FileDropdown / ImageType from user_funcs.py as annotation types to
    get special Streamlit widgets instead of a plain text input.

    Returns {"params": [...], "desc": "..."} compatible with CURATED_METHODS.
    """
    sig = inspect.signature(func)
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
    if selected_func == "loadImg":
        filename = args["filename"]
        img_type = args["img_type"]
        var_name = args["new_var_name"]
        cmd_line = f"{var_name} = ik.{img_type}('{filename}')"
    elif is_standalone:
        args_str = ", ".join(f"{k}={repr(v)}" for k, v in args.items())
        cmd_line = f"import pyvtk.{selected_func} as {selected_func}\n{selected_func}.main()  # args: {args_str}"
    else:
        args_str = ", ".join(f"{k}={repr(v)}" for k, v in args.items())
        if copy_on_write:
            cmd_line = f"{out_var_name} = {selected_var}.copy()\n{out_var_name}.{selected_func}({args_str})"
        else:
            cmd_line = f"{out_var_name} = {selected_var}\n{out_var_name}.{selected_func}({args_str})"
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
    match = re.match(r"^\w+\((.*)\)(?:\s*->\s*\w+)?", first_line)
    if not match:
        return {"params": [], "desc": desc}
    arg_list_str = match.group(1)
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
        if not part or part.startswith("self"):
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
        elif "int" in type_str or "SupportsInt" in type_str or "SupportsIndex" in type_str:
            py_type = int
        elif "float" in type_str or "SupportsFloat" in type_str:
            py_type = float
        elif "Sequence" in type_str or "list" in type_str or "tuple" in type_str:
            py_type = list
        elif "dict" in type_str:
            py_type = dict
            
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
    """Parse args for a VxlImgU8 method from its pybind11 docstring.
    Returns a dict {"params": [...], "desc": "..."} compatible with CURATED_METHODS.
    Falls back to empty params if parsing fails.
    """
    import image3kit as ik
    func = getattr(ik.VxlImgU8, func_name, None)
    if not func:
        return {"params": [], "desc": f"Function {func_name} not found.\n\n{extra_help}"}

    ret_dict = func_args_from_pybind_doc(func.__doc__ or "")
    if extra_help:
        ret_dict["desc"] += f"\n\n{extra_help}"
    return ret_dict

def get_xdmf_func_args(func_name: str, extra_help=None):
    """Parse args for a Xdmf method from its pybind11 docstring.
    Returns a dict {"params": [...], "desc": "..."} compatible with CURATED_METHODS.
    Falls back to empty params if parsing fails.
    """
    import pnmkit as nm
    func = getattr(nm.Xdmf, func_name, None)
    if not func:
        return {"params": [], "desc": f"Function {func_name} not found.\n\n{extra_help}"}

    ret_dict = func_args_from_pybind_doc(func.__doc__ or "")
    if extra_help:
        ret_dict["desc"] += f"\n\n{extra_help}"
    return ret_dict


def run_capturing_output(func, *args, **kwargs):
    """Runs a function and captures its combined stdout and stderr.

    Returns:
        tuple: (result, output_str)
    """
    stdout_buf = io.StringIO()
    with contextlib.redirect_stdout(stdout_buf), contextlib.redirect_stderr(stdout_buf):
        result = func(*args, **kwargs)
    return result, stdout_buf.getvalue()
