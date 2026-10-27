# runoregi (dhh26) reading parquet files with DuckDB (no MariaDB)
# Build with: docker build -t dhh26-runoregi .

FROM python:3.11-slim

RUN apt-get update && apt-get -y --no-install-recommends install \
    git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/runoregi
# OpenShift runs as a random UID without a home directory; gunicorn needs a
# writable $HOME for its control socket.
ENV HOME=/tmp
# Parquet location: URL (default: the FILTER data on Allas) or a mounted directory
ENV PARQUET_BASE=https://a3s.fi/filter-data/
ENV DUCKDB_EXTENSION_DIRECTORY=/opt/duckdb_extensions

WORKDIR /app
COPY requirements.txt /app/runoregi/requirements.txt
RUN pip install --no-cache-dir -r /app/runoregi/requirements.txt

# Preinstall httpfs so the container doesn't download it at runtime
RUN python -c "import duckdb; c = duckdb.connect(); \
c.execute(\"SET extension_directory = '$DUCKDB_EXTENSION_DIRECTORY'\"); \
c.execute('INSTALL httpfs')" \
    && chmod -R a+rX $DUCKDB_EXTENSION_DIRECTORY

COPY fetch_parquet.py /app/fetch_parquet.py
COPY . /app/runoregi/

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["gunicorn", "--config", "runoregi/gunicorn.conf.py", "runoregi.wsgi:application", "--bind", "0.0.0.0:8000"]
