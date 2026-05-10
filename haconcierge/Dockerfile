ARG BUILD_FROM=ghcr.io/home-assistant/aarch64-base-python:latest
FROM ${BUILD_FROM}

# Install system dependencies
RUN apk add --no-cache \
    nodejs \
    npm \
    supervisor \
    gcc \
    musl-dev \
    libffi-dev \
    openssl-dev

WORKDIR /app

# Install Python dependencies
COPY rootfs/app/backend/requirements.txt /app/requirements.txt
RUN pip3 install --no-cache-dir -r requirements.txt

# Install Node.js WhatsApp bridge
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
