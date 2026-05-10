ARG BUILD_FROM=python:3.12-alpine
FROM ${BUILD_FROM}

# System dependencies – no browser needed, Baileys is pure Node.js
RUN apk add --no-cache \
    nodejs \
    npm \
    git \
    supervisor \
    gcc \
    musl-dev \
    libffi-dev \
    openssl-dev \
    bash

WORKDIR /app

# Python dependencies (pydantic-core has musllinux wheels for Python 3.12)
COPY rootfs/app/backend/requirements.txt /app/requirements.txt
RUN pip3 install --no-cache-dir -r requirements.txt

# Node.js WhatsApp bridge
COPY rootfs/app/whatsapp-bridge/package.json /app/whatsapp-bridge/package.json
WORKDIR /app/whatsapp-bridge
RUN npm install --omit=dev --legacy-peer-deps
WORKDIR /app

# Copy all application files into container filesystem
COPY rootfs/ /

RUN mkdir -p /tmp/haconcierge \
    && chmod +x /app/run.sh

EXPOSE 8099

CMD ["/app/run.sh"]
