import os
import sys

# Ensure repository root is in sys.path
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

import image3kit as ik

from state_app import DictStore, SessionStore, Workspace, coerce_to_wrapper

DATA_FILE = os.path.join(repo_root, "runs", "Pak2D_240x200x1_5um.dat")

VOXLIB = ik._core.voxlib


def make_workspace():
    """A Workspace wired to the real unpatched C++ classes, as app.py does."""
    store = DictStore()
    store["original_VxlImgU16"] = VOXLIB.VxlImgU16
    store["original_VxlImgU8"] = VOXLIB.VxlImgU8
    store["original_VxlImgI32"] = VOXLIB.VxlImgI32
    store["original_VxlImgF32"] = VOXLIB.VxlImgF32
    store["original_voxelImageTBase"] = VOXLIB.voxelImageTBase
    return Workspace(store)


# --------------------------------------------------------------------------
# Layering invariant
# --------------------------------------------------------------------------
def test_domain_layer_does_not_import_streamlit():
    """The whole point of these modules: they must stay testable without a
    `streamlit run` context. Importing them must not drag streamlit in.
    """
    import subprocess

    check = subprocess.run(
        [sys.executable, "-c", "import state_app, presenters_app, utils_app, sys;"
                              " sys.exit(1 if 'streamlit' in sys.modules else 0)"],
        cwd=repo_root,
    )
    assert check.returncode == 0, "a framework-free module imported streamlit"


# --------------------------------------------------------------------------
# SessionStore
# --------------------------------------------------------------------------
def test_session_store_item_and_attribute_access_are_the_same_slot():
    """Call sites use st.session_state.x and st.session_state["x"]
    interchangeably, so the port must too.
    """
    store = DictStore()
    store["a"] = 1
    assert store.a == 1
    store.b = 2
    assert store["b"] == 2
    assert dict(store) == {"a": 1, "b": 2}


def test_session_store_missing_attribute_raises_attribute_error():
    """Must behave like an object, not leak KeyError, so hasattr/getattr work."""
    store = DictStore()
    assert not hasattr(store, "nope")


def test_session_store_wraps_an_existing_mapping_in_place():
    """StreamlitStore works by wrapping st.session_state itself, so writes must
    land in the backing mapping rather than a copy.
    """
    backing = {"x": 1}
    store = SessionStore(backing)
    store.y = 2
    assert backing == {"x": 1, "y": 2}


# --------------------------------------------------------------------------
# Workspace.record_command  (replaces the 6x duplicated append idiom)
# --------------------------------------------------------------------------
def test_record_command_on_empty_history_does_not_prepend_blank_lines():
    ws = make_workspace()
    ws.record_command("a = 1")
    assert ws.session_commands == "a = 1"


def test_record_command_appends_with_blank_line_separator():
    ws = make_workspace()
    ws.record_command("a = 1")
    ws.record_command("b = 2")
    assert ws.session_commands == "a = 1\n\nb = 2"


def test_record_command_ignores_empty_command():
    ws = make_workspace()
    ws.record_command("a = 1")
    ws.record_command("")
    assert ws.session_commands == "a = 1"


# --------------------------------------------------------------------------
# Workspace.unique_name
# --------------------------------------------------------------------------
def test_unique_name_returns_base_when_free():
    ws = make_workspace()
    assert ws.unique_name("img_filtered") == "img_filtered"


def test_unique_name_suffixes_past_existing_collisions():
    ws = make_workspace()
    ws.store_var("img_filtered", object())
    ws.store_var("img_filtered_1", object())
    assert ws.unique_name("img_filtered") == "img_filtered_2"


# --------------------------------------------------------------------------
# Workspace image queries / mutations
# --------------------------------------------------------------------------
def test_image_vars_filters_out_non_image_values():
    ws = make_workspace()
    ws.store_var("threshold", 128)
    ws.store_var("label", "not an image")
    img = ik.VxlImgU16(DATA_FILE)
    ws.store_image("wet", img)
    assert ws.image_vars() == ["wet"]


def test_store_image_updates_active_var_and_processed_image_together():
    """The viewer reads active_var, the renderer reads processed_image; they
    drifting apart is what makes an image "not show up" in the tab.
    """
    ws = make_workspace()
    img = ik.VxlImgU16(DATA_FILE)
    ws.store_image("wet", img)
    assert ws.active_var == "wet"
    assert ws.processed_image is img


