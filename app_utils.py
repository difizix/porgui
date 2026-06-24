import inspect
import json
import pwd
import queue
import re
import shlex
import subprocess
import sys
import threading
import time
from pathlib import Path

import streamlit as st

top_dir = Path(__file__).parent.parent.resolve()
assert len(top_dir.name) > 0, "root /app cannot be /"

if str(top_dir) not in sys.path:
    sys.path.insert(0, str(top_dir))
if str(top_dir.parent) not in sys.path:
    sys.path.insert(0, str(top_dir.parent))

from gitops.utils_sh import eval_loss_pc_from_log  # noqa: E402


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






# Try to import the tasks module dynamically
def get_tasks():
    tasks_dict = {}
    try:
        from difiz.gitops import tasks_run  # noqa: PLC0415
        from invoke import Task  # noqa: PLC0415

        # Get all Task instances defined in the module
        for name, obj in inspect.getmembers(tasks_run):
            if isinstance(obj, Task):
                tasks_dict[name] = obj
    except Exception as e:
        import_error = str(e)
    else:
        import_error = None
    return tasks_dict, import_error

class RunCategory:
    def __init__(self, status_code=-1, eval_loss=-100.0, collected=0, latest=False, epoch_tcpu=-1,  eval_tcpu=-1): # order shall be synced with _status_code_eval_loss
        self.status_code = status_code # running -> -1, ok -> 0, failed = 1
        self.collected = collected # conflict -> -1, not -> 0, collected -> 1
        self.latest = latest
        self.eval_loss = eval_loss
        self.epoch_tcpu = epoch_tcpu
        self.eval_tcpu = eval_tcpu

def get_git_head_short(submodule_dir: Path) -> str:
    try:
        res = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(submodule_dir),
            capture_output=True,
            text=True,
            check=True
        )
        return res.stdout.strip()
    except Exception:
        return ""

