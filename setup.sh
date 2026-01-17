sudo apt update
sudo apt install -y \
  python3-gi \
  gir1.2-gstreamer-1.0 \
  gir1.2-gst-plugins-base-1.0 \
  gstreamer1.0-tools \
  gstreamer1.0-plugins-base \
  gstreamer1.0-plugins-good \
  gstreamer1.0-plugins-bad \
  gstreamer1.0-plugins-ugly \
  gstreamer1.0-libav


#!/usr/bin/env bash
set -euo pipefail

# ---- EDIT THESE ----
USER_NAME="${SUDO_USER:-pi}"
PY_SCRIPT="/home/${USER_NAME}/loop_audio_match.py"
AUDIO_FILE="/home/${USER_NAME}/loop.flac"
SERVICE_NAME="audioloop"
# --------------------

if [[ $EUID -ne 0 ]]; then
  echo "Run as root: sudo ./install_loop_service.sh"
  exit 1
fi

if [[ ! -f "$PY_SCRIPT" ]]; then
  echo "Python script not found: $PY_SCRIPT"
  exit 1
fi

if [[ ! -f "$AUDIO_FILE" ]]; then
  echo "Audio file not found: $AUDIO_FILE"
  exit 1
fi

PYTHON_BIN="$(command -v python3)"
if [[ -z "$PYTHON_BIN" ]]; then
  echo "python3 not found"
  exit 1
fi

SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"

cat > "$SERVICE_FILE" <<EOF
[Unit]
Description=Loop audio on boot (GStreamer playbin gapless loop)
After=sound.target network.target
Wants=sound.target

[Service]
Type=simple
User=${USER_NAME}
WorkingDirectory=/home/${USER_NAME}
ExecStart=${PYTHON_BIN} ${PY_SCRIPT} ${AUDIO_FILE}
Restart=always
RestartSec=2

# Helps when launching audio services at boot
Environment=XDG_RUNTIME_DIR=/run/user/%U

# If your pi is headless and you SSH in, log output here:
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

chmod 644 "$SERVICE_FILE"

systemctl daemon-reload
systemctl enable "${SERVICE_NAME}.service"
systemctl restart "${SERVICE_NAME}.service"

echo "Installed and started: ${SERVICE_NAME}.service"
echo "Check status:  systemctl status ${SERVICE_NAME}.service -n 50"
echo "View logs:     journalctl -u ${SERVICE_NAME}.service -f"
