import time
import sys
import socket
import select
import ujson

import server
import serial_cli
import hardware
import logging_util

def load_settings():
    try:
        with open('udp.json') as f:
            data = ujson.load(f)
            logging_util.setup_udp(data['ip'], data['port'])
    except:
        pass

    try:
        with open('wifi.json') as f:
            creds = ujson.load(f)
            if hardware.connect_wifi(creds['ssid'], creds['password']):
                logging_util.log("Home wifi connected")
                logging_util.log(hardware.sync_time())
            else:
                hardware.start_ap()
    except:
        hardware.start_ap()

def main_loop():
    s = socket.socket()
    s.bind(('0.0.0.0', 8080))
    s.listen(1)
    s.settimeout(0.1)

    logging_util.log("HTTP server running on 8080...")
    logging_util.log("Serial CLI ready (type 'help')")

    while True:
        try:
            cl, addr = s.accept()
            server.handle_client(cl)
        except OSError:
            pass

        serial_cli.handle_serial()
        hardware.check_relay_timer()

logging_util.log("Booting device...")
time.sleep(1)
load_settings()
main_loop()
