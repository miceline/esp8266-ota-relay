import sys
import select
import os
import machine
import logging_util

def handle_serial():
    if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
        cmd = sys.stdin.readline().strip().lower()
        if cmd == "clear wifi":
            try:
                os.remove('wifi.json')
                logging_util.log("WiFi settings cleared. Rebooting...")
                machine.reset()
            except:
                logging_util.log("Failed to clear WiFi settings.")
        elif cmd == "clear udp_log":
            try:
                os.remove('udp.json')
                logging_util.log("UDP settings cleared. Rebooting...")
                machine.reset()
            except:
                logging_util.log("Failed to clear UDP settings.")
        elif cmd == "help":
            logging_util.log("Available commands: clear wifi | clear udp_log | help")
        else:
            logging_util.log("Unknown command. Type 'help'.")
