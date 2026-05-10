ARG BUILD_FROM
FROM ${BUILD_FROM}

# Install system dependencies (no chromium needed - Baileys uses no browser)
RUN apk add --no-cache \
    nodejs \
    npm \
    supervisor \
    gcc \
    musl-dev \
    libffi-dev \
    openssl-dev

# Set working directory
WORKDIR /app

# Install Python dependencies
COPY rootfs/app/backend/requirements.txt /app/requirements.txt
RUN pip3 install --no-cache-dir -r requirements.txt

# Install Node.js WhatsApp bridge dependencies
# Use npm install (not npm ci) since no lockfile in repo
COPY rootfs/app/whatsapp-bridge/package.json /app/whatsapp-bridge/package.json
WORKDIR /app/whatsapp-bridge
RUN npm install --omit=dev --legacy-peer-deps
WORKDIR /app

# Copy all application files
COPY rootfs/ /

# Create persistent data directories (will be mounted from /config)
RUN mkdir -p /tmp/haconcierge

# Executable permissions
RUN chmod +x /app/run.sh

EXPOSE 8099

CMD ["/app/run.sh"]
