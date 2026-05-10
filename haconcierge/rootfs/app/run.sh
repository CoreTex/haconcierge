#!/usr/bin/with-contenv bashio

export LOG_LEVEL=$(bashio::config 'log_level')
export HA_TOKEN="${SUPERVISOR_TOKEN}"
export HA_URL="http://supervisor/core"
export DATA_DIR="/config/haconcierge"
export SESSION_DIR="/config/haconcierge/sessions"

# Ensure data directories exist
mkdir -p "${DATA_DIR}"
mkdir -p "${SESSION_DIR}"

# Install/update custom integration into HA
INTEGRATION_SRC="/app/custom_components/haconcierge"

INTEGRATION_DST="/config/custom_components/haconcierge"
if [ -d "${INTEGRATION_SRC}" ]; then
    mkdir -p "/config/custom_components"
    if ! diff -rq "${INTEGRATION_SRC}" "${INTEGRATION_DST}" > /dev/null 2>&1; then
        bashio::log.info "Updating HAConcierge custom integration..."
        cp -rf "${INTEGRATION_SRC}" "/config/custom_components/"
        bashio::log.info "Integration updated – please restart Home Assistant if this is the first install."
    fi
fi

bashio::log.info "Starting HAConcierge..."
exec supervisord -c /etc/supervisord.conf
