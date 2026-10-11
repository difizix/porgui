# Optional native dependencies (snm, xpm), built and installed wherever make runs: a host venv or
# the porgui container. Included by the top-level Makefile; the GUI Make page runs it as
# `make -f porgui/deps.mk <target>` when the workspace has no Makefile (infra/compose).
# Override any ?= variable, e.g. a public mirror: `make installSnm SNM_GIT=https://.../snm.git`.

PYTHON ?= python3
SNM_GIT ?= git@github.com:difizix/snm.git
XPM_GIT ?= git@github.com:difizix/xpm-core.git
SNM_REF ?=
XPM_REF ?=
SNM_DIR ?= snm
XPM_DIR ?= xpm
DEPS_PREFIX ?= $(shell $(PYTHON) -c "import sys; print(sys.prefix)")
JOBS ?= 4

.PHONY: installSnm installXpm installXpmPip cleanSnm cleanXpm

$(SNM_DIR):
	git clone $(if $(SNM_REF),--branch $(SNM_REF)) $(SNM_GIT) $(SNM_DIR)

$(XPM_DIR):
	git clone $(if $(XPM_REF),--branch $(XPM_REF)) $(XPM_GIT) $(XPM_DIR)

installSnm: $(SNM_DIR)  # build skelor, scalor, cnflow and install them to DEPS_PREFIX/bin
	cmake -S $(SNM_DIR) -B $(SNM_DIR)/build -DCMAKE_BUILD_TYPE=Release
	cmake --build $(SNM_DIR)/build -j $(JOBS)
	cmake --install $(SNM_DIR)/build --prefix $(DEPS_PREFIX)

installXpm: $(XPM_DIR)  # build xpm and pnextract (headless) and install them to DEPS_PREFIX/bin
	cmake -S $(XPM_DIR) -B $(XPM_DIR)/build -DCMAKE_BUILD_TYPE=Release -DXPM_HEADLESS=ON
	cmake --build $(XPM_DIR)/build -j $(JOBS) --target xpm pnextract
	install -m 755 $(XPM_DIR)/build/bin/xpm $(XPM_DIR)/build/bin/pnextract/pnextract $(DEPS_PREFIX)/bin/

installXpmPip: $(XPM_DIR)  # pip-install xpm (headless) into the active Python
	CMAKE_BUILD_PARALLEL_LEVEL=$(JOBS) $(PYTHON) -m pip install ./$(XPM_DIR) --config-settings=cmake.define.XPM_HEADLESS=ON

cleanSnm:  # remove the snm build directory
	rm -rf $(SNM_DIR)/build

cleanXpm:  # remove the xpm build directory
	rm -rf $(XPM_DIR)/build
