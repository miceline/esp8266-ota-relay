#!/bin/bash

# --- Configuration ---
ESP_IP="192.168.4.1"       # Default IP address of ESP Access Point
ESP_PORT="8080"            # Port of HTTP server

# --- Check arguments ---
if [ "$#" -ne 2 ]; then
  echo "Usage: $0 <SSID> <Password>"
  exit 1
fi

SSID="$1"
PASSWORD="$2"

# --- Prepare JSON payload ---
JSON_PAYLOAD="{\"ssid\":\"${SSID}\", \"password\":\"${PASSWORD}\"}"

# --- Send WiFi credentials to ESP8266 ---
echo "Sending WiFi credentials to ESP at ${ESP_IP}:${ESP_PORT}..."
curl --connect-timeout 5 --max-time 10 --retry 3 --retry-delay 2 \
  -X POST -H "Content-Type: application/json" \
  -d "${JSON_PAYLOAD}" \
  http://${ESP_IP}:${ESP_PORT}/setup_wifi

if [ $? -eq 0 ]; then
  echo "✅ WiFi credentials sent successfully!"
  echo "🔄 ESP should reboot and connect to your WiFi."
else
  echo "❌ Failed to send WiFi credentials."
fi
