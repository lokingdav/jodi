FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && \
    apt-get install -y libssl-dev libgmp-dev libmpfr-dev libmpc-dev libsodium-dev libopenblas-dev libomp-dev && \
    apt-get autoremove -y && apt-get clean

COPY . .

RUN pip install --no-cache-dir -r requirements.txt

RUN pip install -e .

