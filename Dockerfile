FROM python:3.8-slim

WORKDIR /app

RUN apt-get update && \
    apt-get install -y libssl-dev libgmp-dev libmpfr-dev libmpc-dev libsodium-dev libcurl4-openssl-dev libopenblas-dev libomp-dev && \
    apt-get autoremove -y && apt-get clean

RUN git clone https://github.com/lokingdav/libcpex.git && \
    cd libcpex && \
    pip install build && \
    python -m build && \
    pip install dist/*.whl \
    cd .. && \
    rm -rf libcpex

COPY . .

RUN pip install --no-cache-dir -r requirements.txt

RUN pip install -e .

