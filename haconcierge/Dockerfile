ARG BUILD_FROM
FROM ${BUILD_FROM}

# Install system dependencies
RUN apk add --no-cache \
    nodejs \
    npm \
    supervisor \
    gcc \
    musl-dev \
    libffi-dev \
    openssl-dev \
    cargo \
    chromium-chromedriver

# Set working directory
WORKDIR /app

# Install Python dependencies
COPY rootfs/app/backend/requirements.txt /app/requirements.txt
RUN pip3 install --no-cache-dir -r requirements.txt

# Install Node.js WhatsApp bridge dependencies
COPY rootfs/app/whatsapp-bridge/package.json /app/whatsapp-bridge/package.json
COPY rootfs/app/whatsapp-bridge/package-lock.json* /app/whatsapp-bridge/package-lock.json
WORKDIR /app/whatsapp-bridge
RUN npm ci --omit=dev
WORKDIR /app

# Copy application files
COPY rootfs/ /

# Create data directory symlinks
RUN mkdir -p /config/haconcierge/sessions \
    && mkdir -p /config/haconcierge/data \
    && mkdir -p /tmp/haconcierge

# Set permissions
RUN chmod +x /app/run.sh

EXPOSE 8099

CMD ["/app/run.sh"]
