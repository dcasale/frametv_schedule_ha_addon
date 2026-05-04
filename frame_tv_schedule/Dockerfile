ARG BUILD_FROM=ghcr.io/home-assistant/base:latest
FROM $BUILD_FROM

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

RUN apk add --no-cache font-dejavu python3 py3-pip py3-pillow

WORKDIR /app

COPY requirements.txt /app/
RUN python3 -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir --upgrade pip \
    && /opt/venv/bin/pip install --no-cache-dir -r /app/requirements.txt

COPY app /app/app
COPY run.sh /
RUN chmod a+x /run.sh

ENV PATH="/opt/venv/bin:${PATH}"
CMD ["/run.sh"]
