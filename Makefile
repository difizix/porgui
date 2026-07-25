help:
	@echo "Available targets:"
	@echo "  build-snm      - Compile snm executables (skelor, scalor, cnflow)"
	@echo "  build-xpm      - Compile xpm executable"
	@echo "  install-snm    - Install snm executables to Python/active environment prefix"
	@echo "  install-xpm    - Install xpm executable to Python/active environment prefix"
	@echo "  clean-snm      - Remove snm build directory"
	@echo "  clean-xpm      - Remove xpm build directory"
	@echo "  restartPodman  - Rebuild and restart the Podman container"

.PHONY: build-snm build-xpm install-snm install-xpm clean-snm clean-xpm restartPodman

VENV_DIR := $(shell \
	if [ -d .venv ]; then echo .venv; \
	elif [ -d ../.venv ]; then echo ../.venv; \
	else echo $$HOME/miniforge3; fi)


VENV_BIN := $(VENV_DIR)/bin
PYTHON   := $(VENV_BIN)/python
PIP      := $(VENV_BIN)/pip

build-snm:
	cmake -S snm -B snm/build -DCMAKE_BUILD_TYPE=Release
	cmake --build snm/build -j4

build-xpm:
	cmake -S xpm -B xpm/build -DCMAKE_BUILD_TYPE=Release
	cmake --build xpm/build -j4

install-snm: build-snm
	cmake --install snm/build --prefix $$(${PYTHON} -c "import sys; print(sys.prefix)")

install-xpm: build-xpm
	cmake --install xpm/build --prefix $$(${PYTHON} -c "import sys; print(sys.prefix)")

clean-snm:
	rm -rf snm/build

clean-xpm:
	rm -rf xpm/build

test:
	${PYTHON} -m pytest 
	
restartPodman:
	cd ../pods/compose && podman-compose build porsmgui
	podman rm -f porsmgui || true
	cd ../pods/compose && podman-compose up -d porsmgui
	cd ../pods/compose && podman-compose up -d --force-recreate pingapsrvr
	podman ps -a
