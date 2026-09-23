help:
	@echo "Available targets:"
	@echo "  build-snm      - Compile snm executables (skelor, scalor, cnflow)"
	@echo "  build-xpm      - Compile xpm executable"
	@echo "  install-snm    - Install snm executables to Python/active environment prefix"
	@echo "  install-xpm    - Install xpm executable to Python/active environment prefix"
	@echo "  clean-snm      - Remove snm build directory"
	@echo "  clean-xpm      - Remove xpm build directory"
	@echo "  restartPodman  - Rebuild and restart the container"
	@echo "  runPodman      - Build and run container using Podman or Docker"

.PHONY: build-snm build-xpm install-snm install-xpm clean-snm clean-xpm runPodman runDocker runContainer restartPodman injectSnm test help

PODMAN ?= $(shell command -v podman 2>/dev/null || command -v docker 2>/dev/null || echo podman)

VENV_DIR := $(shell \
	if [ -d .venv ]; then echo .venv; \
	elif [ -d ../.venv ]; then echo ../.venv; \
	else echo $$HOME/miniconda3; fi)


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
	cmake --install snm/build --prefix `${PYTHON} -c "import sys; print(sys.prefix)"`

install-xpm: build-xpm
	cmake --install xpm/build --prefix `${PYTHON} -c "import sys; print(sys.prefix)"`

clean-snm:
	rm -rf snm/build

clean-xpm:
	rm -rf xpm/build

test:
	${PYTHON} -m pytest 
	
runPodman:
	${PODMAN} build -t porsmgui -f Dockerfile .
	${PODMAN} run -v $$PWD:/app:z -p 8501:8501 --rm --name porsmgui porsmgui

runDocker: runPodman
runContainer: runPodman
restartPodman: runPodman

injectSnm:
	@echo Compiling and injecting snm into porsmgui container, contact for access.
	( [ -d snm ] || git clone git@github.com:difizix/snm.git )
	( [ -d image3kit ] || git clone git@github.com:difizix/image3kit.git )
	${PODMAN} exec -t porsmgui bash -c "\
	cmake -S /app/snm -B /app/snm/build -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=/usr/local && \
	cmake --build /app/snm/build -j 4 && \
	cmake --install /app/snm/build"