def test_store_image_can_leave_the_active_variable_alone():
    ws = make_workspace()
    first = ik.VxlImgU16(DATA_FILE)
    ws.store_image("wet", first)
    ws.store_image("mask", ik.VxlImgU16(DATA_FILE), make_active=False)
    assert ws.active_var == "wet"
    assert "mask" in ws.image_vars()


def test_set_active_ignores_unknown_names():
    ws = make_workspace()
    ws.store_image("wet", ik.VxlImgU16(DATA_FILE))
    ws.set_active("does_not_exist")
    assert ws.active_var == "wet"


# --------------------------------------------------------------------------
# Workspace.absorb_namespace  (was app.py's update_workspace_vars)
# --------------------------------------------------------------------------
def test_absorb_namespace_picks_up_only_image_typed_variables():
    ws = make_workspace()
    absorbed = ws.absorb_namespace({
        "MAX_NZ": 50,
        "wet": ik.VxlImgU16(DATA_FILE),
        "Path": os.path,
    })
    assert absorbed == ["wet"]
    assert ws.image_vars() == ["wet"]


def test_absorb_namespace_prefers_a_variable_named_img_as_active():
    ws = make_workspace()
    ws.absorb_namespace({
        "wet": ik.VxlImgU16(DATA_FILE),
        "img": ik.VxlImgU16(DATA_FILE),
    })
    assert ws.active_var == "img"


def test_absorb_namespace_exposes_threshold01_otsu_result():
    """Regression guard for the rock_mask case: threshold01_otsu returns a
    VxlImgU8 straight from _core.voxlib (not a patched wrapper), and running
    differential_imaging.py in the editor must leave it selectable in the
    Image Processing tab's variable dropdown.
    """
    ws = make_workspace()
    wet = ik.VxlImgU16(DATA_FILE)
    rock_mask = ik.threshold01_otsu(wet)

    ws.absorb_namespace({"wet": wet, "rock_mask": rock_mask})

    assert "rock_mask" in ws.image_vars()


def test_absorb_namespace_keeps_images_built_before_a_script_failed():
    """A workflow script that dies partway must not lose the variables it had
    already produced. differential_imaging.py computes rock_mask early and can
    fail later; app_editor.py now absorbs the namespace on the error path too.
    """
    ws = make_workspace()
    namespace = {}
    script = (
        "import image3kit as ik\n"
        f"wet = ik.VxlImgU16({DATA_FILE!r})\n"
        "rock_mask = ik.threshold01_otsu(wet)\n"
        "raise RuntimeError('boom, partway through')\n"
    )

    try:
        exec(script, namespace)
    except RuntimeError:
        pass

    ws.absorb_namespace(namespace)

    assert "rock_mask" in ws.image_vars()
    assert "wet" in ws.image_vars()


def test_image_types_includes_the_common_voxel_base_class():
    """voxelImageTBase is what catches images returned straight from
    _core.voxlib; dropping it from the tuple silently hides those results.
    """
    ws = make_workspace()
    assert VOXLIB.voxelImageTBase in ws.image_types


def test_workspace_tolerates_missing_image_type_registrations():
    """On the very first rerun app.py may not have populated the class refs
    yet; the workspace must degrade quietly rather than raise.
    """
    bare = Workspace(DictStore())
    assert bare.image_types == ()
    assert bare.image_vars() == []
    assert bare.absorb_namespace({"x": 1}) == []


# --------------------------------------------------------------------------
# coerce_to_wrapper
# --------------------------------------------------------------------------
def test_coerce_to_wrapper_rewraps_a_raw_core_image():
    class PatchedU8(VOXLIB.VxlImgU8):
        pass

    raw = ik.threshold01_otsu(ik.VxlImgU16(DATA_FILE))
    assert not isinstance(raw, PatchedU8)

    out = coerce_to_wrapper(raw, {VOXLIB.VxlImgU8: PatchedU8})
    assert isinstance(out, PatchedU8)


def test_coerce_to_wrapper_leaves_already_wrapped_images_untouched():
    class PatchedU8(VOXLIB.VxlImgU8):
        pass

    already = PatchedU8(ik.threshold01_otsu(ik.VxlImgU16(DATA_FILE)))
    assert coerce_to_wrapper(already, {VOXLIB.VxlImgU8: PatchedU8}) is already


def test_coerce_to_wrapper_passes_through_none_and_non_images():
    assert coerce_to_wrapper(None, {VOXLIB.VxlImgU8: VOXLIB.VxlImgU8}) is None
    stats = [1.0, 2.0]
    assert coerce_to_wrapper(stats, {VOXLIB.VxlImgU8: VOXLIB.VxlImgU8}) is stats
