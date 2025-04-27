# Makefile

# Configuration
DEVICE_IP ?= 192.168.20.32
DEVICE_PORT ?= 8080
FILE ?= main.py

# Target to upload the Python file
upload:
	curl --progress-bar --output /dev/null -X POST --data-binary "@$(FILE)" http://$(DEVICE_IP):$(DEVICE_PORT)/upload

log:
	@echo "Listening for logs on UDP port 12345..."
	nc -u -l 12345
	@echo "Press Ctrl+C to stop listening."
	