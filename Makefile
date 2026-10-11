help:
	@echo "Available targets:"
	@echo "  installSnm, installXpm, installXpmPip - build and install snm/xpm here (porgui/deps.mk)"
	@echo "  injectSnm, injectXpm, injectXpmPip    - the same, inside the running porsmgui container"
	@echo "  runPodman      - Build and run the container using Podman or Docker"
	@echo "  testXpmInPod   - Run xpm regression tests inside the container"
	@echo "  update_screenshots - Retake docs/img/*.png from a running porgui (SHOT_URL)"

.PHONY: update_screenshots runPodman runDocker runContainer restartPodman injectSnm injectXpm injectXpmPip testXpmInPod test help

PODMAN ?= $(shell command -v docker 2>/dev/null || command -v podman 2>/dev/null || echo docker)

VENV_DIR := $(shell \
	if [ -d .venv ]; then echo .venv; \
	elif [ -d ../.venv ]; then echo ../.venv; \
	else echo $$HOME/miniconda3; fi)


VENV_BIN := $(VENV_DIR)/bin
PYTHON   := $(VENV_BIN)/python
PIP      := $(VENV_BIN)/pip

include porgui/deps.mk

run-local:
	python -m streamlit run porgui/app.py

# README screenshots; start porgui first (host or container). CHROME=/usr/bin/google-chrome skips `playwright install chromium`
SHOT_URL = http://localhost:8501
CHROME =
update_screenshots: runs/pakextr/extruded_ms.xmf
	${PYTHON} tests/make_screenshots.py $(SHOT_URL) $(if $(CHROME),--chrome $(CHROME))

runs/pakextr/extruded_ms.xmf:  # the screenshots' data (needs snm: make installSnm)
	cd runs && ${PYTHON} pnm_from_extrude.py

test:
	${PYTHON} -m pytest 
	
runPodman:
	${PODMAN} build -t porsmgui -f Dockerfile .
	${PODMAN} run -v $$PWD:/app:z -p 8501:8501 --rm --name porsmgui porsmgui

runDocker: runPodman
runContainer: runPodman
restartPodman: runPodman

# snm/xpm are cloned inside the container unless ./snm, ./xpm are bind-mounted; pass a public SNM_GIT/XPM_GIT if needed
DEPS_VARS = SNM_GIT=$(SNM_GIT) XPM_GIT=$(XPM_GIT) SNM_REF=$(SNM_REF) XPM_REF=$(XPM_REF) JOBS=$(JOBS)

injectSnm:  # installSnm inside the porsmgui container
	${PODMAN} exec -t porsmgui make -f porgui/deps.mk installSnm $(DEPS_VARS)

injectXpm:  # installXpm inside the porsmgui container
	${PODMAN} exec -t porsmgui make -f porgui/deps.mk installXpm $(DEPS_VARS)

injectXpmPip:  # installXpmPip inside the porsmgui container
	${PODMAN} exec -t porsmgui make -f porgui/deps.mk installXpmPip $(DEPS_VARS)

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

