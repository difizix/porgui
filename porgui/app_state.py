"""GUI-framework-independent session state and workspace model.

This file shall not contain any streamlit related imports, the adapter that
binds SessionStore to st.session_state lives in app_common.py.

Streamlit's st.session_state only functions under `streamlit run`, so any logic
reaching for it directly cannot be unit tested. SessionStore is the port that
hides it: the domain code below talks to the port, the app binds it to the real
st.session_state, and tests bind it to a plain dict (DictStore).
"""

from collections.abc import MutableMapping


class SessionStore(MutableMapping):
    """Per-session key/value state, independent of any UI framework.

    Backed by any MutableMapping. Supports both item and attribute access so
    that call sites read the same whether they are backed by st.session_state
    (itself a MutableMapping) or by a plain dict in tests.
    """

    def __init__(self, data=None):
        object.__setattr__(self, "_data", {} if data is None else data)

    # -- Mapping interface -------------------------------------------------
    def __getitem__(self, key):
        return self._data[key]

    def __setitem__(self, key, value):
        self._data[key] = value

    def __delitem__(self, key):
        del self._data[key]

    def __iter__(self):
        return iter(self._data)

    def __len__(self):
        return len(self._data)

    # -- Attribute access, mirroring st.session_state ----------------------
    def __getattr__(self, name):
        # Only called when normal lookup fails; guard "_" names so that the
        # internal _data lookup can never recurse.
        if name.startswith("_"):
            raise AttributeError(name)
        try:
            return self._data[name]
        except KeyError:
            raise AttributeError(name) from None

    def __setattr__(self, name, value):
        if name.startswith("_"):
            object.__setattr__(self, name, value)
        else:
            self._data[name] = value

    def __repr__(self):
        return f"{type(self).__name__}({dict(self._data)!r})"


class DictStore(SessionStore):
    """Plain-dict SessionStore for tests and any non-streamlit front end."""


def coerce_to_wrapper(raw, wrappers):
    """Re-wrap a raw C++ image in its matching subclass from `wrappers`.

    app.py monkeypatches ik.VxlImg* with caching subclasses; results handed back
    from image3kit are plain _core.voxlib instances. `wrappers` maps a base class
    to the wrapper to re-wrap it with, so results stay the caching kind. Anything
    already an instance of its wrapper, or matching no base, is returned as is.
    """
    if raw is None:
        return None
    for base, wrapper in wrappers.items():
        if isinstance(raw, base) and not isinstance(raw, wrapper):
            return wrapper(raw)
    return raw


class Workspace:
    """The user's live workspace: named images, the active one, and history.

    Wraps a SessionStore rather than owning a dict so that state survives
    streamlit reruns when bound to st.session_state, while staying a plain
    object that tests can drive directly.
    """

    #: session keys holding the unpatched C++ classes, set up by app.py.
    #: VoxelImagesBase is the common base of every VxlImg* type, so it also
    #: catches images returned straight from _core.voxlib (e.g. the VxlImgU8
    #: from threshold01_otsu) that are not instances of the patched wrappers.
    IMAGE_TYPE_KEYS = (
        "original_VxlImgU16",
        "original_VxlImgU8",
        "original_VxlImgI32",
        "original_VxlImgF32",
        "original_VxlImgBase",
    )

    def __init__(self, store=None):
        self._store = DictStore() if store is None else store
        self._store.setdefault("workspace_vars", {})
        self._store.setdefault("image_cache", {})
        self._store.setdefault("session_commands", "")
        self._store.setdefault("active_var", None)
        self._store.setdefault("processed_image", None)

    # -- backing state -----------------------------------------------------
    @property
    def store(self):
        return self._store

    @property
    def vars(self) -> dict:
        """All named workspace variables, images or not."""
        return self._store["workspace_vars"]

    @property
    def image_cache(self) -> dict:
        return self._store["image_cache"]

    @property
    def session_commands(self) -> str:
        return self._store["session_commands"]

    @property
    def active_var(self):
        return self._store["active_var"]

    @property
    def processed_image(self):
        return self._store["processed_image"]

    @property
    def image_types(self) -> tuple:
        """The unpatched VxlImg classes, for isinstance checks."""
        found = (self._store.get(key) for key in self.IMAGE_TYPE_KEYS)
        return tuple(cls for cls in found if cls is not None)

    # -- queries -----------------------------------------------------------
    def get(self, name, default=None):
        return self.vars.get(name, default)

    def vars_of_type(self, types) -> list:
        """Names of workspace variables matching `types`, in insertion order.

        Used for meshes (pyvista) as well as images, hence the generic form.
        """
        if not types:
            return []
        return [k for k, v in self.vars.items() if isinstance(v, types)]

    def image_vars(self) -> list:
        """Names of workspace variables that are images."""
        return self.vars_of_type(self.image_types)

    def unique_name(self, base: str) -> str:
        """`base` if free, else the first free `base_1`, `base_2`, ... ."""
        if base not in self.vars:
            return base
        suffix = 1
        while f"{base}_{suffix}" in self.vars:
            suffix += 1
        return f"{base}_{suffix}"

    # -- mutations ---------------------------------------------------------
    def set_active(self, name):
        """Make `name` the viewed variable. Unknown names are ignored."""
        if name not in self.vars:
            return
        self._store["active_var"] = name
        self._store["processed_image"] = self.vars[name]

    def store_var(self, name, value):
        """Store any value under `name` without touching the active variable."""
        self.vars[name] = value

    def store_image(self, name, img, make_active=True):
        """Store an image and, by default, make it the viewed variable."""
        self.vars[name] = img
        if make_active:
            self._store["active_var"] = name
            self._store["processed_image"] = img
        return name

    def record_command(self, command_line: str):
        """Append to the session's generated-code history."""
        if not command_line:
            return
        existing = self._store["session_commands"]
        self._store["session_commands"] = (
            f"{existing}\n\n{command_line}" if existing else command_line
        )

    def absorb_namespace(self, namespace) -> list:
        """Pull every image variable out of an executed script's namespace.

        Returns the names absorbed. Mirrors the previous update_workspace_vars:
        a variable literally named "img", or any image seen while nothing is
        being viewed yet, becomes the active variable.
        """
        types = self.image_types
        if not types:
            return []
        absorbed = []
        for name, value in namespace.items():
            if not isinstance(value, types):
                continue
            self.vars[name] = value
            absorbed.append(name)
            if name == "img" or self.processed_image is None:
                self._store["active_var"] = name
                self._store["processed_image"] = value
        return absorbed
