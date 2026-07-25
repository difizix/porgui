import os
import sys

# Ensure repository root is in sys.path
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if not os.path.exists(repo_root) and os.path.exists("/app"):
    repo_root = "/app"
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

import image3kit as ik

from app_presenters import (
    ExecutionPresenter,
    format_args,
    parse_cli_args,
    resolve_object_args,
    run_script,
)
from app_state import DictStore, Workspace

DATA_FILE = os.path.join(repo_root, "runs", "Pak2D_240x200x1_5um.dat")

VOXLIB = ik._core.voxlib
TYPE_NAMES = ("VxlImgU16", "VxlImgU8", "VxlImgI32", "VxlImgF32", "VxlImg")


def make_workspace():
    store = DictStore()
    store["original_VxlImgU16"] = VOXLIB.VxlImgU16
    store["original_VxlImgU8"] = VOXLIB.VxlImgU8
    store["original_VxlImgI32"] = VOXLIB.VxlImgI32
    store["original_VxlImgF32"] = VOXLIB.VxlImgF32
    store["original_voxelImageTBase"] = VOXLIB.voxelImageTBase
    return Workspace(store)


def make_presenter():
    workspace = make_workspace()
    return ExecutionPresenter(workspace), workspace


# --------------------------------------------------------------------------
# run_python_func
# --------------------------------------------------------------------------
def test_run_python_func_stores_image_result_and_records_command():
    presenter, ws = make_presenter()

    res = presenter.run_python_func("read_image", ik.read_image, {"filename": DATA_FILE})

    assert res.ok and res.is_image
    assert res.stored_var == "read_image"
    assert ws.get("read_image") is not None
    assert ws.active_var == "read_image"
    assert ws.session_commands.startswith("read_image = read_image(")


def test_run_python_func_captures_cpp_stdout():
    """C++ std::cout output must reach the panel, not the server terminal."""
    presenter, _ = make_presenter()
    res = presenter.run_python_func("read_image", ik.read_image, {"filename": DATA_FILE})
    assert "reading" in res.stdout.lower()


def test_run_python_func_rejects_empty_filename_without_running():
    presenter, ws = make_presenter()
    res = presenter.run_python_func("read_image", ik.read_image, {"filename": ""})
    assert not res.ok and res.invalid
    assert res.error == "Please select a file to load."
    assert ws.session_commands == ""


def test_run_python_func_honours_explicit_output_variable_name():
    presenter, ws = make_presenter()
    presenter.run_python_func("read_image", ik.read_image, {"filename": DATA_FILE}, out_var_name="dry")
    assert ws.image_vars() == ["dry"]


def test_run_python_func_keeps_non_image_result_out_of_the_workspace():
    presenter, ws = make_presenter()

    def stats(**kwargs):
        return [1.0, 2.0, 3.0]

    res = presenter.run_python_func("stats", stats, {})
    assert not res.is_image
    assert res.nonimage_result == [1.0, 2.0, 3.0]
    assert res.nonimage_func == "stats"
    assert ws.image_vars() == []


def test_run_python_func_reports_exceptions_instead_of_raising():
    presenter, _ = make_presenter()

    def boom(**kwargs):
        raise RuntimeError("kaboom")

    res = presenter.run_python_func("boom", boom, {})
    assert not res.ok
    assert "kaboom" in res.error


def test_run_python_func_stores_threshold01_otsu_result():
    """threshold01_otsu returns a raw _core.voxlib.VxlImgU8; it must still be
    recognised as an image and land in the workspace (the rock_mask case).
    """
    presenter, ws = make_presenter()
    wet = ik.VxlImgU16(DATA_FILE)
    ws.store_image("wet", wet)

    res = presenter.run_python_func("threshold01_otsu", ik.threshold01_otsu, {"image": wet}, out_var_name="rock_mask")

    assert res.is_image
    assert "rock_mask" in ws.image_vars()


