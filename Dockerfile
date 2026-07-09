FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
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
    && rm -rf /var/lib/apt/lists/*

ENV PIP_ROOT_USER_ACTION=ignore

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir numpy scikit-build-core pybind11

WORKDIR /app

# Cache step, just in case requirements.txt is changed
RUN pip install --no-cache-dir \
    vtk \
    streamlit \
    streamlit_code_editor \
    Pillow \
    pytest \
    scipy \
    sqlalchemy \
    imageio \
    imageio-ffmpeg \
    pyvista[jupyter] \
    stpyvista


# To be removed once pnmkit is stable
# RUN git clone https://github.com/difizix/pnmkit.git pnmkit
COPY pnmkit /app/pnmkit
RUN pip install --no-cache-dir ./pnmkit/image3kit --config-settings=cmake.build-type=Release
RUN pip install --no-cache-dir ./pnmkit --config-settings=cmake.build-type=Release

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# To be removed once pyvtk is stable
# RUN git clone https://github.com/difizix/pyvtk.git pyvtk
COPY pyvtk /app/pyvtk
RUN pip install --no-cache-dir ./pyvtk --config-settings=cmake.build-type=Release

COPY . /app

EXPOSE 8501

CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0", "--browser.gatherUsageStats=false"]

# , "--server.fileWatcherType=none"

# podman build -t img3_ui  -f Dockerfile .