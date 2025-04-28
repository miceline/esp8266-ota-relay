# Makefile

# Configuration
DEVICE_IP ?= 192.168.20.32
DEVICE_PORT ?= 8080
FILE ?= main.py
UDP_SERVER_IP ?= 192.168.20.50
UDP_SERVER_PORT ?= 12345

# Target to upload the Python file
upload:
	@echo "Uploading all .py files to ESP at $(DEVICE_IP)..."
	@for file in *.py; do \
		echo "Uploading $$file..."; \
		checksum=$$(sha1sum $$file | awk '{print $$1}'); \
		curl --progress-bar --max-time 10 -X POST --data-binary "@$$file" "http://$(DEVICE_IP):$(DEVICE_PORT)/upload?filename=$$file&checksum=$$checksum"; \
	done
	@echo "✅ All files uploaded! ESP will reboot."
	@$(MAKE) reboot_device
	@sleep 3
	@echo "Waiting for ESP to reboot..."
	@while ! ping -c 1 $(DEVICE_IP) > /dev/null 2>&1; do \
		echo "Waiting for ESP to reboot..."; \
		sleep 1; \
	done
	@echo "ESP is back online!"

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
	curl -X POST -d "on:10" http://$(DEVICE_IP):$(DEVICE_PORT)/relay
	@echo "✅ Relay ON command sent!"

relay_off:
	curl -X POST -d "off" http://$(DEVICE_IP):$(DEVICE_PORT)/relay
	@echo "✅ Relay OFF command sent!"

reboot_device:
	curl -X GET http://$(DEVICE_IP):$(DEVICE_PORT)/reboot
	@echo "✅ Reboot command sent!"
	