#!/bin/bash
# Install USB automount on the host (run once)
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Copy mount script
sudo cp "$SCRIPT_DIR/usb-mount.sh" /usr/local/bin/usb-mount.sh
sudo chmod +x /usr/local/bin/usb-mount.sh

# Copy udev rule
sudo cp "$SCRIPT_DIR/99-usb-automount.rules" /etc/udev/rules.d/

# Reload udev
sudo udevadm control --reload-rules
sudo udevadm trigger

echo "USB automount installed. Plug in a USB drive to test."
