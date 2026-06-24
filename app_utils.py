import inspect
import json
import re
import shlex
import sys
import time
from pathlib import Path
import streamlit as st

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

def get_output_files():
    png_files = []
    log_files = []
    exclude_dirs = {".git", ".venv", "__pycache__", ".ruff_cache", ".agents", ".antigravity", "tmp-"}

    try:
        for path in top_dir.rglob("*"):
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

def render_parseargs(params, key_prefix=""):
    args_dict = {}
    for param in params:
        p_name = param.name
        default = param.default
        has_default = param.has_default
        is_iterable = param.is_iterable
        type_val = param.type_val
        widget_key = f"{key_prefix}_{p_name}"

        col_label, col_widget = st.columns([1, 4])

        if is_iterable:
            with col_label:
                st.markdown(f"<div style='display: flex; align-items: flex-start; padding-top: 10px;'><strong>{p_name}</strong></div>", unsafe_allow_html=True)
            with col_widget:
                default_str = ""
                if has_default and default:
                    if isinstance(default, (list, tuple)):
                        default_str = "\n".join(str(d) for d in default)
                    else:
                        default_str = str(default)
                val = st.text_area(
                    p_name,
                    value=default_str,
                    key=widget_key,
                    label_visibility="collapsed"
                )
                args_dict[p_name] = [line.strip() for line in val.split("\n") if line.strip()]
        elif type_val is bool:
            with col_label:
                st.markdown(f"<div style='display: flex; align-items: center; min-height: 40px;'><strong>{p_name}</strong></div>", unsafe_allow_html=True)
            with col_widget:
                val = st.checkbox(p_name, value=bool(default), key=widget_key, label_visibility="collapsed")
                args_dict[p_name] = val
        elif type_val in (int, float):
            with col_label:
                st.markdown(f"<div style='display: flex; align-items: center; min-height: 40px;'><strong>{p_name}</strong></div>", unsafe_allow_html=True)
            with col_widget:
                if type_val is int:
                    val = st.number_input(p_name, value=int(default) if (default is not None and default is not inspect.Parameter.empty) else 0, step=1, key=widget_key, label_visibility="collapsed")
                else:
                    val = st.number_input(p_name, value=float(default) if (default is not None and default is not inspect.Parameter.empty) else 0.0, step=0.1, key=widget_key, label_visibility="collapsed")
                args_dict[p_name] = val
        else:
            with col_label:
                st.markdown(f"<div style='display: flex; align-items: center; min-height: 40px;'><strong>{p_name}</strong></div>", unsafe_allow_html=True)
            with col_widget:
                default_str = ""
                if has_default and default is not None and default is not inspect.Parameter.empty:
                    default_str = str(default)
                val = st.text_input(p_name, value=default_str, key=widget_key, label_visibility="collapsed")
                args_dict[p_name] = val

    return args_dict


def parse_pybind_docstring(docstring):
    if not docstring:
        return []
    first_line = docstring.strip().split("\n")[0]
    match = re.match(r"^\w+\((.*)\)(?:\s*->\s*\w+)?", first_line)
    if not match:
        return []
    arg_list_str = match.group(1)
    args = []
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
                
        args.append({
            "name": name,
            "type": py_type,
            "default": default_val,
            "desc": f"Type: {type_str}"
        })
    return args