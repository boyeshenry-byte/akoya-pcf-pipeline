FROM nvidia/cuda:12.8.0-cudnn-runtime-ubuntu22.04

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y \
    python3.11 \
    python3.11-dev \
    python3-pip \
    libgl1 \
    libglib2.0-0 \
    git \
    && rm -rf /var/lib/apt/lists/*  \
    && update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1 \
    && pip3 install --upgrade pip

WORKDIR  /app

COPY requirements.txt .

RUN pip3 install --no-cache-dir -r requirements.txt
#Install squidpy separately to resolve PyPI installation issues
RUN pip3 install --no-cache-dir git+https://github.com/scverse/squidpy.git@v1.8.1

COPY scripts/ ./scripts/
COPY configs/ ./configs/

CMD ["python3", "scripts/ingestion.py", "--help"]