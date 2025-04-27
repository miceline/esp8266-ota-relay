# Makefile

# Configuration
DEVICE_IP ?= 192.168.20.32
DEVICE_PORT ?= 8080
FILE ?= main.py
UDP_SERVER_IP ?= 192.168.20.50
UDP_SERVER_PORT ?= 12345

# Target to upload the Python file
upload:
	curl --progress-bar --output /dev/null -X POST --data-binary "@$(FILE)" http://$(DEVICE_IP):$(DEVICE_PORT)/upload

log:
	@echo "Listening for logs on UDP port 12345..."
	nc -u -l 12345
	@echo "Press Ctrl+C to stop listening."

setup_udp:
	@echo "Setting up UDP log destination to $(UDP_SERVER_IP):$(UDP_SERVER_PORT)..."
	curl -X POST -H "Content-Type: application/json" \
		-d '{"ip":"$(UDP_SERVER_IP)", "port":$(UDP_SERVER_PORT)}' \
		http://$(DEVICE_IP):$(DEVICE_PORT)/setup_udp
	@echo "✅ UDP setup sent!"

relay_on:
	curl -X POST -d "on" http://$(DEVICE_IP):$(DEVICE_PORT)/relay
	@echo "✅ Relay ON command sent!"

relay_off:
	curl -X POST -d "off" http://$(DEVICE_IP):$(DEVICE_PORT)/relay
	@echo "✅ Relay OFF command sent!"

reboot_device:
	curl -X GET http://$(DEVICE_IP):$(DEVICE_PORT)/reboot
	@echo "✅ Reboot command sent!"
	