def _status_code_eval_loss(log):
    path = Path(log)
    if not path.exists() and not path.is_absolute():
        path = top_dir / path

    assert path.exists()

    with path.open("r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()

    try:
        eval_loss = eval_loss_pc_from_log(lines)
    except Exception:
        eval_loss = None

    eval_loss_val = round(eval_loss * 100, 2) if eval_loss is not None else -100.0

    is_recent = False
    try:
        mtime = path.stat().st_mtime
        if time.time() - mtime < 20 * 60:
            is_recent = True
    except Exception:
        pass

    if eval_loss_val != -100.0:
        status_code = 0
    elif is_recent:
        status_code = -1
    else:
        status_code = 1

    return status_code, eval_loss_val

def _is_latest_git(checkout_hashs):
    latest = True
    if not checkout_hashs:
        latest = False
    for item in checkout_hashs:
        if "/" in item:
            module, commit_hash = item.split("/", 1)
            current_head = get_git_head_short(top_dir / module)
            if not current_head or not current_head.startswith(commit_hash):
                latest = False
                break
        else:
            latest = False
            break
    return latest

def log_categories(logs: list[str]) -> dict[str, RunCategory]:
    # expensive function, shall be called in demand, e.g. via a button-click
    ret = {}
    processed_run_names = set()

    for log in logs:
        if "runs/" in log:
            path = Path(log)
            parts = path.parts
            if "runs" in parts:
                idx = parts.index("runs")
                run_name = parts[idx + 1]
            else:
                run_name = path.parent.name

            if run_name in processed_run_names:
                continue
            processed_run_names.add(run_name)

            model_name = None
            for name in ["darcy", "lbx", "sin", "watinj"]:
                if run_name.startswith(name):
                    model_name = name
                    break
            if not model_name:
                model_name = run_name.split("-")[0]

            summary_path = top_dir / f"{model_name}_res" / "run_summary.json"

            summarys = {}
            if summary_path.exists():
                try:
                    with summary_path.open("r") as f:
                        summarys = json.load(f)
                except Exception:
                    pass
            run_key = run_name
            if run_key not in summarys:
                run_key = run_name.split("--")[0] + "-$HEAD"


            if run_key in summarys:
                run_sum = summarys[run_key]
                latest = _is_latest_git(run_sum.get("checkout_hashs", []))
                expected_run_name = run_sum.get("run_name", "")
                if expected_run_name == run_name:
                    loss_val = run_sum.get("loss-eval")
                    if loss_val is not None and loss_val != -100.0:
                        args = run_sum.get("args") or {}
                        train_time = run_sum.get("train-time", -1)
                        num_epochs = args.get("--num-epochs", 1) or 1
                        try:
                            epoch_tcpu = float(train_time) / float(num_epochs)
                        except (ValueError, TypeError, ZeroDivisionError):
                            epoch_tcpu = -1
                        eval_tcpu = run_sum.get("loadnn-time", -1) or -1.0
                        ret[log] = RunCategory(status_code=0, eval_loss=loss_val, collected=1, latest=latest, epoch_tcpu=epoch_tcpu, eval_tcpu=eval_tcpu)
                    else:
                        status, loss_val = _status_code_eval_loss(log)
                        ret[log] = RunCategory(status_code=status, eval_loss=loss_val, collected=-1, latest=latest)
                else:
                    status, loss_val = _status_code_eval_loss(log)
                    ret[log] = RunCategory(status_code=status, eval_loss=loss_val, collected=-1, latest=latest)
            else:
                status, loss_val = _status_code_eval_loss(log)
                ret[log] = RunCategory(status_code=status, eval_loss=loss_val, collected=0, latest=True)

    for summary_path in top_dir.glob("*_res/run_summary.json"):
        try:
            with summary_path.open("r") as f:
                summarys = json.load(f)
        except Exception:
            continue

        for data in summarys.values():
            run_name = data.get("run_name")
            if not run_name:
                continue

            if run_name in processed_run_names:
                continue

            logtag = run_name.split("--")[0]
            log_path = f"runs/{run_name}/log_{logtag}.txt"

            latest = _is_latest_git(data.get("checkout_hashs", []))

            eval_loss = data.get("loss-eval")
            eval_loss_val = eval_loss if eval_loss is not None else -100.0

            status = 0
            collected = 1
            if (top_dir / log_path).exists():
                status, loss_val = _status_code_eval_loss(log_path)
                if loss_val != -100.0:
                    if abs(eval_loss_val-loss_val) > 0.001:
                        collected = -1
                    eval_loss_val = loss_val

            ret[log_path] = RunCategory(status_code=status, eval_loss=eval_loss_val, collected=collected, latest=latest)
            processed_run_names.add(run_name)

    return ret

# Helper to find output logs and images in the project directory
def get_output_files():
    png_files = []
    log_files = []
    exclude_dirs = {".git", ".venv", "__pycache__", ".ruff_cache", ".agents", ".antigravity", "tmp-"}

    try:
        for path in top_dir.rglob("*"):
            if path.is_dir():
                continue
            # Exclude cache or virtualenv directories
            if any(parent.name in exclude_dirs for parent in path.parents):
                continue
            if path.suffix == ".png":
                if "runs" in str(path) and "/rz/" not in str(path):
                    continue # duplicate, unnecassary copy
                png_files.append(path.relative_to(top_dir))
            elif path.suffix == ".log" or path.name in {"log", "log-"} or path.name.startswith("log_"):
                fname = path.name.replace("log_","").replace(".txt","")
                if "runs" in str(path) and fname not in str(path.parent):
                    continue # duplicate, unnecassary copy
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


def filter_files_by_model(files: list, model_name: str) -> list:
    """Return only files whose path string contains the model_name filter.

    If model_name contains '_', only the first segment (before the first '_')
    is used as the filter prefix.
    """
    if not files:
        return ["files-list is empty!"]
    if not model_name or not model_name.strip():
        return files
    # prefix = model_name.strip().split("_")[0]
    return [f for f in files if model_name.lower() in str(f).lower()]


def run_proc_monitor(exec_parts):
    # Start non-blocking process
    proc = subprocess.Popen(
        exec_parts, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=str(top_dir), text=True, bufsize=1
    )

    # Setup async queue reader
    q = queue.Queue()

    def log_reader(p, out_q):
        for line in iter(p.stdout.readline, ""):
            out_q.put(line)
        p.stdout.close()
        p.wait()
        out_q.put(None)  # EOF

    t = threading.Thread(target=log_reader, args=(proc, q), daemon=True)
    t.start()
    return proc, q
 

def filter_by_search_query(file_list, query_str):
    """Filter a list of files (strings or Path objects) by a whitespace-separated query string.

    Each term in the query string is applied as a case-insensitive regex search.
    Returns:
        (filtered_list, has_error)
    """
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


def run_topwd(command_query: str) -> str:
    """Useless: simulate topwd bash function: lsof + top filtered by command_query inside the container."""
    lsof_lines = ["COMMAND    PID    USER    FD      TYPE  DEVICE  SIZE/OFF  NODE  NAME"]

    try:
        proc_dir = Path("/proc")
        pids = []
        for p in proc_dir.iterdir():
            if p.name.isdigit():
                pids.append(int(p.name))
        pids.sort()

        for pid in pids:
            try:
                pid_path = proc_dir / str(pid)
                comm = (pid_path / "comm").read_text().strip()
                cmdline = (pid_path / "cmdline").read_text().replace("\x00", " ").strip()
                if command_query.lower() not in comm.lower() and command_query.lower() not in cmdline.lower():
                    continue
                cwd = str((pid_path / "cwd").readlink())
                stat_info = pid_path.stat()
                try:
                    username = pwd.getpwuid(stat_info.st_uid).pw_name
                except KeyError:
                    username = str(stat_info.st_uid)

                lsof_lines.append(f"{comm:<10} {pid:<6} {username:<7} cwd     DIR   -       -         -     {cwd}")
            except Exception:
                continue
    except Exception as e:
        lsof_lines.append(f"Error scanning /proc: {e}")

    lsof_output = "\n".join(lsof_lines)

    try:
        top_res = subprocess.run(
            ["top", "-b", "-n", "1", "-c", "-w", "512"],
            capture_output=True,
            text=True,
            check=True,
        )
        top_lines = top_res.stdout.splitlines()

        filtered_top = []
        header_idx = 6
        for idx, line in enumerate(top_lines):
            if "PID" in line and "USER" in line:
                header_idx = idx
                break

        filtered_top.extend(top_lines[:header_idx+1])

        for line in top_lines[header_idx+1:]:
            if command_query.lower() in line.lower():
                filtered_top.append(line)

        top_output = "\n".join(filtered_top)
    except Exception as e:
        top_output = f"Error running top: {e}"

    return (
        f"+ lsof -a -d cwd -c {command_query}\n"
        f"{lsof_output}\n\n"
        f"+ top -n 1 -b -c | grep {command_query}\n"
        f"{top_output}"
    )


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
                    help=param.help_text or f"Iterable flag. Values will be passed as multiple --{p_name.replace('_', '-')} values.",
                    key=widget_key,
                    label_visibility="collapsed"
                )
                args_dict[p_name] = [line.strip() for line in val.split("\n") if line.strip()]
        elif type_val is bool:
            with col_label:
                st.markdown(f"<div style='display: flex; align-items: center; min-height: 40px;'><strong>{p_name}</strong></div>", unsafe_allow_html=True)
            with col_widget:
                val = st.checkbox(p_name, value=bool(default), key=widget_key, help=param.help_text, label_visibility="collapsed")
                args_dict[p_name] = val
        elif type_val in (int, float):
            with col_label:
                st.markdown(f"<div style='display: flex; align-items: center; min-height: 40px;'><strong>{p_name}</strong></div>", unsafe_allow_html=True)
            with col_widget:
                if type_val is int:
                    val = st.number_input(p_name, value=int(default) if (default is not None and default is not inspect.Parameter.empty) else 0, step=1, key=widget_key, label_visibility="collapsed", help=param.help_text)
                else:
                    val = st.number_input(p_name, value=float(default) if (default is not None and default is not inspect.Parameter.empty) else 0.0, step=0.1, key=widget_key, label_visibility="collapsed", help=param.help_text)
                args_dict[p_name] = val
        else:
            with col_label:
                st.markdown(f"<div style='display: flex; align-items: center; min-height: 40px;'><strong>{p_name}</strong></div>", unsafe_allow_html=True)
            with col_widget:
                default_str = ""
                if has_default and default is not None and default is not inspect.Parameter.empty:
                    default_str = str(default)
                val = st.text_input(p_name, value=default_str, key=widget_key, label_visibility="collapsed", help=param.help_text)
                args_dict[p_name] = val

    return args_dict