# --------------------------------------------------------------------------
# run_method
# --------------------------------------------------------------------------
def test_run_method_copy_on_write_leaves_the_source_image_untouched():
    presenter, ws = make_presenter()
    ws.store_image("img", ik.VxlImgU16(DATA_FILE))
    source = ws.get("img")

    presenter.run_method("median_filter", "img", {}, copy_on_write=True, out_var_name="img_filtered")

    assert ws.get("img") is source
    assert "img_filtered" in ws.image_vars()


def test_run_method_treats_void_mutator_result_as_the_image():
    """median_filter mutates in place and returns None; the run object is the
    result, otherwise an in-place op would look like it produced nothing.
    """
    presenter, ws = make_presenter()
    ws.store_image("img", ik.VxlImgU16(DATA_FILE))

    res = presenter.run_method("median_filter", "img", {}, copy_on_write=True, out_var_name="out")

    assert res.is_image
    assert res.stored_var == "out"
    assert ws.get("out") is not None


def test_run_method_keeps_genuine_data_results_out_of_the_workspace():
    """otsu_threshold returns a list of stats, not an image."""
    presenter, ws = make_presenter()
    ws.store_image("img", ik.VxlImgU16(DATA_FILE))

    res = presenter.run_method("otsu_threshold", "img", {}, copy_on_write=True, out_var_name="stats")

    assert not res.is_image
    assert res.nonimage_result is not None
    assert "stats" not in ws.image_vars()


def test_run_method_rejects_a_missing_target_image():
    presenter, ws = make_presenter()
    res = presenter.run_method("median_filter", "nope", {})
    assert not res.ok and res.invalid
    assert ws.session_commands == ""


def test_run_method_command_line_reflects_copy_on_write():
    presenter, ws = make_presenter()
    ws.store_image("img", ik.VxlImgU16(DATA_FILE))

    copied = presenter.run_method("median_filter", "img", {}, copy_on_write=True, out_var_name="a")
    assert copied.command_line == "a = img.copy()\na.median_filter()"

    inplace = presenter.run_method("median_filter", "img", {}, copy_on_write=False, out_var_name="b")
    assert inplace.command_line == "b = img\nb.median_filter()"


# --------------------------------------------------------------------------
# run_standalone
# --------------------------------------------------------------------------
def test_run_standalone_records_command_and_reports_success():
    presenter, ws = make_presenter()
    calls = []

    res = presenter.run_standalone("mextract", lambda **kw: calls.append(kw), {"x": 1})

    assert res.ok and calls == [{"x": 1}]
    assert "mextract" in ws.session_commands


def test_run_standalone_reports_an_unwired_function_without_crashing():
    presenter, _ = make_presenter()
    res = presenter.run_standalone("ghost", None, {})
    assert res.ok
    assert "not wired in" in res.stdout


# --------------------------------------------------------------------------
# history accumulates across runs
# --------------------------------------------------------------------------
def test_session_commands_accumulate_across_successive_runs():
    presenter, ws = make_presenter()
    presenter.run_python_func("read_image", ik.read_image, {"filename": DATA_FILE}, out_var_name="a")
    presenter.run_method("median_filter", "a", {}, copy_on_write=True, out_var_name="b")

    assert ws.session_commands.count("\n\n") == 1
    assert "a = read_image(" in ws.session_commands
    assert "b = a.copy()" in ws.session_commands


# --------------------------------------------------------------------------
# resolve_object_args
# --------------------------------------------------------------------------
def test_resolve_object_args_swaps_variable_names_for_objects():
    workspace_vars = {"mask": "THE MASK"}
    params = [{"name": "mask", "type": "VxlImgU8"}]
    out = resolve_object_args({"mask": "mask"}, params, workspace_vars, TYPE_NAMES)
    assert out == {"mask": "THE MASK"}


def test_resolve_object_args_drops_none_selection_so_defaults_apply():
    params = [{"name": "mask", "type": "VxlImgU8"}]
    out = resolve_object_args({"mask": ""}, params, {}, TYPE_NAMES)
    assert "mask" not in out


