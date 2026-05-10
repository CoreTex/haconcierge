#!/bin/bash
# HAConcierge startup script – no bashio dependency

export LOG_LEVEL="${LOG_LEVEL:-info}"
export HA_TOKEN="${SUPERVISOR_TOKEN:-}"
export HA_URL="http://supervisor/core"
export DATA_DIR="/config/haconcierge"
export SESSION_DIR="/config/haconcierge/sessions"

mkdir -p "${DATA_DIR}" "${SESSION_DIR}"

# Auto-install custom integration into HA config
INTEGRATION_SRC="/app/custom_components/haconcierge"
INTEGRATION_DST="/config/custom_components/haconcierge"
if [ -d "${INTEGRATION_SRC}" ]; then
    mkdir -p "/config/custom_components"
    if ! diff -rq "${INTEGRATION_SRC}" "${INTEGRATION_DST}" > /dev/null 2>&1; then
        echo "[HAConcierge] Installing/updating custom integration..."
        cp -rf "${INTEGRATION_SRC}" "/config/custom_components/"
        echo "[HAConcierge] Integration installed – restart HA once if this is first install."
    fi
fi

echo "[HAConcierge] Starting services (log level: ${LOG_LEVEL})..."
exec supervisord -c /etc/supervisord.conf
