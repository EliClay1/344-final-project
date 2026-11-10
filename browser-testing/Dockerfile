# Runs all the necessary installations for a worker to activate. 
# All of these get pre-installed so the first build on a cold start is going to take much longer.
# Afterwards, all future workers should boot up very quickly.

ARG PW_VERSION=1.58.0
FROM mcr.microsoft.com/playwright/python:v${PW_VERSION}-noble

ARG PW_VERSION

RUN apt-get update \
    && apt-get install -y --no-install-recommends tini \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .

RUN python -m pip install --no-cache-dir \
    "playwright==${PW_VERSION}" \
    -r requirements.txt

COPY worker.py .

ENV PYTHONUNBUFFERED=1

USER pwuser

ENTRYPOINT ["/usr/bin/tini", "--"]

# Once all of the needed pieces are installed, it will now run the worker.
CMD ["python", "worker.py"]
