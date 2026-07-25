import os
import sys
import time

# Ensure repository root is in sys.path
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if not os.path.exists(repo_root) and os.path.exists("/app"):
    repo_root = "/app"
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

import image3kit as ik
from utils_app import stream_process_output, stream_callable_output
from app_presenters import ExecutionPresenter, run_script_stream
from app_state import DictStore, Workspace


def test_stream_process_output():
    cmd = [
        sys.executable,
        "-u",
        "-c",
        "import sys; print('Line 1'); print('Line 2'); sys.stdout.flush()",
    ]
    lines = list(stream_process_output(cmd, cwd=repo_root))
    assert any("Line 1" in l for l in lines)
    assert any("Line 2" in l for l in lines)


def test_stream_callable_output():
    def sample_func(a, b):
        print("Starting computation...")
        res = a + b
        print(f"Result is {res}")
        return res

    holder = {}
    chunks = list(stream_callable_output(sample_func, holder, 10, 20))
    full_output = "".join(chunks)
    assert "Starting computation..." in full_output
    assert "Result is 30" in full_output
    assert holder["result"] == 30
    assert holder["error"] is None


def make_workspace():
    store = DictStore()
    store["original_VxlImgU16"] = ik._core.voxlib.VxlImgU16
    store["original_VxlImgU8"] = ik._core.voxlib.VxlImgU8
    store["original_VxlImgI32"] = ik._core.voxlib.VxlImgI32
    store["original_VxlImgF32"] = ik._core.voxlib.VxlImgF32
    store["original_voxelImageTBase"] = ik._core.voxlib.voxelImageTBase
    return Workspace(store)


def test_run_script_stream():
    ws = make_workspace()

    code = (
        "import image3kit as ik\n"
        "print('Workflow step 1')\n"
        "img1 = ik.VxlImgU16()\n"
        "print('Workflow step 2')\n"
    )

    script_path = os.path.join(repo_root, "runs", "test_stream_wf.py")
    result_holder = {}
    stream_chunks = list(run_script_stream(script_path, code, "", ws, ik, result_holder))
    streamed_text = "".join(stream_chunks)

    res = result_holder.get("result")
    assert res is not None
    assert res.ok is True
    assert "Workflow step 1" in streamed_text
    assert "Workflow step 2" in streamed_text
    assert "img1" in res.absorbed_vars
    assert ws.get("img1") is not None


def test_execution_presenter_streaming():
    store = DictStore()
    ws = Workspace(store)
    presenter = ExecutionPresenter(ws)

    def my_py_func(val: int):
        print(f"py_func with val={val}")
        return val * 2

    holder = {}
    chunks = list(presenter.run_python_func_stream("my_py_func", my_py_func, {"val": 21}, result_holder=holder))
    streamed_text = "".join(chunks)
    res = holder.get("result")

    assert res is not None
    assert res.ok is True
    assert "py_func with val=21" in streamed_text
    assert res.nonimage_result == 42