def test_resolve_object_args_leaves_scalar_params_alone():
    params = [{"name": "threshold", "type": int}]
    out = resolve_object_args({"threshold": 128}, params, {}, TYPE_NAMES)
    assert out == {"threshold": 128}


def test_format_args_uses_repr_so_the_snippet_is_runnable():
    assert format_args({"path": "a.raw", "n": 3}) == "path='a.raw', n=3"


# --------------------------------------------------------------------------
# parse_cli_args
# --------------------------------------------------------------------------
def test_parse_cli_args_resolves_an_existing_relative_path_to_absolute(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "input.dat").write_text("data")

    parsed = parse_cli_args("--x0 374 input.dat --flag")

    assert parsed[0] == "--x0"
    assert parsed[1] == "374"
    assert parsed[2] == str((tmp_path / "input.dat").resolve())
    assert parsed[3] == "--flag"


def test_parse_cli_args_leaves_nonexistent_paths_alone(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert parse_cli_args("--name not_a_real_file.dat") == ["--name", "not_a_real_file.dat"]


# --------------------------------------------------------------------------
# run_script
# --------------------------------------------------------------------------
def test_run_script_success_stores_variables_and_captures_cpp_stdout():
    ws = make_workspace()
    script = (
        "import image3kit as ik\n"
        f"wet = ik.VxlImgU16({DATA_FILE!r})\n"
        "wet.print_info()\n"
    )

    result = run_script("differential_imaging.py", script, "", ws, ik)

    assert result.ok
    assert result.message == "Workflow completed successfully!"
    assert "wet" in result.absorbed_vars
    assert "wet" in ws.image_vars()
    assert "total_porosity" in result.console_output
    assert result.log_text.startswith("✅")


def test_run_script_clean_sys_exit_is_treated_as_success():
    ws = make_workspace()
    result = run_script("script.py", "import sys\nsys.exit(0)\n", "", ws, ik)
    assert result.ok
    assert result.message == "Workflow completed successfully!"


def test_run_script_nonzero_sys_exit_is_an_error_with_the_code_in_the_message():
    ws = make_workspace()
    result = run_script("script.py", "import sys\nsys.exit(2)\n", "", ws, ik)
    assert not result.ok
    assert "exited with code 2" in result.message
    assert "SystemExit: 2" in result.log_text


def test_run_script_keeps_variables_built_before_a_later_failure():
    """Regression guard for the rock_mask bug: a script that builds an image
    and then dies must not lose that image. Exercises the real run_script,
    not a hand-simulated exec/except like the earlier Workspace-level test.
    """
    ws = make_workspace()
    script = (
        "import image3kit as ik\n"
        f"wet = ik.VxlImgU16({DATA_FILE!r})\n"
        "rock_mask = ik.threshold01_otsu(wet)\n"
        "raise RuntimeError('boom, partway through')\n"
    )

    result = run_script("differential_imaging.py", script, "", ws, ik)

    assert not result.ok
    assert result.message == "Workflow failed with execution error."
    assert "RuntimeError" in result.console_output
    assert "rock_mask" in result.absorbed_vars
    assert "rock_mask" in ws.image_vars()
    assert result.log_text.startswith("⛔")


def test_run_script_restores_sys_argv_and_sys_path():
    import sys

    ws = make_workspace()
    original_argv = list(sys.argv)
    original_path = list(sys.path)

    run_script("differential_imaging.py", "x = 1\n", "--foo bar", ws, ik)

    assert sys.argv == original_argv
    assert sys.path == original_path


def test_run_script_passes_workspace_variables_into_the_script():
    ws = make_workspace()
    ws.store_image("wet", ik.VxlImgU16(DATA_FILE))

    result = run_script("script.py", "assert wet is not None\nresult_ok = True\n", "", ws, ik)

    assert result.ok
