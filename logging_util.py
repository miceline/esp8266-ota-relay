import socket
import time

log_socket = None
udp_ip = None
udp_port = None
TIMEZONE_OFFSET_HOURS = -4  # Aruba

def setup_udp(ip, port):
    global log_socket, udp_ip, udp_port
    udp_ip = ip
    udp_port = int(port)
    log_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

def current_timestamp():
    try:
        now = time.time() + TIMEZONE_OFFSET_HOURS * 3600
        tm = time.localtime(now)
        return "%04d-%02d-%02d %02d:%02d:%02d" % (tm[0], tm[1], tm[2], tm[3], tm[4], tm[5])
    except:
        return "0000-00-00 00:00:00"  # fallback if time not set

def log(message):
    try:
        timestamp = current_timestamp()
        full_message = f"[{timestamp}] {message}"
        if log_socket and udp_ip and udp_port:
            log_socket.sendto((full_message + '\n').encode('utf-8'), (udp_ip, udp_port))
        else:
            print(full_message)
    except:
        print(message)
