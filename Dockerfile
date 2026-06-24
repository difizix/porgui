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

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir numpy scikit-build-core pybind11

WORKDIR /app

COPY pnmkit /app/pnmkit
# Install image3kit first (from pnmkit submodule), then pnmkit itself
RUN pip install --no-cache-dir ./pnmkit/image3kit --config-settings=cmake.build-type=Release
RUN pip install --no-cache-dir ./pnmkit --config-settings=cmake.build-type=Release



RUN pip install --no-cache-dir \
    vtk \
    streamlit \
    streamlit_code_editor \
    Pillow

COPY . /app

EXPOSE 8501

CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0", "--browser.gatherUsageStats=false"]

# , "--server.fileWatcherType=none"

# podman build -t img3_ui  -f Dockerfile .