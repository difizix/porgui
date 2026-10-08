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
	@echo "  injectSnm      - Compile and inject snm into container"
	@echo "  injectXpm      - Compile and inject xpm into container"
	@echo "  injectXpmPip   - Build and inject xpm via pip into container"
	@echo "  testXpmInPod   - Run xpm regression tests inside container"

.PHONY: build-snm build-xpm install-snm install-xpm clean-snm clean-xpm runPodman runDocker runContainer restartPodman injectSnm injectXpm injectXpmPip testXpmInPod test help

PODMAN ?= $(shell command -v docker 2>/dev/null || command -v podman 2>/dev/null || echo docker)

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

run-local:
	python -m streamlit run porgui/app.py

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

injectXpm:
	@echo Compiling and injecting xpm into porsmgui container, contact for access.
	( [ -d xpm ] || git clone git@github.com:difizix/xpm.git )
	${PODMAN} exec -t porsmgui bash -c "\
		apt-get update ;\
		apt-get install -y \
			cmake ninja-build openmpi-bin libopenmpi-dev \
			libboost-iostreams-dev libboost-graph-dev \
			libfmt-dev nlohmann-json3-dev zlib1g-dev ;\
		cmake -S /app/xpm -B /app/xpm/build -DCMAKE_BUILD_TYPE=Release -DXPM_HEADLESS=ON && \
		cmake --build /app/xpm/build -j 4 --target xpm pnextract && \
		cp /app/xpm/build/bin/xpm /app/xpm/build/bin/pnextract/pnextract /usr/local/bin/"



injectXpmPip:
	@echo Compiling and injecting xpm into porsmgui container, contact for access.
	( [ -d xpm ] || git clone git@github.com:difizix/xpm.git )
	${PODMAN} exec -t porsmgui bash -c "\
		apt-get update ;\
		apt-get install -y \
			cmake ninja-build openmpi-bin libopenmpi-dev \
			libboost-iostreams-dev libboost-graph-dev \
			libfmt-dev nlohmann-json3-dev zlib1g-dev ;\
		CMAKE_BUILD_PARALLEL_LEVEL=4 pip install -e ./xpm --config-settings=cmake.define.XPM_HEADLESS=ON"

testXpmInPod:
	mkdir -p xpm/runs
	${PODMAN} exec -t porsmgui bash -c "\
		pip install image3kit ; \
		export OMPI_ALLOW_RUN_AS_ROOT=1 ;\
		export OMPI_ALLOW_RUN_AS_ROOT_CONFIRM=1 ;\
		export PRTE_ALLOW_RUN_AS_ROOT=1 ;\
		export PRTE_ALLOW_RUN_AS_ROOT_CONFIRM=1 ;\
		export PRTE_MCA_rmaps_default_mapping_policy=:oversubscribe ;\
		export OMPI_MCA_rmaps_base_oversubscribe=true ;\
		cd xpm && pytest --slow --workdir=runs -s  # --update-reference"

