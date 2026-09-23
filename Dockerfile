FROM python:3.14-trixie

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    ninja-build \
    git \
    libgl1 \
    libglx0 \
    libglib2.0-0 \
    libgomp1 \
    libegl1 \
    zlib1g-dev \
    libtiff-dev \
    libopenmpi-dev \
    libboost-iostreams-dev \
    libboost-graph-dev \
    libfmt-dev \
    nlohmann-json3-dev \
    libblas-dev \
    liblapack-dev \
    && rm -rf /var/lib/apt/lists/*

ENV PIP_ROOT_USER_ACTION=ignore

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir numpy scikit-build-core pybind11

WORKDIR /app


# Cache step, keep in sync with pyproject.toml
RUN pip install --no-cache-dir \
    streamlit \
    streamlit_code_editor \
    Pillow \
    vtk \
    cmake \
    pyvista[jupyter] \
    stpyvista \
    scipy \
    sqlalchemy \
    imageio \
    imageio-ffmpeg \
    pytest \
    playwright


# Second least-frequently-changed file, for cache-friendliness
COPY pyproject.toml /app/pyproject.toml
RUN mkdir -p porgui && touch porgui/__init__.py && \
    pip install --no-cache-dir -e ".[dev]"

# Edit pyproject.toml to force an update of XPM
RUN pip install --no-cache-dir git+https://github.com/difizix/xpm.git

# NB! SNM is injected/updated via `make injectSnm`, which works when the container is started.

# NB! /app is bind-mounted, so this is not used, see below
COPY porgui /app/porgui

EXPOSE 8501

CMD ["streamlit", "run", "porgui/app.py", "--server.port=8501", "--browser.gatherUsageStats=false"]

# , "--server.fileWatcherType=none"

# This image is not self-contained: app code (porgui/, tests/, etc.) is not
# baked in and must be supplied via a bind mount at run time, e.g.:
# podman build -t porsmgui -f Dockerfile .
# podman run -v $PWD:/app:z -p 8501:8501 --rm --name porsmgui porsmgui
